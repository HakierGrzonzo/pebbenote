from sqlalchemy import Select, desc, func
from sqlalchemy.dialects.postgresql import distinct_on, insert

from pebbenote.auth import CurrentUser
from pebbenote.db import DbSession
from pebbenote.tables import InstructionList, InstructionRevision

from .exceptions import InstructionsConflict
from .schemas import InstructionsEditModel, InstructionsModel


class UserInstructionRepository:
    """
    The standing instructions of the user. Versioned like a note: the list is
    its latest revision, the version is the number of that revision.
    """

    def __init__(self, session: DbSession, user: CurrentUser) -> None:
        self.session = session
        self.user = user

    def _select_list(self) -> Select[tuple[InstructionList, InstructionRevision, int]]:
        version = func.row_number().over(
            partition_by=InstructionRevision.instruction_list_id,
            order_by=(
                InstructionRevision.created_at,
                InstructionRevision.instruction_revision_id,
            ),
        )
        latest_revision_id = (
            Select(
                InstructionRevision.instruction_list_id,
                InstructionRevision.instruction_revision_id,
                version.label("version"),
            )
            .ext(distinct_on(InstructionRevision.instruction_list_id))
            .order_by(
                InstructionRevision.instruction_list_id,
                desc(InstructionRevision.created_at),
                desc(InstructionRevision.instruction_revision_id),
            )
            .cte("latest_revision_id")
        )
        return (
            Select(InstructionList, InstructionRevision, latest_revision_id.c.version)
            .join(
                latest_revision_id,
                latest_revision_id.c.instruction_list_id
                == InstructionList.instruction_list_id,
            )
            .join(
                InstructionRevision,
                InstructionRevision.instruction_revision_id
                == latest_revision_id.c.instruction_revision_id,
            )
            .where(InstructionList.owner == self.user)
        )

    async def _create_list(self) -> None:
        # The unique owner makes this safe against concurrent requests
        list_id = (
            await self.session.execute(
                insert(InstructionList)
                .values(owner=self.user)
                .on_conflict_do_nothing(index_elements=[InstructionList.owner])
                .returning(InstructionList.instruction_list_id)
            )
        ).scalar_one_or_none()

        if list_id is not None:
            self.session.add(
                InstructionRevision(instruction_list_id=list_id, instructions=[])
            )
            await self.session.flush()

    async def _raw_get_instructions(
        self,
    ) -> tuple[InstructionList, InstructionRevision, int]:
        query = self._select_list()

        row = (await self.session.execute(query)).one_or_none()

        if row is None:
            # The first time the user's instructions are looked at
            await self._create_list()
            row = (await self.session.execute(query)).one()

        instruction_list, revision, version = row
        return instruction_list, revision, version

    async def get_instructions(self) -> InstructionsModel:
        _, revision, version = await self._raw_get_instructions()

        return InstructionsModel(instructions=revision.instructions, version=version)

    async def claim_version(self, base_version: int) -> InstructionsModel:
        """
        The first step of a write that is based on base_version of the
        instructions: raises InstructionsConflict, with the instructions as
        they are now, when that is no longer the latest version. Otherwise the
        list is locked for the caller's write, until the transaction ends.
        """
        instruction_list, _, _ = await self._raw_get_instructions()
        await self.session.execute(
            Select(InstructionList.instruction_list_id)
            .where(
                InstructionList.instruction_list_id
                == instruction_list.instruction_list_id
            )
            .with_for_update()
        )
        # Read again in a new statement: it sees what a writer that held the
        # lock before has committed
        instructions = await self.get_instructions()
        if instructions.version != base_version:
            raise InstructionsConflict(instructions)

        return instructions

    async def add_revision(self, instruction_texts: list[str]) -> InstructionsModel:
        """
        Makes the texts the instructions of the user. The caller has claimed
        the version they are based on.
        """
        instruction_list, _, _ = await self._raw_get_instructions()
        self.session.add(
            InstructionRevision(
                instruction_list_id=instruction_list.instruction_list_id,
                instructions=instruction_texts,
            )
        )
        await self.session.flush()

        return await self.get_instructions()

    async def replace_instructions(
        self, instructions_model: InstructionsEditModel
    ) -> InstructionsModel:
        """An edit by hand, one that changes nothing is not stored"""
        instructions = await self.claim_version(instructions_model.base_version)

        # The order of the instructions does not matter
        if sorted(instructions_model.instructions) == sorted(instructions.instructions):
            return instructions
        return await self.add_revision(instructions_model.instructions)
