from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends
from sqlalchemy import Connection, event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, SessionTransaction

from .auth import CurrentUser
from .config import settings


def _url(user: str, password: str) -> str:
    return f"postgresql+asyncpg://{user}:{password}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"


# Owns the tables, for migrations
owner_url = _url(settings.POSTGRES_USER, settings.POSTGRES_PASSWORD)
# Row level security applies to the app: it sees only the rows of the user in
# the pebbenote.user setting, and nothing without it
app_url = _url(settings.POSTGRES_APP_USER, settings.POSTGRES_APP_PASSWORD)

async_engine = create_async_engine(app_url, echo=settings.POSTGRES_LOG_QUERIES)
async_session = async_sessionmaker(async_engine, expire_on_commit=True)

SET_USER = text("SELECT set_config('pebbenote.user', :user, true)")


@event.listens_for(Session, "after_begin")
def _set_user(
    session: Session, transaction: SessionTransaction, connection: Connection
) -> None:
    # The setting lasts until the transaction ends, so it is set again for
    # each one: a route or task may commit and keep using the session
    if (user := session.info.get("user")) is not None:
        connection.execute(SET_USER, {"user": user})


async def get_db(user: CurrentUser) -> AsyncGenerator[AsyncSession, Any]:
    # Commits explicitly instead of using session.begin(), so a route can
    # commit early and keep using the session. An exception skips the commit
    # and closing the session rolls back.
    async with async_session(info={"user": user}) as session:
        yield session
        await session.commit()


@asynccontextmanager
async def get_test_db(user: str | None = None):
    """A session of the user, all in one transaction that is rolled back"""
    async_test_engine = create_async_engine(app_url, echo=settings.POSTGRES_LOG_QUERIES)
    async_test_session = async_sessionmaker(async_test_engine, expire_on_commit=True)
    async with (
        async_test_session(info={"user": user}) as session,
        session.begin(),
    ):
        yield session
        await session.rollback()
    await async_test_engine.dispose()


@asynccontextmanager
async def as_user(session: AsyncSession, user: str):
    """Makes the session act for another user for a while, in tests"""
    previous = session.info.get("user")
    session.info["user"] = user
    await session.execute(SET_USER, {"user": user})
    try:
        yield
    finally:
        session.info["user"] = previous
        await session.execute(SET_USER, {"user": previous or ""})


DbSession = Annotated[AsyncSession, Depends(get_db)]


class Base(DeclarativeBase):
    pass
