import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import TestCase

from .errors import CliError
from .http import USER_AGENT, request


class RecordingHandler(BaseHTTPRequestHandler):
    """Records each request and replies with the route's (status, body)."""

    routes = {
        "/json": (200, b'{"ok": true}'),
        "/empty": (204, b""),
        "/missing": (404, b'{"detail": "Not found"}'),
        "/broken": (500, b"<html>oops</html>"),
    }
    requests: list = []

    def handle_any(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.requests.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers),
                "body": self.rfile.read(length),
            }
        )
        status, body = self.routes[self.path]
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PATCH = handle_any

    def log_message(self, format, *args):
        pass


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RequestTestCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), RecordingHandler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        RecordingHandler.requests.clear()

    def last_request(self) -> dict:
        return RecordingHandler.requests[-1]

    def test_json_body(self):
        status, payload = request("PATCH", f"{self.base}/json", data={"a": 1})

        self.assertEqual((status, payload), (200, {"ok": True}))
        sent = self.last_request()
        self.assertEqual(sent["method"], "PATCH")
        self.assertEqual(sent["headers"]["Content-Type"], "application/json")
        self.assertEqual(json.loads(sent["body"]), {"a": 1})

    def test_form_body(self):
        request("POST", f"{self.base}/json", form={"client_id": "x y"})

        sent = self.last_request()
        self.assertEqual(
            sent["headers"]["Content-Type"], "application/x-www-form-urlencoded"
        )
        self.assertEqual(sent["body"], b"client_id=x+y")

    def test_headers(self):
        request("GET", f"{self.base}/json", token="abc")

        headers = self.last_request()["headers"]
        self.assertEqual(headers["Authorization"], "Bearer abc")
        self.assertEqual(headers["User-Agent"], USER_AGENT)

    def test_no_token_no_authorization(self):
        request("GET", f"{self.base}/json")

        self.assertNotIn("Authorization", self.last_request()["headers"])

    def test_empty_body(self):
        self.assertEqual(request("GET", f"{self.base}/empty"), (204, None))

    def test_error_with_json(self):
        self.assertEqual(
            request("GET", f"{self.base}/missing"), (404, {"detail": "Not found"})
        )

    def test_error_without_json(self):
        self.assertEqual(request("GET", f"{self.base}/broken"), (500, None))

    def test_unreachable(self):
        with self.assertRaises(CliError):
            request("GET", f"http://127.0.0.1:{free_port()}/json")
