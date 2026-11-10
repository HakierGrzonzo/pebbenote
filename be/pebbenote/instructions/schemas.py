from typing import Annotated

from pydantic import BaseModel, StringConstraints

InstructionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class InstructionsModel(BaseModel):
    instructions: list[str]
    # The number of revisions of the list, an edit has to name the one it is
    # based on
    version: int


class InstructionsEditModel(BaseModel):
    instructions: list[InstructionText]
    # The version of the list the edit was made on
    base_version: int


class InstructionsConflictModel(BaseModel):
    detail: str
    # The instructions as they are now, to merge the edit with
    current: InstructionsModel
