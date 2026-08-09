# Production Logging

## Ownership

Application logging is configured in:

- Backend: `backend/app/config/logging.py`
- Agent Service: `aniforce-agent/app/core/logging.py`
- Local/cloud process wiring: `run_server.sh`
- Agent traces: `aniforce-agent/app/core/sdk_tracing.py` and Phoenix
- Approval and write-operation audit: Backend database tables

Logs, traces, metrics, and audit records have separate responsibilities:

- Logs: service events, failures, and operational context.
- Traces: one Agent execution across LLM and tool spans.
- Metrics: aggregate health, latency, errors, queue depth, and usage.
- Audit: durable records of approvals, edited arguments, and writes.

Do not duplicate complete prompts, model responses, tool arguments, or tool results in application logs. Phoenix owns that diagnostic view when sensitive tracing is explicitly enabled.

## Output modes

### Local development

`./run_server.sh --mode local` writes role-specific JSON Lines files under `logs/local/`:

```text
logs/local/YYYYMMDD.local.backend-api.jsonl
logs/local/YYYYMMDD.local.agent-api.jsonl
logs/local/YYYYMMDD.local.agent-run-worker-1.jsonl
logs/local/YYYYMMDD.local.agent-reconcile-worker.jsonl
```

Application files rotate at 100 MB, retain 14 days, and compress rotated files. Bootstrap and frontend files are shell output and are only intended for local startup diagnosis.

### Production

`./run_server.sh --mode cloud` writes application logs under `logs/cloud/` by default. Each process gets its own JSON Lines file via `LOG_FILE`, and uvicorn bootstrap output also lands in the same directory.

Recommended flow:

```text
Application JSONL files
  -> logs/cloud/
  -> grep / jq / company log shipper
  -> Loki / Elasticsearch / company logging platform
```

The application writes process-scoped files in a dedicated directory so local inspection is straightforward.

## Environment contract

| Variable | Production value | Meaning |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Minimum application level |
| `LOG_FORMAT` | `json` | Machine-readable Loguru JSON |
| `LOG_OUTPUT` | `file` | File sink only |
| `LOG_FILE` | path under `logs/cloud/` | Application-owned production file |
| `LOG_SERVICE` | `backend` or `agent-service` | Stable service identity |
| `LOG_ROLE` | `api`, `agent-run-worker`, or `agent-reconcile-worker` | Process role |
| `APP_ENV` | `cloud` | Deployment environment |

The structured record includes stable correlation fields:

```text
service, role, environment, event, request_id, trace_id, span_id,
run_id, session_id, worker_id
```

Absent fields remain `null` so collectors receive a stable schema.

## Correlation

- Accept an upstream `X-Request-ID` up to 128 characters or generate `req_<hex>`.
- Return `X-Request-ID` in the HTTP response.
- Bind `run_id` and `session_id` for Agent execution lifecycle events.
- Use `run_id` as the stable cross-system key between application logs and Phoenix trace metadata.
- `trace_id` and `span_id` are populated automatically only when a log is emitted inside an active OpenTelemetry span; they may be `null` for lifecycle logs outside SDK spans.
- Do not use user prompt text as an index or correlation key.

Useful local queries:

```bash
jq -c 'select(.record.extra.event == "agent.run.failed")' logs/cloud/*.jsonl
jq -c 'select(.record.extra.run_id == "run_xxx")' logs/cloud/*.jsonl
jq -c 'select(.record.extra.request_id == "req_xxx")' logs/cloud/*.jsonl
```

## Security

Production defaults:

- `diagnose=false` and `backtrace=false` in Loguru sinks.
- `AGENT_TRACE_INCLUDE_SENSITIVE_DATA=false`.
- Never log authorization headers, cookies, JWTs, API keys, passwords, provider request bodies, or raw database rows.
- Keep Phoenix and log-platform access behind authentication and least-privilege authorization.
- Treat local JSONL files and Phoenix data directories as sensitive developer artifacts.

Audit data must remain in the Backend database. It must not depend on sampled or expired logs and traces.

## Metrics

Backend and Agent Service expose Prometheus text format at:

```text
GET /metrics
```

Initial production metrics include:

```text
aniforce_http_requests_total
aniforce_http_request_duration_seconds
aniforce_agent_runs_total
aniforce_agent_run_duration_seconds
aniforce_agent_tokens_total
aniforce_agent_worker_executions_total
aniforce_agent_worker_execution_duration_seconds
aniforce_agent_worker_active_runs
aniforce_agent_worker_errors_total
aniforce_agent_reconcile_runs_total
aniforce_agent_reconcile_actions_total
aniforce_agent_trace_export_errors_total
```

Metrics labels are intentionally low cardinality. Request, Run, Session, User, Worker instance, Prompt, and arbitrary URL values must never become labels. Use logs and Phoenix for individual execution diagnosis.

In production, restrict `/metrics` at the ingress or service-network layer so only the monitoring system can access it. Configure Prometheus or the company monitoring platform to scrape Backend and Agent Service independently.

Minimum alerts:

- Agent Run failure ratio exceeds the agreed SLO window.
- HTTP 5xx ratio or P95 latency increases.
- Worker iteration or lease-lost errors increase.
- Active runs remain nonzero without terminal throughput.
- Reconcile conflicts increase.
- Trace exporter errors increase.

## Collector requirements

A production collector should parse each stdout line as JSON and index at least:

```text
record.time
record.level.name
record.message
record.extra.service
record.extra.role
record.extra.environment
record.extra.event
record.extra.request_id
record.extra.run_id
record.extra.session_id
record.extra.worker_id
```

Recommended retention:

- Application logs: 14-30 days hot, according to incident requirements.
- Security/audit records: according to business compliance policy, in the database.
- Agent traces: shorter retention than audit data, with sensitive payloads disabled by default.

## Production acceptance

Before deployment, verify:

1. Each service emits valid JSON Lines files under `logs/cloud/` with `LOG_FORMAT=json`.
2. `LOG_OUTPUT=file` and `LOG_FILE` is set for each application process.
3. API responses contain `X-Request-ID`.
4. Agent application logs contain `run_id`, `session_id`, duration, and token usage.
5. SQL polling and raw SDK stream events do not appear at INFO.
6. Collector search works by `request_id` and `run_id`.
7. Phoenix failure does not block Agent execution.
8. Alerts exist for Run failure rate, Provider errors, queue depth, stale workers, and hanging Runs.
