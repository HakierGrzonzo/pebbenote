from typing import Annotated
from uuid import UUID

from fastapi import Depends

from pebbenote.actions.repository import NoteActionRepository
from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import NoteViewModel


class NoteView:
    def __init__(
        self,
        note_repository: Annotated[NoteRepository, Depends()],
        action_repository: Annotated[NoteActionRepository, Depends()],
    ) -> None:
        self.note_repository = note_repository
        self.action_repository = action_repository

    async def get_note_by_id(self, note_id: UUID) -> NoteViewModel:
        note = await self.note_repository.get_note_by_id(note_id)

        actions = await self.action_repository.list_actions(note_id)

        return NoteViewModel(**note.model_dump(), actions=actions)
