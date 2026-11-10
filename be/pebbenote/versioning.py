from pydantic import BaseModel


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
