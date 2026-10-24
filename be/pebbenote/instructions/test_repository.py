from unittest import IsolatedAsyncioTestCase

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
