from unittest import IsolatedAsyncioTestCase

from sqlalchemy import select

from pebbenote.db import get_test_db

from .repository import UserInstructionRepository


class UserInstructionRepositoryTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.session = await self.enterAsyncContext(get_test_db())
        self.repository = UserInstructionRepository(session=self.session, user="A")
        self.other = UserInstructionRepository(session=self.session, user="B")

    async def test_list_is_scoped_to_user_and_ordered(self):
        await self.repository.add_instruction("first")
        await self.other.add_instruction("not mine")
        await self.repository.add_instruction("second")

        self.assertEqual(await self.repository.list_instructions(), ["first", "second"])
        self.assertEqual(await self.other.list_instructions(), ["not mine"])

    async def test_replace_sets_the_list(self):
        await self.repository.add_instruction("old")
        await self.other.add_instruction("not mine")

        replaced = await self.repository.replace_instructions(["b", "a", "c"])

        self.assertEqual(replaced, ["b", "a", "c"])
        self.assertCountEqual(
            await self.repository.list_instructions(), ["a", "b", "c"]
        )
        self.assertEqual(await self.other.list_instructions(), ["not mine"])

    async def test_replace_with_empty_list_clears(self):
        await self.repository.add_instruction("old")

        await self.repository.replace_instructions([])

        self.assertEqual(await self.repository.list_instructions(), [])

    async def test_instructions_are(self):
        async def instructions_are(texts: list[str]) -> bool:
            condition = self.repository.instructions_are(texts)
            return (await self.session.execute(select(condition))).scalar_one()

        self.assertTrue(await instructions_are([]))
        self.assertFalse(await instructions_are(["a"]))

        await self.repository.replace_instructions(["a", "b"])
        await self.other.add_instruction("c")

        self.assertTrue(await instructions_are(["b", "a"]))
        self.assertFalse(await instructions_are(["a"]))
        self.assertFalse(await instructions_are(["a", "b", "c"]))
        self.assertFalse(await instructions_are([]))
