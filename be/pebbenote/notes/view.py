from datetime import datetime
from typing import Annotated

from fastapi import Depends

from pebbenote.actions.repository import NoteActionRepository
from pebbenote.actions.schemas import ActionModel
from pebbenote.http_dates import last_modified
from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import NoteModel, NoteViewModel
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

        return NoteViewModel(
            **note.model_dump(),
            actions=actions,
            last_modified=last_modified(self.updated_at(note, actions)),
        )

    async def get_updated_at(self, note_id: NoteId) -> datetime:
        view = await self.get_note_by_id(note_id)
        return self.updated_at(view, view.actions)

    @staticmethod
    def updated_at(note: NoteModel, actions: list[ActionModel]) -> datetime:
        """When anything shown in the note view last changed"""
        return max([note.updated_at, *(action.updated_at for action in actions)])
