from .base import PromptTestCase, revision


class InstructionsTestCase(PromptTestCase):
    async def test_applies_an_instruction(self):
        note = await self.edit(
            revision("- pears\n- apples\n- cherries"),
            action=None,
            instructions=["I should always sort lists alphabetically."],
        )

        self.assertEqual(self.entries(note), ["apples", "cherries", "pears"])

    async def test_note_that_follows_them_is_unchanged(self):
        content = "- apples\n- cherries\n- pears"
        note = await self.edit(
            revision(content),
            action=None,
            instructions=["I should always sort lists alphabetically."],
        )

        self.assertEqual(self.entries(note), self.entries(content))

    async def test_instruction_followed_during_an_edit(self):
        note = await self.edit(
            revision("- bananas\n- cherries"),
            action="add apples",
            instructions=["I should keep lists sorted alphabetically."],
        )

        self.assertEqual(self.entries(note), ["apples", "bananas", "cherries"])
