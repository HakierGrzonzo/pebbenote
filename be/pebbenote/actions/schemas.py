from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from pebbenote.notes.types import NoteId
from pebbenote.tables import ActionStatus


class ActionModel(BaseModel):
    note_action_id: UUID
    note_id: UUID

    action: str
    status: ActionStatus

    created_at: datetime
    updated_at: datetime


class ActionEditModel(BaseModel):
    note_id: NoteId
    action: str


class ActionAcceptedModel(BaseModel):
    """The action is still being applied, poll the note for the result"""

    action: ActionModel
    # HTTP-date to send as If-Modified-Since while polling the note
    note_last_modified: str
