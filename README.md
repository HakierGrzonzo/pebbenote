# Pebbenote

A simple, ollama powered note taking app for the pebble smartwatch!

## Features:

- A FastAPI backend for note storage
    - Ollama for transforming your dictated ramblings into nicely formatted notes
    - Standing instructions ("always sort the grocery list by aisle") are 
      detected by a decision model and stored per user
- A pebble watchapp that can view a note and supports dictation on `select` key press
    - Written in C, TS and uses a generated OpenAPI client!

The project is in very early stages, to the point where you need to create your 
first note via the API. But it is my first pebble app

## How to work on:

Requirements:

- python
- node
- docker
- pebble sdk

Ollama (0.35 or newer, for decision models) must run on the host with the
models pulled: `ollama pull gemma4:e2b` and `ollama pull nimble`.

Bring up the backend via the following command:

```bash
docker compose up --build --watch
```

Then, run the migrations via `docker compose exec be poetry run alembic upgrade head`

In the `./pebbenote` folder, run:

- `npm install`, to install js dependencies and tooling
- `npm run openapi`, to regenerate the openapi client from local BE.
- `npm run build:dev` to build against the local stack (`docker compose up`), or
  `npm run build:prod` for the deployed one. Then `pebble install --emulator basalt`
  (or `--phone <ip>`).

Environments live in `pebbenote/environments.json` (backend url, Keycloak issuer,
app uuid). Dev has its own uuid and name, so it installs next to prod with separate
settings and sign-in. Building rewrites `uuid`/`displayName` in `package.json`, so
run `npm run build:prod` (or `npm run use-env prod`) before committing. Override
the urls for a one-off build with `PEBBENOTE_BACKEND_URL` / `PEBBENOTE_ISSUER`.
`localhost` only works in the emulator; a real phone needs an `https://` url.

### Git hooks

Linting and formatting (`ruff` for `./be`, `prettier` for the watchapp's TS) run
via [pre-commit](https://pre-commit.com). Install it (e.g. `pipx install pre-commit`),
then run `pre-commit install` once in the repo root. Use `pre-commit run --all-files`
to check everything.

Refer to `pebble sdk` docs for further instructions.
