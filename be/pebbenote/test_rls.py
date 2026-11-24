from unittest import IsolatedAsyncioTestCase
from uuid import uuid4

from sqlalchemy import Select, func
from sqlalchemy.exc import DBAPIError

from pebbenote.db import as_user, get_test_db
from pebbenote.tables import (
    InstructionList,
    InstructionRevision,
    Note,
    NoteAction,
    NoteRevision,
)

TABLES = [Note, NoteRevision, NoteAction, InstructionList, InstructionRevision]


class RowLevelSecurityTestCase(IsolatedAsyncioTestCase):
    """The policies themselves, below the repositories"""

    async def asyncSetUp(self) -> None:
        self.session = await self.enterAsyncContext(get_test_db("A"))
        # One row in every table, owned by B
        async with as_user(self.session, "B"):
            self.note_id = uuid4()
            self.list_id = uuid4()
            self.action_id = uuid4()
            self.session.add(Note(note_id=self.note_id))
            self.session.add(InstructionList(instruction_list_id=self.list_id))
            await self.session.flush()
            self.session.add(
                NoteAction(
                    note_action_id=self.action_id, note_id=self.note_id, action_text="x"
                )
            )
            self.session.add(NoteRevision(note_id=self.note_id, note_text="x"))
            self.session.add(
                InstructionRevision(instruction_list_id=self.list_id, instructions=[])
            )
            await self.session.flush()
        self.session.expunge_all()

    async def count(self, table) -> int:
        return (
            await self.session.execute(Select(func.count()).select_from(table))
        ).scalar_one()

    async def test_owner_sees_every_row(self):
        async with as_user(self.session, "B"):
            for table in TABLES:
                self.assertEqual(await self.count(table), 1, table.__tablename__)

    async def test_others_see_no_rows(self):
        for table in TABLES:
            self.assertEqual(await self.count(table), 0, table.__tablename__)
        self.assertIsNone(await self.session.get(Note, self.note_id))
        self.assertIsNone(await self.session.get(NoteAction, self.action_id))

    async def test_without_a_user_no_rows(self):
        async with as_user(self.session, ""):
            for table in TABLES:
                self.assertEqual(await self.count(table), 0, table.__tablename__)

    async def test_owner_is_the_user(self):
        self.session.add(note := Note())
        await self.session.flush()
        await self.session.refresh(note)

        self.assertEqual(note.owner, "A")

    async def test_cannot_insert_for_another_user(self):
        self.session.add(Note(owner="B"))
        with self.assertRaises(DBAPIError):
            await self.session.flush()

    async def test_cannot_add_to_another_users_note(self):
        self.session.add(NoteRevision(note_id=self.note_id, note_text="mine now"))
        with self.assertRaises(DBAPIError):
            await self.session.flush()

    async def test_cannot_add_to_another_users_instructions(self):
        self.session.add(
            InstructionRevision(instruction_list_id=self.list_id, instructions=["x"])
        )
        with self.assertRaises(DBAPIError):
            await self.session.flush()
