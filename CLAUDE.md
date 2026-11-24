# Pebbenote

Monorepo: `be/` (FastAPI backend, Postgres, taskiq worker, Ollama), `cli/`
(Python CLI), `pebbenote/` (Pebble watchapp in C + TS), `keycloak/` (realm and
local auth helpers). See `README.md` for running the stack.

## Testing

CI (`.github/workflows/ci.yml`) runs four jobs: pre-commit, backend tests,
CLI tests and watchapp JS tests. Run the same locally before pushing.

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
- The app and the tests connect as `pebbenote_app`, which row level security
  limits to the rows of the user in the `pebbenote.user` setting. Sessions get
  it from `get_db(user)` / `get_test_db(user)`, and `as_user(session, user)`
  switches it in a test. Migrations run as `postgres`.
- New table: the migration grants it to `pebbenote_app` and adds an
  `owner_only` policy (see `c1a2b3d4e5f6_add_row_level_security.py`),
  otherwise the app can't read it.
- The LLM is replaced by `MockAdapter` (`pebbenote/llm/mock.py`): set its
  answer with `set_result(...)` and read the chat it got with
  `get_called_with()`. Unit tests never call Ollama.
- `ERROR:pebbenote.auth:Failed to verify token` tracebacks in the output are
  expected, they come from the auth tests checking rejected tokens.
- New migration: also check it downgrades and upgrades on the test database:
  `POSTGRES_HOST=127.0.0.1 POSTGRES_DB=test poetry run alembic downgrade -1`,
  then `upgrade head`.

### Prompt tests (`be/pebbenote/prompt_tests/`)

```bash
cd be && PEBBENOTE_PROMPT_TESTS=1 poetry run python -m unittest discover -v -s pebbenote/prompt_tests -t .
```

Cases sent to the real models (`CHAT_MODEL`, `DECISION_MODEL`) through local
Ollama, checking what the prompts make them do: edits, undo, standing
instructions, the classifier, instruction rewrites and titles. No Postgres
needed, the chat comes from `build_note_chat` like in production. Without the
env var they are skipped, so `run_tests.sh` and CI never need Ollama.

The `prompt-tests` pre-commit hook runs them when a commit touches the
prompts, the chat building, `llm/`, `config.py` or the tests; it fails when
Ollama is down. `SKIP=prompt-tests git commit ...` to commit without them
(CI skips them the same way). A failure is about the prompt or the model, not
necessarily the code: look at the answer in the message before loosening an
assertion.

### CLI (`cli/`)

```bash
cd cli && poetry run python -m unittest discover -v
```

No services needed, HTTP and auth are mocked.

### Watchapp JS (`pebbenote/`)

```bash
cd pebbenote && npm test
```

`node:test` run through `tsx`, tests are `src/ts/**/*.test.ts`. The phone side
talks to the backend and the watch through injected functions, so tests use
fakes instead of `Pebble`, `PebbleTS` and HTTP.

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
until the action's `status` is no longer `pending`. An action queued behind
another pending one of the same note gets its `202` at once.

Edits name the version they are based on (`base_version` in `PATCH /note/{id}`
and `PUT /instruction/`, the `version` of the last GET); an outdated one is a
`409` with the current state.

Use a throwaway user for these tests, so the developer's own notes stay intact.

Traces, metrics and logs land in Grafana at `localhost:3000` (the `otel-lgtm`
service); a trace of `POST /action/` shows the task, the queries and the
`chat <model>` spans with token counts. The Grafana API answers without auth
locally, e.g. `curl 'localhost:3000/api/datasources/proxy/uid/tempo/api/search?tags=service.name%3Dpebbenote-worker'`.

Watchapp screenshots: `pebbenote/scripts/screenshots.sh [platform...]` (signs the
emulators in as `dev` with `keycloak/approve-device.sh`, about a minute per
platform), then look at each PNG in `pebbenote/screenshots/`.
An emulator stays signed in as the user it first got, whatever user a later
run asks for: check whose note it shows before dictating into it, `pebble wipe`
signs it out. `pebble transcribe "<text>"` keeps running and answers the
dictation a Select press opens, a second Select confirms the text.
`pebbenote/scripts/publish.sh "<release notes>"` publishes them to the store, as
part of a release that goes live at once (bump the version first).
Local Postgres is at `127.0.0.1:5432`, password `postgres`
(`PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres`).
