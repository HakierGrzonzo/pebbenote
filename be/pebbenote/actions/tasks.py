from logging import getLogger
from typing import Annotated
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import Context, TaskiqDepends

from pebbenote.actions.action_service import NoteActionService
from pebbenote.actions.repository import NoteActionRepository
from pebbenote.auth import get_current_user
from pebbenote.config import settings
from pebbenote.db import get_db
from pebbenote.notes.schemas import NoteModel
from pebbenote.tables import ActionStatus
from pebbenote.versioning import VersionConflict
from pebbenote.worker import broker

logger = getLogger(__name__)


def task_owner(context: Annotated[Context, TaskiqDepends()]) -> str:
    """Stands in for get_current_user, the API passes the owner along"""
    return context.message.kwargs["owner"]


# taskiq resolves the FastAPI Depends of the service and repositories, only
# the user has to come from the task instead of a bearer token
broker.dependency_overrides[get_current_user] = task_owner


def is_last_attempt(context: Context) -> bool:
    # Mirrors how SmartRetryMiddleware counts attempts
    labels = context.message.labels
    retries = int(labels.get("_retries", 0)) + 1
    max_retries = int(labels.get("max_retries", settings.ACTION_MAX_RETRIES))
    return retries >= max_retries


@broker.task(retry_on_error=True, max_retries=settings.ACTION_MAX_RETRIES)
async def apply_action_task(
    action_id: str,
    owner: str,
    context: Annotated[Context, TaskiqDepends()],
    session: Annotated[AsyncSession, TaskiqDepends(get_db)],
    service: Annotated[NoteActionService, TaskiqDepends()],
    actions: Annotated[NoteActionRepository, TaskiqDepends()],
) -> NoteModel:
    try:
        return await service.apply_action(UUID(action_id))
    except Exception:
        if is_last_attempt(context):
            logger.exception("Giving up on action %s", action_id)
            # Drop the failed attempt's writes, then record the failure
            await session.rollback()
            await actions.set_status(UUID(action_id), ActionStatus.failed)
            await session.commit()
        raise


@broker.task(retry_on_error=True, max_retries=settings.ACTION_MAX_RETRIES)
async def apply_instructions_task(
    note_id: str,
    owner: str,
    session: Annotated[AsyncSession, TaskiqDepends(get_db)],
    service: Annotated[NoteActionService, TaskiqDepends()],
    reruns: int = 0,
) -> NoteModel | None:
    """
    Applies the user's standing instructions to one note. Starts itself again
    when the note or the instructions change while the LLM is busy.
    """
    try:
        return await service.apply_instructions(UUID(note_id))
    except VersionConflict:
        if reruns >= settings.ACTION_MAX_RERUNS:
            raise
        logger.info("Note %s or the instructions have changed, rerunning", note_id)
        await session.rollback()
        await apply_instructions_task.kiq(
            note_id=note_id, owner=owner, reruns=reruns + 1
        )
        return None
