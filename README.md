# Capital Architects — YouTube Shorts Automation Pipeline

Autonomous finance news Shorts factory for the **Capital Architects** YouTube channel.

- **Audience:** India
- **Topic:** Finance, RBI, SEBI, taxation, budget, inflation, investing
- **Format:** Vertical 1080×1920, ≤60 seconds
- **Cadence:** Every 6 hours via OpenClaw scheduler

---

## Folder Structure

```
content-generation-pipeline/
├── agents/               # One Python file per pipeline stage
├── pipeline/             # Shared utilities (logger, state)
├── prompts/              # GPT-4o system prompts
├── data/                 # Runtime-generated (gitignored)
├── logs/                 # Daily rotating log files
├── run_pipeline.py       # Main orchestrator
├── auth_youtube.py       # One-time OAuth2 authentication
├── openclaw_task.yaml    # OpenClaw scheduler config
├── requirements.txt
└── .env.template
```

---

## Prerequisites

### 1. System Dependencies

```bash
# FFmpeg (required for video stitching)
brew install ffmpeg

# Python 3.11+
python3 --version
```

### 2. Python Environment

```bash
cd /Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline

# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> **Note on Coqui TTS:** The first run will download the VCTK model (~1.5 GB).
> This is a one-time download cached in `~/.local/share/tts/`.

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
# Point OpenClaw at the task config
openclaw register openclaw_task.yaml
```

Or manually add the task in the OpenClaw UI, pointing to:
- **Command:** `python3 run_pipeline.py`
- **Working directory:** `/Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline`
- **Config file:** `openclaw_task.yaml`

---

## Running Manually

```bash
cd /Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline
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

## Monitoring

Logs are written to `logs/pipeline_YYYYMMDD.log` and printed to console.

```bash
# Watch live log output
tail -f logs/pipeline_$(date +%Y%m%d).log
```

Pipeline run history (last 100 runs) is stored in `data/pipeline_state.json`.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `OPENROUTER_API_KEY not set` | Check `.env` file exists and is populated |
| `YouTube token not found` | Run `python3 auth_youtube.py` |
| `ffmpeg not found` | Run `brew install ffmpeg` |
| Coqui TTS slow first run | Model download in progress (~1.5 GB, one-time) |
| `No new stories found` | Normal if all stories were seen in the last 6h run |
| Judge keeps rejecting scripts | Lower `APPROVAL_THRESHOLD` in `agents/judge.py` (default 85) |

---

## Security Notes

- `.env`, `youtube_token.json`, and `client_secret.json` are gitignored — never commit them
- All API calls go to HTTPS only
- OpenClaw sandbox restricts file access to the project directory
- No shell exec is allowed from within the pipeline tasks
