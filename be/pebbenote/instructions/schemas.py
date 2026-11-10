from typing import Annotated

from pydantic import BaseModel, StringConstraints

InstructionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class InstructionsModel(BaseModel):
    instructions: list[InstructionText]
