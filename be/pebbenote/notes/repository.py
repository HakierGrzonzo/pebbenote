from typing import cast
from uuid import UUID

from sqlalchemy import Select, update
from sqlalchemy.dialects.postgresql import insert

from pebbenote.auth import CurrentUser
from pebbenote.db import DbSession

from ..tables import Note
from .exceptions import NoteDoesNotExist
from .schemas import NoteEditModel, NoteModel
from .types import NoteId


class NoteRepository:
    def __init__(self, session: DbSession, user: CurrentUser) -> None:
        self.session = session
        self.user = user

    @classmethod
    def map_note(cls, note: Note) -> NoteModel:
        return NoteModel(
            note_id=note.note_id,
            content=note.note_text,
            is_default=note.is_default,
        )

    async def list_notes(self) -> list[NoteModel]:
        query: Select = Select(Note).where(Note.owner == self.user)

        results = await self.session.execute(query)

        notes = cast(list[Note], results.scalars().all())

        return [self.map_note(note) for note in notes]

    async def _raw_get_default_note(self) -> Note:
        query = Select(Note).where(Note.owner == self.user).where(Note.is_default)

        note = cast(Note | None, (await self.session.execute(query)).scalars().first())
        if note is not None:
            return note

        # The user's first visit: create the default note. The partial unique
        # index makes this safe against concurrent requests.
        await self.session.execute(
            insert(Note)
            .values(note_text="", owner=self.user, is_default=True)
            .on_conflict_do_nothing(
                index_elements=[Note.owner], index_where=Note.is_default
            )
        )

        return cast(Note, (await self.session.execute(query)).scalars().one())

    async def _raw_get_note_by_id(self, note_id: NoteId) -> Note:
        if note_id == "default":
            return await self._raw_get_default_note()

        query = (
            Select(Note).where(Note.note_id == note_id).where(Note.owner == self.user)
        )
        result = await self.session.execute(query)

        note = cast(Note | None, result.scalars().first())

        if note is None:
            raise NoteDoesNotExist(note_id)

        return note

    async def get_note_by_id(self, note_id: NoteId):
        note = await self._raw_get_note_by_id(note_id)

        return self.map_note(note)

    async def update_note(self, note_id: NoteId, note_model: NoteEditModel):
        note = await self._raw_get_note_by_id(note_id)
        note.note_text = note_model.content
        await self.session.flush([note])
        return self.map_note(note)

    async def create_note(self, note_model: NoteEditModel) -> NoteModel:
        note = Note(note_text=note_model.content, owner=self.user)
        self.session.add(note)
        await self.session.flush([note])

        return self.map_note(note)

    async def set_default_note(self, note_id: UUID) -> NoteModel:
        note = await self._raw_get_note_by_id(note_id)

        if not note.is_default:
            # Clear the old default first: the partial unique index allows
            # only one default per owner at any point.
            await self.session.execute(
                update(Note)
                .where(Note.owner == self.user)
                .where(Note.is_default)
                .values(is_default=False)
            )
            note.is_default = True
            await self.session.flush([note])

        return self.map_note(note)
