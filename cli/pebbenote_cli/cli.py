# PYTHON_ARGCOMPLETE_OK
"""Edit a Pebbenote note in $EDITOR and sync it with the backend on quit."""

import argparse
import sys

import argcomplete

from pebbenote_cli import api, auth
from pebbenote_cli.client.api.actions import apply_action
from pebbenote_cli.client.api.instructions import (
    list_instructions,
    replace_instructions,
)
from pebbenote_cli.client.api.notes import (
    delete_note,
    edit_note_by_id,
    get_note_by_id,
    list_notes,
)
from pebbenote_cli.client.models import (
    ActionAcceptedModel,
    ActionEditModel,
    InstructionsEditModel,
    NoteUpdateModel,
)
from pebbenote_cli.config import UNRESOLVED_FILE, load_config
from pebbenote_cli.editor import edit_text
from pebbenote_cli.errors import CliError, ConflictError
from pebbenote_cli.instructions import format_instructions, parse_instructions
from pebbenote_cli.merge import has_markers, merge3


def push_merging(base, edited, version, push, text_of):
    """
    Syncs `edited`, an edit of the text `base` that had `version` on the
    server, with push(text, base_version).

    When the server has a newer version, its text (text_of the conflict's
    current state) is merged with the edit like git would: changes in
    different places are combined and pushed again, changes to the same place
    are opened in the editor between conflict markers.
    """
    while True:
        try:
            return push(edited, version)
        except ConflictError as conflict:
            theirs = text_of(conflict.current)
            edited, has_conflicts = merge3(base, edited, theirs)
            base, version = theirs, conflict.current.version

        if not has_conflicts:
            print("Merged with changes made on the server.", file=sys.stderr)
            continue
        print(
            "Changed on the server in the same places; resolve the conflicts.",
            file=sys.stderr,
        )
        edited = edit_text(edited)
        if has_markers(edited):
            UNRESOLVED_FILE.parent.mkdir(parents=True, exist_ok=True)
            UNRESOLVED_FILE.write_text(edited)
            raise CliError(
                f"Conflict markers left; not syncing. Your text is in {UNRESOLVED_FILE}"
            )


def cmd_edit(config, args):
    note = api.call(config, get_note_by_id, note_id=args.note_id)
    if not sys.stdout.isatty():
        sys.stdout.write(note.content)
        return
    edited = edit_text(note.content)
    if edited == note.content:
        print("No changes; nothing to sync.", file=sys.stderr)
        return

    def push(text, base_version):
        # The note that was read: "default" may point at another one by now
        api.call(
            config,
            edit_note_by_id,
            note_id=note.note_id,
            body=NoteUpdateModel(content=text, base_version=base_version),
        )

    push_merging(note.content, edited, note.version, push, lambda note: note.content)
    print("Note synced.", file=sys.stderr)


def first_line(note):
    return note.content.splitlines()[0] if note.content else ""


def cmd_delete(config, args):
    note = api.call(config, get_note_by_id, note_id=args.note_id)
    if not args.yes:
        if not sys.stdin.isatty():
            raise CliError("Not deleting without a terminal to confirm; pass --yes")
        answer = input(f'Delete note "{first_line(note)}"? [y/N] ')
        if answer.strip().lower() not in ("y", "yes"):
            print("Not deleted.", file=sys.stderr)
            return
    # The note that was read: "default" may point at another one by now
    api.call(config, delete_note, note_id=note.note_id)
    print("Note deleted.", file=sys.stderr)


def cmd_list(config, _args):
    for note in api.call(config, list_notes):
        marker = "*" if note.is_default else " "
        print(f"{marker} {note.note_id}  {first_line(note)}")


