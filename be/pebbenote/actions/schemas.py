from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ActionModel(BaseModel):
    note_action_id: UUID
    note_id: UUID

    action: str

    created_at: datetime


class ActionEditModel(BaseModel):
    note_id: UUID
    action: str
