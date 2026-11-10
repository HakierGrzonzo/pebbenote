from typing import cast

from sqlalchemy import ColumnElement, Select, Text, asc, delete, func, insert, literal
from sqlalchemy.dialects.postgresql import ARRAY

from pebbenote.auth import CurrentUser
from pebbenote.db import DbSession
from pebbenote.tables import UserInstruction


class UserInstructionRepository:
    def __init__(self, session: DbSession, user: CurrentUser) -> None:
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
        await self.session.flush()

        return instruction.instruction_text

    async def replace_instructions(self, instruction_texts: list[str]) -> list[str]:
        await self.session.execute(
            delete(UserInstruction).where(UserInstruction.owner == self.user)
        )
        if instruction_texts:
            await self.session.execute(
                insert(UserInstruction).values(
                    [
                        {"owner": self.user, "instruction_text": text}
                        for text in instruction_texts
                    ]
                )
            )

        return instruction_texts

    def instructions_are(self, instruction_texts: list[str]) -> ColumnElement[bool]:
        """
        SQL condition: the user's instructions are exactly these, in any order.
        For a WHERE clause, so a write can depend on it without a race.
        """
        texts = ARRAY(Text)
        current = func.coalesce(
            Select(func.array_agg(UserInstruction.instruction_text, type_=texts))
            .where(UserInstruction.owner == self.user)
            .scalar_subquery(),
            literal([], texts),
            type_=texts,
        )
        expected = literal(instruction_texts, texts)

        return current.contains(expected) & current.contained_by(expected)
