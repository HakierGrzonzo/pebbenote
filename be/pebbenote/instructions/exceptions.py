from pebbenote.versioning import VersionConflict


class InstructionsConflict(VersionConflict):
    detail = "The instructions have changed since base_version"
