from typing import Annotated
from uuid import UUID

from fastapi import Depends

from pebbenote.llm import ai_provider
from pebbenote.llm.base import AIAdapter

from .repository import NoteRepository
from .schemas import NoteModel


class NoteTitleService:
    def __init__(
        self,
        note_repository: Annotated[NoteRepository, Depends()],
        ai: Annotated[AIAdapter, Depends(ai_provider)],
    ):
        self.note_repository = note_repository
        self.ai = ai

    async def generate_title(self, note_id: UUID) -> NoteModel:
        """
        Has the LLM make a title for the note as it is now and stores it.

        Nothing is locked while the LLM is busy, so when the note changes
        meanwhile it raises NoteConflict without having written anything: the
        change starts a title of its own.
        """
        note = await self.note_repository.get_note_by_id(note_id)
        title = await self.ai.generate_title(note.content) if note.content else None

        await self.note_repository.claim_version(note.note_id, note.version)
        # An empty title falls back to the first line
        await self.note_repository.set_title(note.note_id, title or None)
        return await self.note_repository.get_note_by_id(note.note_id)
