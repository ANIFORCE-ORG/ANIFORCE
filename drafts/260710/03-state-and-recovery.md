# 03 状态协议与恢复

## 1. Run 状态机

```text
queued -> running -> completed
                  -> requires_action -> resuming -> completed
                  -> error
                  -> cancel_requested -> cancelled
                  -> interrupted
requires_action -> expired
```

规则：

- 一个 run 只能有一个 terminal event。
- terminal：`completed/error/cancelled/expired`。
- `requires_action` 不是终态，必须有 Approval 事实。
- 状态迁移由 Backend `RunService` 单点执行并使用 CAS。
- runtime event 只能提出 transition command，不能直接更新多个状态源。
- Session activity 由 latest run 投影，不单独维护一套可漂移状态机。

## 2. 唯一终态提交

终态事务同时完成：

1. CAS 更新 run；
2. 完成最终 message 或错误 message；
3. 写 terminal `agent_run_event`；
4. 写 `terminal_event_id`；
5. 清理 lease。

事务提交后才能发布 SSE。若 CAS 失败，不得广播第二个终态，并记录一致性告警。

## 3. 关键事件

持久事件：

```text
run.created / run.started / run.requires_action
run.completed / run.error / run.cancelled / run.expired
message.created / message.completed / message.error
Tool.started / tool.completed / tool.error
approval.created / approval.resolved / approval.expired
artifact.created / artifact.updated
side_effect.recorded
```

命名落地时统一小写 `tool.*`。token/reasoning delta、heartbeat 是短期实时事件，可丢失；关键事件不可静默丢失。

## 4. SSE 与 snapshot

```text
GET /sessions/{id}/snapshot
GET /runs/{id}/events?after_sequence=N
```

Snapshot 至少包含：

```json
{
  "session": {},
  "messages": [],
  "latest_run": {},
  "pending_approval": null,
  "artifacts": [],
  "last_persisted_sequence": 0
}
```

SQLite 阶段 SSE worker 每 100-300ms 查询新增关键事件。若实时 token buffer 已丢失，返回 `snapshot_required`，Frontend 重拉 snapshot，不把 token replay 当恢复正确性的前提。

## 5. HITL 审批

审批流程：

```text
Runtime interruption
  -> Backend 创建 Approval + run requires_action
User resolve
  -> Backend 校验 owner、权限、expires_at、参数 schema
  -> CAS pending -> resuming
  -> 读取当前业务实体版本和 Workspace context
  -> Agent Service CAS claim checkpoint
  -> 使用最新 context 恢复 RunState
  -> 工具幂等执行
  -> Backend 提交 ToolCall、side effect 和 run 终态
```

审批必须绑定 `approval_id + checkpoint_ref + tool_call_id + tool_name`。不得只按 `run_id` 查询最近一条 approved arguments。

恢复前必须检查：

- checkpoint 未过期；
- SDK/agent/context schema 版本兼容；
- 当前用户仍有权限；
- 目标实体 `updated_at/version` 未变化；
- 编辑参数通过工具 schema；
- approval 未被其他 worker claim。

## 6. Worker 崩溃恢复

Run worker 定期续租。Reconcile worker扫描 lease 过期记录：

- 尚未调用 runtime：回到 queued；
- 已调用 runtime但无 checkpoint：标记 interrupted，并给 retryable error；
- requires_action 且 checkpoint 有效：保持等待审批；
- checkpoint 过期：approval/run 收敛为 expired；
- 业务副作用可能完成但结果未知：进入 reconciliation，禁止盲目重试写工具。

## 7. 取消

取消分两步：

```text
running -> cancel_requested -> cancelled
```

Backend 先持久化请求；runtime worker和工具边界检查取消标记。Agent Service 的本地 cancel handle 只是加速。只有执行确认停止或租约回收完成后，才能提交 `cancelled`。

## 8. 幂等与副作用

所有写工具使用稳定 logical operation id。Backend endpoint 计算 request hash：

- 首次请求：执行并保存结果；
- 相同 key + 相同 hash：返回已有结果；
- 相同 key + 不同 hash：409 conflict；
- in_progress：返回处理中，不并发执行。

create/update/delete/link/unlink/status 全部覆盖。工具成功但模型回复失败时，Frontend 必须展示已核对的副作用事实，不能提示用户直接重复操作。

## 9. 错误协议

统一结构：

```json
{
  "code": "UPSTREAM_TIMEOUT",
  "category": "upstream",
  "retryable": true,
  "user_message": "模型服务响应超时，请重试。",
  "correlation_id": "..."
}
```

堆栈、URL、SQL、token 和原始 exception 只进入脱敏日志。用户可见错误写入 message/run 事实，刷新后仍可见。
