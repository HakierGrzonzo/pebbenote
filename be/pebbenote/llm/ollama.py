from logging import getLogger

from ollama import (
    AsyncClient,
    ChatResponse,
    SystemOneChoiceAnswer,
    SystemOneChoiceQuestion,
)

from pebbenote.actions.prompts import (
    generate_title_system_prompt,
    rewrite_instruction_system_prompt,
)

from ..config import settings
from .base import AIAdapter
from .schemas import InputClassification
from .telemetry import llm_call

logger = getLogger(__name__)


class OllamaAdapter(AIAdapter):
    model = settings.CHAT_MODEL
    temperature = settings.CHAT_TEMPERATURE

    def __init__(self) -> None:
        self._ollama = AsyncClient()

    async def _chat(self, task: str, messages: list) -> str:
        with llm_call(self.model, task, temperature=self.temperature) as call:
            response: ChatResponse = await self._ollama.chat(
                model=self.model,
                messages=messages,
                options={"temperature": self.temperature},
            )
            call.record_response(
                response.model, response.prompt_eval_count, response.eval_count
            )
        return _strip_fences(response.message.content or "")

    async def get_completion(self, chat):
        logger.info("Starting chat")
        return await self._chat("note", self.map_messages(chat.messages))

    async def classify_input(self, text: str) -> InputClassification:
        # A failing classifier must never break plain dictation
        try:
            with llm_call(settings.DECISION_MODEL, "classify") as call:
                response = await self._ollama.systemone(
                    model=settings.DECISION_MODEL,
                    state=text,
                    questions={
                        "kind": SystemOneChoiceQuestion(
                            instructions="What is the user dictating?",
                            criteria={
                                "note": "Content to add to, remove from or change "
                                "in a note",
                                "instruction": "A standing rule about how notes "
                                "should always be formatted, sorted or organized "
                                "from now on",
                            },
                        ),
                        "history": SystemOneChoiceQuestion(
                            instructions="Does the user refer to earlier "
                            "versions of the note?",
                            criteria={
                                "history": "Refers to earlier changes or states "
                                "of the note: undo, revert, bring back or restore "
                                "something, as it was before",
                                "current": "Only needs the note as it is now",
                            },
                        ),
                    },
                )
                call.record_response(
                    response.model,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                )
                kind = response.answers["kind"]
                history = response.answers["history"]
                assert isinstance(kind, SystemOneChoiceAnswer)
                assert isinstance(history, SystemOneChoiceAnswer)
        except Exception:
            # Sending the whole history is the safe default
            logger.exception("Decision model failed, treating input as a note")
            return InputClassification(kind="note", needs_history=True)

        return InputClassification(
            kind="instruction" if kind.choice == "instruction" else "note",
            needs_history=history.choice == "history",
        )

    async def rewrite_instruction(self, text: str) -> str:
        instruction = await self._chat(
            "rewrite_instruction",
            [
                {"role": "system", "content": rewrite_instruction_system_prompt},
                {"role": "user", "content": text},
            ],
        )
        instruction = " ".join(instruction.split()).strip('"')
        # An instruction about capital letters gets the model to lowercase the
        # sentence itself
        if instruction.lower().startswith("i should"):
            instruction = "I should" + instruction[len("I should") :]
        return instruction

    async def generate_title(self, note: str) -> str:
        title = await self._chat(
            "title",
            [
                {"role": "system", "content": generate_title_system_prompt},
                {"role": "user", "content": note},
            ],
        )
        # A title is one line
        return " ".join(title.split()).strip('"')


def _strip_fences(text: str) -> str:
    """The answer without a surrounding ``` code block, models like to add one"""
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
