from logging import getLogger

from ollama import AsyncClient, ChatResponse


from .base import AIAdapter

logger = getLogger(__name__)


class OllamaAdapter(AIAdapter):
    model = "qwen3:30b"

    def __init__(self) -> None:
        self._ollama = AsyncClient()

    async def get_completion(self, chat):
        messages = [
            *self.map_messages(chat.messages),
        ]
        logger.info("Starting chat")
        response: ChatResponse = await self._ollama.chat(
            model=self.model, messages=messages
        )
        content = response.message.content
        assert content is not None
        return content.strip()
