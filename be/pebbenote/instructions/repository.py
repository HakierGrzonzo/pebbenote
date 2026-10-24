from typing import cast

from sqlalchemy import Select, asc

from pebbenote.db import DbSession
from pebbenote.pebble_tokens import PebbleUserToken
from pebbenote.tables import UserInstruction


class UserInstructionRepository:
    def __init__(self, session: DbSession, user: PebbleUserToken) -> None:
        self.session = session
        self.user = user

    async def list_instructions(self) -> list[str]:
        query = (
            Select(UserInstruction)
            .where(UserInstruction.owner == self.user)
            .order_by(asc(UserInstruction.created_at))
        )

        results = await self.session.execute(query)

        instructions = cast(list[UserInstruction], results.scalars().all())

        return [instruction.instruction_text for instruction in instructions]

    async def add_instruction(self, instruction_text: str) -> str:
        instruction = UserInstruction(
            owner=self.user, instruction_text=instruction_text
        )
        self.session.add(instruction)
        await self.session.flush([instruction])

        return instruction.instruction_text
