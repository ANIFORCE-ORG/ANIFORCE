#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_ENV="${1:-${ROOT_DIR}/aniforce-agent/.env}"
LOG_DIR="${2:-${ROOT_DIR}/logs}"
PID_FILE="${3:-${ROOT_DIR}/.server_pids}"
PHOENIX_PORT="${PHOENIX_PORT:-6006}"
PHOENIX_GRPC_PORT="${PHOENIX_GRPC_PORT:-4317}"
PHOENIX_HOST="${PHOENIX_HOST:-127.0.0.1}"
PHOENIX_BIN="${ROOT_DIR}/aniforce-agent/.venv/bin/phoenix"
PHOENIX_LOG="${LOG_DIR}/$(date +%Y%m%d).phoenix.log"
PHOENIX_WORKING_DIR="${PHOENIX_WORKING_DIR:-${ROOT_DIR}/.phoenix}"

read_env() {
  local key="$1"
  grep -E "^${key}=" "${AGENT_ENV}" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

tracing_enabled="$(read_env AGENT_TRACING_ENABLED)"
tracing_provider="$(read_env AGENT_TRACING_PROVIDER)"
# macOS ships Bash 3.2, which does not support ${value,,} lowercase expansion.
tracing_enabled="$(printf '%s' "${tracing_enabled}" | tr '[:upper:]' '[:lower:]')"
tracing_provider="$(printf '%s' "${tracing_provider}" | tr '[:upper:]' '[:lower:]')"
if [[ "${tracing_enabled}" != "true" || "${tracing_provider}" != "phoenix" ]]; then
  echo "Phoenix tracing is disabled; skipping collector startup."
  exit 0
fi

if [[ ! "${PHOENIX_PORT}" =~ ^[1-9][0-9]{3}$ ]]; then
  echo "PHOENIX_PORT must be a four-digit port, got: ${PHOENIX_PORT}" >&2
  exit 1
fi
if [[ ! "${PHOENIX_GRPC_PORT}" =~ ^[1-9][0-9]{3}$ ]]; then
  echo "PHOENIX_GRPC_PORT must be a four-digit port, got: ${PHOENIX_GRPC_PORT}" >&2
  exit 1
fi
if [[ ! -x "${PHOENIX_BIN}" ]]; then
  echo "Phoenix server is not installed. Install aniforce-agent/requirements.txt first." >&2
  exit 1
fi

health_url="http://${PHOENIX_HOST}:${PHOENIX_PORT}/healthz"
if curl --noproxy '*' -fsS --max-time 2 "${health_url}" >/dev/null 2>&1; then
  echo "Phoenix already ready: ${health_url}"
  exit 0
fi
if ss -ltn 2>/dev/null | grep -qE ":${PHOENIX_PORT}\\b"; then
  echo "Port ${PHOENIX_PORT} is occupied by a non-healthy service." >&2
  exit 1
fi

mkdir -p "${LOG_DIR}" "${PHOENIX_WORKING_DIR}"
PHOENIX_HOST="${PHOENIX_HOST}" \
PHOENIX_PORT="${PHOENIX_PORT}" \
PHOENIX_GRPC_PORT="${PHOENIX_GRPC_PORT}" \
PHOENIX_WORKING_DIR="${PHOENIX_WORKING_DIR}" \
  "${PHOENIX_BIN}" serve >"${PHOENIX_LOG}" 2>&1 &
phoenix_pid="$!"
echo "${phoenix_pid}" >> "${PID_FILE}"

for _ in $(seq 1 90); do
  if curl --noproxy '*' -fsS --max-time 2 "${health_url}" >/dev/null 2>&1; then
    echo "Phoenix ready: ${health_url} (PID ${phoenix_pid})"
    echo "Phoenix UI: http://${PHOENIX_HOST}:${PHOENIX_PORT}"
    echo "Phoenix logs: ${PHOENIX_LOG}"
    exit 0
  fi
  if ! kill -0 "${phoenix_pid}" >/dev/null 2>&1; then
    echo "Phoenix exited during startup. See ${PHOENIX_LOG}" >&2
    tail -n 30 "${PHOENIX_LOG}" >&2 || true
    exit 1
  fi
  sleep 1
done

echo "Phoenix did not become healthy within 90 seconds. See ${PHOENIX_LOG}" >&2
kill "${phoenix_pid}" >/dev/null 2>&1 || true
exit 1
