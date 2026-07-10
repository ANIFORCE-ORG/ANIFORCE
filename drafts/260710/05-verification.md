# 05 验证与上线门槛

## 1. 最小测试分层

```text
Unit
  状态迁移、event reducer、error mapper、request hash

Repository
  SQLite CAS、lease、sequence、unique terminal、migration

Integration
  API -> DB -> run worker -> Agent stub -> snapshot/SSE

Fault injection
  kill Backend worker、kill Agent worker、断网、并发审批

Frontend
  snapshot hydration、event dedupe、approval refresh、artifact restore
```

pytest discovery 必须限制到项目测试目录并排除 `.venv`、`venv`、`uv_cache`、`npm_cache`、`node_modules`、`drafts`。

## 2. Phase 0 验收

- runtime.error 后没有 completed event。
- 每个 run 只有一个终态。
- requires_action 时 run/session/approval 一致。
- 过期 checkpoint 返回 409/410，不执行工具。
- 两个并发 approve 仅一个成功。
- 跨用户 history 请求被拒绝。
- 内部异常不出现在 SSE 用户消息中。

## 3. Backend 多 worker 验收

- POST run 和 GET events 落到不同 API worker仍正常。
- 两个 run worker竞争同一 run，只有一个 claim 成功。
- 同 session 两个 run不能同时 active。
- worker在模型流中被 kill，lease 到期后被 reconcile。
- SSE 断开重连不重复关键事件。
- 实时 buffer 丢失后 snapshot 可恢复完整 UI。
- queue/消费者变慢时 terminal 事实不丢失。
- SQLite 锁冲突有界重试，无长事务。

## 4. Agent 多 worker 验收

- 两个 Agent worker竞争 checkpoint，只有一个恢复。
- 审批等待期间实体变化会触发 precondition conflict。
- resume 使用最新 Workspace context。
- Agent worker崩溃不会让 Backend 永久 running。
- SDK/agent schema 版本不兼容时拒绝恢复。
- cancel 不依赖请求命中原 worker。

## 5. 写操作验收

对 create/update/delete/link/unlink/status 逐一测试：

- 相同 key + 相同 payload 只产生一次效果；
- 相同 key + 不同 payload 返回冲突；
- 网络超时重试不重复创建；
- 业务成功但模型失败，side effect 仍可查询；
- ToolCall status 与业务 DB 结果一致。

## 6. Frontend 验收

- running 时刷新，消息、run 和 stream 可恢复。
- requires_action 时刷新，审批参数和 artifact 可恢复。
- completed/error 时刷新，最终消息和错误仍存在。
- 相同 event sequence 不重复渲染。
- Workspace 只依赖 artifact，不依赖历史 tool event 配对。
- 旧 AG-UI 页面/调用删除后构建无引用错误。

## 7. 数据库验收

- 空库可通过 migration 创建完整 schema。
- 现有库可升级且历史 run可查询。
- downgrade 或回滚方案经过演练。
- 所有外键、唯一键、check constraint 和索引存在。
- 请求路径无 `CREATE TABLE`/`ALTER TABLE`。
- Git 不再以运行 `.db` 文件发布 schema。

## 8. 多 worker 开关

只有以下命令对应测试全部通过后，才允许修改部署 worker 数：

```text
Backend workers > 1：Phase 0 + Backend 多 worker + DB migration
Agent workers > 1：以上全部 + Agent 多 worker + HITL fault injection
```

SQLite 模式始终限定单主机。任何多主机部署必须先切共享 PostgreSQL；Redis只能优化通知，不能替代事实数据库。

## 9. 每阶段交付清单

- migration 与回填脚本；
- 状态/API contract；
- 自动化测试和实际命令结果；
- reconcile/回滚方案；
- 删除清单和引用检查；
- 监控指标：queued age、lease expiry、stale running、approval expiry、terminal conflict、SQLite lock retry；
- 更新本手册中已完成阶段和遗留风险。
