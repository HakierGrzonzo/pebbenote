import io
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from unittest import TestCase, mock
from uuid import UUID

from . import cli
from .client.api.notes import edit_note_by_id, get_note_by_id, list_notes
from .client.models import NoteEditModel, NoteModel, NoteViewModel
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
    actions=[],
)


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
            body=NoteEditModel(content="Updated"),
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
            ),
        ]
        stdout, _ = self.run_cli("list")

        self.call.assert_called_once_with(CONFIG, list_notes)
        self.assertEqual(
            stdout,
            f"* {NOTE_ID}  Shopping\n  00000000-0000-0000-0000-00000000000b  \n",
        )

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
