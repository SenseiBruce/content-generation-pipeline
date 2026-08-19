# Capital Architects — YouTube Shorts Automation Pipeline

**Project classification:** Python content-automation service (CLI / scheduled job).
This repository is **not** infrastructure-as-code.

**Infrastructure scope:** there is no Terraform, Kubernetes, Helm, Pulumi, or
Ansible. The only container files are `Dockerfile` and `docker-compose.yml`,
used to run this Python app and its tests in isolation. OpenClaw schedules
`python3 run_pipeline.py` on the host. See `docs/architecture.md`.

Autonomous finance news Shorts factory for the **Capital Architects** YouTube channel.

- **Audience:** India
- **Topic:** Finance, RBI, SEBI, taxation, budget, inflation, investing
- **Format:** Vertical 1080×1920, ≤60 seconds
- **Cadence:** Every 6 hours via OpenClaw scheduler

See [CONTRIBUTING.md](CONTRIBUTING.md) for the offline test workflow (`pytest --disable-socket`), ruff/mypy gates, and branch naming.

---

## Folder Structure

```
content-generation-pipeline/
├── agents/               # One Python file per pipeline stage
├── pipeline/             # Shared utilities (http_client, logger, schemas, state)
├── prompts/              # GPT-4o system prompts
├── tests/                # pytest suite (no live API keys required)
├── data/                 # Runtime-generated (gitignored)
├── logs/                 # Daily rotating log files
├── run_pipeline.py       # Main orchestrator
├── auth_youtube.py       # One-time OAuth2 authentication
├── openclaw_task.yaml    # OpenClaw scheduler config
├── CONTRIBUTING.md
├── CHANGELOG.md
├── requirements.txt
├── requirements.lock     # pip-compile/uv pins (install with pip)
├── uv.lock               # uv lockfile (recognized by dependency scanners)
├── requirements-dev.txt
└── .env.template
```

---

## Prerequisites

### 1. System Dependencies

```bash
# FFmpeg (required for video stitching)
brew install ffmpeg   # macOS
# sudo apt-get install -y ffmpeg   # Debian/Ubuntu

# Python 3.11+
python3 --version
```

### 2. Python Environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate

# Reproducible install (preferred)
pip install -r requirements.lock
# equivalent: uv sync --frozen

# Or from the unpinned-to-exact spec
pip install -r requirements.txt
```

CI fails if `requirements.lock` or `uv.lock` is missing or out of sync (`./scripts/check-lockfile.sh`).

Optional Coqui TTS (not required — the voicer agent uses Voicebox over HTTP):

```bash
pip install -r requirements-optional.txt
```

---

## Setup

### Step 1: Configure API Keys

```bash
cp .env.template .env
```

Edit `.env` and fill in:

| Variable | Where to get it |
|---|---|
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `OPENROUTER_MODEL` | Keep as `openai/gpt-4o` (or change to `gpt-4o-mini` for lower cost) |
| `RUNWARE_API_KEY` | [runware.ai](https://runware.ai) dashboard |
| `VOICEBOX_API_URL` | Voicebox server URL (default `http://localhost:8000`) |
| `VOICEBOX_PROFILE_ID` | Voice profile ID from the Voicebox UI |
| `ERROR_WEBHOOK_URL` | Optional HTTPS webhook fired when a run aborts (leave empty locally) |

### Step 2: YouTube OAuth Authentication (once only)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **YouTube Data API v3**
3. Create OAuth 2.0 credentials → Download as `client_secret.json`
4. Place `client_secret.json` in the project root
5. Run:

```bash
python3 auth_youtube.py
```

A browser window opens → sign in with the Capital Architects Google account → approve permissions.
This saves `youtube_token.json`. You will not need to repeat this step.

### Step 3: Register with OpenClaw

From the OpenClaw dashboard or config, register the task:

```bash
openclaw register openclaw_task.yaml
```

Or manually add the task in the OpenClaw UI, pointing to:
- **Command:** `python3 run_pipeline.py`
- **Working directory:** the repository root
- **Config file:** `openclaw_task.yaml`

---

## Running Manually

```bash
source .venv/bin/activate

# Run the full pipeline once
python3 run_pipeline.py
```

### Running Individual Agents (for debugging)

```bash
# Stage 1: Fetch news only
python3 -m agents.watchtower

# Stage 2: Prioritize stories (requires data/raw/ to have batches)
python3 -m agents.prioritizer

# Stage 3: Generate scripts (requires data/prioritized/)
python3 -m agents.scriptwriter

# Stage 4: Judge scripts (requires data/scripts/)
python3 -m agents.judge
```

---

## Tests

Install the test extras, then run the suite. Tests monkeypatch `pipeline.http_client` and do not need live API keys or network access.

```bash
pip install -r requirements-dev.txt
pytest --cov=agents --cov=pipeline --cov-report=term --disable-socket
```

CI (GitHub Actions) runs `ruff check .` and the same pytest command on every push and pull request.

---

## Docker

```bash
docker build -t content-generation-pipeline .
docker run --rm content-generation-pipeline
docker compose run --rm pipeline
```

The default container command runs the offline test suite. Container files here
are an app runtime, not cloud IaC (see **Infrastructure scope** at the top of
this README). Policy scanning (Checkov/tfsec) does not apply.

---

## Monitoring

Logs are written as JSON lines to `logs/pipeline_YYYYMMDD.log` (fields:
`timestamp`, `level`, `message`, `stage`, `run_id`, `duration_ms`) and as
readable text on the console.

```bash
# Watch live log output
tail -f logs/pipeline_$(date +%Y%m%d).log
```

Pipeline run history (last 100 runs) is stored in `data/pipeline_state.json`.
Aborted runs are recorded with `status: aborted` and `abort_reason`. When
`ERROR_WEBHOOK_URL` is set, `run_pipeline._abort` POSTs that payload so a
missed 6-hour OpenClaw slot can still page.

Poll last-run health as machine-readable JSON (exit 0 = last run succeeded
within 8 hours; exit 1 if missing, stale, or aborted):

```bash
./scripts/health_check.sh
```

Each `record_run` also writes `data/pipeline_metrics.json` and a Prometheus
text file `data/pipeline_metrics.prom` (`pipeline_runs_total`,
`pipeline_last_run_timestamp_seconds`, `pipeline_last_run_healthy`,
`pipeline_videos_uploaded`) for the same pollers.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `OPENROUTER_API_KEY not set` | Check `.env` file exists and is populated |
| `YouTube token not found` | Run `python3 auth_youtube.py` |
| `ffmpeg not found` | Install FFmpeg (`brew install ffmpeg` or `apt-get install ffmpeg`) |
| `VOICEBOX_PROFILE_ID is not set` | Create a profile in the Voicebox UI and add its ID to `.env` |
| `Could not connect to Voicebox` | Start the Voicebox server and confirm `VOICEBOX_API_URL` |
| `No new stories found` | Normal if all stories were seen in the last 6h run |
| Judge keeps rejecting scripts | Lower `APPROVAL_THRESHOLD` in `agents/judge.py` (default 85) |

---

## Security Notes

- `.env`, `youtube_token.json`, and `client_secret.json` are gitignored — never commit them
- All API calls go to HTTPS only (Voicebox may be local HTTP on localhost)
- OpenClaw sandbox restricts file access to the project directory
- No shell exec is allowed from within the pipeline tasks
