from collections.abc import Iterator
from difflib import unified_diff
from itertools import pairwise

from pebbenote.llm.schemas import Chat, Message
from pebbenote.notes.schemas import NoteRevisionModel

from .prompts import (
    apply_action_system_prompt,
    manual_edit_prefix,
    note_now_prefix,
    standing_instructions_prefix,
)


def note_diff(before: str, after: str) -> str:
    """A unified diff of two note versions, a format models know from code"""
    return "\n".join(
        unified_diff(
            before.splitlines(), after.splitlines(), "note", "note", lineterm=""
        )
    )


def build_history(revisions: list[NoteRevisionModel]) -> Iterator[Message]:
    """
    Replays the revisions as a chat: the oldest one is the starting note, then
    each change as a diff, asked for by the user and answered by the LLM, or
    made by the user by hand. Ends with the current note.
    """
    yield Message(kind="user", content=revisions[0].content)

    for before, after in pairwise(revisions):
        diff = note_diff(before.content, after.content)
        if after.action is None:
            yield Message(kind="user", content=f"{manual_edit_prefix}\n{diff}")
        else:
            yield Message(kind="user", content=after.action)
            yield Message(kind="assistant", content=diff)

    # Small models drift back to older states, so restate the current one
    yield Message(kind="user", content=f"{note_now_prefix}\n{revisions[-1].content}")


def build_note_chat(
    revisions: list[NoteRevisionModel],
    instructions: list[str],
    preamble: str,
    user_message: str | None,
) -> Chat:
    """
    The chat that asks for a new version of the note: the history of the given
    revisions, the standing instructions, then the preamble and the user's
    request, if there is one
    """
    messages = [
        Message(kind="system", content=apply_action_system_prompt),
        *build_history(revisions),
    ]
    if instructions:
        bullets = "\n".join(f"- {instruction}" for instruction in instructions)
        messages.append(
            Message(
                kind="assistant",
                content=f"{standing_instructions_prefix}\n{bullets}",
            )
        )
    messages.append(Message(kind="system", content=preamble))
    if user_message is not None:
        messages.append(Message(kind="user", content=user_message))

    return Chat(messages=messages)
