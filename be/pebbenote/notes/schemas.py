from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from pebbenote.actions.schemas import ActionModel


class NoteModel(BaseModel):
    note_id: UUID
    content: str
    is_default: bool
    updated_at: datetime
    # The number of revisions of the note, an edit has to name the one it is
    # based on
    version: int


class NoteEditModel(BaseModel):
    content: str


class NoteUpdateModel(NoteEditModel):
    # The version of the note the edit was made on. Clients from before
    # versioning leave it out, their edit wins over any newer version.
    base_version: int | None = None


class NoteConflictModel(BaseModel):
    detail: str
    # The note as it is now, to merge the edit with
    current: NoteModel


class NoteViewModel(NoteModel):
    actions: list[ActionModel]
    # The Last-Modified of this response, for the If-Modified-Since of the
    # next poll. Not the newest updated_at: the current second is never
    # claimed, a change later in it would be missed.
    last_modified: str


class NoteRevisionModel(BaseModel):
    note_revision_id: UUID
    note_id: UUID
    content: str
    # The dictated action that made this revision, None for edits by hand
    action: str | None
    created_at: datetime
