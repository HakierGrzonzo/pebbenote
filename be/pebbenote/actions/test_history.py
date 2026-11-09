from datetime import UTC, datetime
from unittest import TestCase
from uuid import uuid4

from pebbenote.notes.schemas import NoteRevisionModel

from .history import build_history, note_diff

NOTE_ID = uuid4()


def revision(content: str, action: str | None = None) -> NoteRevisionModel:
    return NoteRevisionModel(
        note_revision_id=uuid4(),
        note_id=NOTE_ID,
        content=content,
        action=action,
        created_at=datetime.now(UTC),
    )


class HistoryTestCase(TestCase):
    def test_single_revision_is_the_note_restated(self):
        messages = list(build_history([revision("- milk")]))

        self.assertEqual(
            [(m.kind, m.content) for m in messages],
            [("user", "- milk"), ("user", "The note is now:\n- milk")],
        )

    def test_action_becomes_request_and_diff_answer(self):
        messages = list(
            build_history(
                [revision("- milk"), revision("- milk\n- eggs", action="add eggs")]
            )
        )

        self.assertEqual(
            [m.kind for m in messages], ["user", "user", "assistant", "user"]
        )
        self.assertEqual(messages[1].content, "add eggs")
        self.assertIn("+- eggs", messages[2].content)
        self.assertEqual(messages[-1].content, "The note is now:\n- milk\n- eggs")

    def test_manual_edit_is_a_user_diff(self):
        messages = list(build_history([revision("- milk\n- eggs"), revision("- milk")]))

        self.assertEqual([m.kind for m in messages], ["user", "user", "user"])
        self.assertTrue(messages[1].content.startswith("I edited the note myself:"))
        self.assertIn("-- eggs", messages[1].content)
        self.assertEqual(messages[-1].content, "The note is now:\n- milk")

    def test_note_diff_is_unified(self):
        diff = note_diff("- milk\n- eggs", "- milk\n- bread")

        self.assertEqual(
            diff.splitlines(),
            [
                "--- note",
                "+++ note",
                "@@ -1,2 +1,2 @@",
                " - milk",
                "-- eggs",
                "+- bread",
            ],
        )
