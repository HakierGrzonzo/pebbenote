from typing import cast
from uuid import UUID

from sqlalchemy import Select, asc
from pebbenote.actions.schemas import ActionEditModel, ActionModel
from pebbenote.db import DbSession
from pebbenote.tables import NoteAction


class NoteActionRepository:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    @classmethod
    def map_action(cls, action: NoteAction) -> ActionModel:
        return ActionModel(
            note_action_id=action.note_action_id,
            note_id=action.note_id,
            action=action.action_text,
            created_at=action.created_at,
        )

    async def list_actions(self, note_id: UUID):
        query = (
            Select(NoteAction)
            .where(NoteAction.note_id == note_id)
            .order_by(asc(NoteAction.created_at))
        )

        results = await self.session.execute(query)

        actions = cast(list[NoteAction], results.scalars().all())

        return [self.map_action(action) for action in actions]

    async def add_action(self, action_model: ActionEditModel):
        action = NoteAction(
            note_id=action_model.note_id, action_text=action_model.action
        )
        self.session.add(action)
        await self.session.flush([action])

        return self.map_action(action)
