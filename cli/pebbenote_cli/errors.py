class CliError(Exception):
    pass


class ConflictError(CliError):
    """The edit was based on an old version, `current` is the one on the server"""

    def __init__(self, message: str, current) -> None:
        super().__init__(message)
        self.current = current
