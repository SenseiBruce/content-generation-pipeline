# Changelog

## Unreleased

### Dependency freshness (2026-08-19)

Runtime pins in `[project.dependencies]` (9 packages) were checked with
`uv pip list --outdated`. Direct runtime pins still on the lockfile: feedparser
6.0.11, requests 2.33.0, python-dotenv 1.2.2, pydantic 2.9.2, pillow 12.3.0,
google-api-python-client 2.136.0, google-auth 2.35.0, google-auth-oauthlib 1.2.1,
google-auth-httplib2 0.2.0. Newer majors exist for some (pydantic 2.13, google
client 2.198) and will be taken via Dependabot (`.github/dependabot.yml`, weekly
pip + GitHub Actions). `pip-audit -r requirements.lock` currently reports no
known vulnerabilities.

Dev tools live only in `[dependency-groups] dev` (not duplicated under
`[project.optional-dependencies]`).

## [0.1.0] — 2026-08-19

Reproducible baseline for the Capital Architects YouTube Shorts pipeline.

- Offline pytest suite (`pytest --cov=agents --cov=pipeline --disable-socket`)
- Committed `uv.lock` and `requirements.lock`, verified in CI
- CI jobs: lockfile sync, ruff check + format, mypy, pytest, pip-audit
- Docker image and compose file; Voicebox remains an external TTS service
- Pydantic validation for scripts, Runware image responses, and YouTube upload payloads
