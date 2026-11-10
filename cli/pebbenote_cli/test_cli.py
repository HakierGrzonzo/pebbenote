import io
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from unittest import TestCase, mock
from uuid import UUID

from . import cli
from .client.api.instructions import list_instructions, replace_instructions
from .client.api.notes import edit_note_by_id, get_note_by_id, list_notes
from .client.models import (
    InstructionsModel,
    NoteModel,
    NoteUpdateModel,
    NoteViewModel,
)
from .config import Config
from .errors import CliError

CONFIG = Config(backend_url="http://backend", issuer="http://issuer")
NOTE_ID = UUID("00000000-0000-0000-0000-00000000000a")
UPDATED_AT = datetime(2026, 1, 1)
NOTE = NoteViewModel(
    note_id=NOTE_ID,
    content="Shopping\n- milk\n",
    is_default=True,
    updated_at=UPDATED_AT,
    version=3,
    actions=[],
)
INSTRUCTIONS = InstructionsModel(instructions=["use metric units", "sort by aisle"])
INSTRUCTIONS_TEXT = "- use metric units\n- sort by aisle\n"


class MainTestCase(TestCase):
    def setUp(self) -> None:
        self.call = self.patch("pebbenote_cli.cli.api.call")
        self.edit_text = self.patch("pebbenote_cli.cli.edit_text")
        self.login = self.patch("pebbenote_cli.cli.auth.login")
        self.patch("pebbenote_cli.cli.load_config", return_value=CONFIG)

    def patch(self, target, *args, **kwargs):
        patcher = mock.patch(target, *args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def run_cli(self, *argv, tty=True):
        stdout, stderr = io.StringIO(), io.StringIO()
        stdout.isatty = lambda: tty
        with (
            mock.patch("sys.argv", ["pebbenote", *argv]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            cli.main()
        return stdout.getvalue(), stderr.getvalue()

    def test_no_command_edits_default_note(self):
        self.call.return_value = NOTE
        self.run_cli(tty=False)

        self.call.assert_called_once_with(CONFIG, get_note_by_id, note_id="default")

    def test_bare_note_id_edits_that_note(self):
        self.call.return_value = NOTE
        self.run_cli("abc", tty=False)

        self.call.assert_called_once_with(CONFIG, get_note_by_id, note_id="abc")

    def test_edit_without_tty_prints_content(self):
        self.call.return_value = NOTE
        stdout, _ = self.run_cli("edit", "abc", tty=False)

        self.assertEqual(stdout, NOTE.content)
        self.edit_text.assert_not_called()

    def test_edit_unchanged_does_not_sync(self):
        self.call.return_value = NOTE
        self.edit_text.return_value = NOTE.content
        _, stderr = self.run_cli("edit", "abc")

        self.assertIn("No changes", stderr)
        self.assertEqual(self.call.call_count, 1)

    def test_edit_changed_syncs(self):
        self.call.return_value = NOTE
        self.edit_text.return_value = "Updated"
        _, stderr = self.run_cli("edit", "abc")

        self.edit_text.assert_called_once_with(NOTE.content)
        self.call.assert_called_with(
            CONFIG,
            edit_note_by_id,
            note_id="abc",
            body=NoteUpdateModel(content="Updated", base_version=3),
        )
        self.assertIn("Note synced", stderr)

    def test_list(self):
        self.call.return_value = [
            NOTE,
            NoteModel(
                note_id=UUID("00000000-0000-0000-0000-00000000000b"),
                content="",
                is_default=False,
                updated_at=UPDATED_AT,
                version=1,
            ),
        ]
        stdout, _ = self.run_cli("list")

        self.call.assert_called_once_with(CONFIG, list_notes)
        self.assertEqual(
            stdout,
            f"* {NOTE_ID}  Shopping\n  00000000-0000-0000-0000-00000000000b  \n",
        )

    def test_instructions_without_tty_prints_list(self):
        self.call.return_value = INSTRUCTIONS
        stdout, _ = self.run_cli("instructions", tty=False)

        self.call.assert_called_once_with(CONFIG, list_instructions)
        self.assertEqual(stdout, INSTRUCTIONS_TEXT)
        self.edit_text.assert_not_called()

    def test_instructions_unchanged_does_not_sync(self):
        self.call.return_value = INSTRUCTIONS
        # Reformatting and reordering alone are not a change
        self.edit_text.return_value = "* sort by aisle\n\n* use metric units"
        _, stderr = self.run_cli("instructions")

        self.edit_text.assert_called_once_with(INSTRUCTIONS_TEXT)
        self.assertIn("No changes", stderr)
        self.assertEqual(self.call.call_count, 1)

    def test_instructions_changed_syncs(self):
        self.call.return_value = INSTRUCTIONS
        self.edit_text.return_value = "- sort by aisle\n- write in Polish\n"
        _, stderr = self.run_cli("instructions")

        self.call.assert_called_with(
            CONFIG,
            replace_instructions,
            body=InstructionsModel(instructions=["sort by aisle", "write in Polish"]),
            apply=True,
        )
        self.assertIn("Instructions synced (2); notes will be updated", stderr)

    def test_instructions_no_apply_only_saves(self):
        self.call.return_value = INSTRUCTIONS
        self.edit_text.return_value = "- write in Polish\n"
        _, stderr = self.run_cli("instructions", "--no-apply")

        self.call.assert_called_with(
            CONFIG,
            replace_instructions,
            body=InstructionsModel(instructions=["write in Polish"]),
            apply=False,
        )
        self.assertIn("Instructions synced (1).", stderr)

    def test_instructions_emptied_clears(self):
        self.call.return_value = INSTRUCTIONS
        self.edit_text.return_value = ""
        _, stderr = self.run_cli("instructions")

        self.call.assert_called_with(
            CONFIG,
            replace_instructions,
            body=InstructionsModel(instructions=[]),
            apply=True,
        )
        self.assertIn("Instructions synced (0).", stderr)

    def test_login(self):
        _, stderr = self.run_cli("login")

        self.login.assert_called_once_with(CONFIG)
        self.assertIn("Logged in", stderr)

    def test_cli_error_exits_with_message(self):
        self.call.side_effect = CliError("boom")

        with self.assertRaises(SystemExit) as ctx:
            self.run_cli("list")
        self.assertEqual(ctx.exception.code, "error: boom")

    def test_keyboard_interrupt_exits_130(self):
        self.call.side_effect = KeyboardInterrupt

        with self.assertRaises(SystemExit) as ctx:
            self.run_cli("list")
        self.assertEqual(ctx.exception.code, 130)
