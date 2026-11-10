import io
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from unittest import TestCase, mock
from uuid import UUID

from . import cli
from .client.api.instructions import list_instructions, replace_instructions
from .client.api.notes import edit_note_by_id, get_note_by_id, list_notes
from .client.models import (
    InstructionsEditModel,
    InstructionsModel,
    NoteModel,
    NoteUpdateModel,
    NoteViewModel,
)
from .config import Config
from .errors import CliError, ConflictError

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
    last_modified="Thu, 01 Jan 2026 00:00:00 GMT",
)
INSTRUCTIONS = InstructionsModel(
    instructions=["use metric units", "sort by aisle"], version=4
)
INSTRUCTIONS_TEXT = "- use metric units\n- sort by aisle\n"


def saved(*instructions):
    return InstructionsModel(instructions=list(instructions), version=5)


def conflict(current):
    return ConflictError("conflict", current)


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
            note_id=NOTE_ID,
            body=NoteUpdateModel(content="Updated", base_version=3),
        )
        self.assertIn("Note synced", stderr)

    def test_edit_of_default_syncs_the_note_that_was_read(self):
        self.call.return_value = NOTE
        self.edit_text.return_value = "Updated"
        self.run_cli()

        self.call.assert_called_with(
            CONFIG,
            edit_note_by_id,
            note_id=NOTE_ID,
            body=NoteUpdateModel(content="Updated", base_version=3),
        )

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
        self.call.side_effect = [
            INSTRUCTIONS,
            saved("sort by aisle", "write in Polish"),
        ]
        self.edit_text.return_value = "- sort by aisle\n- write in Polish\n"
        _, stderr = self.run_cli("instructions")

        self.call.assert_called_with(
            CONFIG,
            replace_instructions,
            body=InstructionsEditModel(
                instructions=["sort by aisle", "write in Polish"], base_version=4
            ),
            apply=True,
        )
        self.assertIn("Instructions synced (2); notes will be updated", stderr)

    def test_instructions_no_apply_only_saves(self):
        self.call.side_effect = [INSTRUCTIONS, saved("write in Polish")]
        self.edit_text.return_value = "- write in Polish\n"
        _, stderr = self.run_cli("instructions", "--no-apply")

        self.call.assert_called_with(
            CONFIG,
            replace_instructions,
            body=InstructionsEditModel(
                instructions=["write in Polish"], base_version=4
            ),
            apply=False,
        )
        self.assertIn("Instructions synced (1).", stderr)

    def test_instructions_emptied_clears(self):
        self.call.side_effect = [INSTRUCTIONS, saved()]
        self.edit_text.return_value = ""
        _, stderr = self.run_cli("instructions")

        self.call.assert_called_with(
            CONFIG,
            replace_instructions,
            body=InstructionsEditModel(instructions=[], base_version=4),
            apply=True,
        )
        self.assertIn("Instructions synced (0).", stderr)

    def server_note(self, content):
        return NoteModel(
            note_id=NOTE_ID,
            content=content,
            is_default=True,
            updated_at=UPDATED_AT,
            version=4,
        )

    def test_edit_merges_changes_in_other_places(self):
        theirs = self.server_note("Shopping\n- milk\n- eggs")
        self.call.side_effect = [NOTE, conflict(theirs), theirs]
        self.edit_text.return_value = "Groceries\n- milk\n"
        _, stderr = self.run_cli("edit", "abc")

        # Pushed again without the editor, on top of the server's version
        self.edit_text.assert_called_once_with(NOTE.content)
        self.call.assert_called_with(
            CONFIG,
            edit_note_by_id,
            note_id=NOTE_ID,
            body=NoteUpdateModel(content="Groceries\n- milk\n- eggs\n", base_version=4),
        )
        self.assertIn("Merged with changes made on the server", stderr)
        self.assertIn("Note synced", stderr)

    def test_edit_conflict_is_resolved_in_the_editor(self):
        theirs = self.server_note("Shopping\n- soy milk")
        self.call.side_effect = [NOTE, conflict(theirs), theirs]
        self.edit_text.side_effect = [
            "Shopping\n- oat milk\n",
            "Shopping\n- oat and soy milk\n",
        ]
        _, stderr = self.run_cli("edit", "abc")

        self.edit_text.assert_called_with(
            "Shopping\n<<<<<<< yours\n- oat milk\n=======\n- soy milk\n>>>>>>> server\n"
        )
        self.call.assert_called_with(
            CONFIG,
            edit_note_by_id,
            note_id=NOTE_ID,
            body=NoteUpdateModel(
                content="Shopping\n- oat and soy milk\n", base_version=4
            ),
        )
        self.assertIn("resolve the conflicts", stderr)
        self.assertIn("Note synced", stderr)

    def test_edit_with_markers_left_is_saved_not_synced(self):
        unresolved = self.patch("pebbenote_cli.cli.UNRESOLVED_FILE")
        theirs = self.server_note("Shopping\n- soy milk")
        self.call.side_effect = [NOTE, conflict(theirs)]
        marked = "Shopping\n<<<<<<< yours\n- oat milk\n"
        self.edit_text.side_effect = ["Shopping\n- oat milk\n", marked]

        with self.assertRaises(SystemExit) as ctx:
            self.run_cli("edit", "abc")

        self.assertIn("Conflict markers left", ctx.exception.code)
        unresolved.write_text.assert_called_once_with(marked)
        self.assertEqual(self.call.call_count, 2)

    def test_instructions_merge_changes_made_elsewhere(self):
        theirs = InstructionsModel(
            instructions=["use metric units", "sort by aisle", "be brief"], version=5
        )
        merged = ["write in Polish", "sort by aisle", "be brief"]
        self.call.side_effect = [INSTRUCTIONS, conflict(theirs), saved(*merged)]
        self.edit_text.return_value = "- write in Polish\n- sort by aisle\n"
        _, stderr = self.run_cli("instructions")

        self.call.assert_called_with(
            CONFIG,
            replace_instructions,
            body=InstructionsEditModel(instructions=merged, base_version=5),
            apply=True,
        )
        self.assertIn("Merged with changes made on the server", stderr)
        self.assertIn("Instructions synced (3)", stderr)

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
