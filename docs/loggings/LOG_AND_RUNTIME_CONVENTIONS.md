# Log and Agent Runtime Conventions

## Log file naming

Use this pattern for newly generated service logs:

```text
logs/YYYYMMDD.<env>.<service>.<stream>.log
```

Fields:

- `YYYYMMDD`: local start date, for example `20260623`
- `env`: `dev`, `cloud`, `prod`, or a short custom environment name
- `service`: `agent`, `backend`, `frontend`, or a focused probe name
- `stream`: `uvicorn`, `vite`, `app`, `probe`, `e2e`, `smoke`, or another concrete source

Current dev stack outputs:

```text
logs/YYYYMMDD.dev.agent.uvicorn.log
logs/YYYYMMDD.dev.backend.uvicorn.log
logs/YYYYMMDD.dev.frontend.vite.log
logs/run/dev.stack.pids
```

Rules:

- Runtime PID files go under `logs/run/`, not mixed with `.log` files.
- Long-lived service logs should be named by service and stream.
- One-off checks should use `logs/YYYYMMDD.dev.<topic>.probe.log`.
- E2E checks should use `logs/YYYYMMDD.dev.<block-or-flow>.e2e.log`.
- Do not write logs under `/tmp`, `/var/log`, or home-directory cache paths for project runs.

Existing historical files are not renamed automatically because they may be referenced by current debugging sessions.

## Agent runtime layout

The agent runtime lives under:

```text
aniforce-agent/runtime/
```

Important paths:

```text
aniforce-agent/runtime/agent/tasks.db
aniforce-agent/runtime/agent/sessions.db
aniforce-agent/runtime/agent/sessions.db-wal
aniforce-agent/runtime/agent/sessions.db-shm
aniforce-agent/runtime/agent/traces/YYYYMMDD/task_xxx/run_xxx.jsonl
aniforce-agent/runtime/agent/sandbox/<session_id>/
aniforce-agent/runtime/skills/
aniforce-agent/runtime/sessions/
aniforce-agent/runtime/logs/
```

Meaning:

- `tasks.db`: local agent task ledger. It stores task rows, task status, SSE/runtime events, and user-facing agent session metadata.
- `sessions.db`: OpenAI Agents SDK conversation memory. It stores model-facing history items used when a session continues.
- `sessions.db-wal` and `sessions.db-shm`: SQLite WAL sidecar files. They are normal while the service is running.
- `traces/YYYYMMDD/task_xxx/run_xxx.jsonl`: local structured trace for one task run. It records SDK calls, SDK events, tool calls, agent events, and timing.
- `sandbox/<session_id>/`: per-session workspace root passed to `SandboxAgent`. Files appear here only when the agent actually uses sandbox file/shell capabilities.
- `skills/`: runtime-loaded skills made available to the sandbox agent.
- `sessions/`: reserved runtime session directory from settings. Current code mainly uses `agent/sessions.db` for SDK session memory.
- `logs/`: reserved runtime-local logs. Current project-level service logs are written to root `logs/`.

## Why many sandbox directories are empty

Empty directories do not by themselves mean sandbox is disabled.

The current runtime creates a per-session sandbox directory when creating a `SandboxAgent`:

```text
runtime/agent/sandbox/<session_id>/
```

For normal business questions such as listing projects, the agent uses MCP tools that call the backend API. Those tools do not need to create files in the sandbox, so the session directory stays empty.

A sandbox directory should contain files only when the model uses sandbox capabilities such as shell/file work, or a skill writes artifacts there. Historical traces show sandbox file execution has worked before, for example `block5_test_hello.txt` under `runtime/agent/sandbox/`.

Practical interpretation:

- Empty `sandbox/session_*` after API-only tasks: expected.
- Files under a sandbox session after shell/file tasks: sandbox write path is active.
- No sandbox directories at all after runs: likely `SandboxAgent` was not created or `SANDBOX_DIR` differs.
- Tool calls only named `list_projects`, `create_project`, etc.: backend MCP path, not sandbox file path.

## Quick checks

Inspect recent service logs:

```bash
ls -lh logs/*.log
tail -f logs/$(date +%Y%m%d).dev.agent.uvicorn.log
tail -f logs/$(date +%Y%m%d).dev.backend.uvicorn.log
tail -f logs/$(date +%Y%m%d).dev.frontend.vite.log
```

Inspect runtime DB files:

```bash
ls -lh aniforce-agent/runtime/agent/*.db*
```

Inspect recent traces:

```bash
find aniforce-agent/runtime/agent/traces/$(date +%Y%m%d) -name '*.jsonl' -print | tail
```

Inspect sandbox contents:

```bash
find aniforce-agent/runtime/agent/sandbox -maxdepth 2 -type f -print
```
