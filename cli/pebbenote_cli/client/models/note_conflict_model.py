from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.note_model import NoteModel


T = TypeVar("T", bound="NoteConflictModel")


@_attrs_define
class NoteConflictModel:
    """
    Attributes:
        detail (str):
        current (NoteModel):
    """

    detail: str
    current: NoteModel
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        detail = self.detail

        current = self.current.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "detail": detail,
                "current": current,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.note_model import NoteModel  # noqa: PLC0415

        d = dict(src_dict)
        detail = d.pop("detail")

        current = NoteModel.from_dict(d.pop("current"))

        note_conflict_model = cls(
            detail=detail,
            current=current,
        )

        note_conflict_model.additional_properties = d
        return note_conflict_model

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
