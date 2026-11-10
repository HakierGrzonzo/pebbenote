from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="NoteModel")


@_attrs_define
class NoteModel:
    """
    Attributes:
        note_id (UUID):
        content (str):
        is_default (bool):
        updated_at (datetime.datetime):
        version (int):
    """

    note_id: UUID
    content: str
    is_default: bool
    updated_at: datetime.datetime
    version: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        note_id = str(self.note_id)

        content = self.content

        is_default = self.is_default

        updated_at = self.updated_at.isoformat()

        version = self.version

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "note_id": note_id,
                "content": content,
                "is_default": is_default,
                "updated_at": updated_at,
                "version": version,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        note_id = UUID(d.pop("note_id"))

        content = d.pop("content")

        is_default = d.pop("is_default")

        updated_at = datetime.datetime.fromisoformat(d.pop("updated_at"))

        version = d.pop("version")

        note_model = cls(
            note_id=note_id,
            content=content,
            is_default=is_default,
            updated_at=updated_at,
            version=version,
        )

        note_model.additional_properties = d
        return note_model

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
