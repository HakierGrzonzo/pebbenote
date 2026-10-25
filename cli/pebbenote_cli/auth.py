import json
import os
import sys
import time

from pebbenote_cli.config import TOKEN_FILE, Config
from pebbenote_cli.errors import CliError
from pebbenote_cli.http import request

CLIENT_ID = "pebbenote-watch"
EXPIRY_MARGIN = 30


def load_tokens():
    try:
        return json.loads(TOKEN_FILE.read_text())
    except (OSError, ValueError):
        return None


def save_tokens(token_response):
    tokens = {
        "access_token": token_response["access_token"],
        "refresh_token": token_response.get("refresh_token"),
        "expires_at": time.time() + token_response.get("expires_in", 0),
    }
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(tokens, f)
    return tokens


def login(config: Config):
    status, device = request(
        "POST",
        f"{config.issuer}/protocol/openid-connect/auth/device",
        form={"client_id": CLIENT_ID},
    )
    if status != 200:
        raise CliError(f"Device authorization failed: {device}")
    print(f"Sign in at: {device.get('verification_uri_complete')}", file=sys.stderr)
    print(f"Code: {device['user_code']}", file=sys.stderr)

    interval = device.get("interval", 5)
    deadline = time.time() + device["expires_in"]
    while time.time() < deadline:
        time.sleep(interval)
        status, token = request(
            "POST",
            f"{config.issuer}/protocol/openid-connect/token",
            form={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": CLIENT_ID,
                "device_code": device["device_code"],
            },
        )
        if status == 200:
            return save_tokens(token)
        error = (token or {}).get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        raise CliError(f"Login failed: {error}")
    raise CliError("Login timed out")


def refresh(config: Config, tokens):
    status, token = request(
        "POST",
        f"{config.issuer}/protocol/openid-connect/token",
        form={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": tokens["refresh_token"],
        },
    )
    if status == 200:
        return save_tokens(token)
    return login(config)


def access_token(config: Config, force_refresh=False):
    tokens = load_tokens()
    if not tokens:
        tokens = login(config)
    elif force_refresh or tokens["expires_at"] - EXPIRY_MARGIN <= time.time():
        if tokens.get("refresh_token"):
            tokens = refresh(config, tokens)
        else:
            tokens = login(config)
    return tokens["access_token"]
