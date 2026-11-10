from typing import Annotated

from fastapi import APIRouter, Depends, status

from pebbenote.actions.tasks import apply_instructions_task
from pebbenote.auth import CurrentUser
from pebbenote.db import DbSession
from pebbenote.instructions.repository import UserInstructionRepository
from pebbenote.instructions.schemas import (
    InstructionsConflictModel,
    InstructionsEditModel,
    InstructionsModel,
)
from pebbenote.notes.repository import NoteRepository

instruction_router = APIRouter(prefix="/instruction", tags=["Instructions"])


@instruction_router.get("/")
async def list_instructions(
    repository: Annotated[UserInstructionRepository, Depends()],
) -> InstructionsModel:
    return await repository.get_instructions()


@instruction_router.put(
    "/",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": InstructionsConflictModel,
            "description": "The instructions have changed since base_version",
        }
    },
)
async def replace_instructions(
    repository: Annotated[UserInstructionRepository, Depends()],
    note_repository: Annotated[NoteRepository, Depends()],
    session: DbSession,
    user: CurrentUser,
    payload: InstructionsEditModel,
    apply: bool = True,
) -> InstructionsModel:
    """
    Replaces the standing instructions. Unless `apply` is false, the new ones
    are then applied in the background to every note of the user.
    """
    instructions = await repository.replace_instructions(payload)
    if instructions.version == payload.base_version:
        # Nothing has changed
        return instructions

    notes = await note_repository.list_notes()
    # The worker uses its own connection, so the instructions must be visible
    await session.commit()

    if apply and instructions.instructions:
        for note in notes:
            await apply_instructions_task.kiq(note_id=str(note.note_id), owner=user)

    return instructions
