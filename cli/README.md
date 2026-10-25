# Pebbenote CLI

Opens a note in `$EDITOR` and syncs it with the backend when the editor quits. Python 3.13+, stdlib only, packaged with Poetry.

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
pebbenote            # edit the default note
pebbenote <note_id>  # edit a specific note
pebbenote list       # list notes (* = default)
pebbenote login      # force a new login
pebbenote > note.md  # piped output prints the note instead of opening the editor
```

## Configuration

On first run `$XDG_CONFIG_HOME/pebbenote/config.toml` (default `~/.config/pebbenote/config.toml`) is created with the production URLs:

```toml
backend_url = "https://dev.grzegorzkoperwas.site"
issuer = "https://auth.grzegorzkoperwas.site/realms/pebbenote"
```

Edit it to point at another backend, e.g. `http://localhost:8000` and `http://localhost:8080/realms/pebbenote` for local development. The editor comes from `$EDITOR`, then `$VISUAL`, then `vi`.

Login uses the Keycloak device flow. Tokens are stored in `$XDG_STATE_HOME/pebbenote/tokens.json` (default `~/.local/state/pebbenote/tokens.json`).
