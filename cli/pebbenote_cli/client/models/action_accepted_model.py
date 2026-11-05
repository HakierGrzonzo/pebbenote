from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.action_model import ActionModel


T = TypeVar("T", bound="ActionAcceptedModel")


@_attrs_define
class ActionAcceptedModel:
    """The action is still being applied, poll the note for the result

    Attributes:
        action (ActionModel):
        note_last_modified (str):
    """

    action: ActionModel
    note_last_modified: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        action = self.action.to_dict()

        note_last_modified = self.note_last_modified

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "action": action,
                "note_last_modified": note_last_modified,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.action_model import ActionModel  # noqa: PLC0415

        d = dict(src_dict)
        action = ActionModel.from_dict(d.pop("action"))

        note_last_modified = d.pop("note_last_modified")

        action_accepted_model = cls(
            action=action,
            note_last_modified=note_last_modified,
        )

        action_accepted_model.additional_properties = d
        return action_accepted_model

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
