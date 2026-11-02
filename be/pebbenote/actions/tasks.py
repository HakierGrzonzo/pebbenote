from logging import getLogger
from uuid import UUID

from taskiq import Context, TaskiqDepends

from pebbenote.actions.action_service import NoteActionService
from pebbenote.actions.repository import NoteActionRepository
from pebbenote.config import settings
from pebbenote.db import async_session
from pebbenote.instructions.repository import UserInstructionRepository
from pebbenote.llm import ai_provider
from pebbenote.notes.repository import NoteRepository
from pebbenote.notes.schemas import NoteModel
from pebbenote.tables import ActionStatus
from pebbenote.worker import broker

logger = getLogger(__name__)


def is_last_attempt(context: Context) -> bool:
    # Mirrors how SmartRetryMiddleware counts attempts
    labels = context.message.labels
    retries = int(labels.get("_retries", 0)) + 1
    max_retries = int(labels.get("max_retries", settings.ACTION_MAX_RETRIES))
    return retries >= max_retries


@broker.task(retry_on_error=True, max_retries=settings.ACTION_MAX_RETRIES)
async def apply_action_task(
    action_id: str, owner: str, context: Context = TaskiqDepends()
) -> NoteModel:
    try:
        # There is no request here, so the repositories get the owner directly
        async with async_session() as session, session.begin():
            service = NoteActionService(
                NoteActionRepository(session),
                NoteRepository(session, owner),
                UserInstructionRepository(session, owner),
                ai_provider(),
            )
            return await service.apply_action(UUID(action_id))
    except Exception:
        if is_last_attempt(context):
            logger.exception("Giving up on action %s", action_id)
            async with async_session() as session, session.begin():
                await NoteActionRepository(session).set_status(
                    UUID(action_id), ActionStatus.failed
                )
        raise
