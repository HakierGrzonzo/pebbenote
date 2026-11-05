import json

import httpx

from pebbenote_cli.auth import access_token
from pebbenote_cli.client import AuthenticatedClient
from pebbenote_cli.config import Config
from pebbenote_cli.errors import CliError
from pebbenote_cli.http import UNAVAILABLE_STATUSES, USER_AGENT


def _client(config: Config, token: str) -> AuthenticatedClient:
    return AuthenticatedClient(
        base_url=config.backend_url,
        token=token,
        headers={"User-Agent": USER_AGENT},
    )


def _detail(content: bytes):
    try:
        payload = json.loads(content or b"null")
    except ValueError:
        return None
    return payload.get("detail") if isinstance(payload, dict) else payload


def call(config: Config, endpoint, **kwargs):
    """Call a generated endpoint module, retrying once with a fresh token on 401."""
    name = endpoint.__name__.rsplit(".", 1)[-1]
    try:
        response = endpoint.sync_detailed(
            client=_client(config, access_token(config)), **kwargs
        )
        if response.status_code == 401:
            response = endpoint.sync_detailed(
                client=_client(config, access_token(config, force_refresh=True)),
                **kwargs,
            )
    except httpx.TransportError as e:
        raise CliError(f"Cannot reach {config.backend_url}: {e}") from e
    if response.status_code in UNAVAILABLE_STATUSES:
        raise CliError(
            f"Cannot reach {config.backend_url} (HTTP {response.status_code}): "
            "the backend seems to be down"
        )
    if response.status_code >= 400:
        raise CliError(
            f"{name} failed ({response.status_code}): {_detail(response.content)}"
        )
    return response.parsed
