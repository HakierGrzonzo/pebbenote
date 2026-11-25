from .base import PromptTestCase

CASES = [
    ("grocery list always sorted by aisle", ["grocery", "aisle"]),
    ("put dates in front of todo items", ["date", "todo"]),
    ("never use capital letters", ["capital"]),
]


class RewriteInstructionTestCase(PromptTestCase):
    async def test_rewrites_in_the_first_person(self):
        for text, keywords in CASES:
            with self.subTest(text=text):
                instruction = await self.ai.rewrite_instruction(text)

                self.assertTrue(instruction.lower().startswith("i should"), instruction)
                self.assertNotIn("\n", instruction)
                for keyword in keywords:
                    self.assertIn(keyword, instruction.lower())
