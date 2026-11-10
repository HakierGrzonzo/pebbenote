from collections import defaultdict
from unittest import IsolatedAsyncioTestCase
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from pebbenote.db import get_test_db
from pebbenote.notes.schemas import NoteEditModel, NoteUpdateModel

from ..tables import Note, NoteAction, NoteRevision
from .exceptions import NoteConflict, NoteDoesNotExist
from .repository import DEFAULT_NOTE_TEXT, NoteRepository

NUMBER_OF_NOTES = 4

uuid_gen = defaultdict(uuid4)


class NoteRepositoryTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.user = "A user"
        self.session = await self.enterAsyncContext(get_test_db())
        self.repository = NoteRepository(session=self.session, user=self.user)
        await self.prep_data()

    async def prep_data(self):
        self.session.add_all(
            [
                Note(
                    owner=self.user if i < NUMBER_OF_NOTES else "Someone else",
                    note_id=uuid_gen["note", i],
                )
                for i in range(NUMBER_OF_NOTES * 2)
            ]
        )
        await self.session.flush()
        self.session.add_all(
            [
                NoteRevision(note_id=uuid_gen["note", i], note_text="Some text")
                for i in range(NUMBER_OF_NOTES * 2)
            ]
        )
        await self.session.flush()

    async def edit(self, note_id, content: str):
        """An edit by hand, based on the latest version"""
        note = await self.repository.get_note_by_id(note_id)
        return await self.repository.update_note(
            note_id, NoteUpdateModel(content=content, base_version=note.version)
        )

    async def test_create_note(self):
        model = NoteEditModel(
            content="A note",
        )
        note = await self.repository.create_note(model)

        self.assertEqual(note.content, model.content)

    async def test_create_note_strips_content(self):
        note = await self.repository.create_note(NoteEditModel(content="  A note\n\n"))

        self.assertEqual(note.content, "A note")

    async def test_update_note_strips_content(self):
        note = await self.edit(uuid_gen["note", 0], "Edited\n\n")

        self.assertEqual(note.content, "Edited")

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
        self.assertEqual(first.content, DEFAULT_NOTE_TEXT)

    async def test_default_note_per_user(self):
        other = NoteRepository(session=self.session, user="Someone else")

        ours = await self.repository.get_note_by_id("default")
        theirs = await other.get_note_by_id("default")

        self.assertNotEqual(ours.note_id, theirs.note_id)

    async def test_update_default_note(self):
        await self.edit("default", "Edited")

        note = await self.repository.get_note_by_id("default")
        self.assertEqual(note.content, "Edited")

    async def test_created_note_is_not_default(self):
        created = await self.repository.create_note(NoteEditModel(content="x"))
        default = await self.repository.get_note_by_id("default")

        self.assertNotEqual(created.note_id, default.note_id)

    async def test_second_default_rejected(self):
        await self.repository.get_note_by_id("default")
        self.session.add(Note(owner=self.user, is_default=True))
        with self.assertRaises(IntegrityError):
            await self.session.flush()

    async def test_set_default_switches(self):
        old = await self.repository.get_note_by_id("default")
        target = uuid_gen["note", 0]

        result = await self.repository.set_default_note(target)
        notes = await self.repository.list_notes()

        self.assertTrue(result.is_default)
        self.assertEqual([n.note_id for n in notes if n.is_default], [target])
        self.assertNotEqual(old.note_id, target)

    async def test_set_default_idempotent(self):
        target = uuid_gen["note", 0]
        await self.repository.set_default_note(target)
        result = await self.repository.set_default_note(target)

        self.assertTrue(result.is_default)

    async def test_set_default_non_ours(self):
        with self.assertRaises(NoteDoesNotExist):
            await self.repository.set_default_note(uuid_gen["note", 5])

    async def test_update_bumps_updated_at(self):
        before = await self.repository.get_note_by_id(uuid_gen["note", 0])
        after = await self.edit(uuid_gen["note", 0], "Edited")

        self.assertGreater(after.updated_at, before.updated_at)

    async def revisions(self, note_id=uuid_gen["note", 0]):
        return await self.repository.list_revisions(note_id, limit=100)

    async def test_content_is_latest_revision(self):
        await self.edit(uuid_gen["note", 0], "First")
        await self.edit(uuid_gen["note", 0], "Second")

        note = await self.repository.get_note_by_id(uuid_gen["note", 0])
        listed = {n.note_id: n for n in await self.repository.list_notes()}

        self.assertEqual(note.content, "Second")
        self.assertEqual(listed[uuid_gen["note", 0]].content, "Second")
        self.assertEqual(listed[uuid_gen["note", 1]].content, "Some text")

    async def test_update_adds_revision(self):
        await self.edit(uuid_gen["note", 0], "Edited")

        revisions = await self.revisions()

        self.assertEqual([r.content for r in revisions], ["Some text", "Edited"])
        self.assertIsNone(revisions[-1].action)

    async def test_unchanged_manual_edit_adds_no_revision(self):
        await self.edit(uuid_gen["note", 0], "Some text\n")

        self.assertEqual(len(await self.revisions()), 1)

    async def test_action_edit_links_action(self):
        action = NoteAction(note_id=uuid_gen["note", 0], action_text="keep it")
        self.session.add(action)
        await self.session.flush()

        # Even an unchanged note is stored, so every done action has a revision
        await self.repository.add_revision(
            uuid_gen["note", 0], "Some text", action.note_action_id
        )

        revisions = await self.revisions()
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[-1].action, "keep it")

    async def test_create_and_default_have_first_revision(self):
        created = await self.repository.create_note(NoteEditModel(content="New"))
        default = await self.repository.get_note_by_id("default")

        self.assertEqual(
            [r.content for r in await self.revisions(created.note_id)], ["New"]
        )
        self.assertEqual(
            [r.content for r in await self.revisions("default")], [DEFAULT_NOTE_TEXT]
        )
        self.assertEqual(default.content, DEFAULT_NOTE_TEXT)

    async def test_list_revisions_keeps_latest(self):
        for i in range(5):
            await self.edit(uuid_gen["note", 0], f"Edit {i}")

        revisions = await self.repository.list_revisions(uuid_gen["note", 0], 2)

        self.assertEqual([r.content for r in revisions], ["Edit 3", "Edit 4"])

    async def test_version_is_the_number_of_revisions(self):
        created = await self.repository.create_note(NoteEditModel(content="New"))
        self.assertEqual(created.version, 1)

        first = await self.edit(uuid_gen["note", 0], "First")
        second = await self.edit(uuid_gen["note", 0], "Second")

        self.assertEqual((first.version, second.version), (2, 3))
        listed = {n.note_id: n for n in await self.repository.list_notes()}
        self.assertEqual(listed[uuid_gen["note", 0]].version, 3)
        self.assertEqual(listed[uuid_gen["note", 1]].version, 1)

    async def test_unchanged_edit_keeps_the_version(self):
        note = await self.edit(uuid_gen["note", 0], "Some text\n")

        self.assertEqual(note.version, 1)

    async def test_edit_of_an_old_version_conflicts(self):
        current = await self.edit(uuid_gen["note", 0], "Theirs")

        with self.assertRaises(NoteConflict) as ctx:
            await self.repository.update_note(
                uuid_gen["note", 0], NoteUpdateModel(content="Mine", base_version=1)
            )

        self.assertEqual(ctx.exception.current, current)
        note = await self.repository.get_note_by_id(uuid_gen["note", 0])
        self.assertEqual(note, current)

    async def test_edit_without_a_base_version_wins(self):
        # Clients from before versioning
        await self.edit(uuid_gen["note", 0], "Theirs")

        note = await self.repository.update_note(
            uuid_gen["note", 0], NoteUpdateModel(content="Mine")
        )

        self.assertEqual(note.content, "Mine")
        self.assertEqual(note.version, 3)

    async def test_claim_version(self):
        note = await self.repository.claim_version("default", 1)
        self.assertEqual(note.version, 1)

        with self.assertRaises(NoteConflict):
            await self.repository.claim_version("default", 2)
