from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.action_status import ActionStatus

T = TypeVar("T", bound="ActionModel")


@_attrs_define
class ActionModel:
    """
    Attributes:
        note_action_id (UUID):
        note_id (UUID):
        action (str):
        status (ActionStatus):
        created_at (datetime.datetime):
        updated_at (datetime.datetime):
    """

    note_action_id: UUID
    note_id: UUID
    action: str
    status: ActionStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        note_action_id = str(self.note_action_id)

        note_id = str(self.note_id)

        action = self.action

        status = self.status.value

        created_at = self.created_at.isoformat()

        updated_at = self.updated_at.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "note_action_id": note_action_id,
                "note_id": note_id,
                "action": action,
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        note_action_id = UUID(d.pop("note_action_id"))

        note_id = UUID(d.pop("note_id"))

        action = d.pop("action")

        status = ActionStatus(d.pop("status"))

        created_at = datetime.datetime.fromisoformat(d.pop("created_at"))

        updated_at = datetime.datetime.fromisoformat(d.pop("updated_at"))

        action_model = cls(
            note_action_id=note_action_id,
            note_id=note_id,
            action=action,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
        )

        action_model.additional_properties = d
        return action_model

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
