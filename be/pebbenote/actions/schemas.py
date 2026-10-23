from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from pebbenote.notes.types import NoteId


class ActionModel(BaseModel):
    note_action_id: UUID
    note_id: UUID

    action: str

    created_at: datetime


class ActionEditModel(BaseModel):
    note_id: NoteId
    action: str
