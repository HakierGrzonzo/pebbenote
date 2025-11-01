from pydantic import BaseModel
from uuid import UUID

from pebbenote.actions.schemas import ActionModel


class NoteModel(BaseModel):
    note_id: UUID
    content: str


class NoteEditModel(BaseModel):
    content: str


class NoteViewModel(NoteModel):
    actions: list[ActionModel]
