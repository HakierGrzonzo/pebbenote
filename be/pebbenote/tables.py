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
from sqlalchemy.dialects.postgresql import ARRAY
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
    actions: Mapped[list["NoteAction"]] = relationship(back_populates="note")
    # The content of a note is the text of its latest revision, which is
    # also when the note was last updated
    revisions: Mapped[list["NoteRevision"]] = relationship(back_populates="note")

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
    revision: Mapped["NoteRevision | None"] = relationship(
        back_populates="action", uselist=False
    )


class NoteRevision(Base):
    """A snapshot of a note after a change, made by an action or by hand"""

    __tablename__ = "note_revision"
    note_revision_id = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )

    note_id = mapped_column(ForeignKey(Note.note_id), nullable=False)
    note_text = mapped_column(Text, nullable=False)

    # Empty for edits made outside of the LLM, like deleting lines on the watch
    note_action_id = mapped_column(
        ForeignKey(NoteAction.note_action_id), nullable=True, unique=True
    )

    # Set from Python so flushed objects keep a loaded value
    created_at = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.clock_timestamp(),
    )

    note: Mapped[Note] = relationship(back_populates="revisions")
    action: Mapped[NoteAction | None] = relationship(back_populates="revision")

    __table_args__ = (Index("ix_note_revision_note_created", "note_id", "created_at"),)


class InstructionList(Base):
    """The standing instructions of a user, the row to lock when they change"""

    __tablename__ = "instruction_list"
    instruction_list_id = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )

    owner = mapped_column(Text, nullable=False, unique=True)

    # The instructions are the ones of the latest revision
    revisions: Mapped[list["InstructionRevision"]] = relationship(
        back_populates="instruction_list"
    )


class InstructionRevision(Base):
    """A snapshot of a user's standing instructions after a change"""

    __tablename__ = "instruction_revision"
    instruction_revision_id = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )

    instruction_list_id = mapped_column(
        ForeignKey(InstructionList.instruction_list_id), nullable=False
    )
    instructions: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)

    # Set from Python so flushed objects keep a loaded value
    created_at = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.clock_timestamp(),
    )

    instruction_list: Mapped[InstructionList] = relationship(back_populates="revisions")

    __table_args__ = (
        Index(
            "ix_instruction_revision_list_created", "instruction_list_id", "created_at"
        ),
    )
