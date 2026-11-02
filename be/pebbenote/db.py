from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings

postgresql_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"

async_engine = create_async_engine(postgresql_url, echo=settings.POSTGRES_LOG_QUERIES)
async_session = async_sessionmaker(async_engine, expire_on_commit=True)


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    # Commits explicitly instead of using session.begin(), so a route can
    # commit early and keep using the session. An exception skips the commit
    # and closing the session rolls back.
    async with async_session() as session:
        yield session
        await session.commit()


@asynccontextmanager
async def get_test_db():
    async_test_engine = create_async_engine(
        postgresql_url, echo=settings.POSTGRES_LOG_QUERIES
    )
    async_test_session = async_sessionmaker(async_test_engine, expire_on_commit=True)
    async with async_test_session() as session, session.begin():
        yield session
        await session.rollback()


DbSession = Annotated[AsyncSession, Depends(get_db)]


class Base(DeclarativeBase):
    pass
