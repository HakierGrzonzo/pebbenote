import io
import json
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from unittest import TestCase, mock

from . import auth
from .config import Config
from .errors import CliError

CONFIG = Config(backend_url="http://backend", issuer="http://issuer")
NOW = 1_000_000.0

DEVICE = {
    "device_code": "dev-code",
    "user_code": "ABCD",
    "verification_uri_complete": "http://issuer/device?code=ABCD",
    "expires_in": 600,
    "interval": 5,
}


def token_response(access="new-access", refresh="new-refresh", expires_in=300):
    return {"access_token": access, "refresh_token": refresh, "expires_in": expires_in}


class AuthTestCase(TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.token_file = Path(tmp.name) / "pebbenote" / "tokens.json"

        self.request = self.patch("pebbenote_cli.auth.request")
        self.sleep = self.patch("pebbenote_cli.auth.time.sleep")
        self.patch("pebbenote_cli.auth.TOKEN_FILE", self.token_file)
        self.patch("pebbenote_cli.auth.time.time", return_value=NOW)
        stderr = redirect_stderr(io.StringIO())
        stderr.__enter__()
        self.addCleanup(stderr.__exit__, None, None, None)

    def patch(self, target, *args, **kwargs):
        patcher = mock.patch(target, *args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def store(self, **overrides):
        tokens = {
            "access_token": "cached-access",
            "refresh_token": "cached-refresh",
            "expires_at": NOW + 300,
        } | overrides
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps(tokens))

    def stored(self):
        return json.loads(self.token_file.read_text())

    def forms(self):
        return [c.kwargs.get("form") for c in self.request.call_args_list]


class TokenStorageTestCase(AuthTestCase):
    def test_save_tokens(self):
        auth.save_tokens(token_response(expires_in=300))

        self.assertEqual(
            self.stored(),
            {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_at": NOW + 300,
            },
        )
        self.assertEqual(self.token_file.stat().st_mode & 0o777, 0o600)

    def test_load_missing(self):
        self.assertIsNone(auth.load_tokens())

    def test_load_garbage(self):
        self.token_file.parent.mkdir(parents=True)
        self.token_file.write_text("not json")
        self.assertIsNone(auth.load_tokens())


class AccessTokenTestCase(AuthTestCase):
    def test_valid_cached_token(self):
        self.store()

        self.assertEqual(auth.access_token(CONFIG), "cached-access")
        self.request.assert_not_called()

    def test_no_tokens_logs_in(self):
        self.request.side_effect = [(200, DEVICE), (200, token_response())]

        self.assertEqual(auth.access_token(CONFIG), "new-access")
        self.assertEqual(self.forms()[0], {"client_id": auth.CLIENT_ID})

    def test_expiring_token_is_refreshed(self):
        self.store(expires_at=NOW + auth.EXPIRY_MARGIN)
        self.request.return_value = (200, token_response())

        self.assertEqual(auth.access_token(CONFIG), "new-access")
        self.assertEqual(
            self.forms(),
            [
                {
                    "grant_type": "refresh_token",
                    "client_id": auth.CLIENT_ID,
                    "refresh_token": "cached-refresh",
                }
            ],
        )
        self.assertEqual(self.stored()["access_token"], "new-access")

    def test_expired_without_refresh_token_logs_in(self):
        self.store(expires_at=NOW - 1, refresh_token=None)
        self.request.side_effect = [(200, DEVICE), (200, token_response())]

        self.assertEqual(auth.access_token(CONFIG), "new-access")
        self.assertEqual(self.forms()[0], {"client_id": auth.CLIENT_ID})

    def test_force_refresh(self):
        self.store()
        self.request.return_value = (200, token_response())

        self.assertEqual(auth.access_token(CONFIG, force_refresh=True), "new-access")
        self.assertEqual(self.forms()[0]["grant_type"], "refresh_token")

    def test_rejected_refresh_logs_in(self):
        self.store(expires_at=NOW - 1)
        self.request.side_effect = [
            (400, {"error": "invalid_grant"}),
            (200, DEVICE),
            (200, token_response()),
        ]

        self.assertEqual(auth.access_token(CONFIG), "new-access")
        self.assertEqual(self.forms()[1], {"client_id": auth.CLIENT_ID})


class LoginTestCase(AuthTestCase):
    def test_pending_then_success(self):
        self.request.side_effect = [
            (200, DEVICE),
            (400, {"error": "authorization_pending"}),
            (200, token_response()),
        ]

        tokens = auth.login(CONFIG)

        self.assertEqual(tokens["access_token"], "new-access")
        self.assertEqual(self.stored()["access_token"], "new-access")
        self.assertEqual(
            self.forms()[2],
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": auth.CLIENT_ID,
                "device_code": "dev-code",
            },
        )
        self.assertEqual(
            self.request.call_args.args[1],
            "http://issuer/protocol/openid-connect/token",
        )

    def test_slow_down_increases_interval(self):
        self.request.side_effect = [
            (200, DEVICE),
            (400, {"error": "slow_down"}),
            (200, token_response()),
        ]

        auth.login(CONFIG)

        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [5, 10])

    def test_other_error(self):
        self.request.side_effect = [(200, DEVICE), (400, {"error": "access_denied"})]

        with self.assertRaisesRegex(CliError, "access_denied"):
            auth.login(CONFIG)

    def test_device_endpoint_failure(self):
        self.request.return_value = (401, {"error": "unauthorized_client"})

        with self.assertRaises(CliError):
            auth.login(CONFIG)

    def test_timeout(self):
        clock = iter(range(0, 1000, 10))
        self.patch("pebbenote_cli.auth.time.time", side_effect=lambda: next(clock))
        self.request.side_effect = [(200, DEVICE | {"expires_in": 15})] + [
            (400, {"error": "authorization_pending"})
        ] * 10

        with self.assertRaisesRegex(CliError, "timed out"):
            auth.login(CONFIG)
        self.assertFalse(self.token_file.exists())
