# 04 迁移与代码清理计划

## 1. 迁移策略

采用纵向替换：建立新能力 -> 迁移一个完整流程 -> 验收 -> 删除旧路径。不要先全仓重命名或搬目录。

## 2. Phase 0：状态止血

目标：当前单 worker行为可信。

- 修复 `runtime.error` 后仍 complete。
- `requires_action` 正确投影 Session activity。
- checkpoint 增加 expires_at 校验和 CAS。
- runtime 禁止 body user_id 覆盖认证身份。
- history 校验 session owner。
- 内部错误改为结构化脱敏错误。
- 提供一次性 SessionState/run reconcile。

验收后仍保持 Backend/Agent 各 1 worker。

## 3. Phase 1：持久事实层

- 增加 run_events、messages、tool_calls、approvals、artifacts、leases。
- RunService 成为唯一状态迁移入口。
- POST run 只写 queued 事实，不创建进程内后台任务。
- 建 snapshot API 和 DB sequence。
- 所有 schema 变化迁入 Alembic/runtime migrations。

## 4. Phase 2：Backend 多 worker

- 新建独立 run worker和 reconcile worker。
- 用 DB claim/lease 替代 `SessionLockManager`。
- SSE 从事件表读取，event bus 降为可选优化。
- kill worker、重复 claim、断线重连测试通过。
- 通过后才将 cloud Backend 从 1 调到 2 worker。

## 5. Phase 3：Agent Service 多 worker

- runtime DB 启用 WAL 和 migration。
- checkpoint claim、过期、版本校验完成。
- 同 product session 由 Backend lease 保证单活。
- resume 使用 Backend 当前 context，不使用 checkpoint 旧 context。
- `_ACTIVE_RUNTIME_RUNS` 不再承担正确性。
- 通过后才启用 Agent worker > 1。

## 6. Phase 4：Frontend 恢复与拆分

从 `useHomeAgentSession.ts` 提取：

```text
runConnectionManager
runEventReducer
messageAssembler
TimelineReducer
approvalController
workspaceArtifactStore
```

Reducer 使用纯函数并单测。刷新从 snapshot 恢复 active run、sequence、approval、message 和 artifact。localStorage 只保存非权威 UI 偏好。

## 7. Phase 5：删除残留

确认无路由、页面、动态注册和测试引用后删除：

- 旧 `/agent/chat/...` 和 `/hitl` 客户端；
- 旧 AG-UI/Plan-Execute types 与 service；
- 引用 `app.agent_platform` 的旧测试；
- `agentService.ts` 中已失效 API；
- 进程内 event bus/lock 的正确性路径；
- repository/checkpoint 中动态 `ALTER TABLE`；
- 重复 Workspace tool result parser；
- 无调用方的旧 model/repository/service。

删除必须单独提交，并附 `rg`、route list、构建和测试证据。

## 8. 文件迁移规则

- 新领域代码进入 `backend/app/agent/`，旧文件通过 adapter 调用新 service。
- 不允许新代码继续直接 import `Sqlite*Repository`；由 dependency/provider 注入 protocol。
- 每迁移一个 endpoint，旧 endpoint 保持兼容或明确版本化。
- 不在架构提交中顺带格式化 Meta MAPI、广告单元等共建业务文件。
- master 后续有更新时先 fetch，再合并；共同修改文件做语义合并，不用整文件 ours/theirs。
- `.db` 二进制冲突不做 Git 合并，依据 migration 和数据回填解决。

## 9. 提交粒度

建议提交序列：

```text
docs: define sqlite multi-worker contracts
db: add agent control migrations
test: add run state and approval CAS coverage
refactor: introduce agent run application service
feat: persist critical run events
feat: add run worker lease and reconciliation
feat: add session snapshot recovery
refactor: migrate frontend run reducers
cleanup: remove legacy agent protocol
```

每个提交必须可运行；数据库 migration 与使用新字段的代码不可无序发布。

## 10. PostgreSQL 切换

SQLite 阶段结束后新增 PostgreSQL infrastructure adapter：

- 不改 domain states；
- 不改 API contract；
- 不改 event schema；
- lease 改用 row lock/`SKIP LOCKED`；
- polling 可改 LISTEN/NOTIFY 或 Redis；
- 先双环境 contract test，再迁移数据。
