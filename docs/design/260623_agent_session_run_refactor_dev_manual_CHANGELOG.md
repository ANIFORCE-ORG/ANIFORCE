# 改造方案文档更新说明

**日期**：2026-06-23  
**版本**：v1.1（务实调整版）

---

## 更新内容

基于深度复盘和技术可行性分析，对原方案进行了 3 处关键调整：

### 1. Block 2：增加 content_json 格式明确定义

**问题**：原方案只说"存前端展示结构"，但没有明确格式。

**更新**：
- 定义了 `content_json` 的 blocks 数组格式
- 明确了 text / thinking / tool_call / error 四种 block 类型
- 增加了 ChatEventAssembler 的实现伪码
- 说明了 thinking 长文本的保存策略（开发保存，生产可裁剪）

**收益**：
- 避免实现时对格式理解不一致
- 前端/后端对接更清晰
- 为 UI 渲染提供明确规范

---

### 2. Block 5：SDK Session Cache 改为"短期保留本地 SQLite"

**问题**：原方案建议实现 `BackendSession(Session)` 让 SDK 通过 HTTP 读写 backend，过于理想化。

**更新**：
- **短期方案**：继续使用 agent-service/runtime/sessions.db（本地 SQLite）
- **原因说明**：SDK Session 高频读写，本地 SQLite 性能最好，避免网络开销
- **中期优化**：定期 compaction，摘要写入 backend SessionState.summary
- **长期方案**：分布式部署用 Redis，而不是 BackendSession HTTP

**收益**：
- 不为"完美分层"牺牲性能
- 降低实现复杂度
- 单机部署保持简单，多实例部署有明确扩展路径

---

### 3. Block 7：HITL 改为"MVP 版本"，不依赖 RunState

**问题**：原方案直接用 SDK RunState pause/resume，但 RunState 序列化很脆弱。

**更新**：
- **MVP 方案**（推荐）：高风险工具触发审批，用户 approve 后"重新 run"，而不是"resume"
- 只保存 `{tool, args, risk_reason}`，不保存完整 RunState JSON
- **完整方案**（后续扩展）：如果 MVP 不够用，再引入 RunState 持久化
- 增加了风险控制说明（agent 版本兼容性检查、24h 过期、反序列化失败降级）

**收益**：
- 降低实现风险（不依赖复杂状态序列化）
- MVP 快速上线，验证真实需求
- 避免 agent 升级后 RunState 无法反序列化的坑

---

## 其他调整

### 4. 目标章节（第 0 节）

增加了"关键决策"总结：
- ✅ Session 元数据和消息历史迁移到 backend
- ✅ Task 降级为 Run execution log
- ✅ Act 暂不实现
- ✅ SDK Session cache 保留本地 SQLite
- ✅ HITL 先做 MVP

### 5. 核心边界章节（第 1 节）

- 1.1 产品 Session：增加 status 索引，明确"此表在 backend"
- 1.3 SDK Session Cache：完全重写，说明为什么保留本地 SQLite
- 1.5 SessionState：补充了 changelog/linked_entities/summary 的格式示例

### 6. 风险处理章节（第 6 节）

- 风险 2：增加了 compaction 伪码示例
- 风险 5：从"RunState 反序列化失败"改为"HITL 审批流程状态管理"，对比 MVP 和完整方案

---

## 关键设计原则

**务实优先**：
- 不为"架构完美"牺牲性能和可靠性
- 不引入过早优化（BackendSession、RunState）
- MVP 先行，根据真实需求迭代

**渐进式改造**：
- Block 1-3 是核心（session/messages/runs 迁移）
- Block 4-6 是清理（删除旧 API、SessionState 完善）
- Block 7-10 是验证（HITL MVP、前端切换、安全测试、E2E）

**可验证性**：
- 每个 Block 有明确产物、验收标准、E2E 脚本
- 清空 agent-service runtime 不丢产品数据

---

## 下一步

1. **复审文档**：确认技术方案和团队达成共识
2. **创建 E2E 测试目录**：`aniforce-agent/tests/e2e_openai_refactor/`
3. **实现 Block 0**：baseline 测试，冻结当前行为
4. **实现 Block 1**：backend agent_sessions 表和 API
5. **渐进式迁移**：按 Block 1-10 顺序推进

---

## 文档版本历史

- **v1.0**（2026-06-23 初稿）：完整改造方案，Block 0-10
- **v1.1**（2026-06-23 务实调整）：
  - Block 2 增加 content_json 格式定义
  - Block 5 改为保留本地 SQLiteSession
  - Block 7 改为 HITL MVP，不依赖 RunState
  - 增加关键决策总结和设计原则说明
