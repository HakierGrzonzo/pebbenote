# Pebbenote

Monorepo: `be/` (FastAPI backend, Postgres, taskiq worker, Ollama), `cli/`
(Python CLI), `pebbenote/` (Pebble watchapp in C + TS), `keycloak/` (realm and
local auth helpers). See `README.md` for running the stack.

## Testing

CI (`.github/workflows/ci.yml`) runs three jobs: pre-commit, backend tests and
CLI tests. Run the same locally before pushing.

### Backend (`be/`)

```bash
cd be && poetry run bash run_tests.sh
```

- Needs Postgres on `127.0.0.1:5432` (user/password `postgres`). The `db`
  service from `docker compose up` works.
- `run_tests.sh` drops and recreates a separate `test` database, runs
  `alembic upgrade head`, then `python -m unittest discover`. It never touches
  the app's `postgres` database.
- Each test runs in a transaction that is rolled back (`get_test_db()` in
  `pebbenote/db.py`), so tests can write freely.
- The LLM is replaced by `MockAdapter` (`pebbenote/llm/mock.py`): set its
  answer with `set_result(...)` and read the chat it got with
  `get_called_with()`. Unit tests never call Ollama.
- `ERROR:pebbenote.auth:Failed to verify token` tracebacks in the output are
  expected, they come from the auth tests checking rejected tokens.
- New migration: also check it downgrades and upgrades on the test database:
  `POSTGRES_HOST=127.0.0.1 POSTGRES_DB=test poetry run alembic downgrade -1`,
  then `upgrade head`.

### CLI (`cli/`)

```bash
cd cli && poetry run python -m unittest discover -v
```

No services needed, HTTP and auth are mocked.

### Lint and format

`pre-commit run --all-files` from the repo root: ruff for Python, eslint and
prettier for the watchapp TS (needs `npm install` in `pebbenote/` first),
clang-format for C. In `be/`, `poetry run ruff check .` and
`poetry run ruff format .` are quicker.

### Against the running stack and real models

For changes to prompts or LLM behavior, unit tests are not enough, try them on
the local stack (`docker compose up --build --watch`, Ollama on the host with
the models pulled). The `be` and `worker` containers sync and reload `be/`, but
migrations are manual:
`docker compose exec be poetry run alembic upgrade head`.

Get a token with password login (local only, creates the `pebbenote-dev`
client and the user through the Keycloak admin API when missing):

```bash
TOKEN=$(keycloak/get-token.sh)             # user dev / devpassword
TOKEN=$(keycloak/get-token.sh alice pass1234)
curl -H "Authorization: Bearer $TOKEN" localhost:8000/note/default
```

`POST /action/` waits `ACTION_WAIT_SECONDS` for the LLM and answers `200` with
the note, or `202` while it is still running: then poll `GET /note/default`
until the action's `status` is no longer `pending`.

Use a throwaway user for these tests, so the developer's own notes stay intact.

Watchapp screenshots: `pebbenote/scripts/screenshots.sh [platform...]` (signs the
emulators in as `dev` with `keycloak/approve-device.sh`, about a minute per
platform), then look at each PNG in `pebbenote/screenshots/`.
`pebbenote/scripts/publish.sh "<release notes>"` publishes them to the store, as
part of a release that goes live at once (bump the version first).
Local Postgres is at `127.0.0.1:5432`, password `postgres`
(`PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres`).
