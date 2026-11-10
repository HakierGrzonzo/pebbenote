from uuid import UUID

from sqlalchemy import Select, desc, func, update
from sqlalchemy.dialects.postgresql import distinct_on, insert

from pebbenote.auth import CurrentUser
from pebbenote.db import DbSession

from ..tables import Note, NoteAction, NoteRevision, utc_now
from .exceptions import NoteConflict, NoteDoesNotExist
from .schemas import NoteEditModel, NoteModel, NoteRevisionModel, NoteUpdateModel
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

    def _select_notes(self) -> Select[tuple[Note, NoteRevision, int]]:
        """
        The user's notes with their latest revision, which holds the content,
        and their version: the number of that revision
        """
        version = func.row_number().over(
            partition_by=NoteRevision.note_id,
            order_by=(NoteRevision.created_at, NoteRevision.note_revision_id),
        )
        latest_revision_id = (
            Select(
                NoteRevision.note_id,
                NoteRevision.note_revision_id,
                version.label("version"),
            )
            .ext(distinct_on(NoteRevision.note_id))
            .order_by(
                NoteRevision.note_id,
                desc(NoteRevision.created_at),
                desc(NoteRevision.note_revision_id),
            )
            .cte("latest_revision_id")
        )
        return (
            Select(Note, NoteRevision, latest_revision_id.c.version)
            .join(latest_revision_id, latest_revision_id.c.note_id == Note.note_id)
            .join(
                NoteRevision,
                NoteRevision.note_revision_id == latest_revision_id.c.note_revision_id,
            )
            .where(Note.owner == self.user)
            # A job reads the note again after the LLM call, in one session
            .execution_options(populate_existing=True)
        )

    @classmethod
    def map_note(cls, note: Note, revision: NoteRevision, version: int) -> NoteModel:
        return NoteModel(
            note_id=note.note_id,
            content=revision.note_text,
            is_default=note.is_default,
            updated_at=note.updated_at,
            version=version,
        )

    async def list_notes(self) -> list[NoteModel]:
        query = self._select_notes()

        results = await self.session.execute(query)

        return [self.map_note(*row) for row in results]

    async def add_revision(
        self, note_id: UUID, text: str, action_id: UUID | None = None
    ) -> NoteModel:
        """
        Makes the text the content of the note. Pass the action that made the
        edit. The caller has claimed the version the text is based on.
        """
        note, _, _ = await self._raw_get_note_by_id(note_id)
        self.session.add(
            NoteRevision(
                note_id=note.note_id, note_text=text.strip(), note_action_id=action_id
            )
        )
        # The note row itself is unchanged, bump it for Last-Modified
        note.updated_at = utc_now()
        await self.session.flush()

        return await self.get_note_by_id(note.note_id)

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
            await self.session.flush()

    async def _raw_get_note_by_id(
        self, note_id: NoteId
    ) -> tuple[Note, NoteRevision, int]:
        query = self._select_notes()
        if note_id == "default":
            query = query.where(Note.is_default)
        else:
            query = query.where(Note.note_id == note_id)

        row = (await self.session.execute(query)).one_or_none()

        if row is None and note_id == "default":
            # The user's first visit
            await self._create_default_note()
            row = (await self.session.execute(query)).one()

        if row is None:
            raise NoteDoesNotExist(note_id)

        note, revision, version = row
        return note, revision, version

    async def get_note_by_id(self, note_id: NoteId) -> NoteModel:
        return self.map_note(*await self._raw_get_note_by_id(note_id))

    async def lock_note(self, note_id: UUID) -> None:
        """
        Holds the note until the transaction ends. Statements after this one
        see what a writer that held the lock before has committed.
        """
        await self.session.execute(
            Select(Note.note_id)
            .where(Note.note_id == note_id, Note.owner == self.user)
            .with_for_update()
        )

    async def claim_version(self, note_id: NoteId, base_version: int) -> NoteModel:
        """
        The first step of a write that is based on base_version of the note:
        raises NoteConflict, with the note as it is now, when that is no longer
        the latest version. Otherwise the note is locked for the caller's
        write, until the transaction ends.
        """
        note = await self.get_note_by_id(note_id)
        await self.lock_note(note.note_id)
        note = await self.get_note_by_id(note.note_id)
        if note.version != base_version:
            raise NoteConflict(note)

        return note

    async def update_note(
        self, note_id: NoteId, note_model: NoteUpdateModel
    ) -> NoteModel:
        """An edit by hand, one that changes nothing is not stored"""
        note = await self.claim_version(note_id, note_model.base_version)

        if note_model.content.strip() == note.content:
            return note
        return await self.add_revision(note.note_id, note_model.content)

    async def create_note(self, note_model: NoteEditModel) -> NoteModel:
        note = Note(owner=self.user)
        self.session.add(note)
        await self.session.flush()
        self.session.add(
            NoteRevision(note_id=note.note_id, note_text=note_model.content.strip())
        )
        await self.session.flush()

        return await self.get_note_by_id(note.note_id)

    async def set_default_note(self, note_id: UUID) -> NoteModel:
        note, revision, version = await self._raw_get_note_by_id(note_id)

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
            await self.session.flush()

        return self.map_note(note, revision, version)

    async def list_revisions(
        self, note_id: NoteId, limit: int
    ) -> list[NoteRevisionModel]:
        """The latest revisions of a note, oldest first"""
        note, _, _ = await self._raw_get_note_by_id(note_id)
        query = (
            Select(NoteRevision, NoteAction.action_text)
            .outerjoin(NoteAction)
            .where(NoteRevision.note_id == note.note_id)
            .order_by(desc(NoteRevision.created_at))
            .limit(limit)
        )

        rows = (await self.session.execute(query)).all()

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
