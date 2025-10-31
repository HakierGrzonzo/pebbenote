from .schemas import Chat, Message


class AIAdapter:
    def map_messages(self, messages: list[Message]):
        for message in messages:
            ollama_message = {"role": message.kind, "content": message.content}
            yield ollama_message

    async def get_completion(self, chat: Chat) -> str:
        raise NotImplementedError()


class AIProvider:
    def __init__(self, ai_class: type[AIAdapter]) -> None:
        self.ai_object = ai_class()

    def __call__(
        self,
    ):
        """
        Returns an instance of the AI API adapter, will return 403 if the
        account is inactive
        """
        return self.ai_object
