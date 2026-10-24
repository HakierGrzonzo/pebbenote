from logging import getLogger

from ollama import (
    AsyncClient,
    ChatResponse,
    SystemOneChoiceAnswer,
    SystemOneChoiceQuestion,
)
from pydantic import ValidationError

from pebbenote.actions.prompts import rewrite_instruction_system_prompt

from ..config import settings
from .base import AIAdapter
from .markdown import render_markdown_list
from .schemas import InputKind, InstructionRewrite, NoteList

logger = getLogger(__name__)


class OllamaAdapter(AIAdapter):
    model = settings.CHAT_MODEL

    def __init__(self) -> None:
        self._ollama = AsyncClient()

    async def get_completion(self, chat):
        messages = [
            *self.map_messages(chat.messages),
        ]
        logger.info("Starting chat")
        response: ChatResponse = await self._ollama.chat(
            model=self.model,
            messages=messages,
            format=NoteList.model_json_schema(),
            options={"temperature": 0},
        )
        content = response.message.content
        assert content is not None
        try:
            note = NoteList.model_validate_json(content)
        except ValidationError:
            logger.exception("LLM returned data not matching the note schema")
            raise
        return render_markdown_list(note)

    async def classify_input(self, text: str) -> InputKind:
        # A failing classifier must never break plain dictation
        try:
            response = await self._ollama.systemone(
                model=settings.DECISION_MODEL,
                state=text,
                questions={
                    "kind": SystemOneChoiceQuestion(
                        instructions="What is the user dictating?",
                        criteria={
                            "note": "Content to add to, remove from or change in "
                            "a note",
                            "instruction": "A standing rule about how notes should "
                            "always be formatted, sorted or organized from now on",
                        },
                    )
                },
            )
            answer = response.answers["kind"]
            assert isinstance(answer, SystemOneChoiceAnswer)
        except Exception:
            logger.exception("Decision model failed, treating input as a note")
            return "note"

        return "instruction" if answer.choice == "instruction" else "note"

    async def rewrite_instruction(self, text: str) -> str:
        response: ChatResponse = await self._ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": rewrite_instruction_system_prompt},
                {"role": "user", "content": text},
            ],
            format=InstructionRewrite.model_json_schema(),
            options={"temperature": 0},
        )
        content = response.message.content
        assert content is not None
        try:
            return InstructionRewrite.model_validate_json(content).instruction
        except ValidationError:
            logger.exception("LLM returned data not matching the instruction schema")
            raise
