from typing import Annotated
from fastapi import APIRouter, Depends

from pebbenote.actions.action_service import NoteActionService
from pebbenote.actions.schemas import ActionEditModel
from pebbenote.notes.schemas import NoteModel


action_router = APIRouter(prefix="/action", tags=["Actions"])


@action_router.post("/")
async def apply_action(
    service: Annotated[NoteActionService, Depends()], payload: ActionEditModel
) -> NoteModel:
    return await service.create_and_apply_action(payload)
