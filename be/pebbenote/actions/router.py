from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from taskiq.exceptions import TaskiqResultTimeoutError

from pebbenote.actions.action_service import NoteActionService
from pebbenote.actions.schemas import ActionAcceptedModel, ActionEditModel
from pebbenote.actions.tasks import apply_action_task
from pebbenote.auth import CurrentUser
from pebbenote.config import settings
from pebbenote.db import DbSession
from pebbenote.http_dates import last_modified
from pebbenote.notes.schemas import NoteModel
from pebbenote.notes.view import NoteView

action_router = APIRouter(prefix="/action", tags=["Actions"])

# Seconds the client should wait between polls of the note
POLL_INTERVAL = 2


@action_router.post(
    "/",
    response_model=NoteModel,
    responses={
        status.HTTP_202_ACCEPTED: {
            "model": ActionAcceptedModel,
            "description": "Still applying, poll the note with If-Modified-Since",
        }
    },
)
async def apply_action(
    service: Annotated[NoteActionService, Depends()],
    note_view: Annotated[NoteView, Depends()],
    session: DbSession,
    user: CurrentUser,
    payload: ActionEditModel,
) -> NoteModel | JSONResponse:
    action = await service.enqueue_action(payload)
    # The worker uses its own connection, so the action must be visible first
    await session.commit()

    task = await apply_action_task.kiq(action_id=str(action.note_action_id), owner=user)
    try:
        result = await task.wait_result(timeout=settings.ACTION_WAIT_SECONDS)
        if not result.is_err:
            return NoteModel.model_validate(result.return_value)
    except TaskiqResultTimeoutError:
        pass

    # Read after waiting: the note last changed when the action was added, a
    # whole wait ago, so the date is exact and the first poll can be a 304
    note_last_modified = last_modified(await note_view.get_updated_at(action.note_id))

    accepted = ActionAcceptedModel(action=action, note_last_modified=note_last_modified)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=accepted.model_dump(mode="json"),
        headers={
            "Location": f"/note/{action.note_id}",
            "Retry-After": str(POLL_INTERVAL),
            "Last-Modified": note_last_modified,
        },
    )
