from typing import Annotated

from fastapi import Depends

from pebbenote.actions.repository import NoteActionRepository
from pebbenote.actions.schemas import ActionEditModel
from pebbenote.instructions.repository import UserInstructionRepository
from pebbenote.llm import ai_provider
from pebbenote.llm.base import AIAdapter
from pebbenote.llm.schemas import Chat, Message
from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import NoteEditModel

from .prompts import (
    apply_action_preamble,
    apply_action_system_prompt,
    apply_instructions_preamble,
    standing_instructions_prefix,
)


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

    async def create_and_apply_action(self, action_model: ActionEditModel):
        # Resolves "default" and checks ownership before touching actions
        note = await self.note_repository.get_note_by_id(action_model.note_id)

        action = await self.action_repository.add_action(
            note.note_id, action_model.action
        )

        if await self.ai.classify_input(action.action) == "instruction":
            instruction = await self.ai.rewrite_instruction(action.action)
            await self.instruction_repository.add_instruction(instruction)
            preamble, user_message = apply_instructions_preamble, None
        else:
            preamble, user_message = apply_action_preamble, action.action

        instructions = await self.instruction_repository.list_instructions()

        messages = [
            Message(kind="system", content=apply_action_system_prompt),
            Message(kind="user", content=note.content),
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

        response = await self.ai.get_completion(Chat(messages=messages))

        new_note = await self.note_repository.update_note(
            note.note_id, NoteEditModel(content=response)
        )

        return new_note
