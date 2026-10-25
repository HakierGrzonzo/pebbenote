from pebbenote_cli.auth import access_token
from pebbenote_cli.config import Config
from pebbenote_cli.errors import CliError
from pebbenote_cli.http import request


def call(config: Config, method, path, data=None):
    url = f"{config.backend_url}{path}"
    status, payload = request(method, url, data=data, token=access_token(config))
    if status == 401:
        status, payload = request(
            method, url, data=data, token=access_token(config, force_refresh=True)
        )
    if status >= 400:
        detail = payload.get("detail") if isinstance(payload, dict) else payload
        raise CliError(f"{method} {path} failed ({status}): {detail}")
    return payload
