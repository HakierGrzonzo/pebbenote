#!/bin/bash
# Takes the watchapp screenshots in pebbenote/screenshots/: one per platform and
# note, signed in as a local user against the local stack.
#
# Stops all Pebble emulators when done.
#
# Needs: the stack running (docker compose up), the Pebble SDK, jq, and
# `npm install` in pebbenote/. Builds the dev variant; package.json and
# src/ts/env.ts are put back afterwards.
#
# Usage: pebbenote/scripts/screenshots.sh [platform...]   (default: all)
# Env:   SCREENSHOT_USER / SCREENSHOT_PASSWORD (default dev / devpassword)
#        SCREENSHOT_WAIT seconds for the app to load a note (default 8)

set -euo pipefail

APP_DIR=$(cd "$(dirname "$0")/.." && pwd)
REPO=$(dirname "$APP_DIR")
USERNAME="${SCREENSHOT_USER:-dev}"
PASSWORD="${SCREENSHOT_PASSWORD:-devpassword}"
WAIT="${SCREENSHOT_WAIT:-8}"
API="http://localhost:8000"
OUT="$APP_DIR/screenshots"

# Same text as DEFAULT_NOTE_TEXT in be/pebbenote/notes/repository.py
WELCOME_NOTE='Welcome to Pebbenote!
Select: dictate, AI tidies it into the note
Up/Down: move highlight
Hold Select: delete highlighted line
Say "always ..." to set a lasting rule
Hold Select on these lines to clear them'
GROCERIES_NOTE='- Groceries:
    - apples
    - milk
    - bread
    - eggs'
# Screenshot name suffix -> note content
declare -A NOTES=([welcome]="$WELCOME_NOTE" [groceries]="$GROCERIES_NOTE")

cd "$APP_DIR"
if [ $# -gt 0 ]; then
  platforms=("$@")
else
  mapfile -t platforms < <(jq -r '.pebble.targetPlatforms[]' package.json)
fi

work=$(mktemp -d)
original_default=""
config_pid=""
cp package.json src/ts/env.ts "$work/"
cleanup() {
  if [ -n "$config_pid" ]; then kill "$config_pid" 2>/dev/null || true; fi
  # Stops every emulator, including ones started outside this script
  pebble kill >/dev/null 2>&1 || true
  cp "$work/package.json" package.json
  cp "$work/env.ts" src/ts/env.ts
  if [ -n "$original_default" ]; then
    api -X PUT "$API/note/$original_default/default" >/dev/null || true
  fi
  rm -rf "$work"
}
trap cleanup EXIT

token=$("$REPO/keycloak/get-token.sh" "$USERNAME" "$PASSWORD")
api() { curl -sf -H "Authorization: Bearer $token" "$@"; }

# Find or create each note, so reruns don't pile up copies
notes=$(api "$API/note/")
original_default=$(jq -r '.[] | select(.is_default) | .note_id' <<<"$notes")
declare -A note_ids
for name in "${!NOTES[@]}"; do
  id=$(jq -r --arg c "${NOTES[$name]}" \
    'first(.[] | select(.content == $c) | .note_id) // empty' <<<"$notes")
  if [ -z "$id" ]; then
    id=$(api -X POST -G "$API/note/" --data-urlencode "content=${NOTES[$name]}" |
      jq -r .note_id)
    echo "Created $name note $id"
  fi
  note_ids[$name]=$id
done

npm run build:dev

# Opens the config page, which is where the app starts a device sign-in, and
# approves it if the page offers one. Fails when it had to sign in, so the
# caller checks again once the app got its tokens. The BROWSER hook saves the
# page pebble writes instead of opening it.
open_config() {
  local platform=$1 page="$work/config.html"
  rm -f "$page"
  printf '#!/bin/sh\ncp "${1#file://}" %q\n' "$page" >"$work/browser"
  chmod +x "$work/browser"
  # No output from it, so a background pebble can't hold our stdout open
  BROWSER="$work/browser" pebble emu-app-config --emulator "$platform" \
    >"$work/config.log" 2>&1 &
  config_pid=$!
  for _ in $(seq 60); do
    [ -s "$page" ] && break
    sleep 0.5
  done
  if [ ! -s "$page" ]; then
    kill "$config_pid" 2>/dev/null || true
    echo "No config page from the $platform emulator" >&2
    return 1
  fi
  # pebble's page only redirects to the config page pypkjs serves, with a
  # return_to url that pebble waits on until the page is closed
  local page_url close_url sign_in_url
  page_url=$(grep -oE 'URL=[^"]*' "$page" | cut -d= -f2-)
  close_url=$(jq -rn --arg u "$page_url" \
    '$u | capture("return_to=(?<r>[^&]*)").r | gsub("%3A"; ":") | gsub("%2F"; "/") | gsub("%3F"; "?")')
  sign_in_url=$(curl -sf "${page_url%%\?*}" |
    sed -nE 's/^ *var signInUrl = (.*);$/\1/p' | jq -r '. // empty')
  if [ -n "$sign_in_url" ]; then
    "$REPO/keycloak/approve-device.sh" "$sign_in_url" "$USERNAME" "$PASSWORD"
  fi
  # Closing without a response keeps the settings, pebble then exits
  curl -sf "$close_url" >/dev/null
  wait "$config_pid"
  config_pid=""
  [ -z "$sign_in_url" ]
}

# The app polls Keycloak every few seconds for the approved sign-in, and a
# restart before that loses it, so wait until the config page shows notes
sign_in() {
  for _ in 1 2 3; do
    if open_config "$1"; then
      echo "$1: signed in as $USERNAME"
      return
    fi
    sleep 8
  done
  echo "$1: sign in failed" >&2
  return 1
}

# Installs into the emulator fail now and then, a retry helps
install() {
  for attempt in 1 2 3; do
    pebble install --emulator "$1" && return
    echo "Install on $1 failed (attempt $attempt)" >&2
    sleep 3
  done
  return 1
}

mkdir -p "$OUT"
for platform in "${platforms[@]}"; do
  echo "== $platform"
  install "$platform"
  sign_in "$platform"
  for name in "${!NOTES[@]}"; do
    api -X PUT "$API/note/${note_ids[$name]}/default" >/dev/null
    # Reinstalling restarts the app, which then loads the default note
    install "$platform"
    sleep "$WAIT"
    pebble screenshot --emulator "$platform" --no-open "$OUT/${platform}_$name.png"
  done
done
