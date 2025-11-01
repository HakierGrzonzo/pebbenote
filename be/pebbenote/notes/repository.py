from typing import cast
from sqlalchemy import Select
from uuid import UUID
from pebbenote.db import DbSession
from .exceptions import NoteDoesNotExist
from .schemas import NoteEditModel, NoteModel
from ..tables import Note


class NoteRepository:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    @classmethod
    def map_note(cls, note: Note) -> NoteModel:
        return NoteModel(note_id=note.note_id, content=note.note_text)

    async def list_notes(self) -> list[NoteModel]:
        query: Select = Select(Note)

        results = await self.session.execute(query)

        notes = cast(list[Note], results.scalars().all())

        return [self.map_note(note) for note in notes]

    async def _raw_get_note_by_id(self, note_id: UUID) -> Note:
        query = Select(Note).where(Note.note_id == note_id)
        result = await self.session.execute(query)

        note = cast(Note | None, result.scalars().first())

        if note is None:
            raise NoteDoesNotExist(note_id)

        return note

    async def get_note_by_id(self, note_id: UUID):
        note = await self._raw_get_note_by_id(note_id)

        return self.map_note(note)

    async def update_note(self, note_id: UUID, note_model: NoteEditModel):
        note = await self._raw_get_note_by_id(note_id)
        note.note_text = note_model.content
        await self.session.flush([note])
        return self.map_note(note)

    async def create_note(self, note_model: NoteEditModel) -> NoteModel:
        note = Note(note_text=note_model.content)
        self.session.add(note)
        await self.session.flush([note])

        return self.map_note(note)
