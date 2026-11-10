from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status

from pebbenote.http_dates import is_modified_since, last_modified
from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import (
    NoteConflictModel,
    NoteEditModel,
    NoteModel,
    NoteUpdateModel,
    NoteViewModel,
)
from pebbenote.notes.types import NoteId
from pebbenote.notes.view import NoteView

note_router = APIRouter(prefix="/note", tags=["Notes"])


@note_router.get("/")
async def list_notes(
    repository: Annotated[NoteRepository, Depends()],
) -> list[NoteModel]:
    return await repository.list_notes()


def is_not_modified(
    note_id: NoteId, updated_at: datetime, if_modified_since: str | None
) -> bool:
    """
    Whether the client already has the note. Never for "default": the alias
    can be moved to another note, older than what the client has, and no row
    records when.
    """
    if note_id == "default":
        return False
    return not is_modified_since(updated_at, if_modified_since)


@note_router.get(
    "/{note_id}",
    response_model=NoteViewModel,
    responses={status.HTTP_304_NOT_MODIFIED: {"description": "Not modified"}},
)
async def get_note_by_id(
    view: Annotated[NoteView, Depends()],
    note_id: NoteId,
    response: Response,
    if_modified_since: Annotated[str | None, Header()] = None,
) -> NoteViewModel | Response:
    note = await view.get_note_by_id(note_id)
    updated_at = NoteView.updated_at(note)

    headers = {
        "Last-Modified": last_modified(updated_at),
        # Clients may cache the note, but must revalidate it every time
        "Cache-Control": "no-cache",
    }
    if is_not_modified(note_id, updated_at, if_modified_since):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    response.headers.update(headers)
    return note


@note_router.patch(
    "/{note_id}",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": NoteConflictModel,
            "description": "The note has changed since base_version",
        }
    },
)
async def edit_note_by_id(
    repository: Annotated[NoteRepository, Depends()],
    note_id: NoteId,
    note: NoteUpdateModel,
) -> NoteModel:
    return await repository.update_note(note_id, note)


@note_router.post("/")
async def create_note(
    repository: Annotated[NoteRepository, Depends()],
    new_note: Annotated[NoteEditModel, Depends()],
) -> NoteModel:
    return await repository.create_note(new_note)


@note_router.put("/{note_id}/default")
async def set_default_note(
    repository: Annotated[NoteRepository, Depends()],
    note_id: UUID,
) -> NoteModel:
    return await repository.set_default_note(note_id)
