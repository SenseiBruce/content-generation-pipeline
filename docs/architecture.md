# Deployment architecture

This repository is a **Python application pipeline**, not infrastructure-as-code.
There are no Terraform, Kubernetes, Helm, Pulumi, or Ansible manifests; dimension
O (IaC) does not apply.

## Runtime target

The production cadence is the **OpenClaw scheduler** (`openclaw_task.yaml`):

- Command: `python3 run_pipeline.py`
- Working directory: the repository root
- Interval: every 6 hours
- Runtime cap: 25 minutes (the orchestrator self-checks at 23 minutes)

Secrets stay in `.env` (from `.env.template`). YouTube OAuth tokens are
`youtube_token.json` after `auth_youtube.py`.

## Container target

`Dockerfile` builds a Python 3.11 image with FFmpeg and the locked dependencies.
Default container command runs the offline pytest suite.

`docker-compose.yml` describes:

| Service    | Role |
|------------|------|
| `pipeline` | This application image |
| `voicebox` | Optional TTS HTTP server on port 8000 (`VOICEBOX_API_URL`) |

Voicebox is **not** vendored here. Point `VOICEBOX_API_URL` at a host-side
Voicebox process (`http://host.docker.internal:8000`) or enable the `tts`
compose profile as a stub listener.

```bash
docker build -t content-generation-pipeline .
docker compose run --rm pipeline
```

## External APIs (not deployed by this repo)

- OpenRouter — script generation and judging
- Runware — scene image inference
- YouTube Data API v3 — upload and scheduling
- RSS sources — watchtower fetch

See `PIPELINE_ARCHITECTURE.md` for per-agent flow.
