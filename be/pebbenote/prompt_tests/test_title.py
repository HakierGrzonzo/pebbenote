import re

from .base import PromptTestCase

SHOPPING = """- Shopping:
    - oat milk
    - sourdough bread
    - free range eggs"""

TWO_HEADINGS = """- Kitchen:
    - fix the leaking tap
    - paint the cupboards
- Bathroom:
    - replace the mirror"""

NO_HEADING = """- walk the dog
- send the invoice"""


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


class TitleTestCase(PromptTestCase):
    async def test_titles_are_short_and_from_the_note(self):
        for note in [SHOPPING, TWO_HEADINGS, NO_HEADING]:
            with self.subTest(note=note.splitlines()[0]):
                title = await self.ai.generate_title(note)

                self.assertLess(len(title), 50, title)
                self.assertLessEqual(words(title), words(note), title)

    async def test_starts_with_the_heading(self):
        title = await self.ai.generate_title(SHOPPING)

        self.assertTrue(title.lower().startswith("shopping"), title)

    async def test_names_each_heading(self):
        title = await self.ai.generate_title(TWO_HEADINGS)

        self.assertIn("kitchen", title.lower())
        self.assertIn("bathroom", title.lower())
        self.assertIn(";", title)
