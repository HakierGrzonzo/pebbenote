from __future__ import annotations

from collections.abc import Mapping
from typing import (
    Any,
    Literal,
    TypeVar,
    cast,
)
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ActionEditModel")


@_attrs_define
class ActionEditModel:
    """
    Attributes:
        note_id (Literal['default'] | UUID):
        action (str):
    """

    note_id: Literal["default"] | UUID
    action: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        note_id: Literal["default"] | str
        if isinstance(self.note_id, UUID):
            note_id = str(self.note_id)
        else:
            note_id = self.note_id

        action = self.action

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "note_id": note_id,
                "action": action,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_note_id(data: object) -> Literal["default"] | UUID:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                note_id_type_0 = UUID(data)

                return note_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            note_id_type_1 = cast(Literal["default"], data)
            if note_id_type_1 != "default":
                raise ValueError(
                    f"note_id_type_1 must match const 'default', got '{note_id_type_1}'"
                )
            return note_id_type_1

        note_id = _parse_note_id(d.pop("note_id"))

        action = d.pop("action")

        action_edit_model = cls(
            note_id=note_id,
            action=action,
        )

        action_edit_model.additional_properties = d
        return action_edit_model

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
