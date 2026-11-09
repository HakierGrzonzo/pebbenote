from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from pebbenote.actions.schemas import ActionModel


class NoteModel(BaseModel):
    note_id: UUID
    content: str
    is_default: bool
    updated_at: datetime


class NoteEditModel(BaseModel):
    content: str


class NoteViewModel(NoteModel):
    actions: list[ActionModel]


class NoteRevisionModel(BaseModel):
    note_revision_id: UUID
    note_id: UUID
    content: str
    # The dictated action that made this revision, None for edits by hand
    action: str | None
    created_at: datetime
