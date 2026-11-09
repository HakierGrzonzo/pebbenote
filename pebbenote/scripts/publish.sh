#!/bin/bash
# Publishes a release of the watchapp to the Rebble appstore, with the
# screenshots in pebbenote/screenshots/ replacing the store's current ones.
#
# The release goes live right away: pebble publish always sets it published.
# Bump the version in package.json first, the store rejects a repeated one.
#
# Needs: `pebble login`, the Pebble SDK, and `npm install` in pebbenote/.
# Builds the prod variant.
#
# Usage: pebbenote/scripts/publish.sh "<release notes>" [pebble publish args...]

set -euo pipefail

if [ $# -lt 1 ] || [ -z "$1" ]; then
  echo "Usage: $0 \"<release notes>\" [pebble publish args...]" >&2
  exit 1
fi
notes=$1
shift

APP_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$APP_DIR"

npm run build:prod

shopt -s nullglob
screenshots=(screenshots/*.png)
if [ ${#screenshots[@]} -eq 0 ]; then
  echo "No screenshots in $APP_DIR/screenshots, run scripts/screenshots.sh" >&2
  exit 1
fi

pebble publish \
  --pbw build/pebbenote.pbw \
  --non-interactive \
  --no-gif-all-platforms \
  --screenshots "${screenshots[@]}" \
  --replace-screenshots \
  --release-notes "$notes" \
  "$@"
