from typing import cast
from uuid import UUID

from sqlalchemy import Select, desc, update
from sqlalchemy.dialects.postgresql import insert

from pebbenote.auth import CurrentUser
from pebbenote.db import DbSession

from ..tables import Note, NoteAction, NoteRevision, utc_now
from .exceptions import NoteDoesNotExist
from .schemas import NoteEditModel, NoteModel, NoteRevisionModel
from .types import NoteId

# Seeded into a user's first default note. One line per watch item, so each
# hint can be deleted on its own.
DEFAULT_NOTE_TEXT = "\n".join(
    [
        "Welcome to Pebbenote!",
        "Select: dictate, AI tidies it into the note",
        "Up/Down: move highlight",
        "Hold Select: delete highlighted line",
        'Say "always ..." to set a lasting rule',
        "Hold Select on these lines to clear them",
    ]
)


class NoteRepository:
    def __init__(self, session: DbSession, user: CurrentUser) -> None:
        self.session = session
        self.user = user

    def _select_notes(self) -> Select[tuple[Note, NoteRevision]]:
        """The user's notes with their latest revision, which holds the content"""
        latest_revision_id = (
            Select(NoteRevision.note_id, NoteRevision.note_revision_id)
            .distinct(NoteRevision.note_id)
            .order_by(NoteRevision.note_id, desc(NoteRevision.created_at))
            .cte("latest_revision_id")
        )
        return (
            Select(Note, NoteRevision)
            .join(latest_revision_id, latest_revision_id.c.note_id == Note.note_id)
            .join(
                NoteRevision,
                NoteRevision.note_revision_id == latest_revision_id.c.note_revision_id,
            )
            .where(Note.owner == self.user)
        )

    @classmethod
    def map_note(cls, note: Note, revision: NoteRevision) -> NoteModel:
        return NoteModel(
            note_id=note.note_id,
            content=revision.note_text,
            is_default=note.is_default,
            updated_at=note.updated_at,
        )

    async def list_notes(self) -> list[NoteModel]:
        query = self._select_notes()

        results = await self.session.execute(query)

        return [self.map_note(note, revision) for note, revision in results.tuples()]

    async def _add_revision(
        self, note: Note, text: str, action_id: UUID | None = None
    ) -> NoteRevision:
        revision = NoteRevision(
            note_id=note.note_id, note_text=text, note_action_id=action_id
        )
        self.session.add(revision)
        # The note row itself is unchanged, bump it for Last-Modified
        note.updated_at = utc_now()
        await self.session.flush([note, revision])
        return revision

    async def _create_default_note(self) -> None:
        # The partial unique index makes this safe against concurrent requests
        note_id = (
            await self.session.execute(
                insert(Note)
                .values(owner=self.user, is_default=True)
                .on_conflict_do_nothing(
                    index_elements=[Note.owner], index_where=Note.is_default
                )
                .returning(Note.note_id)
            )
        ).scalar_one_or_none()

        if note_id is not None:
            revision = NoteRevision(note_id=note_id, note_text=DEFAULT_NOTE_TEXT)
            self.session.add(revision)
            await self.session.flush([revision])

    async def _raw_get_note_by_id(
        self, note_id: NoteId, for_update: bool = False
    ) -> tuple[Note, NoteRevision]:
        query = self._select_notes()
        if note_id == "default":
            query = query.where(Note.is_default)
        else:
            query = query.where(Note.note_id == note_id)
        if for_update:
            # Serializes concurrent edits of one note
            query = query.with_for_update(of=Note).execution_options(
                populate_existing=True
            )

        row = (await self.session.execute(query)).tuples().one_or_none()

        if row is None and note_id == "default":
            # The user's first visit
            await self._create_default_note()
            row = (await self.session.execute(query)).tuples().one()

        if row is None:
            raise NoteDoesNotExist(note_id)

        return row

    async def get_note_by_id(self, note_id: NoteId, for_update: bool = False):
        note, revision = await self._raw_get_note_by_id(note_id, for_update)

        return self.map_note(note, revision)

    async def update_note(
        self,
        note_id: NoteId,
        note_model: NoteEditModel,
        action_id: UUID | None = None,
    ) -> NoteModel:
        """
        Stores the new content as a revision. Pass the action that made the
        edit, edits by hand that change nothing are not stored.
        """
        note, revision = await self._raw_get_note_by_id(note_id)
        text = note_model.content.strip()

        if action_id is not None or text != revision.note_text:
            revision = await self._add_revision(note, text, action_id)

        return self.map_note(note, revision)

    async def create_note(self, note_model: NoteEditModel) -> NoteModel:
        note = Note(owner=self.user)
        self.session.add(note)
        await self.session.flush([note])
        revision = await self._add_revision(note, note_model.content.strip())

        return self.map_note(note, revision)

    async def set_default_note(self, note_id: UUID) -> NoteModel:
        note, revision = await self._raw_get_note_by_id(note_id)

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

        return self.map_note(note, revision)

    async def list_revisions(
        self, note_id: NoteId, limit: int
    ) -> list[NoteRevisionModel]:
        """The latest revisions of a note, oldest first"""
        note, _ = await self._raw_get_note_by_id(note_id)
        query = (
            Select(NoteRevision, NoteAction.action_text)
            .outerjoin(NoteAction)
            .where(NoteRevision.note_id == note.note_id)
            .order_by(desc(NoteRevision.created_at))
            .limit(limit)
        )

        rows = cast(
            list[tuple[NoteRevision, str | None]],
            (await self.session.execute(query)).tuples().all(),
        )

        return [
            NoteRevisionModel(
                note_revision_id=revision.note_revision_id,
                note_id=revision.note_id,
                content=revision.note_text,
                action=action,
                created_at=revision.created_at,
            )
            for revision, action in reversed(rows)
        ]
