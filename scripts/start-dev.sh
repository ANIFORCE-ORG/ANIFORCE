#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
unset VIRTUAL_ENV
BACKEND_DIR="${ROOT_DIR}/backend"
AGENT_DIR="${ROOT_DIR}/aniforce-agent"
FRONTEND_DIR="${ROOT_DIR}/frontend"
LOG_DIR="${ROOT_DIR}/logs"
RUN_DIR="${LOG_DIR}/run"
LOG_DATE="$(date +%Y%m%d)"
LOG_ENV="${LOG_ENV:-dev}"
AGENT_LOG="${LOG_DIR}/${LOG_DATE}.${LOG_ENV}.agent.uvicorn.log"
BACKEND_LOG="${LOG_DIR}/${LOG_DATE}.${LOG_ENV}.backend.uvicorn.log"
FRONTEND_LOG="${LOG_DIR}/${LOG_DATE}.${LOG_ENV}.frontend.vite.log"
PID_FILE="${RUN_DIR}/${LOG_ENV}.stack.pids"

HOST="${HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
AGENT_PORT="${AGENT_PORT:-8020}"
FRONTEND_PORT="${FRONTEND_PORT:-3010}"
PHOENIX_PORT="${PHOENIX_PORT:-6006}"
PYPI_INDEX_URL="${PYPI_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
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

mkdir -p "${LOG_DIR}" "${RUN_DIR}" "${BACKEND_DIR}/uv_cache" "${AGENT_DIR}/uv_cache" "${ROOT_DIR}/npm_cache"
: > "${PID_FILE}"
: > "${AGENT_LOG}"
: > "${BACKEND_LOG}"
: > "${FRONTEND_LOG}"

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
  if [[ -f "${PID_FILE}" ]]; then
    while read -r pid; do
      if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
        pkill -TERM -P "${pid}" >/dev/null 2>&1 || true
        kill -TERM "${pid}" >/dev/null 2>&1 || true
      fi
    done < "${PID_FILE}"
  fi
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
  UV_CACHE_DIR="${ROOT_DIR}/uv_cache" uv pip install --index-url "${PYPI_INDEX_URL}" -r requirements.txt

  echo "Preparing agent uv environment..."
  cd "${AGENT_DIR}"
  ensure_uv_venv "agent"
  UV_CACHE_DIR="${ROOT_DIR}/uv_cache" uv pip install --index-url "${PYPI_INDEX_URL}" -r requirements.txt

  echo "Preparing frontend pnpm environment..."
  cd "${FRONTEND_DIR}"
  npm_config_cache="${ROOT_DIR}/npm_cache" npx pnpm install
fi

echo "Checking Redis Agent event stream..."
"${ROOT_DIR}/scripts/ensure-redis.sh" "${BACKEND_DIR}/.env" "${LOG_DIR}"

echo "Checking Phoenix tracing collector..."
PHOENIX_PORT="${PHOENIX_PORT}" \
  "${ROOT_DIR}/scripts/ensure-phoenix.sh" "${AGENT_DIR}/.env" "${LOG_DIR}" "${PID_FILE}"

echo "Migrating backend database..."
cd "${BACKEND_DIR}"
UV_CACHE_DIR=./uv_cache uv run python -m alembic upgrade head

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
PHOENIX_COLLECTOR_ENDPOINT="http://127.0.0.1:${PHOENIX_PORT}/v1/traces" \
uv run python -m uvicorn app.main:app \
  --host "${HOST}" \
  --port "${AGENT_PORT}" \
  "${RELOAD_ARGS[@]}" \
  > "${AGENT_LOG}" 2>&1 &
AGENT_PID="$!"
echo "${AGENT_PID}" >> "${PID_FILE}"
echo "Agent logs: ${AGENT_LOG}"

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
    > "${BACKEND_LOG}" 2>&1 &
  BACKEND_PID="$!"
  echo "Backend logs: ${BACKEND_LOG}"
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
  > "${FRONTEND_LOG}" 2>&1 &
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
Phoenix traces: http://${DISPLAY_HOST}:${PHOENIX_PORT}

Bind host:      ${HOST}
If you open from another machine/browser environment, use the Network URL above.

Logs:
EOF

if [[ "${LOG_TO_FILE}" -eq 1 ]]; then
  echo "  Agent:    ${AGENT_LOG}"
  echo "  Backend:  ${BACKEND_LOG}"
  echo "  Frontend: ${FRONTEND_LOG}"
  echo ""
  echo "To view logs:"
  echo "  tail -f ${AGENT_LOG}"
  echo "  tail -f ${BACKEND_LOG}"
  echo "  tail -f ${FRONTEND_LOG}"
else
  echo "  Agent:    ${AGENT_LOG}"
  echo "  Backend:  console (below)"
  echo "  Frontend: ${FRONTEND_LOG}"
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
