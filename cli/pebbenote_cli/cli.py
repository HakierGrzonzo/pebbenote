"""Edit a Pebbenote note in $EDITOR and sync it with the backend on quit."""

import argparse
import sys

from pebbenote_cli import api, auth
from pebbenote_cli.config import load_config
from pebbenote_cli.editor import edit_text
from pebbenote_cli.errors import CliError


def cmd_edit(config, args):
    note = api.call(config, "GET", f"/note/{args.note_id}")
    if not sys.stdout.isatty():
        sys.stdout.write(note["content"])
        return
    edited = edit_text(note["content"])
    if edited == note["content"]:
        print("No changes; nothing to sync.", file=sys.stderr)
        return
    api.call(config, "PATCH", f"/note/{args.note_id}", {"content": edited})
    print("Note synced.", file=sys.stderr)


def cmd_list(config, _args):
    for note in api.call(config, "GET", "/note/"):
        marker = "*" if note["is_default"] else " "
        first_line = note["content"].splitlines()[0] if note["content"] else ""
        print(f"{marker} {note['note_id']}  {first_line}")


def cmd_login(config, _args):
    auth.login(config)
    print("Logged in.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(prog="pebbenote", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    edit = sub.add_parser("edit", help="edit a note (default command)")
    edit.add_argument("note_id", nargs="?", default="default")
    edit.set_defaults(func=cmd_edit)

    sub.add_parser("list", help="list notes").set_defaults(func=cmd_list)
    sub.add_parser("login", help="force a new login").set_defaults(func=cmd_login)

    args = parser.parse_args()
    if args.command is None:
        args = parser.parse_args(["edit", *sys.argv[1:]])
    try:
        args.func(load_config(), args)
    except CliError as e:
        sys.exit(f"error: {e}")
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
