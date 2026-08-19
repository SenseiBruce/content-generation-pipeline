#!/usr/bin/env bash
# Fail if committed lockfiles are missing or out of sync with requirements.txt / pyproject.toml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f requirements.lock ]]; then
  echo "error: requirements.lock is missing" >&2
  exit 1
fi

if [[ ! -f uv.lock ]]; then
  echo "error: uv.lock is missing (scanners and CI require a recognized lockfile)" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is required to verify lockfile sync" >&2
  exit 1
fi

uv lock --check

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
uv pip compile --python-version 3.11 requirements.txt -o "$TMP"

filter_pins() {
  grep -E '^[a-zA-Z0-9._-]+==' "$1" | tr '[:upper:]' '[:lower:]' | sort
}

if ! diff -u <(filter_pins requirements.lock) <(filter_pins "$TMP"); then
  echo "error: requirements.lock is out of sync with requirements.txt" >&2
  echo "regenerate with: uv pip compile --python-version 3.11 requirements.txt -o requirements.lock" >&2
  exit 1
fi

echo "lockfiles ok"
