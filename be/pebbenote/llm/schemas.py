from typing import Literal

from pydantic import BaseModel

type InputKind = Literal["note", "instruction"]


class Message(BaseModel):
    kind: Literal["assistant", "user", "system"]
    content: str


class Chat(BaseModel):
    messages: list[Message]


class InputClassification(BaseModel):
    kind: InputKind
    # Whether the past revisions of the note are needed, e.g. for an undo
    needs_history: bool
