#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

unset VIRTUAL_ENV
unset CONDA_PREFIX
unset CONDA_DEFAULT_ENV
unset PYENV_VERSION
unset PYTHONHOME
unset PYTHONPATH

BACKEND_VENV="$(cd "$PROJECT_ROOT/../backend/.venv/bin" 2>/dev/null && pwd || true)"
ROOT_VENV="$(cd "$PROJECT_ROOT/../.venv/bin" 2>/dev/null && pwd || true)"
AGENT_VENV="$(cd "$PROJECT_ROOT/.venv/bin" && pwd)"

clean_path=""
IFS=':' read -r -a path_parts <<< "${PATH:-}"
for path_part in "${path_parts[@]}"; do
  normalized_path_part="$(cd "$path_part" 2>/dev/null && pwd || printf '%s' "$path_part")"
  case "$path_part" in
    "$BACKEND_VENV"|"$ROOT_VENV"|"$AGENT_VENV"|"")
      ;;
    *)
      case "$normalized_path_part" in
        "$BACKEND_VENV"|"$ROOT_VENV"|"$AGENT_VENV")
          ;;
        *)
          if [[ -z "$clean_path" ]]; then
            clean_path="$path_part"
          else
            clean_path="$clean_path:$path_part"
          fi
          ;;
      esac
      ;;
  esac
done

export VIRTUAL_ENV="$PROJECT_ROOT/.venv"
export PATH="$AGENT_VENV:$clean_path"
export UV_PROJECT_ENVIRONMENT=".venv"
export UV_CACHE_DIR="./uv_cache"

exec "$@"
