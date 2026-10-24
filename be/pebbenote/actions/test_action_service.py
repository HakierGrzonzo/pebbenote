from unittest import IsolatedAsyncioTestCase

from pebbenote.db import get_test_db
from pebbenote.instructions.repository import UserInstructionRepository
from pebbenote.llm.mock import MockAdapter
from pebbenote.llm.schemas import Chat
from pebbenote.notes.repository import NoteRepository

from .action_service import NoteActionService
from .repository import NoteActionRepository
from .schemas import ActionEditModel


class NoteActionServiceTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        user = "A user"
        self.session = await self.enterAsyncContext(get_test_db())
        self.ai = MockAdapter()
        self.ai.set_result("- result")
        self.instructions = UserInstructionRepository(self.session, user)
        self.service = NoteActionService(
            NoteActionRepository(self.session),
            NoteRepository(self.session, user),
            self.instructions,
            self.ai,
        )

    def called_chat(self) -> Chat:
        chat = self.ai.get_called_with()
        assert isinstance(chat, Chat)
        return chat

    async def test_note_input_is_not_stored(self):
        await self.service.create_and_apply_action(
            ActionEditModel(note_id="default", action="add milk")
        )

        self.assertEqual(await self.instructions.list_instructions(), [])
        chat = self.called_chat()
        self.assertEqual(chat.messages[-1].content, "add milk")
        self.assertNotIn("assistant", [m.kind for m in chat.messages])

    async def test_instruction_is_stored_and_applied(self):
        self.ai.input_kind = "instruction"
        self.ai.rewritten_instruction = "I should sort groceries."

        note = await self.service.create_and_apply_action(
            ActionEditModel(note_id="default", action="sort groceries")
        )

        self.assertEqual(
            await self.instructions.list_instructions(), ["I should sort groceries."]
        )
        self.assertEqual(note.content, "- result")
        chat = self.called_chat()
        assistant = [m for m in chat.messages if m.kind == "assistant"]
        self.assertIn("I should sort groceries.", assistant[0].content)
        # The raw utterance is not sent as an edit request
        self.assertNotEqual(chat.messages[-1].kind, "user")

    async def test_stored_instructions_reach_note_edits(self):
        await self.instructions.add_instruction("I should sort groceries.")

        await self.service.create_and_apply_action(
            ActionEditModel(note_id="default", action="add milk")
        )

        chat = self.called_chat()
        self.assertTrue(
            any(
                "sort groceries" in m.content
                for m in chat.messages
                if m.kind == "assistant"
            )
        )
