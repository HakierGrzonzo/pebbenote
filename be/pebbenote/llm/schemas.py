from typing import Literal

from pydantic import BaseModel


class Message(BaseModel):
    kind: Literal["assistant", "user", "system"]
    content: str


class Chat(BaseModel):
    messages: list[Message]
