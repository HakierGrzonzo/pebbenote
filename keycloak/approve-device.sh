#!/bin/bash
# Approves an OAuth2 device sign-in (the watchapp's "Sign in" link) as a user,
# by logging in to the Keycloak pages with curl instead of a browser.
#
# Local development only: it scrapes the default Keycloak login theme.
#
# Usage: keycloak/approve-device.sh <verification_uri_complete> [username] [password]

set -euo pipefail

URL="${1:?usage: $0 <verification_uri_complete> [username] [password]}"
USERNAME="${2:-dev}"
PASSWORD="${3:-devpassword}"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
jar="$work/cookies"

fetch() {
  curl -sfL -c "$jar" -b "$jar" -o "$work/page.html" -w '%{url_effective}' "$@"
}

# Prints the action of the page's first form matching the given id pattern
form_action() {
  grep -oE "<form[^>]*$1[^>]*>" "$work/page.html" | head -1 |
    sed -E 's/.*action="([^"]*)".*/\1/; s/&amp;/\&/g'
}

base=$(sed -E 's#^(https?://[^/]+).*#\1#' <<<"$URL")
absolute() { [[ $1 == /* ]] && echo "$base$1" || echo "$1"; }

fetch "$URL" >/dev/null
action=$(form_action 'id="kc-form-login"')
if [ -z "$action" ]; then
  echo "No login form at $URL (expired code?)" >&2
  exit 1
fi
landed=$(fetch "$(absolute "$action")" \
  --data-urlencode "username=$USERNAME" --data-urlencode "password=$PASSWORD")

# The consent screen is skipped once the user granted the client its scopes
if [[ $landed == *OAUTH_GRANT* ]]; then
  code=$(grep -oE 'name="code" value="[^"]*"' "$work/page.html" |
    sed -E 's/.*value="([^"]*)"/\1/')
  landed=$(fetch "$(absolute "$(form_action 'consent')")" \
    --data-urlencode "code=$code" -d accept=Yes)
fi

if [[ $landed != */device/status* ]] ||
  ! grep -q "Device Login Successful" "$work/page.html"; then
  echo "Device approval failed, ended at $landed" >&2
  exit 1
fi
echo "Approved device sign-in for $USERNAME" >&2
