#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
unset VIRTUAL_ENV
BACKEND_DIR="${ROOT_DIR}/backend"
AGENT_DIR="${ROOT_DIR}/aniforce-agent"
FRONTEND_DIR="${ROOT_DIR}/frontend"
LOG_DIR="${ROOT_DIR}/logs"
PID_FILE="${LOG_DIR}/aniforce_dev.pids"

HOST="${HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
AGENT_PORT="${AGENT_PORT:-8020}"
FRONTEND_PORT="${FRONTEND_PORT:-3010}"
LOCAL_NO_PROXY="localhost,127.0.0.1,0.0.0.0,::1,${HOST}"
BACKEND_RELOAD=0
SKIP_INSTALL=0
CLEAR_PORTS=1
LOG_TO_FILE=1  # 默认写入文件

usage() {
  cat <<EOF
Usage:
  scripts/start-dev.sh [options]

Options:
  --host HOST             Default: 127.0.0.1
  --backend-port PORT     Default: 8010
  --agent-port PORT       Default: 8020
  --frontend-port PORT    Default: 3010
  --reload                Enable backend/agent uvicorn reload
  --skip-install          Skip dependency installation
  --no-clear-ports        Do not clear selected ports
  --log-to-file           Write logs to files instead of console
  -h, --help              Show help

URLs:
  Frontend:       http://HOST:FRONTEND_PORT
  Backend health: http://HOST:BACKEND_PORT/health
  Agent health:   http://HOST:AGENT_PORT/health
  API docs:       http://HOST:BACKEND_PORT/docs
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --backend-port) BACKEND_PORT="$2"; shift 2 ;;
    --agent-port) AGENT_PORT="$2"; shift 2 ;;
    --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
    --reload) BACKEND_RELOAD=1; shift 1 ;;
    --no-backend-reload) BACKEND_RELOAD=0; shift 1 ;;
    --skip-install) SKIP_INSTALL=1; shift 1 ;;
    --no-clear-ports) CLEAR_PORTS=0; shift 1 ;;
    --log-to-file) LOG_TO_FILE=1; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

export NO_PROXY="${LOCAL_NO_PROXY}${NO_PROXY:+,${NO_PROXY}}"
export no_proxy="${LOCAL_NO_PROXY}${no_proxy:+,${no_proxy}}"

mkdir -p "${LOG_DIR}" "${BACKEND_DIR}/uv_cache" "${AGENT_DIR}/uv_cache" "${ROOT_DIR}/npm_cache"
: > "${PID_FILE}"
: > "${LOG_DIR}/agent-dev.log"
: > "${LOG_DIR}/backend-dev.log"
: > "${LOG_DIR}/frontend-dev.log"

DISPLAY_HOST="${HOST}"
if [[ "${HOST}" == "0.0.0.0" ]]; then
  DISPLAY_HOST="$(hostname -I | tr ' ' '\n' | grep -E '^[0-9]' | head -1)"
fi

AGENT_PID=""
BACKEND_PID=""
FRONTEND_PID=""

process_command() {
  local pid="$1"
  ps -p "${pid}" -o command= 2>/dev/null || true
}

port_pids() {
  local port="$1"
  ss -ltnp 2>/dev/null \
    | grep -E ":${port}\\b" \
    | grep -oE 'pid=[0-9]+' \
    | cut -d= -f2 \
    | sort -u || true
}

show_port() {
  local port="$1"
  ss -ltnp 2>/dev/null | grep -E ":${port}\\b" || true
}

