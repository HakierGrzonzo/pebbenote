from unittest import IsolatedAsyncioTestCase

from pebbenote.db import get_test_db
from pebbenote.llm.mock import MockAdapter

from .exceptions import NoteConflict
from .repository import NoteRepository
from .schemas import NoteEditModel, NoteUpdateModel
from .title_service import NoteTitleService

SHOPPING_LIST = "- Shopping list:\n    - A\n    - B\n    - C"


class NoteTitleServiceTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.session = await self.enterAsyncContext(get_test_db())
        self.ai = MockAdapter()
        self.ai.title = "Shopping list: A, B, C"
        self.notes = NoteRepository(self.session, "A user")
        self.service = NoteTitleService(self.notes, self.ai)

    async def test_stores_the_title(self):
        note = await self.notes.create_note(NoteEditModel(content=SHOPPING_LIST))
        self.assertEqual(note.title, "Shopping list:")

        titled = await self.service.generate_title(note.note_id)

        self.assertEqual(self.ai.titled, [SHOPPING_LIST])
        self.assertEqual(titled.title, "Shopping list: A, B, C")
        self.assertEqual(titled.version, note.version)

    async def test_changed_note_conflicts_without_writing(self):
        note = await self.notes.create_note(NoteEditModel(content=SHOPPING_LIST))
        generate_title = self.ai.generate_title

        async def edited_meanwhile(text: str) -> str:
            await self.notes.update_note(
                note.note_id, NoteUpdateModel(content="- Something else")
            )
            return await generate_title(text)

        self.ai.generate_title = edited_meanwhile

        with self.assertRaises(NoteConflict):
            await self.service.generate_title(note.note_id)
        current = await self.notes.get_note_by_id(note.note_id)
        self.assertEqual(current.title, "Something else")

    async def test_empty_note_falls_back_without_the_llm(self):
        note = await self.notes.create_note(NoteEditModel(content=SHOPPING_LIST))
        await self.service.generate_title(note.note_id)
        await self.notes.update_note(note.note_id, NoteUpdateModel(content=""))

        titled = await self.service.generate_title(note.note_id)

        self.assertEqual(len(self.ai.titled), 1)
        self.assertEqual(titled.title, "")
