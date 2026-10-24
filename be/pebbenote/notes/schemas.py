from uuid import UUID

from pydantic import BaseModel

from pebbenote.actions.schemas import ActionModel


class NoteModel(BaseModel):
    note_id: UUID
    content: str
    is_default: bool


class NoteEditModel(BaseModel):
    content: str


class NoteViewModel(NoteModel):
    actions: list[ActionModel]
