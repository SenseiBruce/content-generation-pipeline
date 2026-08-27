# Changelog

## [Unreleased]

### Added
- `--dry-run` produces videos locally and skips YouTube upload (and does not mark stories as seen)
- `--max-stories N` caps how many approved scripts are produced in a run
## Unreleased

- `python3 rerun_approved.py --list` prints a JSON catalog of `data/approved/`.

- WhatsApp `STATUS` prints last-run health from `pipeline.health.inspect_health`.

- `python3 scripts/list_runs.py` prints recent `data/pipeline_state.json` run records as JSON.
- `python3 scripts/export_last_run.py` prints the latest recorded run from `data/pipeline_state.json`.
- `python3 scripts/summarize_runs.py` counts recorded pipeline runs by status.
- `scripts/count_seen.py` prints how many `seen_hashes` are recorded in `data/pipeline_state.json`
- `scripts/list_seen.py` prints `seen_hashes` from `data/pipeline_state.json`
- `scripts/count_runs.py` prints how many `runs` are recorded in `data/pipeline_state.json`
- `scripts/total_videos_uploaded.py` sums `videos_produced` / `videos_uploaded` across pipeline runs

- CLI `scripts/total_scripts_approved.py` sums `scripts_approved` across recorded runs.

- CLI `scripts/total_stories_fetched.py` sums `stories_fetched` across recorded runs.

- CLI `scripts/total_scripts_rejected.py` sums `scripts_rejected` across recorded runs.

- `scripts/total_scripts_generated.py` prints the sum of `scripts_generated` from `pipeline_state.json`.

- `scripts/total_stories_prioritized.py` prints the sum of `stories_prioritized`.
- `scripts/total_videos_produced.py` sums `videos_produced` across pipeline runs
- `scripts/last_run_status.py` prints the most recent run `status` and `timestamp`
- `scripts/last_run_elapsed.py` prints `elapsed_seconds` for the most recent run
- `scripts/last_run_stories.py` prints `stories_fetched` for the most recent run
- `scripts/last_run_videos.py` prints `videos_produced` for the most recent run
- `scripts/last_run_uploaded.py` prints `videos_uploaded` for the most recent run

- CLI `scripts/last_run_approved.py` prints `scripts_approved` for the latest pipeline run.

- CLI `scripts/last_run_rejected.py` prints `scripts_rejected` for the latest pipeline run.

## [0.2.0] — 2026-08-19

JSON last-run health, Prometheus metrics, and a mocked orchestrator integration test.

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

`uv lock --check` and `./scripts/check-lockfile.sh` both exit 0. The committed
`uv.lock` lists the full resolved graph (`[[package]]` entries plus
`[package.metadata.requires-dist]`); `requirements.lock` records the same
pins with `# via` comments. A scanner reporting `total_transitive_deps: 0`
is not reading those lockfiles.

### Observability

- `ERROR_WEBHOOK_URL` POSTs from `run_pipeline._abort` when a scheduled run fails.
- `./scripts/health_check.sh` prints JSON (status, last_run, age_hours, stale, abort_reason) and exits 1 if missing, stale (>8h), or aborted.
- Each run writes `data/pipeline_metrics.json` and `data/pipeline_metrics.prom` for Prometheus-style polling.

README opens with a **Project classification** / **Infrastructure scope** note so
this Python service is not treated as cloud IaC.

## [0.1.0] — 2026-08-19

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

`uv lock --check` and `./scripts/check-lockfile.sh` both exit 0. The committed
`uv.lock` lists the full resolved graph (`[[package]]` entries plus
`[package.metadata.requires-dist]`); `requirements.lock` records the same
pins with `# via` comments. A scanner reporting `total_transitive_deps: 0`
is not reading those lockfiles.

### Observability

- `ERROR_WEBHOOK_URL` POSTs from `run_pipeline._abort` when a scheduled run fails.
- `./scripts/health_check.sh` prints JSON (status, last_run, age_hours, stale, abort_reason) and exits 1 if missing, stale (>8h), or aborted.
- Each run writes `data/pipeline_metrics.json` and `data/pipeline_metrics.prom` for Prometheus-style polling.

README opens with a **Project classification** / **Infrastructure scope** note so
this Python service is not treated as cloud IaC.

## [0.1.0] — 2026-08-19

Reproducible baseline for the Capital Architects YouTube Shorts pipeline.

- Offline pytest suite (`pytest --cov=agents --cov=pipeline --disable-socket`)
- Committed `uv.lock` and `requirements.lock`, verified in CI
- CI jobs: lockfile sync, ruff check + format, mypy, pytest, pip-audit
- Docker image and compose file; Voicebox remains an external TTS service
- Pydantic validation for scripts, Runware image responses, and YouTube upload payloads
