from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from pydantic import BaseModel
from sqlalchemy import CTE, Select, desc, func
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import InstrumentedAttribute


class VersionConflict(Exception):
    """
    A write was based on a version that is no longer the latest one.

    Carries the current state. Over HTTP it becomes a 409 for the client to
    merge with, in the worker the job runs again on the current state.
    """

    detail = "The resource has changed since base_version"

    def __init__(self, current: BaseModel) -> None:
        super().__init__(self.detail)
        self.current = current


def latest_revisions(
    parent_id: InstrumentedAttribute[Any],
    revision_id: InstrumentedAttribute[Any],
    created_at: InstrumentedAttribute[Any],
) -> CTE:
    """
    The latest revision of each parent, by created_at then id, with its
    version: the number of that revision. Columns: parent_id, revision_id and
    version, to join the parent and the revision on.
    """
    version = func.row_number().over(
        partition_by=parent_id, order_by=(created_at, revision_id)
    )
    return (
        Select(
            parent_id.label("parent_id"),
            revision_id.label("revision_id"),
            version.label("version"),
        )
        .ext(distinct_on(parent_id))
        .order_by(parent_id, desc(created_at), desc(revision_id))
        .cte("latest_revision")
    )


class Versioned(Protocol):
    version: int


async def claim_version[M: Versioned](
    lock: Callable[[], Awaitable[None]],
    read: Callable[[], Awaitable[M]],
    base_version: int | None,
    conflict: Callable[[M], VersionConflict],
) -> M:
    """
    The first step of a write that is based on base_version: locks the
    resource until the transaction ends, then raises conflict with the
    resource as it is now when that is no longer the latest version. Without
    a base_version any version is taken.
    """
    await lock()
    # Read in a statement after the lock: it sees what a writer that held the
    # lock before has committed
    current = await read()
    if base_version is not None and current.version != base_version:
        raise conflict(current)
    return current
