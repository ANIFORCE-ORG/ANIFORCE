# SQLite 多 Worker 生产化改造手册

更新时间：2026-07-10

## 1. 文档目的

本手册指导 ANIFORCE 在 PostgreSQL 尚未就绪时，先使用 SQLite 完成可迁移的多 worker 架构改造，同时整理 Frontend、Backend、Agent Service 的职责和历史残留。

本手册只约束后续生产代码，不依赖 `notebooks/`。

## 2. 当前代码基线

- 工作分支：`docs/sqlite-multiworker-refactor-260710`
- 最新远程 master：`origin/master@807ee1c`
- 合并提交：`e09f659`
- 当前分支同时包含 master 的 Meta MAPI/广告单元改动和现有 Agent/Workspace 改动。
- master 已把 cloud Backend 临时调整为 1 worker。多 worker 基础设施完成前保持该配置。
- `backend/data/sqlite/animagus.db` 的本地修改不是本次改造资产，不得提交或覆盖。

## 3. 部署边界

SQLite 阶段支持：

```text
单台主机
  Backend API worker x N
  Backend run worker x N
  Agent Runtime worker x N
  所有同类 worker 访问同一个本机 SQLite 文件
```

SQLite 阶段不支持：

- 多台主机共享 SQLite；
- 网络文件系统上的 SQLite；
- 高吞吐并发写入；
- 无共享磁盘的 Agent Runtime 多实例。

代码、状态机和 repository 接口必须按多实例设计。SQLite 只是当前基础设施实现，未来切 PostgreSQL 时不得改产品 API 和领域状态机。

## 4. 必读顺序

1. [01-architecture.md](01-architecture.md)：三端职责、目录和多 worker 运行模型。
2. [02-sqlite-and-schema.md](02-sqlite-and-schema.md)：SQLite 配置、表和迁移规范。
3. [03-state-and-recovery.md](03-state-and-recovery.md)：Run、审批、事件、SSE 和恢复协议。
4. [04-migration-and-cleanup.md](04-migration-and-cleanup.md)：分阶段开发、文件迁移和残留清理。
5. [05-verification.md](05-verification.md)：上线门槛和故障测试。

原始审计报告保留在同目录供本地追溯；实施与评审以这组精简手册为准。

## 5. 不可违反的原则

1. Backend 是产品 Session、Run、Message、Approval、Artifact 和关键事件的唯一事实源。
2. Agent Service 只负责 SDK 执行、RunState 和 runtime checkpoint。
3. Frontend 只拥有临时交互状态，刷新后必须能从 Backend snapshot 重建。
4. 正确性不能依赖进程内 dict、`asyncio.Lock`、活动任务句柄或 SSE 连接。
5. 一个 run 只能提交一个终态。
6. 所有 claim、状态迁移和审批恢复使用数据库 CAS。
7. 所有写工具都必须幂等，并记录业务副作用。
8. 所有表结构变化只通过 migration；禁止请求路径 `CREATE/ALTER TABLE`。
9. 网络调用不得包含在 SQLite 写事务中。
10. 先迁移主链，再删除旧代码；不做无验收标准的全仓搬家。

## 6. 执行顺序

```text
Phase 0  稳定当前单 worker 和状态终态
Phase 1  建持久事实表、CAS、lease、snapshot
Phase 2  拆出 DB run worker，验证 Backend 多 worker
Phase 3  改造 Agent Runtime checkpoint/session，验证 Agent 多 worker
Phase 4  Frontend snapshot 恢复和模块拆分
Phase 5  删除旧协议、旧 service、旧测试和动态改表
Phase 6  PostgreSQL repository adapter
```

任何阶段都必须保持应用可运行、migration 可回滚、旧数据可对账。Phase 2 验收前不得把 Backend worker 调回 2；Phase 3 验收前不得启动多个 Agent worker。
