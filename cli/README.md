# Pebbenote CLI

Opens a note in `$EDITOR` and syncs it with the backend when the editor quits. Python 3.13+, packaged with Poetry. Talks to the backend through a client generated from its OpenAPI schema.

## Install

As a shell command available everywhere (builds with Poetry's backend):

```sh
pipx install ./cli        # from the repo root; use `pipx install --force ./cli` to update
```

For development, install into the project virtualenv and prefix commands with `poetry run`:

```sh
cd cli
poetry install
```

## Usage

```sh
pebbenote               # edit the default note
pebbenote <note_id>     # edit a specific note
pebbenote list          # list notes (* = default)
pebbenote instructions  # edit the standing instructions as a list
pebbenote login         # force a new login
pebbenote > note.md     # piped output prints the note instead of opening the editor
```

`pebbenote instructions` opens the standing instructions (the ones the assistant follows on every note) as a list, one `- ` item each. Add, reword or delete items; the saved list replaces the stored one, and the backend then applies it in the background to every note. `--no-apply` only saves the list. Piped, it prints the list.

### Conflicts

An edit is sent with the version it was made on. When the note or the instructions were changed elsewhere while the editor was open (on the watch, by the assistant, in another terminal), the backend refuses the edit and the CLI merges both like git: changes in different places are combined and synced without asking, changes to the same lines reopen the editor with both versions between markers:

```
<<<<<<< yours
- oat milk
=======
- soy milk
>>>>>>> server
```

Edit that into what you want and quit. If markers are still there, nothing is synced and the text is kept in `$XDG_STATE_HOME/pebbenote/unresolved.md`.

## Configuration

On first run `$XDG_CONFIG_HOME/pebbenote/config.toml` (default `~/.config/pebbenote/config.toml`) is created with the production URLs:

```toml
backend_url = "https://dev.grzegorzkoperwas.site"
issuer = "https://auth.grzegorzkoperwas.site/realms/pebbenote"
```

Edit it to point at another backend, e.g. `http://localhost:8000` and `http://localhost:8080/realms/pebbenote` for local development. The editor comes from `$EDITOR`, then `$VISUAL`, then `vi`.

Login uses the Keycloak device flow. Tokens are stored in `$XDG_STATE_HOME/pebbenote/tokens.json` (default `~/.local/state/pebbenote/tokens.json`).

## Regenerating the API client

`pebbenote_cli/client/` is generated with [openapi-python-client](https://github.com/openapi-generators/openapi-python-client) from a locally running backend (`ENVIRONMENT=local`, which serves `/openapi.json`). Don't edit it by hand; after changing the backend API run:

```sh
./generate_client.sh   # uses http://localhost:8000/openapi.json, override with OPENAPI_URL
```
