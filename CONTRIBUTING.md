# Contributing

No live API keys or external accounts are required to develop or test this
repository. Follow the steps below from a fresh clone.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock -r requirements-dev.txt
```

Optional: `uv sync --frozen` instead of pip.

## Tests (offline)

```bash
pytest --cov=agents --cov=pipeline --disable-socket
```

`--disable-socket` fails the run if a test tries to use the network.
Agents call `pipeline.http_client` rather than `requests` directly; tests
monkeypatch `pipeline.http_client.post` / `.get` with fixture payloads.
See `tests/test_imager.py` and `tests/test_publisher.py` for the pattern to
copy when adding a new agent test.

## CI gates (run the same commands locally)

```bash
ruff check .
ruff format --check .
mypy agents pipeline
./scripts/check-lockfile.sh   # requires `uv`
```

GitHub Actions runs those plus `pip-audit -r requirements.lock` on every
push and pull request.

## Branch naming

Use a short, scoped branch:

- `feat/<agent-or-area>-<change>`
- `fix/<agent-or-area>-<bug>`
- `test/<area>`
- `chore/<task>`

Examples: `feat/logger-json-fields`, `fix/imager-empty-runware`.

## Commits

Land one behavior per commit. If you change `agents/` or `pipeline/`, include
the matching `tests/` update in the **same** commit.

Use conventional prefixes: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.

```text
feat: validate Runware responses with pydantic
```

Do not mix formatting-only changes with feature work.

## Secrets

Never commit `.env`, `youtube_token.json`, or `client_secret.json`. Copy
`.env.template` locally if you run the live pipeline.