clear_port() {
  local port="$1"
  local name="$2"
  local pids
  pids="$(port_pids "${port}")"
  if [[ -z "${pids}" ]]; then
    return 0
  fi

  echo "Clearing ${name} port ${port}:"
  show_port "${port}"

  while read -r pid; do
    [[ -z "${pid}" ]] && continue
    if kill -0 "${pid}" >/dev/null 2>&1; then
      echo "  TERM pid ${pid}: $(process_command "${pid}")"
      pkill -TERM -P "${pid}" >/dev/null 2>&1 || true
      kill -TERM "${pid}" >/dev/null 2>&1 || true
    fi
  done <<< "${pids}"

  for _ in $(seq 1 30); do
    if [[ -z "$(port_pids "${port}")" ]]; then
      return 0
    fi
    sleep 0.2
  done

  pids="$(port_pids "${port}")"
  while read -r pid; do
    [[ -z "${pid}" ]] && continue
    if kill -0 "${pid}" >/dev/null 2>&1; then
      echo "  KILL pid ${pid}: $(process_command "${pid}")"
      pkill -KILL -P "${pid}" >/dev/null 2>&1 || true
      kill -KILL "${pid}" >/dev/null 2>&1 || true
    fi
  done <<< "${pids}"

  for _ in $(seq 1 10); do
    if [[ -z "$(port_pids "${port}")" ]]; then
      return 0
    fi
    sleep 0.2
  done

  echo "Failed to clear ${name} port ${port}:" >&2
  show_port "${port}" >&2
  exit 1
}

check_port_free() {
  local port="$1"
  local name="$2"
  if [[ -n "$(port_pids "${port}")" ]]; then
    echo "${name} port ${port} is already in use:" >&2
    show_port "${port}" >&2
    echo "Use --clear-ports or stop that process yourself." >&2
    exit 1
  fi
}

cleanup() {
  for pid in "${AGENT_PID}" "${BACKEND_PID}" "${FRONTEND_PID}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      pkill -TERM -P "${pid}" >/dev/null 2>&1 || true
      kill -TERM "${pid}" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup EXIT INT TERM

wait_http() {
  local url="$1"
  local name="$2"
  for _ in $(seq 1 60); do
    if curl --noproxy '*' -fsS "${url}" >/dev/null 2>&1; then
      echo "${name} ready: ${url}"
      return 0
    fi
    sleep 1
  done
  echo "${name} did not become ready: ${url}" >&2
  exit 1
}

check_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing command: $1" >&2
    exit 1
  }
}

ensure_uv_venv() {
  local name="$1"
  if [[ -d ".venv" ]]; then
    if [[ -L ".venv/bin/python" && ! -e ".venv/bin/python" ]] || [[ -L ".venv/bin/python3" && ! -e ".venv/bin/python3" ]]; then
      echo "${name} .venv is broken; recreating..."
      rm -rf .venv
    fi
  fi

  if [[ ! -d ".venv" ]]; then
    UV_CACHE_DIR=./uv_cache uv venv --python 3.11
  fi
}

check_command ss
check_command curl
check_command uv
check_command npm
check_command npx

if [[ "${CLEAR_PORTS}" -eq 1 ]]; then
  clear_port "${BACKEND_PORT}" "backend"
  clear_port "${AGENT_PORT}" "agent"
  clear_port "${FRONTEND_PORT}" "frontend"
else
  check_port_free "${BACKEND_PORT}" "backend"
  check_port_free "${AGENT_PORT}" "agent"
  check_port_free "${FRONTEND_PORT}" "frontend"
fi

if [[ "${SKIP_INSTALL}" -eq 0 ]]; then
  echo "Preparing backend uv environment..."
  cd "${BACKEND_DIR}"
  ensure_uv_venv "backend"
  UV_CACHE_DIR=./uv_cache uv pip install -r requirements.txt

  echo "Preparing agent uv environment..."
  cd "${AGENT_DIR}"
  ensure_uv_venv "agent"
  UV_CACHE_DIR=./uv_cache uv pip install -r requirements.txt

  echo "Preparing frontend pnpm environment..."
  cd "${FRONTEND_DIR}"
  npm_config_cache="${ROOT_DIR}/npm_cache" npx pnpm install
fi

RELOAD_ARGS=()
if [[ "${BACKEND_RELOAD}" -eq 1 ]]; then
  RELOAD_ARGS=(--reload)
fi

cd "${AGENT_DIR}"
echo "Starting agent service on ${HOST}:${AGENT_PORT}..."
UV_CACHE_DIR=./uv_cache \
HOST="${HOST}" \
PORT="${AGENT_PORT}" \
BACKEND_BASE_URL="http://${HOST}:${BACKEND_PORT}" \
uv run python -m uvicorn app.main:app \
  --host "${HOST}" \
  --port "${AGENT_PORT}" \
  "${RELOAD_ARGS[@]}" \
  > "${LOG_DIR}/agent-dev.log" 2>&1 &
