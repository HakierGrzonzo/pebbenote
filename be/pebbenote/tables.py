from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Enum,
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


def utc_now() -> datetime:
    return datetime.now(UTC)


def updated_at_column():
    # Set from Python so flushed objects keep a loaded value, a SQL expression
    # would expire the attribute and need a lazy load
    return mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.clock_timestamp(),
    )


class ActionStatus(StrEnum):
    pending = "pending"
    done = "done"
    failed = "failed"


class Note(Base):
    __tablename__ = "note"
    note_id = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    note_text = mapped_column(Text, nullable=False)

    actions: Mapped[list["NoteAction"]] = relationship(back_populates="note")

    owner = mapped_column(Text, nullable=False)

    is_default = mapped_column(Boolean, nullable=False, server_default=false())

    updated_at = updated_at_column()

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

    status = mapped_column(
        Enum(
            ActionStatus,
            name="action_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        server_default=ActionStatus.done.value,
    )

    updated_at = updated_at_column()

    note: Mapped[Note] = relationship(back_populates="actions")


class UserInstruction(Base):
    __tablename__ = "user_instruction"
    instruction_id = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )

    owner = mapped_column(Text, nullable=False, index=True)
    instruction_text = mapped_column(Text, nullable=False)

    created_at = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.clock_timestamp(),
    )
