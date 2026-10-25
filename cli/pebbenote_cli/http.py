import json
import urllib.error
import urllib.parse
import urllib.request

from pebbenote_cli.errors import CliError

USER_AGENT = "pebbenote-cli"


def request(method, url, *, data=None, form=None, token=None):
    headers = {"User-Agent": USER_AGENT}
    body = None
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read() or "null")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read() or "null")
        except ValueError:
            payload = None
        return e.code, payload
    except urllib.error.URLError as e:
        raise CliError(f"Cannot reach {url}: {e.reason}") from e
