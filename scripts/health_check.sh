#!/usr/bin/env bash
# Poll data/pipeline_state.json for OpenClaw / CI. Exit 0 if the last run is healthy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

exec python3 -m pipeline.health "$@"
