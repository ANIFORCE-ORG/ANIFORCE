# Agent 开发验证指南

> 版本：v1.0  
> 更新：2026-06-12

---

## 🚀 启动开发环境

### 方式 1：控制台输出（推荐开发时使用）

```bash
cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE

# 启动，后端日志直接输出到控制台
./scripts/start-dev.sh

# 你会看到：
# - Backend 日志实时输出
# - 包含 [RUNTIME] 和 [TRACE] 标记的详细日志
# - Agent 执行的每一步
```

### 方式 2：日志写入文件

```bash
# 如果你觉得控制台日志太多，可以写入文件
./scripts/start-dev.sh --log-to-file

# 查看日志
tail -f logs/backend-dev.log
tail -f logs/frontend-dev.log
```

---

## 📋 验证清单

### 1. 启动验证

访问以下地址确认服务启动成功：

```bash
# 后端健康检查
curl http://127.0.0.1:18003/health

# 前端页面
open http://127.0.0.1:13003

# API 文档
open http://127.0.0.1:18003/docs
```

### 2. 前端对话验证

1. 打开前端：http://127.0.0.1:13003
2. 登录（Demo 模式下任意用户名密码）
3. 找到 Agent 对话入口
4. 发送消息："你好，请介绍一下自己"

**观察后端控制台日志：**

```text
2026-06-12 17:30:00.123 | INFO     | [RUNTIME] Task started: conversation
2026-06-12 17:30:00.124 | DEBUG    | [RUNTIME] Status updated: RUNNING
2026-06-12 17:30:00.125 | INFO     | [RUNTIME] Event[0]: runtime.started
2026-06-12 17:30:00.126 | DEBUG    | [RUNTIME] Agent created: ANIFORCE Assistant
2026-06-12 17:30:00.127 | INFO     | [RUNTIME] Created new session: session_abc123
2026-06-12 17:30:00.128 | INFO     | [RUNTIME] Executing Agent...
2026-06-12 17:30:00.129 | DEBUG    | [TRACE] SDK call: run_streamed | agent=ANIFORCE Assistant
2026-06-12 17:30:01.234 | DEBUG    | [TRACE] SDK event: raw_response_event
2026-06-12 17:30:01.235 | DEBUG    | [TRACE] Agent event[1]: message.updated
2026-06-12 17:30:01.236 | DEBUG    | [RUNTIME] Event[1]: message.updated | delta_len=3
2026-06-12 17:30:01.345 | DEBUG    | [TRACE] Agent event[2]: message.updated
2026-06-12 17:30:01.346 | DEBUG    | [RUNTIME] Event[2]: message.updated | delta_len=5
...
2026-06-12 17:30:05.678 | INFO     | [TRACE] LLM response: claude-opus-4-6 | response_len=234
2026-06-12 17:30:05.679 | DEBUG    | [TRACE] Agent event[20]: message.completed
2026-06-12 17:30:05.680 | INFO     | [RUNTIME] Status updated: COMPLETED
2026-06-12 17:30:05.681 | INFO     | [RUNTIME] Event[21]: runtime.completed
2026-06-12 17:30:05.682 | INFO     | [RUNTIME] Task completed successfully
2026-06-12 17:30:05.683 | INFO     | [TRACE] Task completed in 5.56s
```

**预期结果：**
- 前端显示流式打字效果
- 后端日志显示完整执行流程
- 没有报错

### 3. 多轮对话验证

继续在同一个对话中发送：

```text
用户: "我叫张三，请记住我的名字"
助手: "好的，张三，我记住了..."

用户: "我叫什么名字？"
助手: "您叫张三..."
```

**观察后端日志：**

```text
2026-06-12 17:31:00.123 | INFO     | [RUNTIME] Reusing session: session_abc123
```

**预期结果：**
- 助手能记住之前的对话内容
- 日志显示复用了 session

### 4. Tracing 文件验证

