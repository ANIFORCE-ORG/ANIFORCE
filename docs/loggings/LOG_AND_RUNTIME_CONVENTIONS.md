# Log and Agent Runtime Conventions

## Canonical logging document

Production ownership, environment variables, collector requirements, security rules, and acceptance checks are defined in:

```text
docs/loggings/PRODUCTION_LOGGING.md
```

## Local log files

`./run_server.sh --mode local` writes role-specific JSON Lines files:

```text
logs/YYYYMMDD.local.backend-api.jsonl
logs/YYYYMMDD.local.agent-api.jsonl
logs/YYYYMMDD.local.agent-run-worker-1.jsonl
logs/YYYYMMDD.local.agent-reconcile-worker.jsonl
```

Bootstrap and frontend output use:

```text
logs/YYYYMMDD.local.backend.bootstrap.log
logs/YYYYMMDD.local.agent.bootstrap.log
logs/YYYYMMDD.local.frontend.vite.log
```

Rules:

- Local application JSONL files rotate at 100 MB, retain 14 days, and compress old files.
- Bootstrap logs are only for process startup failures.
- PID files are runtime control files, not application logs.
- Existing historical files are not renamed or deleted automatically.
- Cloud mode emits JSON to stdout and does not use project log files as centralized storage.

## Agent runtime layout

The Agent runtime lives under:

```text
aniforce-agent/runtime/
```

Important paths:

```text
aniforce-agent/runtime/agent/tasks.db
aniforce-agent/runtime/agent/sessions.db
aniforce-agent/runtime/agent/sessions.db-wal
aniforce-agent/runtime/agent/sessions.db-shm
aniforce-agent/runtime/agent/sandbox/<session_id>/
aniforce-agent/runtime/skills/
aniforce-agent/runtime/sessions/
```

Meaning:

- `tasks.db`: local task and runtime event storage.
- `sessions.db`: OpenAI Agents SDK model-facing conversation memory.
- `sessions.db-wal` and `sessions.db-shm`: normal SQLite WAL sidecars while running.
- `sandbox/<session_id>/`: per-session workspace used for file or shell capabilities.
- `skills/`: runtime-loaded skills.
- `sessions/`: reserved runtime directory configured by settings.

The former `runtime/agent/traces/...jsonl` LocalTracer path is retired. Agent LLM and tool traces are exported through OpenInference/OpenTelemetry to Phoenix when tracing is enabled.

## Sandbox interpretation

An empty sandbox directory is expected for API-only business tasks. MCP tools such as `list_projects` and `create_project` call Backend APIs and do not create local files.

- Empty sandbox after API-only tasks: expected.
- Files after shell/file tasks: sandbox write path is active.
- No sandbox directory after any run: inspect `SANDBOX_DIR` and Agent construction.

## Quick checks

Inspect local application logs:

```bash
ls -lh logs/*.jsonl
jq -c 'select(.record.extra.event == "agent.run.failed")' logs/*.jsonl
jq -c 'select(.record.extra.run_id == "run_xxx")' logs/*.jsonl
```

Inspect runtime databases and sandbox files:

```bash
ls -lh aniforce-agent/runtime/agent/*.db*
find aniforce-agent/runtime/agent/sandbox -maxdepth 2 -type f -print
```

Inspect Agent traces in the configured Phoenix project and correlate them by `metadata.run_id`.
