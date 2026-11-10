from unittest import TestCase

from .instructions import format_instructions, parse_instructions


class InstructionsTestCase(TestCase):
    def test_format(self):
        self.assertEqual(format_instructions(["a", "b"]), "- a\n- b\n")
        self.assertEqual(format_instructions([]), "")

    def test_round_trip(self):
        instructions = ["I should use metric units", "I should sort - by aisle"]

        self.assertEqual(
            parse_instructions(format_instructions(instructions)), instructions
        )

    def test_blank_lines_and_empty_bullets_are_dropped(self):
        self.assertEqual(parse_instructions("\n- a\n\n-\n- \n  - b  \n"), ["a", "b"])

    def test_star_bullets(self):
        self.assertEqual(parse_instructions("* a\n* b\n"), ["a", "b"])

    def test_wrapped_lines_continue_the_instruction(self):
        self.assertEqual(
            parse_instructions("- first\n  wrapped\n- second\n"),
            ["first wrapped", "second"],
        )

    def test_line_without_bullet_is_an_instruction(self):
        self.assertEqual(parse_instructions("plain\n- a\n"), ["plain", "a"])

    def test_empty_text(self):
        self.assertEqual(parse_instructions(" \n"), [])
