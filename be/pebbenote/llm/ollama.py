from logging import getLogger

from ollama import AsyncClient, ChatResponse
from pydantic import ValidationError

from .base import AIAdapter
from .markdown import render_markdown_list
from .schemas import NoteList

logger = getLogger(__name__)


class OllamaAdapter(AIAdapter):
    model = "gemma4:e2b"

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
