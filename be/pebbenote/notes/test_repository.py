from collections import defaultdict
from unittest import IsolatedAsyncioTestCase
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from pebbenote.db import get_test_db
from pebbenote.notes.schemas import NoteEditModel
from .repository import NoteRepository
from ..tables import Note
from .exceptions import NoteDoesNotExist

NUMBER_OF_NOTES = 4

uuid_gen = defaultdict(uuid4)

class NoteRepositoryTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.user = "A user"
        self.session = await self.enterAsyncContext(get_test_db())
        self.repository = NoteRepository(session=self.session, user=self.user)
        await self.prep_data()

    async def prep_data(self):
        self.session.add_all([
            Note(
                note_text="Some text",
                owner=self.user if i < NUMBER_OF_NOTES else "Someone else",
                note_id=uuid_gen["note", i]
                )
            for i in range(NUMBER_OF_NOTES * 2)
            ])
        await self.session.flush()

    async def test_create_note(self):
        model = NoteEditModel(
            content="A note",
        )
        note = await self.repository.create_note(model)

        self.assertEqual(note.content, model.content)

    async def test_list_note(self):
        notes = await self.repository.list_notes()

        self.assertEqual(len(notes), NUMBER_OF_NOTES)

    async def test_get_one(self):
        id_to_get = uuid_gen["note", 0]
        note = await self.repository.get_note_by_id(id_to_get)
        self.assertEqual(note.note_id, id_to_get)

    async def test_get_one_non_existing(self):
        id_to_get = uuid_gen["note", "not-exists"]
        with self.assertRaises(NoteDoesNotExist):
            await self.repository.get_note_by_id(id_to_get)

    async def test_get_one_non_ours(self):
        id_to_get = uuid_gen["note", 5]
        with self.assertRaises(NoteDoesNotExist):
            await self.repository.get_note_by_id(id_to_get)

    async def test_default_note_created_once(self):
        first = await self.repository.get_note_by_id("default")
        second = await self.repository.get_note_by_id("default")

        self.assertEqual(first.note_id, second.note_id)
        self.assertEqual(first.content, "")

    async def test_default_note_per_user(self):
        other = NoteRepository(session=self.session, user="Someone else")

        ours = await self.repository.get_note_by_id("default")
        theirs = await other.get_note_by_id("default")

        self.assertNotEqual(ours.note_id, theirs.note_id)

    async def test_update_default_note(self):
        await self.repository.update_note(
            "default", NoteEditModel(content="Edited")
        )

        note = await self.repository.get_note_by_id("default")
        self.assertEqual(note.content, "Edited")

    async def test_created_note_is_not_default(self):
        created = await self.repository.create_note(NoteEditModel(content="x"))
        default = await self.repository.get_note_by_id("default")

        self.assertNotEqual(created.note_id, default.note_id)

    async def test_second_default_rejected(self):
        await self.repository.get_note_by_id("default")
        self.session.add(
            Note(note_text="", owner=self.user, is_default=True)
        )
        with self.assertRaises(IntegrityError):
            await self.session.flush()

    async def test_set_default_switches(self):
        old = await self.repository.get_note_by_id("default")
        target = uuid_gen["note", 0]

        result = await self.repository.set_default_note(target)
        notes = await self.repository.list_notes()

        self.assertTrue(result.is_default)
        self.assertEqual(
            [n.note_id for n in notes if n.is_default], [target]
        )
        self.assertNotEqual(old.note_id, target)

    async def test_set_default_idempotent(self):
        target = uuid_gen["note", 0]
        await self.repository.set_default_note(target)
        result = await self.repository.set_default_note(target)

        self.assertTrue(result.is_default)

    async def test_set_default_non_ours(self):
        with self.assertRaises(NoteDoesNotExist):
            await self.repository.set_default_note(uuid_gen["note", 5])
