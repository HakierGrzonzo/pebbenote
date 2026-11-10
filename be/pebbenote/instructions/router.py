from typing import Annotated

from fastapi import APIRouter, Depends

from pebbenote.actions.tasks import apply_instructions_task
from pebbenote.auth import CurrentUser
from pebbenote.db import DbSession
from pebbenote.instructions.repository import UserInstructionRepository
from pebbenote.instructions.schemas import InstructionsModel
from pebbenote.notes.repository import NoteRepository

instruction_router = APIRouter(prefix="/instruction", tags=["Instructions"])


@instruction_router.get("/")
async def list_instructions(
    repository: Annotated[UserInstructionRepository, Depends()],
) -> InstructionsModel:
    return InstructionsModel(instructions=await repository.list_instructions())


@instruction_router.put("/")
async def replace_instructions(
    repository: Annotated[UserInstructionRepository, Depends()],
    note_repository: Annotated[NoteRepository, Depends()],
    session: DbSession,
    user: CurrentUser,
    payload: InstructionsModel,
    apply: bool = True,
) -> InstructionsModel:
    """
    Replaces the standing instructions. Unless `apply` is false, the new ones
    are then applied in the background to every note of the user that is not
    changed in the meantime.
    """
    instructions = payload.instructions
    if sorted(instructions) == sorted(await repository.list_instructions()):
        return payload

    await repository.replace_instructions(instructions)
    notes = await note_repository.list_notes()
    # The worker uses its own connection, so the instructions must be visible
    await session.commit()

    if apply and instructions:
        for note in notes:
            await apply_instructions_task.kiq(
                note_id=str(note.note_id),
                note_updated_at=note.updated_at.isoformat(),
                instructions=instructions,
                owner=user,
            )

    return payload
