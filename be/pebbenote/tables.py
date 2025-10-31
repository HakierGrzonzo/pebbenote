from sqlalchemy import Text, Uuid, func
from sqlalchemy.orm import mapped_column
from db import DeclarativeBase


class Note(DeclarativeBase):
    __tablename__ = "note"
    note_id = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    note_text = mapped_column(Text, nullable=False)
