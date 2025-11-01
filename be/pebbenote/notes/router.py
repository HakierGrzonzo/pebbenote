from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends

from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import NoteEditModel, NoteModel, NoteViewModel
from pebbenote.notes.view import NoteView


note_router = APIRouter(prefix="/note", tags=["Notes"])


@note_router.get("/")
async def list_notes(
    repository: Annotated[NoteRepository, Depends()],
) -> list[NoteModel]:
    return await repository.list_notes()


@note_router.get("/{note_id}")
async def get_note_by_id(
    view: Annotated[NoteView, Depends()], note_id: UUID
) -> NoteViewModel:
    return await view.get_note_by_id(note_id)


@note_router.post("/")
async def create_note(
    repository: Annotated[NoteRepository, Depends()],
    new_note: Annotated[NoteEditModel, Depends()],
) -> NoteModel:
    return await repository.create_note(new_note)
