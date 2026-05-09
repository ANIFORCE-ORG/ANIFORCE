#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8020}"
PYTHON_BIN="${PYTHON_BIN:-}"

cd "$ROOT_DIR"

if [ -z "$PYTHON_BIN" ]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.11)"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "GEO Diagnosis requires Python 3.10+. Set PYTHON_BIN to a newer Python executable." >&2
  echo "Current Python: $("$PYTHON_BIN" --version)" >&2
  exit 1
fi

if [ -d ".venv" ] && [ -x ".venv/bin/python" ]; then
  if ! ".venv/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    rm -rf .venv
  fi
fi

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

".venv/bin/python" -m pip install --upgrade pip
".venv/bin/python" -m pip install -r backend/requirements.txt

echo "GEO Diagnosis demo: http://127.0.0.1:${PORT}/frontend/index.html"
".venv/bin/uvicorn" backend.app:app --host 127.0.0.1 --port "$PORT"
