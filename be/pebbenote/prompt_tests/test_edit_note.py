from .base import PromptTestCase, revision

GROCERIES = """- Groceries:
    - milk
    - eggs
    - bread
- Todo:
    - call mom
    - fix the bike"""


class EditNoteTestCase(PromptTestCase):
    async def test_adds_an_entry(self):
        note = await self.edit(revision("- milk\n- eggs"), action="add butter")

        self.assertMentions(note, "butter")
        self.assertHasEntry(note, "milk")
        self.assertHasEntry(note, "eggs")

    async def test_adds_under_the_right_heading(self):
        note = await self.edit(revision(GROCERIES), action="add apples to groceries")

        self.assertNestedUnder(note, "apples", "groceries")

    async def test_removes_an_entry(self):
        note = await self.edit(revision(GROCERIES), action="remove the eggs")

        self.assertNoEntry(note, "eggs")
        self.assertHasEntry(note, "milk")
        self.assertHasEntry(note, "bread")

    async def test_renames_an_entry(self):
        note = await self.edit(revision(GROCERIES), action="change milk to oat milk")

        self.assertMentions(note, "oat milk")
        self.assertNotIn("milk", [e for e in self.entries(note)])

    async def test_leaves_the_rest_alone(self):
        note = await self.edit(revision(GROCERIES), action="remove the bread")

        for entry in ["milk", "eggs", "call mom", "fix the bike"]:
            self.assertHasEntry(note, entry)
        self.assertNestedUnder(note, "call mom", "todo")

    async def test_adds_nothing_that_was_not_asked_for(self):
        note = await self.edit(revision(GROCERIES), action="add cheese to groceries")

        self.assertEqual(len(self.entries(note)), len(self.entries(GROCERIES)) + 1)

    async def test_undoes_the_last_action(self):
        note = await self.edit(
            revision("- milk\n- eggs"),
            revision("- milk", action="remove the eggs"),
            action="undo that",
        )

        self.assertHasEntry(note, "milk")
        self.assertHasEntry(note, "eggs")

    async def test_brings_back_an_entry_removed_by_hand(self):
        note = await self.edit(
            revision("- milk\n- eggs\n- bread"),
            revision("- milk\n- bread"),
            revision("- milk\n- bread\n- jam", action="add jam"),
            action="bring back what I deleted",
        )

        for entry in ["milk", "eggs", "bread", "jam"]:
            self.assertHasEntry(note, entry)