```bash
# 查看 tracing 文件
ls -lh runtime/agent/traces/20260612/

# 示例输出：
# -rw-r--r-- 1 user user 12K Jun 12 17:30 task_abc123_1718185800123.jsonl

# 查看内容
cat runtime/agent/traces/20260612/task_abc123_*.jsonl | jq .

# 你会看到结构化的 JSON 日志，包含：
# - trace.start
# - sdk.call
# - sdk.event
# - agent.event
# - llm.response
# - trace.end
```

---

## 🔍 日志解读

### 日志前缀说明

| 前缀 | 含义 | 示例 |
|------|------|------|
| `[RUNTIME]` | Runtime 执行流程 | `[RUNTIME] Task started: conversation` |
| `[TRACE]` | Tracing 系统日志 | `[TRACE] SDK call: run_streamed` |
| 无前缀 | 其他模块日志 | `Task created: conversation` |

### 关键事件

1. **Task 创建**
   ```
   INFO | Task created: conversation
   ```

2. **Runtime 启动**
   ```
   INFO | [RUNTIME] Task started: conversation
   INFO | [RUNTIME] Event[0]: runtime.started
   ```

3. **Session 管理**
   ```
   INFO | [RUNTIME] Created new session: session_xxx
   # 或
   INFO | [RUNTIME] Reusing session: session_xxx
   ```

4. **SDK 调用**
   ```
   DEBUG | [TRACE] SDK call: run_streamed | agent=...
   ```

5. **事件流**
   ```
   DEBUG | [RUNTIME] Event[N]: message.updated | delta_len=X
   ```

6. **完成**
   ```
   INFO | [RUNTIME] Status updated: COMPLETED
   INFO | [RUNTIME] Event[N]: runtime.completed
   INFO | [RUNTIME] Task completed successfully
   INFO | [TRACE] Task completed in X.XXs
   ```

---

## ⚠️ 常见问题

### 1. 后端启动失败

**检查端口占用：**
```bash
ss -ltnp | grep 18003
```

**手动清理：**
```bash
./scripts/start-dev.sh --clear-ports
```

### 2. 前端无法连接后端

**检查环境变量：**
```bash
cat backend/.env | grep BACKEND_BASE_URL
# 应该是: http://127.0.0.1:18003
```

**检查 CORS：**
```bash
curl -H "Origin: http://127.0.0.1:13003" \
  http://127.0.0.1:18003/health -v
```

### 3. Agent 不响应

**检查 OpenAI 配置：**
```bash
cat backend/.env | grep OPENAI
```

**查看后端日志：**
```bash
# 如果写入了文件
tail -f logs/backend-dev.log | grep ERROR

# 如果在控制台
# 直接看控制台输出
```

### 4. Tracing 文件未生成

**检查配置：**
```bash
cat backend/.env | grep AGENT_TRACING_ENABLED
# 应该是: AGENT_TRACING_ENABLED=true
```

**检查目录权限：**
```bash
ls -ld runtime/agent/traces/
# 应该有写权限
```

---

## 📊 性能观察

### 查看事件数量

```bash
# 统计某个 task 的事件数
cat runtime/agent/traces/20260612/task_*.jsonl | grep '"event": "agent.event"' | wc -l
```

### 查看响应时间

```bash
# 提取 duration
cat runtime/agent/traces/20260612/task_*.jsonl | grep 'trace.end' | jq '.duration_ms'
```

### 查看 LLM Token 使用

```bash
# 提取 usage（如果 SDK 返回了）
cat runtime/agent/traces/20260612/task_*.jsonl | grep 'llm.response' | jq '.usage'
```

---

## 🎯 下一步

**前后端已串联，可观察日志后：**

1. **实现第一个业务 Tool**
   - 定义 Tool function
   - 集成到 Agent
   - 观察工具调用日志

2. **完善前端体验**
   - 工具调用状态显示
   - 错误提示优化

3. **性能优化**
   - 观察响应时间
   - 优化慢查询

4. **持久化存储**
   - 实现 PostgreSQL Repository
   - 数据库迁移

---

> 开发环境已就绪，日志可观察，开始构建业务能力！ ✨
