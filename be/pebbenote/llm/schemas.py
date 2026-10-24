from typing import Literal

from pydantic import BaseModel

type InputKind = Literal["note", "instruction"]


class Message(BaseModel):
    kind: Literal["assistant", "user", "system"]
    content: str


class Chat(BaseModel):
    messages: list[Message]


class NoteItem(BaseModel):
    text: str
    children: list["NoteItem"] = []


class NoteList(BaseModel):
    items: list[NoteItem]


class InstructionRewrite(BaseModel):
    instruction: str
