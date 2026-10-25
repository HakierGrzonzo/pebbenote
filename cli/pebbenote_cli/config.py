import os
from dataclasses import dataclass
from pathlib import Path

import tomllib

from pebbenote_cli.errors import CliError

CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
CONFIG_FILE = CONFIG_HOME / "pebbenote" / "config.toml"

STATE_HOME = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
TOKEN_FILE = STATE_HOME / "pebbenote" / "tokens.json"

DEFAULT_BACKEND_URL = "https://dev.grzegorzkoperwas.site"
DEFAULT_ISSUER = "https://auth.grzegorzkoperwas.site/realms/pebbenote"

DEFAULT_CONFIG = f"""\
# Pebbenote CLI configuration. For a local setup use:
#   backend_url = "http://localhost:8000"
#   issuer = "http://localhost:8080/realms/pebbenote"
backend_url = "{DEFAULT_BACKEND_URL}"
issuer = "{DEFAULT_ISSUER}"
"""


@dataclass
class Config:
    backend_url: str
    issuer: str


def load_config() -> Config:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(DEFAULT_CONFIG)
    try:
        data = tomllib.loads(CONFIG_FILE.read_text())
    except tomllib.TOMLDecodeError as e:
        raise CliError(f"Invalid config {CONFIG_FILE}: {e}") from e
    return Config(
        backend_url=data.get("backend_url", DEFAULT_BACKEND_URL).rstrip("/"),
        issuer=data.get("issuer", DEFAULT_ISSUER).rstrip("/"),
    )
