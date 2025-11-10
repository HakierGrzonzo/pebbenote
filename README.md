# Pebbenote

A simple, ollama powered note taking app for the pebble smartwatch!

## Features:

- A FastAPI backend for note storage
    - Ollama for transforming your dictated ramblings into nicely formatted notes
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

Bring up the backend via the following command:

```bash
docker compose up --build --watch
```

Then, run the migrations via `docker compose exec be poetry run alembic upgrade head`

In the `./pebbenote` folder, run:

- `npm install`, to install js dependencies and tooling
- `npm run openapi`, to regenerate the openapi client from local BE.
- `pebble build` to build the app.

You should change the url the watchapp contacts in the `./pebbenote/src/ts/index.ts` file.

Refer to `pebble sdk` docs for further instructions.
