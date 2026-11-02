from datetime import datetime
from typing import Annotated

from fastapi import Depends

from pebbenote.actions.repository import NoteActionRepository
from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import NoteViewModel
from pebbenote.notes.types import NoteId


class NoteView:
    def __init__(
        self,
        note_repository: Annotated[NoteRepository, Depends()],
        action_repository: Annotated[NoteActionRepository, Depends()],
    ) -> None:
        self.note_repository = note_repository
        self.action_repository = action_repository

    async def get_note_by_id(self, note_id: NoteId) -> NoteViewModel:
        note = await self.note_repository.get_note_by_id(note_id)

        actions = await self.action_repository.list_actions(note.note_id)

        return NoteViewModel(**note.model_dump(), actions=actions)

    async def get_updated_at(self, note_id: NoteId) -> datetime:
        return self.updated_at(await self.get_note_by_id(note_id))

    @staticmethod
    def updated_at(view: NoteViewModel) -> datetime:
        """When anything shown in the note view last changed"""
        return max([view.updated_at, *(action.updated_at for action in view.actions)])
