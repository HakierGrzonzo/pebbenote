from .schemas import Chat, InputClassification, Message


class AIAdapter:
    def map_messages(self, messages: list[Message]):
        for message in messages:
            ollama_message = {"role": message.kind, "content": message.content}
            yield ollama_message

    async def get_completion(self, chat: Chat) -> str:
        raise NotImplementedError()

    async def classify_input(self, text: str) -> InputClassification:
        """
        Decides whether the text is note content or a standing instruction,
        and whether the note's history is needed to act on it
        """
        raise NotImplementedError()

    async def rewrite_instruction(self, text: str) -> str:
        """Rewrites a user utterance as a first person standing instruction"""
        raise NotImplementedError()

    async def generate_title(self, note: str) -> str:
        """A short one line title for the note"""
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
