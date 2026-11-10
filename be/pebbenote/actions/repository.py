from typing import cast
from uuid import UUID

from sqlalchemy import Select, asc

from pebbenote.actions.schemas import ActionModel
from pebbenote.db import DbSession
from pebbenote.tables import ActionStatus, NoteAction, utc_now


class NoteActionRepository:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    @classmethod
    def map_action(cls, action: NoteAction) -> ActionModel:
        return ActionModel(
            note_action_id=action.note_action_id,
            note_id=action.note_id,
            action=action.action_text,
            status=action.status,
            created_at=action.created_at,
            updated_at=action.updated_at,
        )

    async def list_actions(self, note_id: UUID):
        query = (
            Select(NoteAction)
            .where(NoteAction.note_id == note_id)
            .order_by(asc(NoteAction.created_at), asc(NoteAction.note_action_id))
        )

        results = await self.session.execute(query)

        actions = cast(list[NoteAction], results.scalars().all())

        return [self.map_action(action) for action in actions]

    async def first_pending(self, note_id: UUID) -> UUID | None:
        """The head of the note's queue: its oldest action that is not applied yet"""
        query = (
            Select(NoteAction.note_action_id)
            .where(NoteAction.note_id == note_id)
            .where(NoteAction.status == ActionStatus.pending)
            .order_by(asc(NoteAction.created_at), asc(NoteAction.note_action_id))
            .limit(1)
        )

        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_action(self, action_id: UUID) -> ActionModel:
        action = await self.session.get_one(NoteAction, action_id)
        return self.map_action(action)

    async def add_action(
        self,
        note_id: UUID,
        action_text: str,
        status: ActionStatus = ActionStatus.done,
    ):
        # The time of the insert, not of the transaction: actions are queued
        # in the order they got hold of the note
        action = NoteAction(
            note_id=note_id,
            action_text=action_text,
            status=status,
            created_at=utc_now(),
        )
        self.session.add(action)
        await self.session.flush()

        return self.map_action(action)

    async def touch(self, action_id: UUID) -> None:
        """
        Marks a pending action as started now. Its updated_at tells whether
        its task may have been lost.
        """
        action = await self.session.get_one(NoteAction, action_id)
        action.updated_at = utc_now()
        await self.session.flush()

    async def set_status(self, action_id: UUID, status: ActionStatus) -> ActionModel:
        action = await self.session.get_one(NoteAction, action_id)
        action.status = status
        await self.session.flush()

        return self.map_action(action)
