## Block 4: 通用任务模型 + DB Schema

**交付物**：任务 CRUD API + Output 验证接口 + 数据库表验证  
**状态**：✅ 通过（2026-06-17）

### 执行
```bash
.venv/bin/python tests/e2e/block4_task_model.py
```

### 验证点
- [x] 创建任务并产生 Output
- [x] 查询任务详情（GET /tasks/{task_id}）
- [x] 查询任务 Outputs（GET /tasks/{task_id}/outputs）
- [x] 更新 Output 状态（PATCH /tasks/outputs/{output_id}）
- [x] 列出用户任务（GET /tasks）
- [x] 查询任务事件流（GET /tasks/{task_id}/events）

### 已实现

**1. 任务 CRUD API**
- `POST /api/agent/tasks`：创建任务
- `GET /api/agent/tasks`：列出用户任务
- `GET /api/agent/tasks/{task_id}`：查询任务详情
- `GET /api/agent/tasks/{task_id}/outputs`：查询任务产物
- `GET /api/agent/tasks/{task_id}/events`：查询任务事件流
- `DELETE /api/agent/tasks/{task_id}`：取消任务

**2. Output 管理 API**
- `PATCH /api/agent/tasks/outputs/{output_id}`：验证/拒绝产物
- 支持状态更新：pending_review → verified / rejected

**3. 数据库表结构验证**
- `tasks` 表：task_id / user_id / task_type / status / title / session_id / input_data / result / error / created_at / updated_at
- `task_outputs` 表：output_id / task_id / type / category / content / confidence / importance / actionable / requires_review / status / verified_by / verified_at / supersedes / superseded_by / created_at
- `events` 表：event_id / task_id / event_type / payload / sequence / created_at
- `evidence_snapshots` 表（预留）

**4. 数据流完整性**
- 任务创建 → 产生 Output → Output 落库
- Output 状态管理：verified / pending_review / rejected
- 事件流持久化：所有 TaskProgressUpdated / TaskOutputProduced 等事件写入 events 表

### 测试结果（2026-06-17）

通过: 8/8

**实测数据**：
- 创建任务并产生 1 个 text 类型 Output
- 查询任务详情：status=completed
- 查询 Outputs：type=text, status=verified
- 更新 Output 状态：verified（成功）
- 列出任务：返回 6 个任务
- 查询事件流：返回 9 个事件

**修复记录**：
- 修复 `BusinessEventAdapter` 数据库连接问题：改为由调用方传入 `db` 连接，避免生成器内 `async with` 导致的异步上下文错误
- 修复 `PATCH /outputs/{output_id}` 参数解析：从 query 改为 body

---
