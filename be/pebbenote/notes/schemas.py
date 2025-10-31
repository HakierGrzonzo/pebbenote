from pydantic import BaseModel
from uuid import UUID


class NoteModel(BaseModel):
    note_id: UUID
    content: str


class NoteEditModel(BaseModel):
    content: str
