import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from pebbenote_cli.errors import CliError


def edit_text(text):
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", prefix="pebbenote-", delete=False
    ) as f:
        f.write(text)
        path = f.name
    try:
        result = subprocess.run([*shlex.split(editor), path])
        if result.returncode != 0:
            raise CliError(f"Editor exited with {result.returncode}; not syncing")
        return Path(path).read_text()
    finally:
        os.unlink(path)
