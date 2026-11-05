import os
import subprocess
from pathlib import Path
from unittest import TestCase, mock

from .editor import edit_text
from .errors import CliError


def temp_path_from(run: mock.Mock) -> Path:
    return Path(run.call_args.args[0][-1])


class EditTextTestCase(TestCase):
    def editor(self, **env):
        clean = {"EDITOR": "", "VISUAL": ""} | env
        return mock.patch.dict(os.environ, clean)

    def test_returns_edited_text_and_cleans_up(self):
        with self.editor(EDITOR="sed -i s/old/new/"):
            with mock.patch(
                "pebbenote_cli.editor.subprocess.run",
                wraps=subprocess.run,
            ) as run:
                self.assertEqual(edit_text("old text\n"), "new text\n")
        path = temp_path_from(run)
        self.assertEqual(path.suffix, ".md")
        self.assertFalse(path.exists())

    def test_failing_editor_raises_and_cleans_up(self):
        with self.editor(EDITOR="false"):
            with mock.patch(
                "pebbenote_cli.editor.subprocess.run",
                wraps=subprocess.run,
            ) as run:
                with self.assertRaises(CliError):
                    edit_text("text")
        self.assertFalse(temp_path_from(run).exists())

    def test_falls_back_to_visual(self):
        with self.editor(VISUAL="code --wait"):
            with mock.patch("pebbenote_cli.editor.subprocess.run") as run:
                run.return_value.returncode = 0
                edit_text("text")
        self.assertEqual(run.call_args.args[0][:2], ["code", "--wait"])

    def test_falls_back_to_vi(self):
        with self.editor():
            with mock.patch("pebbenote_cli.editor.subprocess.run") as run:
                run.return_value.returncode = 0
                edit_text("text")
        self.assertEqual(run.call_args.args[0][0], "vi")
