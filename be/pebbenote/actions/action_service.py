from typing import Annotated

from fastapi import Depends
from pebbenote.actions.repository import NoteActionRepository
from pebbenote.actions.schemas import ActionEditModel
from pebbenote.llm.base import AIAdapter
from pebbenote.llm import ai_provider
from pebbenote.llm.schemas import Chat, Message
from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import NoteEditModel
from .prompts import apply_action_system_prompt, apply_action_preamble


class NoteActionService:
    def __init__(
        self,
        action_repository: Annotated[NoteActionRepository, Depends()],
        note_repository: Annotated[NoteRepository, Depends()],
        ai: Annotated[AIAdapter, Depends(ai_provider)],
    ):
        self.action_repository = action_repository
        self.note_repository = note_repository
        self.ai = ai

    async def create_and_apply_action(self, action_model: ActionEditModel):
        action = await self.action_repository.add_action(action_model)

        note = await self.note_repository.get_note_by_id(action_model.note_id)

        chat = Chat(
            messages=[
                Message(kind="system", content=apply_action_system_prompt),
                Message(kind="user", content=note.content),
                Message(kind="system", content=apply_action_preamble),
                Message(kind="user", content=action.action),
            ]
        )

        response = await self.ai.get_completion(chat)

        new_note = await self.note_repository.update_note(
            note.note_id, NoteEditModel(content=response)
        )

        return new_note
