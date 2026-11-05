#!/usr/bin/env bash
# Regenerate the API client from a locally running backend (ENVIRONMENT=local).
set -euo pipefail
cd "$(dirname "$0")"

URL="${OPENAPI_URL:-http://localhost:8000/openapi.json}"

poetry run openapi-python-client generate \
  --url "$URL" \
  --meta none \
  --output-path pebbenote_cli/client \
  --overwrite
poetry run ruff check --fix pebbenote_cli/client
poetry run ruff format pebbenote_cli/client
