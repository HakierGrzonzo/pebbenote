from http import HTTPStatus
from types import SimpleNamespace
from unittest import TestCase, mock

import httpx

from .api import call
from .client.types import Response
from .config import Config
from .errors import CliError, ConflictError

CONFIG = Config(backend_url="http://backend", issuer="http://issuer")


def response(status, content=b"", parsed=None):
    return Response(
        status_code=HTTPStatus(status), content=content, headers={}, parsed=parsed
    )


class CallTestCase(TestCase):
    def setUp(self) -> None:
        access_token = mock.patch(
            "pebbenote_cli.api.access_token",
            side_effect=lambda config, force_refresh=False: (
                "fresh" if force_refresh else "cached"
            ),
        )
        self.access_token = access_token.start()
        self.addCleanup(access_token.stop)

        self.sync_detailed = mock.Mock()
        self.endpoint = SimpleNamespace(
            __name__="pebbenote_cli.client.api.notes.get_note_by_id",
            sync_detailed=self.sync_detailed,
        )

    def token_of(self, call_args):
        return call_args.kwargs["client"].token

    def test_success(self):
        self.sync_detailed.return_value = response(200, parsed="note")

        self.assertEqual(call(CONFIG, self.endpoint, note_id="a"), "note")
        self.sync_detailed.assert_called_once()
        kwargs = self.sync_detailed.call_args.kwargs
        self.assertEqual(kwargs["note_id"], "a")
        self.assertEqual(kwargs["client"]._base_url, "http://backend")
        self.assertEqual(self.token_of(self.sync_detailed.call_args), "cached")

    def test_401_retries_with_refreshed_token(self):
        self.sync_detailed.side_effect = [response(401), response(200, parsed=["ok"])]

        self.assertEqual(call(CONFIG, self.endpoint), ["ok"])
        self.assertEqual(self.sync_detailed.call_count, 2)
        self.assertEqual(self.token_of(self.sync_detailed.call_args), "fresh")

    def test_error_with_detail(self):
        self.sync_detailed.return_value = response(404, b'{"detail": "Not found"}')

        with self.assertRaises(CliError) as ctx:
            call(CONFIG, self.endpoint, note_id="a")
        self.assertEqual(str(ctx.exception), "get_note_by_id failed (404): Not found")

    def test_error_with_non_json_body(self):
        self.sync_detailed.return_value = response(500, b"Internal Server Error")

        with self.assertRaises(CliError) as ctx:
            call(CONFIG, self.endpoint, note_id="a")
        self.assertEqual(str(ctx.exception), "get_note_by_id failed (500): None")

    def test_conflict_carries_the_current_state(self):
        self.sync_detailed.return_value = response(
            409,
            b'{"detail": "The note has changed", "current": {}}',
            parsed=SimpleNamespace(detail="The note has changed", current="theirs"),
        )

        with self.assertRaises(ConflictError) as ctx:
            call(CONFIG, self.endpoint, note_id="a")
        self.assertEqual(ctx.exception.current, "theirs")
        self.assertEqual(
            str(ctx.exception), "get_note_by_id failed (409): The note has changed"
        )

    def test_backend_down(self):
        self.sync_detailed.return_value = response(502, b"<html>Bad Gateway</html>")

        with self.assertRaises(CliError) as ctx:
            call(CONFIG, self.endpoint)
        self.assertEqual(
            str(ctx.exception),
            "Cannot reach http://backend (HTTP 502): the backend seems to be down",
        )

    def test_repeated_401_raises(self):
        self.sync_detailed.return_value = response(401, b'{"detail": "Unauthorized"}')

        with self.assertRaises(CliError):
            call(CONFIG, self.endpoint)
        self.assertEqual(self.sync_detailed.call_count, 2)

    def test_transport_error_raises_cli_error(self):
        self.sync_detailed.side_effect = httpx.ConnectError("refused")

        with self.assertRaises(CliError) as ctx:
            call(CONFIG, self.endpoint)
        self.assertEqual(str(ctx.exception), "Cannot reach http://backend: refused")
