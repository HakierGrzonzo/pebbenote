from unittest import TestCase, mock

from .api import call
from .config import Config
from .errors import CliError

CONFIG = Config(backend_url="http://backend", issuer="http://issuer")


class CallTestCase(TestCase):
    def setUp(self) -> None:
        request = mock.patch("pebbenote_cli.api.request")
        self.request = request.start()
        self.addCleanup(request.stop)

        access_token = mock.patch(
            "pebbenote_cli.api.access_token",
            side_effect=lambda config, force_refresh=False: (
                "fresh" if force_refresh else "cached"
            ),
        )
        self.access_token = access_token.start()
        self.addCleanup(access_token.stop)

    def test_success(self):
        self.request.return_value = (200, {"note_id": "a"})

        self.assertEqual(call(CONFIG, "PATCH", "/note/a", {"x": 1}), {"note_id": "a"})
        self.request.assert_called_once_with(
            "PATCH", "http://backend/note/a", data={"x": 1}, token="cached"
        )

    def test_401_retries_with_refreshed_token(self):
        self.request.side_effect = [(401, None), (200, ["ok"])]

        self.assertEqual(call(CONFIG, "GET", "/note/"), ["ok"])
        self.assertEqual(self.request.call_count, 2)
        self.assertEqual(self.request.call_args.kwargs["token"], "fresh")

    def test_error_with_detail(self):
        self.request.return_value = (404, {"detail": "Not found"})

        with self.assertRaises(CliError) as ctx:
            call(CONFIG, "GET", "/note/a")
        self.assertEqual(str(ctx.exception), "GET /note/a failed (404): Not found")

    def test_error_with_non_dict_payload(self):
        self.request.return_value = (500, None)

        with self.assertRaises(CliError) as ctx:
            call(CONFIG, "GET", "/note/a")
        self.assertEqual(str(ctx.exception), "GET /note/a failed (500): None")

    def test_repeated_401_raises(self):
        self.request.return_value = (401, {"detail": "Unauthorized"})

        with self.assertRaises(CliError):
            call(CONFIG, "GET", "/note/")
        self.assertEqual(self.request.call_count, 2)