AGENT_PID="$!"
echo "${AGENT_PID}" >> "${PID_FILE}"
echo "Agent logs: ${LOG_DIR}/agent-dev.log"

wait_http "http://${HOST}:${AGENT_PORT}/health" "Agent"

cd "${BACKEND_DIR}"
echo "Starting backend on ${HOST}:${BACKEND_PORT}..."
if [[ "${LOG_TO_FILE}" -eq 1 ]]; then
  UV_CACHE_DIR=./uv_cache \
  AGENT_SERVICE_URL="http://${HOST}:${AGENT_PORT}" \
  uv run python -m uvicorn app.main:app \
    --host "${HOST}" \
    --port "${BACKEND_PORT}" \
    "${RELOAD_ARGS[@]}" \
    > "${LOG_DIR}/backend-dev.log" 2>&1 &
  BACKEND_PID="$!"
  echo "Backend logs: ${LOG_DIR}/backend-dev.log"
else
  UV_CACHE_DIR=./uv_cache \
  LOG_LEVEL=DEBUG \
  AGENT_SERVICE_URL="http://${HOST}:${AGENT_PORT}" \
  uv run python -m uvicorn app.main:app \
    --host "${HOST}" \
    --port "${BACKEND_PORT}" \
    "${RELOAD_ARGS[@]}" &
  BACKEND_PID="$!"
  echo "Backend logs: console (PID ${BACKEND_PID})"
fi
echo "${BACKEND_PID}" >> "${PID_FILE}"

wait_http "http://${HOST}:${BACKEND_PORT}/health" "Backend"

cd "${FRONTEND_DIR}"
echo "Starting frontend on ${HOST}:${FRONTEND_PORT}..."
# 前端日志总是写文件（太多了）
VITE_BACKEND_HOST="${HOST}" \
VITE_BACKEND_PORT="${BACKEND_PORT}" \
VITE_FRONTEND_PORT="${FRONTEND_PORT}" \
npm_config_cache="${ROOT_DIR}/npm_cache" \
npx pnpm --filter main-app dev --host "${HOST}" --port "${FRONTEND_PORT}" --strictPort \
  > "${LOG_DIR}/frontend-dev.log" 2>&1 &
FRONTEND_PID="$!"
echo "${FRONTEND_PID}" >> "${PID_FILE}"

wait_http "http://${HOST}:${FRONTEND_PORT}" "Frontend"

cat <<EOF

========================================
ANIFORCE dev stack is running
========================================
Frontend:       http://${DISPLAY_HOST}:${FRONTEND_PORT}
Backend health: http://${DISPLAY_HOST}:${BACKEND_PORT}/health
Agent health:   http://${DISPLAY_HOST}:${AGENT_PORT}/health
Agent runs API: http://${DISPLAY_HOST}:${AGENT_PORT}/api/agent/runs
API docs:       http://${DISPLAY_HOST}:${BACKEND_PORT}/docs

Bind host:      ${HOST}
If you open from another machine/browser environment, use the Network URL above.

Logs:
EOF

if [[ "${LOG_TO_FILE}" -eq 1 ]]; then
  echo "  Agent:    ${LOG_DIR}/agent-dev.log"
  echo "  Backend:  ${LOG_DIR}/backend-dev.log"
  echo "  Frontend: ${LOG_DIR}/frontend-dev.log"
  echo ""
  echo "To view logs:"
  echo "  tail -f ${LOG_DIR}/agent-dev.log"
  echo "  tail -f ${LOG_DIR}/backend-dev.log"
  echo "  tail -f ${LOG_DIR}/frontend-dev.log"
else
  echo "  Agent:    ${LOG_DIR}/agent-dev.log"
  echo "  Backend:  console (below)"
  echo "  Frontend: ${LOG_DIR}/frontend-dev.log"
  echo ""
  echo "Backend logs will appear below."
  echo "Agent tracing: aniforce-agent/runtime/agent/traces/YYYYMMDD/*.jsonl"
fi

echo ""
echo "PIDs: ${PID_FILE}"
echo "Press Ctrl+C to stop."
echo "========================================"
echo ""

wait
