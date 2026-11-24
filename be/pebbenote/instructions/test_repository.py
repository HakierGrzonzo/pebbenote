from unittest import IsolatedAsyncioTestCase

from pebbenote.db import as_user, get_test_db

from .exceptions import InstructionsConflict
from .repository import UserInstructionRepository
from .schemas import InstructionsEditModel


class UserInstructionRepositoryTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.session = await self.enterAsyncContext(get_test_db("A"))
        self.repository = UserInstructionRepository(session=self.session)

    async def replace(self, texts: list[str]):
        """An edit by hand, based on the latest version"""
        current = await self.repository.get_instructions()
        return await self.repository.replace_instructions(
            InstructionsEditModel(instructions=texts, base_version=current.version)
        )

    async def replace_theirs(self, texts: list[str]):
        """The same, by another user"""
        async with as_user(self.session, "B"):
            return await self.replace(texts)

    async def test_starts_empty_at_version_one(self):
        instructions = await self.repository.get_instructions()

        self.assertEqual(instructions.instructions, [])
        self.assertEqual(instructions.version, 1)

    async def test_replace_sets_the_list_in_order(self):
        await self.replace(["old"])
        await self.replace_theirs(["not mine"])

        replaced = await self.replace(["b", "a", "c"])

        self.assertEqual(replaced.instructions, ["b", "a", "c"])
        self.assertEqual(replaced, await self.repository.get_instructions())
        async with as_user(self.session, "B"):
            theirs = await self.repository.get_instructions()
        self.assertEqual(theirs.instructions, ["not mine"])

    async def test_replace_with_empty_list_clears(self):
        await self.replace(["old"])

        await self.replace([])

        self.assertEqual((await self.repository.get_instructions()).instructions, [])

    async def test_version_is_the_number_of_revisions(self):
        first = await self.replace(["a"])
        second = await self.replace(["a", "b"])
        theirs = await self.replace_theirs(["c"])

        self.assertEqual((first.version, second.version, theirs.version), (2, 3, 2))

    async def test_reordering_keeps_the_version(self):
        await self.replace(["a", "b"])

        reordered = await self.replace(["b", "a"])

        self.assertEqual(reordered.version, 2)
        self.assertEqual(reordered.instructions, ["a", "b"])

    async def test_edit_of_an_old_version_conflicts(self):
        current = await self.replace(["theirs"])

        with self.assertRaises(InstructionsConflict) as ctx:
            await self.repository.replace_instructions(
                InstructionsEditModel(instructions=["mine"], base_version=1)
            )

        self.assertEqual(ctx.exception.current, current)
        self.assertEqual(await self.repository.get_instructions(), current)

    async def test_add_revision(self):
        added = await self.repository.add_revision(["a"])

        self.assertEqual(added.instructions, ["a"])
        self.assertEqual(added.version, 2)
