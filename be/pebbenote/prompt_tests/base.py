import os
import re
from datetime import UTC, datetime
from unittest import IsolatedAsyncioTestCase, skipUnless
from uuid import uuid4

from ollama import AsyncClient

from pebbenote.actions.history import build_note_chat
from pebbenote.actions.prompts import (
    apply_action_preamble,
    apply_instructions_preamble,
)
from pebbenote.llm.ollama import OllamaAdapter
from pebbenote.notes.schemas import NoteRevisionModel

ENABLED = bool(os.environ.get("PEBBENOTE_PROMPT_TESTS"))

NOTE_ID = uuid4()


def revision(content: str, action: str | None = None) -> NoteRevisionModel:
    """A revision of the note, made by the action, or by hand when None"""
    return NoteRevisionModel(
        note_revision_id=uuid4(),
        note_id=NOTE_ID,
        content=content,
        action=action,
        created_at=datetime.now(UTC),
    )


def _normalize(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(".:")


def _lines(note: str) -> list[tuple[int, str]]:
    """The entries of a markdown list as (depth, text)"""
    entries = []
    for line in note.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        text = re.sub(r"^\s*[-*]\s*", "", line)
        entries.append((indent // 4, _normalize(text)))
    return entries


@skipUnless(ENABLED, "set PEBBENOTE_PROMPT_TESTS=1 to run against Ollama")
class PromptTestCase(IsolatedAsyncioTestCase):
    maxDiff = None

    async def asyncSetUp(self):
        try:
            async with AsyncClient() as client:
                await client.list()
        except Exception as error:
            raise RuntimeError(
                "Ollama is not reachable: start it, or commit with SKIP=prompt-tests"
            ) from error
        self.ai = OllamaAdapter()
        # Its connections belong to this test's event loop
        self.addAsyncCleanup(self.ai._ollama.close)

    async def edit(
        self,
        *revisions: NoteRevisionModel,
        action: str | None,
        instructions: list[str] = [],
    ) -> str:
        """
        The new note for the action, or for applying the instructions when
        the action is None, as the production chat asks for it
        """
        preamble = apply_action_preamble if action else apply_instructions_preamble
        chat = build_note_chat(list(revisions), instructions, preamble, action)
        return await self.ai.get_completion(chat)

    def entries(self, note: str) -> list[str]:
        return [text for _, text in _lines(note)]

    def assertHasEntry(self, note: str, entry: str):
        self.assertIn(_normalize(entry), self.entries(note), f"in:\n{note}")

    def assertNoEntry(self, note: str, entry: str):
        """No entry mentions it, also not as part of a longer one"""
        word = _normalize(entry)
        found = [text for text in self.entries(note) if word in text]
        self.assertEqual(found, [], f"in:\n{note}")

    def assertMentions(self, note: str, entry: str):
        """Some entry contains the text"""
        word = _normalize(entry)
        self.assertTrue(
            any(word in text for text in self.entries(note)), f"{entry} in:\n{note}"
        )

    def assertNestedUnder(self, note: str, child: str, parent: str):
        """The child is an entry nested, at any depth, under the parent"""
        child, parent = _normalize(child), _normalize(parent)
        stack: list[tuple[int, str]] = []
        for depth, text in _lines(note):
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if child in text and any(parent in p for _, p in stack):
                return
            stack.append((depth, text))
        self.fail(f"{child!r} not nested under {parent!r} in:\n{note}")
