from datetime import UTC, datetime, timedelta
from email.utils import format_datetime, parsedate_to_datetime


def format_http_date(value: datetime) -> str:
    return format_datetime(value.astimezone(UTC), usegmt=True)


def last_modified(updated_at: datetime, now: datetime | None = None) -> str:
    """
    Last-Modified header for a resource changed at updated_at.

    HTTP dates have whole second resolution, so a later change in the current
    second would get the same date and the client would never see it. The
    current second is never claimed: the client gets one more full response
    once that second is over, then 304s.
    """
    now = now or datetime.now(UTC)
    last_full_second = now.replace(microsecond=0) - timedelta(seconds=1)
    return format_http_date(min(updated_at.replace(microsecond=0), last_full_second))


def is_modified_since(updated_at: datetime, if_modified_since: str | None) -> bool:
    """False only when If-Modified-Since proves the client is up to date"""
    if if_modified_since is None:
        return True
    try:
        since = parsedate_to_datetime(if_modified_since)
    except (TypeError, ValueError):
        return True
    if since.tzinfo is None:
        return True

    return updated_at.replace(microsecond=0) > since
