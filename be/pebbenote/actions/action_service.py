from datetime import timedelta
from logging import getLogger
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from pebbenote.actions.repository import NoteActionRepository
from pebbenote.actions.schemas import ActionEditModel, ActionModel
from pebbenote.config import settings
from pebbenote.instructions.exceptions import InstructionsConflict
from pebbenote.instructions.repository import UserInstructionRepository
from pebbenote.llm import ai_provider
from pebbenote.llm.base import AIAdapter
from pebbenote.llm.schemas import Chat, Message
from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import NoteModel
from pebbenote.tables import ActionStatus, utc_now

from .history import build_history
from .prompts import (
    apply_action_preamble,
    apply_action_system_prompt,
    apply_instructions_action_text,
    apply_instructions_preamble,
    standing_instructions_prefix,
)

logger = getLogger(__name__)


class NoteActionService:
    def __init__(
        self,
        action_repository: Annotated[NoteActionRepository, Depends()],
        note_repository: Annotated[NoteRepository, Depends()],
        instruction_repository: Annotated[UserInstructionRepository, Depends()],
        ai: Annotated[AIAdapter, Depends(ai_provider)],
    ):
        self.action_repository = action_repository
        self.note_repository = note_repository
        self.instruction_repository = instruction_repository
        self.ai = ai

    async def enqueue_action(
        self, action_model: ActionEditModel
    ) -> tuple[ActionModel, UUID | None]:
        """
        Stores the action as pending, at the end of its note's queue. The LLM
        part runs in apply_action, one action of a note at a time.

        Also returns the action whose task has to be started now: the new one
        when it is the head of the queue, or a head whose task looks lost.
        Otherwise the action before the new one starts it when done.
        """
        # Resolves "default" and checks ownership before touching actions
        note = await self.note_repository.get_note_by_id(action_model.note_id)
        # A finishing action looks for its successor under the same lock, so
        # exactly one of the two starts this action
        await self.note_repository.lock_note(note.note_id)

        action = await self.action_repository.add_action(
            note.note_id, action_model.action, ActionStatus.pending
        )
        head_id = await self.action_repository.first_pending(note.note_id)
        if head_id is None or head_id == action.note_action_id:
            return action, head_id

        # The head's task, or the hand-off to it, may have been lost. Starting
        # it twice is safe, the second run finds it done or conflicts.
        head = await self.action_repository.get_action(head_id)
        stale_since = utc_now() - timedelta(seconds=settings.ACTION_STALE_SECONDS)
        if head.updated_at < stale_since:
            logger.warning("Restarting action %s, its task looks lost", head_id)
            await self.action_repository.touch(head_id)
            return action, head_id
        return action, None

    async def apply_action(self, action_id: UUID) -> tuple[NoteModel, UUID | None]:
        """
        Runs the LLM on a pending action and stores the new note. Returns it
        with the next action of the queue, to be started after the commit.

        One attempt: nothing is locked while the LLM is busy, so when the note
        or the instructions change meanwhile it raises their VersionConflict
        without having written anything, and is to be run again.
        """
        action = await self.action_repository.get_action(action_id)
        note = await self.note_repository.get_note_by_id(action.note_id)

        if action.status != ActionStatus.pending:
            # Delivered twice, or a retry after starting the next action
            # failed: hand over again, a duplicate start is safe
            return note, await self._next_action(note.note_id)

        instructions = await self.instruction_repository.get_instructions()
        instruction_texts = instructions.instructions
        is_instruction = await self.ai.classify_input(action.action) == "instruction"
        if is_instruction:
            instruction = await self.ai.rewrite_instruction(action.action)
            instruction_texts = [*instruction_texts, instruction]
            preamble, user_message = apply_instructions_preamble, None
        else:
            preamble, user_message = apply_action_preamble, action.action

        response = await self.ai.get_completion(
            await self._build_chat(
                note.note_id, instruction_texts, preamble, user_message
            )
        )

        await self.note_repository.claim_version(note.note_id, note.version)
        if is_instruction:
            await self.instruction_repository.claim_version(instructions.version)
            await self.instruction_repository.add_revision(instruction_texts)

        await self.action_repository.set_status(
            action.note_action_id, ActionStatus.done
        )
        note = await self.note_repository.add_revision(
            note.note_id, response, action.note_action_id
        )
        return note, await self._next_action(note.note_id)

    async def fail_action(self, action_id: UUID) -> UUID | None:
        """
        Gives up on an action. Returns the next action of the queue, to be
        started after the commit.
        """
        action = await self.action_repository.get_action(action_id)
        await self.note_repository.lock_note(action.note_id)

        await self.action_repository.set_status(action_id, ActionStatus.failed)
        return await self._next_action(action.note_id)

    async def _next_action(self, note_id: UUID) -> UUID | None:
        """The head of the note's queue, marked as started"""
        next_id = await self.action_repository.first_pending(note_id)
        if next_id is not None:
            await self.action_repository.touch(next_id)
        return next_id

    async def apply_instructions(self, note_id: UUID) -> NoteModel:
        """
        Applies the standing instructions to a note after they were edited.

        One attempt: nothing is locked while the LLM is busy, so when the note
        or the instructions change meanwhile it raises their VersionConflict
        without having written anything, and is to be run again.
        """
        instructions = await self.instruction_repository.get_instructions()
        note = await self.note_repository.get_note_by_id(note_id)
        if not instructions.instructions:
            return note

        response = await self.ai.get_completion(
            await self._build_chat(
                note_id, instructions.instructions, apply_instructions_preamble, None
            )
        )
        if response.strip() == note.content:
            return note

        await self.note_repository.claim_version(note_id, note.version)
        latest = await self.instruction_repository.get_instructions()
        if latest.version != instructions.version:
            raise InstructionsConflict(latest)

        action = await self.action_repository.add_action(
            note_id, apply_instructions_action_text
        )
        return await self.note_repository.add_revision(
            note_id, response, action.note_action_id
        )

    async def _build_chat(
        self,
        note_id: UUID,
        instructions: list[str],
        preamble: str,
        user_message: str | None,
    ) -> Chat:
        revisions = await self.note_repository.list_revisions(
            note_id, settings.HISTORY_REVISIONS
        )

        messages = [
            Message(kind="system", content=apply_action_system_prompt),
            *build_history(revisions),
        ]
        if instructions:
            bullets = "\n".join(f"- {instruction}" for instruction in instructions)
            messages.append(
                Message(
                    kind="assistant",
                    content=f"{standing_instructions_prefix}\n{bullets}",
                )
            )
        messages.append(Message(kind="system", content=preamble))
        if user_message is not None:
            messages.append(Message(kind="user", content=user_message))

        return Chat(messages=messages)
