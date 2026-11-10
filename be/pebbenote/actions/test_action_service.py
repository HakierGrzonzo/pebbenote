from datetime import timedelta
from unittest import IsolatedAsyncioTestCase

from pebbenote.config import settings
from pebbenote.db import get_test_db
from pebbenote.instructions.exceptions import InstructionsConflict
from pebbenote.instructions.repository import UserInstructionRepository
from pebbenote.instructions.schemas import InstructionsEditModel
from pebbenote.llm.mock import MockAdapter
from pebbenote.llm.schemas import Chat
from pebbenote.notes.exceptions import NoteConflict
from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import NoteUpdateModel
from pebbenote.tables import ActionStatus, NoteAction, utc_now

from .action_service import NoteActionService
from .prompts import apply_instructions_action_text, apply_instructions_preamble
from .repository import NoteActionRepository
from .schemas import ActionEditModel


class NoteActionServiceTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        user = "A user"
        self.session = await self.enterAsyncContext(get_test_db())
        self.ai = MockAdapter()
        self.ai.set_result("- result")
        self.instructions = UserInstructionRepository(self.session, user)
        self.actions = NoteActionRepository(self.session)
        self.notes = NoteRepository(self.session, user)
        self.service = NoteActionService(
            self.actions,
            self.notes,
            self.instructions,
            self.ai,
        )

    async def enqueue(self, action: str):
        pending, _ = await self.service.enqueue_action(
            ActionEditModel(note_id="default", action=action)
        )
        return pending

    async def run_action(self, action: str):
        pending = await self.enqueue(action)
        note, _ = await self.service.apply_action(pending.note_action_id)
        return note

    async def edit_note(self, content: str):
        """An edit by hand of the default note, based on its latest version"""
        note = await self.notes.get_note_by_id("default")
        return await self.notes.update_note(
            "default", NoteUpdateModel(content=content, base_version=note.version)
        )

    async def set_instructions(self, texts: list[str]):
        """An edit by hand of the instructions, based on their latest version"""
        current = await self.instructions.get_instructions()
        return await self.instructions.replace_instructions(
            InstructionsEditModel(instructions=texts, base_version=current.version)
        )

    async def stored_instructions(self) -> list[str]:
        return (await self.instructions.get_instructions()).instructions

    def called_chat(self) -> Chat:
        chat = self.ai.get_called_with()
        assert isinstance(chat, Chat)
        return chat

    async def test_note_input_is_not_stored(self):
        await self.run_action("add milk")

        self.assertEqual(await self.stored_instructions(), [])
        chat = self.called_chat()
        self.assertEqual(chat.messages[-1].content, "add milk")
        self.assertNotIn("assistant", [m.kind for m in chat.messages])

    async def test_instruction_is_stored_and_applied(self):
        self.ai.input_kind = "instruction"
        self.ai.rewritten_instruction = "I should sort groceries."

        note = await self.run_action("sort groceries")

        self.assertEqual(await self.stored_instructions(), ["I should sort groceries."])
        self.assertEqual(note.content, "- result")
        chat = self.called_chat()
        assistant = [m for m in chat.messages if m.kind == "assistant"]
        self.assertIn("I should sort groceries.", assistant[0].content)
        # The raw utterance is not sent as an edit request
        self.assertNotEqual(chat.messages[-1].kind, "user")

    async def test_stored_instructions_reach_note_edits(self):
        await self.set_instructions(["I should sort groceries."])

        await self.run_action("add milk")

        chat = self.called_chat()
        self.assertTrue(
            any(
                "sort groceries" in m.content
                for m in chat.messages
                if m.kind == "assistant"
            )
        )

    async def test_action_goes_from_pending_to_done(self):
        pending = await self.enqueue("add milk")
        self.assertEqual(pending.status, ActionStatus.pending)

        await self.service.apply_action(pending.note_action_id)

        action = await self.actions.get_action(pending.note_action_id)
        self.assertEqual(action.status, ActionStatus.done)

    async def test_done_action_is_not_applied_twice(self):
        pending = await self.enqueue("add milk")
        await self.service.apply_action(pending.note_action_id)
        self.ai.set_result("- second")

        note, next_action = await self.service.apply_action(pending.note_action_id)

        self.assertEqual(note.content, "- result")
        self.assertIsNone(next_action)

    async def test_done_action_run_again_hands_over_again(self):
        # A retry after starting the next action failed
        first = await self.enqueue("add milk")
        second = await self.enqueue("add eggs")
        await self.service.apply_action(first.note_action_id)

        _, next_action = await self.service.apply_action(first.note_action_id)

        self.assertEqual(next_action, second.note_action_id)

    async def test_failed_completion_writes_nothing(self):
        self.ai.input_kind = "instruction"
        before = await self.notes.get_note_by_id("default")
        pending = await self.enqueue("sort groceries")

        self.ai.set_result(None)  # type: ignore[arg-type]
        savepoint = await self.session.begin_nested()
        with self.assertRaises(Exception):
            await self.service.apply_action(pending.note_action_id)
        await savepoint.rollback()

        self.assertEqual(await self.stored_instructions(), [])
        note = await self.notes.get_note_by_id("default")
        self.assertEqual(note.content, before.content)
        action = await self.actions.get_action(pending.note_action_id)
        self.assertEqual(action.status, ActionStatus.pending)

    async def test_status_change_bumps_action_updated_at(self):
        pending = await self.enqueue("add milk")

        failed = await self.actions.set_status(
            pending.note_action_id, ActionStatus.failed
        )

        self.assertGreater(failed.updated_at, pending.updated_at)

    async def test_manual_delete_is_in_history(self):
        await self.edit_note("- milk\n- eggs")
        await self.edit_note("- milk")

        await self.run_action("revert what I just deleted")

        contents = [m.content for m in self.called_chat().messages if m.kind == "user"]
        self.assertTrue(
            any("I edited the note myself" in c and "-- eggs" in c for c in contents)
        )
        self.assertEqual(contents[-1], "revert what I just deleted")

    async def test_past_action_is_a_user_assistant_pair(self):
        await self.run_action("add milk")
        await self.run_action("add eggs")

        messages = self.called_chat().messages
        index = next(i for i, m in enumerate(messages) if m.content == "add milk")
        self.assertEqual(messages[index].kind, "user")
        self.assertEqual(messages[index + 1].kind, "assistant")
        self.assertIn("+- result", messages[index + 1].content)

    async def test_applied_action_links_revision(self):
        pending = await self.enqueue("add milk")
        await self.service.apply_action(pending.note_action_id)

        revisions = await self.notes.list_revisions("default", 10)

        self.assertEqual(revisions[-1].action, "add milk")
        self.assertEqual(revisions[-1].content, "- result")

    def during_completion(self, change):
        """Makes `change` happen while the LLM is busy, on its first call only"""
        complete = self.ai.get_completion
        changes = iter([change])

        async def completion(chat: Chat) -> str:
            for pending_change in changes:
                await pending_change()
            return await complete(chat)

        self.ai.get_completion = completion  # type: ignore[method-assign]

    async def test_note_edited_while_an_action_runs_conflicts(self):
        pending = await self.enqueue("add milk")
        self.during_completion(lambda: self.edit_note("- mine"))

        with self.assertRaises(NoteConflict):
            await self.service.apply_action(pending.note_action_id)

        # The edit is kept and the action is run again on top of it
        note = await self.notes.get_note_by_id("default")
        self.assertEqual(note.content, "- mine")
        action = await self.actions.get_action(pending.note_action_id)
        self.assertEqual(action.status, ActionStatus.pending)

        note, _ = await self.service.apply_action(pending.note_action_id)

        self.assertEqual(note.content, "- result")
        contents = [m.content for m in self.called_chat().messages if m.kind == "user"]
        self.assertTrue(any("- mine" in content for content in contents))
        revisions = await self.notes.list_revisions("default", 10)
        self.assertEqual([r.content for r in revisions[-2:]], ["- mine", "- result"])

    async def test_instructions_edited_while_an_instruction_is_added_conflict(self):
        self.ai.input_kind = "instruction"
        pending = await self.enqueue("sort groceries")
        before = await self.notes.get_note_by_id("default")
        self.during_completion(lambda: self.set_instructions(["I should whisper."]))

        with self.assertRaises(InstructionsConflict):
            await self.service.apply_action(pending.note_action_id)

        # Nothing was written, the action is run again
        self.assertEqual(await self.notes.get_note_by_id("default"), before)
        self.assertEqual(await self.stored_instructions(), ["I should whisper."])

        await self.service.apply_action(pending.note_action_id)

        self.assertEqual(
            await self.stored_instructions(),
            ["I should whisper.", self.ai.rewritten_instruction],
        )

    async def test_only_the_first_action_of_a_queue_is_started(self):
        first, first_start = await self.service.enqueue_action(
            ActionEditModel(note_id="default", action="add milk")
        )
        second, second_start = await self.service.enqueue_action(
            ActionEditModel(note_id="default", action="add eggs")
        )

        self.assertEqual(first_start, first.note_action_id)
        self.assertIsNone(second_start)
        actions = await self.actions.list_actions(first.note_id)
        self.assertEqual(
            [a.note_action_id for a in actions],
            [first.note_action_id, second.note_action_id],
        )

    async def make_stale(self, action_id):
        action = await self.session.get_one(NoteAction, action_id)
        action.updated_at = utc_now() - timedelta(
            seconds=settings.ACTION_STALE_SECONDS + 1
        )
        await self.session.flush()

    async def test_a_stale_head_is_started_again(self):
        first = await self.enqueue("add milk")
        await self.make_stale(first.note_action_id)

        _, start = await self.service.enqueue_action(
            ActionEditModel(note_id="default", action="add eggs")
        )

        self.assertEqual(start, first.note_action_id)
        # Marked as started, the next enqueue leaves it alone
        _, start = await self.service.enqueue_action(
            ActionEditModel(note_id="default", action="add flour")
        )
        self.assertIsNone(start)

    async def test_the_hand_off_marks_the_next_action_started(self):
        first = await self.enqueue("add milk")
        second = await self.enqueue("add eggs")
        await self.make_stale(second.note_action_id)

        await self.service.apply_action(first.note_action_id)

        _, start = await self.service.enqueue_action(
            ActionEditModel(note_id="default", action="add flour")
        )
        self.assertIsNone(start)

    async def test_applied_action_hands_over_to_the_next(self):
        first = await self.enqueue("add milk")
        second = await self.enqueue("add eggs")
        third = await self.enqueue("add flour")

        _, after_first = await self.service.apply_action(first.note_action_id)
        _, after_second = await self.service.apply_action(second.note_action_id)
        _, after_third = await self.service.apply_action(third.note_action_id)

        self.assertEqual(after_first, second.note_action_id)
        self.assertEqual(after_second, third.note_action_id)
        self.assertIsNone(after_third)
        revisions = await self.notes.list_revisions("default", 10)
        self.assertEqual(
            [r.action for r in revisions[-3:]], ["add milk", "add eggs", "add flour"]
        )

    async def test_failed_action_hands_over_to_the_next(self):
        first = await self.enqueue("add milk")
        second = await self.enqueue("add eggs")

        next_action = await self.service.fail_action(first.note_action_id)

        self.assertEqual(next_action, second.note_action_id)
        action = await self.actions.get_action(first.note_action_id)
        self.assertEqual(action.status, ActionStatus.failed)
        _, start = await self.service.enqueue_action(
            ActionEditModel(note_id="default", action="add flour")
        )
        self.assertIsNone(start)

    async def test_a_new_action_after_a_finished_queue_is_started(self):
        await self.run_action("add milk")

        enqueued, start = await self.service.enqueue_action(
            ActionEditModel(note_id="default", action="add eggs")
        )

        self.assertEqual(start, enqueued.note_action_id)

    async def test_edited_instructions_are_applied(self):
        await self.set_instructions(["I should shout.", "I sort."])
        before = await self.notes.get_note_by_id("default")

        note = await self.service.apply_instructions(before.note_id)

        self.assertEqual(note.content, "- result")
        self.assertEqual(note.version, before.version + 1)
        messages = self.called_chat().messages
        self.assertEqual(messages[-1].content, apply_instructions_preamble)
        self.assertIn("I should shout.", messages[-2].content)
        revisions = await self.notes.list_revisions("default", 10)
        self.assertEqual(revisions[-1].action, apply_instructions_action_text)

    async def test_without_instructions_the_llm_is_not_asked(self):
        before = await self.notes.get_note_by_id("default")

        note = await self.service.apply_instructions(before.note_id)

        self.assertEqual(note, before)
        with self.assertRaises(Exception):
            self.ai.get_called_with()

    async def test_note_following_the_instructions_is_left_alone(self):
        await self.set_instructions(["I should shout."])
        before = await self.notes.get_note_by_id("default")
        self.ai.set_result(f"{before.content}\n")

        note = await self.service.apply_instructions(before.note_id)

        self.assertEqual(note, before)
        self.assertEqual(await self.actions.list_actions(before.note_id), [])
        self.assertEqual(len(await self.notes.list_revisions("default", 10)), 1)

    async def test_instructions_edited_during_completion_conflict(self):
        await self.set_instructions(["I should shout."])
        before = await self.notes.get_note_by_id("default")
        self.during_completion(lambda: self.set_instructions(["I should whisper."]))

        with self.assertRaises(InstructionsConflict):
            await self.service.apply_instructions(before.note_id)

        # Nothing was written, the job is run again with the new instructions
        self.assertEqual(await self.notes.get_note_by_id("default"), before)
        self.assertEqual(await self.actions.list_actions(before.note_id), [])

        note = await self.service.apply_instructions(before.note_id)

        self.assertEqual(note.content, "- result")
        self.assertIn("I should whisper.", self.called_chat().messages[-2].content)

    async def test_note_edited_during_completion_conflicts(self):
        await self.set_instructions(["I should shout."])
        before = await self.notes.get_note_by_id("default")
        self.during_completion(lambda: self.edit_note("- mine"))

        with self.assertRaises(NoteConflict) as ctx:
            await self.service.apply_instructions(before.note_id)

        # The edit is kept, the job is run again on top of it
        self.assertEqual(ctx.exception.current.content, "- mine")
        self.assertEqual(await self.actions.list_actions(before.note_id), [])

        note = await self.service.apply_instructions(before.note_id)

        self.assertEqual(note.content, "- result")
        contents = [m.content for m in self.called_chat().messages if m.kind == "user"]
        self.assertTrue(any("- mine" in content for content in contents))
