from typing import Literal

from .base import AIAdapter
from .schemas import Chat

type CallType = Literal["attachment", "chat"]


class MockAdapter(AIAdapter):
    def __init__(self) -> None:
        self._results: dict[CallType, str | None] = {
            "attachment": None,
            "chat": None,
        }
        self._parameters: dict[CallType, str | Chat | None] = {
            "attachment": None,
            "chat": None,
        }

    def set_result(self, value: str, kind: CallType = "chat"):
        self._results[kind] = value

    def get_called_with(self, kind: CallType = "chat") -> Chat | str:
        if (result := self._parameters[kind]) is None:
            raise Exception("Wasn't called")

        return result

    async def get_completion(self, chat: Chat) -> str:
        self._parameters["chat"] = chat
        if (result := self._results["chat"]) is None:
            raise Exception("Result is not set for the mock ai adapter")
        return result
