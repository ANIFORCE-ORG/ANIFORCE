## Block 3: 业务事件系统基础

**交付物**：新入口 `/api/agent/runs` + 业务事件流 + 运行元数据 + 数据库落盘  
**状态**：✅ 通过（2026-06-17）

### 执行
```bash
.venv/bin/python tests/e2e/block3_business_events.py
```

### 验证点
- [x] 新入口 `POST /api/agent/runs` 返回 200
- [x] 收到 TaskCreated 事件
- [x] 收到 TaskProgressUpdated 事件
- [x] 收到 TaskOutputDelta 事件（流式文本增量）
- [x] 收到 TaskOutputProduced 事件
- [x] 收到 TaskCompleted 事件
- [x] 运行元数据包含 model / tools / skills
- [x] telemetry 包含 duration / cost / tokens
- [x] tasks 表正确写入
- [x] events 表正确写入
- [x] task_outputs 表正确写入（type=text）

### 已实现

**1. 新入口和业务事件适配器**
- `app/api/runs.py`：`POST /api/agent/runs` 入口
- `app/services/business_event_adapter.py`：SDK 消息流 → 业务事件流
- 5 个通用事件：TaskCreated / TaskProgressUpdated / TaskOutputDelta / TaskOutputProduced / TaskCompleted

**2. 通用数据模型**
- `app/models/output.py`：TaskOutput / OutputType / OutputStatus
- `app/models/business_event.py`：BusinessEvent
- `app/repositories/output_repo.py`：OutputRepository
- `app/config/database.py`：新增 task_outputs / evidence_snapshots 表

**3. 运行元数据注入**  
每个事件都包含 `runtime` 和 `telemetry`：
- runtime.model: claude-sonnet-4-6
- runtime.tools: 28个工具
- runtime.skills: 14个技能
- telemetry: inputTokens / outputTokens / durationMs / costUsd / charPerSecond

**4. 流式体验保留**
- `TaskOutputDelta` 事件推送文本增量（persist=False，不写 events 表）
- 最终完整文本落成 `TaskOutput(type=text, status=verified)`

**5. 旧代码清理**
- 删除 `app/api/copilotkit.py`
- 删除 `app/services/copilotkit_adapter.py`
- 更新 `app/main.py` 路由注册
- 更新 `tests/e2e/block1_basic_connectivity.py` 和 `block2_claude_sdk.py`

### 测试结果（2026-06-17）

通过: 15/15

实测事件序列：
- TaskCreated → taskId / sessionId / goal / userId
- TaskProgressUpdated (4次) → 初始化 / 运行环境 / 生成回复 / 完成
- TaskOutputDelta → 流式文本："收到"
- TaskOutputProduced → output_id / type=text / content
- TaskCompleted → duration=6204ms / cost=$0.080232

数据库落盘：
- tasks 表：task_id / status=completed / session_id
- events 表：7条事件
- task_outputs 表：output_id / type=text / content={"text":"收到"}

---
