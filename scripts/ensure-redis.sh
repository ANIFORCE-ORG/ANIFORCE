#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-${ROOT_DIR}/backend/.env}"
LOG_DIR="${2:-${ROOT_DIR}/logs}"

read_env_value() {
  local key="$1"
  local file="$2"
  local value

  [[ -f "${file}" ]] || return 0
  value="$(awk -v key="${key}" '
    $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
      line = $0
      sub("^[[:space:]]*" key "[[:space:]]*=[[:space:]]*", "", line)
      result = line
    }
    END { print result }
  ' "${file}")"
  value="${value%$'\r'}"
  if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "${value}" == \'*\' && "${value}" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "${value}"
}

REDIS_URL="${REDIS_URL:-$(read_env_value REDIS_URL "${ENV_FILE}")}"
if [[ -z "${REDIS_URL}" ]]; then
  echo "Redis preflight failed: REDIS_URL is not configured in ${ENV_FILE}." >&2
  exit 1
fi

case "${REDIS_URL}" in
  redis://*|rediss://*) ;;
  *)
    echo "Redis preflight failed: REDIS_URL must use redis:// or rediss://." >&2
    exit 1
    ;;
esac

redis_python() {
  local candidate
  for candidate in \
    "${REDIS_PYTHON:-}" \
    "${ROOT_DIR}/backend/.venv/bin/python" \
    "${ROOT_DIR}/backend/.venv/Scripts/python.exe" \
    python3 \
    python; do
    [[ -n "${candidate}" ]] || continue
    if command -v "${candidate}" >/dev/null 2>&1 || [[ -x "${candidate}" ]]; then
      if "${candidate}" -c 'import redis' >/dev/null 2>&1; then
        printf '%s' "${candidate}"
        return 0
      fi
    fi
  done
  return 1
}

REDIS_PYTHON_BIN="$(redis_python || true)"

if ! command -v redis-cli >/dev/null 2>&1 && [[ -z "${REDIS_PYTHON_BIN}" ]]; then
  echo "Redis preflight failed: no Redis client is available." >&2
  echo "Install backend Python requirements or install redis-cli." >&2
  echo "Ubuntu/Debian: sudo apt-get install redis-server redis-tools" >&2
  echo "RHEL/CentOS/Fedora: sudo dnf install redis || sudo yum install redis" >&2
  echo "Alpine: sudo apk add redis" >&2
  echo "macOS: brew install redis" >&2
  exit 1
fi

redis_ping() {
  if command -v redis-cli >/dev/null 2>&1; then
    [[ "$(redis-cli --no-auth-warning -u "${REDIS_URL}" ping 2>/dev/null || true)" == "PONG" ]] && return 0
  fi

  if [[ -n "${REDIS_PYTHON_BIN}" ]]; then
    REDIS_URL="${REDIS_URL}" "${REDIS_PYTHON_BIN}" - <<'PY' >/dev/null 2>&1 && return 0
import os
import sys

import redis

try:
    client = redis.Redis.from_url(
        os.environ["REDIS_URL"],
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
    )
    sys.exit(0 if client.ping() else 1)
except Exception:
    sys.exit(1)
PY
  fi

  return 1
}

if redis_ping; then
  echo "Redis ready: PONG"
  exit 0
fi

authority="${REDIS_URL#*://}"
authority="${authority%%/*}"
host_port="${authority##*@}"
host="${host_port%%:*}"
port="${host_port##*:}"
if [[ "${port}" == "${host_port}" || ! "${port}" =~ ^[0-9]+$ ]]; then
  port=6379
fi

if [[ "${REDIS_URL}" != redis://* || ( "${host}" != "127.0.0.1" && "${host}" != "localhost" ) ]]; then
  echo "Redis preflight failed: configured Redis is unreachable (${host}:${port})." >&2
  exit 1
fi

if command -v systemctl >/dev/null 2>&1 && [[ "${port}" == "6379" ]]; then
  echo "Redis is not reachable; starting redis-server.service..."
  systemctl start redis-server >/dev/null 2>&1 || sudo systemctl start redis-server >/dev/null 2>&1 || true
  for _ in $(seq 1 20); do
    redis_ping && break
    sleep 0.25
  done
fi

if ! redis_ping && command -v redis-server >/dev/null 2>&1; then
  mkdir -p "${LOG_DIR}/run"
  echo "Redis is not reachable; starting a local Redis process on port ${port}..."
  redis-server \
    --bind 127.0.0.1 \
    --protected-mode yes \
    --port "${port}" \
    --save '' \
    --appendonly no \
    --daemonize yes \
    --pidfile "${LOG_DIR}/run/redis.pid" \
    --logfile "${LOG_DIR}/redis.log" \
    --dir "${LOG_DIR}/run" >/dev/null 2>&1 || true
  for _ in $(seq 1 20); do
    redis_ping && break
    sleep 0.25
  done
fi

if ! redis_ping; then
  echo "Redis preflight failed: unable to connect to ${host}:${port}." >&2
  echo "Install/start Redis or correct REDIS_URL before starting Backend and Agent workers." >&2
  exit 1
fi

echo "Redis ready: PONG"
