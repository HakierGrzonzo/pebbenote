from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends
from sqlalchemy.orm import DeclarativeBase

from .config import settings


from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

postgresql_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"

async_engine = create_async_engine(
    postgresql_url, echo=settings.POSTGRES_LOG_QUERIES
)
async_session = async_sessionmaker(async_engine, expire_on_commit=True)


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    async with async_session() as session, session.begin():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


class Base(DeclarativeBase):
    pass
