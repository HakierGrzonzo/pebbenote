from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Index,
    Text,
    Uuid,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Note(Base):
    __tablename__ = "note"
    note_id = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    note_text = mapped_column(Text, nullable=False)

    actions: Mapped[list["NoteAction"]] = relationship(back_populates="note")

    owner = mapped_column(Text, nullable=False)

    is_default = mapped_column(Boolean, nullable=False, server_default=false())

    __table_args__ = (
        # At most one default note per owner
        Index(
            "uq_note_one_default_per_owner",
            "owner",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )


class NoteAction(Base):
    __tablename__ = "note_action"
    note_action_id = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )

    note_id = mapped_column(ForeignKey(Note.note_id), nullable=False)
    action_text = mapped_column(Text, nullable=False)

    created_at = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    note: Mapped[Note] = relationship(back_populates="actions")