def cmd_instructions(config, args):
    current = api.call(config, list_instructions)
    text = format_instructions(current.instructions)
    if not sys.stdout.isatty():
        sys.stdout.write(text)
        return
    edited = edit_text(text)
    # The order of the instructions does not matter
    if sorted(parse_instructions(edited)) == sorted(current.instructions):
        print("No changes; nothing to sync.", file=sys.stderr)
        return
    apply = not args.no_apply

    def push(text, base_version):
        return api.call(
            config,
            replace_instructions,
            body=InstructionsEditModel(
                instructions=parse_instructions(text), base_version=base_version
            ),
            apply=apply,
        )

    synced = push_merging(
        text,
        edited,
        current.version,
        push,
        lambda current: format_instructions(current.instructions),
    ).instructions
    message = f"Instructions synced ({len(synced)})"
    if apply and synced:
        message += "; notes will be updated in the background"
    print(f"{message}.", file=sys.stderr)


def cmd_action(config, args):
    result = api.call(
        config,
        apply_action,
        body=ActionEditModel(note_id=args.note, action=" ".join(args.text)),
    )
    if isinstance(result, ActionAcceptedModel):
        print(
            "Action is still being applied; "
            "the note will be updated in the background.",
            file=sys.stderr,
        )
        return
    print("Action applied.", file=sys.stderr)
    sys.stdout.write(result.content)
    if result.content and not result.content.endswith("\n"):
        sys.stdout.write("\n")


def complete_note_ids(**_kwargs):
    """Completes note ids, with each note's first line as description."""
    ids = {"default": "the default note"}
    try:
        # Completion runs on every Tab: never start a login from it
        notes = api.call(load_config(), list_notes, interactive=False)
    except Exception:
        # Logged out, offline or a broken config: complete what we know
        return ids
    for note in notes:
        ids[str(note.note_id)] = first_line(note)
    return ids


def cmd_completion(_config, args):
    sys.stdout.write(argcomplete.shellcode(["pebbenote"], shell=args.shell))


def cmd_login(config, _args):
    auth.login(config)
    print("Logged in.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(prog="pebbenote", description=__doc__)
    sub = parser.add_subparsers(dest="command")
    # `pebbenote <note_id>` edits that note, so complete ids next to commands
    sub.completer = complete_note_ids

    edit = sub.add_parser("edit", help="edit a note (default command)")
    edit.add_argument(
        "note_id", nargs="?", default="default"
    ).completer = complete_note_ids
    edit.set_defaults(func=cmd_edit)

    sub.add_parser("list", help="list notes").set_defaults(func=cmd_list)
    delete = sub.add_parser("delete", help="delete a note")
    delete.add_argument(
        "note_id", nargs="?", default="default"
    ).completer = complete_note_ids
    delete.add_argument(
        "-y", "--yes", action="store_true", help="do not ask for confirmation"
    )
    delete.set_defaults(func=cmd_delete)
    instructions = sub.add_parser(
        "instructions", help="edit the standing instructions, one per list item"
    )
    instructions.add_argument(
        "--no-apply",
        action="store_true",
        help="only save the instructions, do not apply them to existing notes",
    )
    instructions.set_defaults(func=cmd_instructions)
    action = sub.add_parser("action", help="ask the assistant to change a note")
    action.add_argument("text", nargs="+", help="what to do, e.g. add oat milk")
    action.add_argument(
        "--note", default="default", help="note id (default note)"
    ).completer = complete_note_ids
    action.set_defaults(func=cmd_action)
    sub.add_parser("login", help="force a new login").set_defaults(func=cmd_login)
    completion = sub.add_parser("completion", help="print the shell completion script")
    completion.add_argument("shell", choices=["bash", "zsh", "fish"])
    completion.set_defaults(func=cmd_completion)

    # Answers the shell's completion request and exits, when there is one
    argcomplete.autocomplete(parser)

    argv = sys.argv[1:]
    # `edit` is the default command: `pebbenote` and `pebbenote <note_id>`
    if not argv or (argv[0] not in sub.choices and not argv[0].startswith("-")):
        argv = ["edit", *argv]
    args = parser.parse_args(argv)
    try:
        args.func(load_config(), args)
    except CliError as e:
        sys.exit(f"error: {e}")
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
