from pebbenote.versioning import VersionConflict


class NoteDoesNotExist(Exception): ...


class NoteConflict(VersionConflict):
    detail = "The note has changed since base_version"
