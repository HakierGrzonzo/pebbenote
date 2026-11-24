from .base import PromptTestCase

CASES = [
    # text, kind, needs_history
    ("buy milk", "note", False),
    ("remove the eggs", "note", False),
    ("add call the dentist to the todo list", "note", False),
    ("always sort the grocery list by aisle", "instruction", False),
    ("from now on write everything in lowercase", "instruction", False),
    ("undo that", "note", True),
    ("bring back the eggs I removed", "note", True),
    ("revert the note to how it was before", "note", True),
]


class ClassifyTestCase(PromptTestCase):
    async def test_classifies_dictation(self):
        for text, kind, needs_history in CASES:
            with self.subTest(text=text):
                classification = await self.ai.classify_input(text)

                self.assertEqual(
                    (classification.kind, classification.needs_history),
                    (kind, needs_history),
                )
