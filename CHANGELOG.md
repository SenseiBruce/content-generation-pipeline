# Changelog

## [0.1.0] — 2026-08-19

Reproducible baseline for the Capital Architects YouTube Shorts pipeline.

- Offline pytest suite (`pytest --cov=agents --cov=pipeline --disable-socket`)
- Committed `uv.lock` and `requirements.lock`, verified in CI
- CI jobs: lockfile sync, ruff check + format, mypy, pytest, pip-audit
- Docker image and compose file; Voicebox remains an external TTS service
- Pydantic validation for scripts, Runware image responses, and YouTube upload payloads
