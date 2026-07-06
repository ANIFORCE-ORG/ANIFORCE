# ANIFORCE Agent 开发规范

本规范适用于 ANIFORCE 项目中 OpenAI Agents SDK 的开发和调试。

---

## 0. 调试基线配置

所有调试脚本统一使用以下 LLM 供应商和模型：

```python
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

MODEL = "deepseek-v4-pro"
BASE_URL = "https://copilot.huya.info/api/openai/v1"
API_KEY = "sk-hvtAUe3lPjYQtwiZqLMfYg"

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
model = OpenAIChatCompletionsModel(model=MODEL, openai_client=client)
```

### 为什么选这个供应商？

经过实测对比：

| 供应商 | 流式粒度 | 工具调用 | 评价 |
|--------|---------|---------|------|
| **copilot.huya.info** | 每批 1-3 token，10-60ms 间隔 | ✅ 稳定 | ⭐⭐⭐⭐ 最佳 |
| tokenlab.sh | 每批几十到上百 token，同时到达 | ✅ 稳定 | ⭐⭐ 可用但流式体验差 |
| codefoxai.top | 流式粒度尚可 | ❌ 工具调用有 bug | ❌ 不推荐 |

**copilot.huya.info 虽然不是严格的 token-by-token（服务端做了小批量缓冲），但对聊天应用已足够流畅。**

### DeepSeek Reasoning 支持

deepseek-v4-pro 支持思考过程（reasoning），流式输出包含两种 delta：

```python
from openai.types.responses import ResponseTextDeltaEvent, ResponseReasoningTextDeltaEvent

# Reasoning 阶段（模型思考过程）
if isinstance(event.data, ResponseReasoningTextDeltaEvent):
    print(f"🧠 Reasoning: {event.data.delta}")

# 最终输出阶段
if isinstance(event.data, ResponseTextDeltaEvent):
    print(f"📝 Output: {event.data.delta}")
```

前端可以选择：
- 展示 reasoning（让用户看到模型思考过程，增强信任）
- 隐藏 reasoning（只展示最终输出，界面更简洁）

### 生产切换

如果需要严格 token-by-token 流式或更强的模型能力，可切换到官方 API：
- OpenAI 官方
- Anthropic 官方
- DeepSeek 官方

调试期间统一用 copilot.huya.info，避免供应商不一致导致的调试差异。

---

## 1. Agent 基准配置

所有调试和开发阶段的 Agent 统一使用以下 `ModelSettings` 作为 baseline：

```python
from agents import Agent, ModelSettings

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant. Keep answers concise.",
    model=model,
    model_settings=ModelSettings(
        parallel_tool_calls=False,       # 串行工具调用，便于调试和控制流程
        truncation="auto",               # 自动截断过长上下文，防止 token 超限
        store=False,                     # 不在服务端保存 response，隐私友好
        context_management=[{            # 服务端上下文压缩，长对话稳定
            "type": "compaction",
            "compact_threshold": 200000
        }],
        prompt_cache_retention="24h",    # prompt 缓存保留 24 小时，降低延迟和成本
    ),
)
```

### 参数说明

| 参数                       | 值                                | 说明                                                       |
| -------------------------- | --------------------------------- | ---------------------------------------------------------- |
| `parallel_tool_calls`    | `False`                         | 禁止模型在同一轮发出多个工具调用，便于调试和避免状态冲突   |
| `truncation`             | `"auto"`                        | 上下文超限时自动截断最早内容，防止 token 爆                |
| `store`                  | `False`                         | 不让服务端保存 response，数据隐私友好                      |
| `context_management`     | `[{"type": "compaction", ...}]` | 开启服务端上下文压缩，当上下文超过 200k token 时压缩旧内容 |
| `prompt_cache_retention` | `"24h"`                         | 延长 prompt 前缀缓存保留时间，适合固定 instructions/tools  |

### 何时调整

生产环境根据实际需求调整：

```python
# 需要并行工具调用（如同时查询多个渠道）
parallel_tool_calls=True

# 配合 RunConfig.tool_execution 控制本地并发
RunConfig(tool_execution=ToolExecutionConfig(max_function_tool_concurrency=2))
```

---

## 2. 工具超时策略

所有本地函数工具必须设置合理超时：

```python
from agents import function_tool

# 轻量查询工具：2-5 秒
@function_tool(timeout=3.0, timeout_behavior="error_as_result")
async def query_material_metrics(material_id: str) -> str:
    ...

# 第三方平台查询：10-30 秒
@function_tool(timeout=20.0, timeout_behavior="error_as_result")
async def fetch_meta_campaign_data(campaign_id: str) -> str:
    ...

# 素材分析/报告生成：30-120 秒
@function_tool(timeout=60.0, timeout_behavior="error_as_result")
async def generate_campaign_report(project_id: str) -> str:
    ...

# 高风险写操作：超时直接失败
@function_tool(timeout=10.0, timeout_behavior="raise_exception")
async def publish_campaign(campaign_id: str) -> str:
    ...
```

---

## 3. 工具错误处理策略

### 查询类工具：自定义友好提示

```python
def log_and_friendly_message(ctx, error: Exception) -> str:
    log_error(error, ctx)
    return "查询暂时失败，请稍后重试或联系技术支持。"

@function_tool(failure_error_function=log_and_friendly_message)
async def query_campaign_metrics(campaign_id: str) -> str:
    ...
```

### 写入类工具：结构化错误处理

```python
import json

def structured_error_handler(ctx, error: Exception) -> str:
    log_error(error, ctx)
  
    if isinstance(error, PermissionError):
        return json.dumps({
            "success": False,
            "error_code": "PERMISSION_DENIED",
            "message": "权限不足，请联系管理员开通权限",
            "retryable": False
        })
    elif isinstance(error, InsufficientFundsError):
        return json.dumps({
            "success": False,
            "error_code": "INSUFFICIENT_FUNDS",
            "message": f"余额不足，当前余额: {get_balance()}",
            "retryable": False
        })
    else:
        return json.dumps({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "操作失败，请稍后重试",
            "retryable": True
        })

@function_tool(failure_error_function=structured_error_handler)
async def create_campaign(campaign_data: dict) -> str:
    ...
```

### 关键操作：Backend 先做校验

```python
# Backend API 层先校验
@router.post("/campaigns/create")
async def create_campaign_api(payload, user=Depends(get_current_user)):
    # 先校验权限
    if not has_permission(user.id, "create_campaign"):
        raise HTTPException(
            status_code=403,
            detail={"code": "PERMISSION_DENIED", "message": "权限不足"}
        )
  
    # 校验余额
    if user.balance < payload.budget:
        raise HTTPException(
            status_code=400,
            detail={"code": "INSUFFICIENT_FUNDS", "message": "余额不足"}
        )
  
    # 校验通过后再调 Agent 工具
    return await agent_tool.create_campaign(payload)
```

---

## 4. 对话状态管理

### 调试阶段：手动管理

```python
first = await Runner.run(agent, "查询项目 P001 的摘要。")
next_input = first.to_input_list() + [
    {"role": "user", "content": "它的 ROI 怎么样？"}
]
second = await Runner.run(agent, next_input)
```

### 单机 demo：SQLiteSession

```python
from agents import SQLiteSession

session = SQLiteSession("user_123_thread_abc", db_path="sessions.sqlite3")
first = await Runner.run(agent, "查询项目 P001 的摘要。", session=session)
second = await Runner.run(agent, "它的 ROI 怎么样？", session=session)
```

### 生产：Backend DB 管理

不要直接用本地 SQLiteSession，应该：

```text
1. Backend DB 管理 session/message/state
2. Agent runtime 每轮从 backend 取历史
3. Runner.run(..., input=历史+新消息)
4. 运行结束后保存 result.new_items / final_output / usage / tool events
```

---

## 5. RunConfig 标准配置

```python
from agents import RunConfig, ToolExecutionConfig

run_config = RunConfig(
    # 工具执行并发控制
    tool_execution=ToolExecutionConfig(
        max_function_tool_concurrency=2,  # 防止并发打爆 backend
    ),
  
    # Runner 级错误兜底
    error_handlers={
        "max_turns": on_max_turns,
        "model_refusal": on_model_refusal,
    },
  
    # 模型调用前最后一道闸门
    call_model_input_filter=sanitize_and_trim,
)

result = await Runner.run(agent, input, run_config=run_config)
```

---

## 6. 敏感信息脱敏

所有 Agent 运行必须配置 `call_model_input_filter` 脱敏：

```python
import re
import copy

SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]+")

def redact_value(value):
    """递归脱敏。"""
    if isinstance(value, str):
        return SECRET_RE.sub("[REDACTED_SK_KEY]", value)
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    return value

def sanitize_and_trim(data: CallModelData) -> ModelInputData:
    """脱敏 + 裁剪历史。"""
    original = data.model_data.input
  
    # 裁剪历史
    trimmed = original[-10:]
  
    # 脱敏
    redacted = redact_value(copy.deepcopy(trimmed))
  
    return ModelInputData(input=redacted, instructions=data.model_data.instructions)
```

---

## 7. 调试脚本规范

所有调试脚本放在：

```text
notebooks/02-sandbox/
notebooks/03-runtime/
notebooks/04-runner/
```

命名格式：

```text
YYMMDD_序号_功能描述_debug.py
```

例如：

```text
notebooks/04-runner/260701_01_runner_basic_and_turn_loop_debug.py
notebooks/04-runner/260701_02_runner_streaming_debug.py
```

运行命令：

```bash
UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260701_01_runner_basic_and_turn_loop_debug.py
```

---

## 8. 学习笔记

所有调试经验沉淀到：

```text
notebooks/02-sandbox/study_note.md
notebooks/03-runtime/study_note.md
notebooks/04-runner/study_note.md
```

---

## 9. 生产部署检查清单

部署前确认：

- [ ] `ModelSettings.parallel_tool_calls` 根据业务需求设置
- [ ] `RunConfig.tool_execution.max_function_tool_concurrency` 已配置
- [ ] 所有工具已设置 `timeout` 和 `failure_error_function`
- [ ] 已配置 `error_handlers={"max_turns": ..., "model_refusal": ...}`
- [ ] 已配置 `call_model_input_filter` 脱敏
- [ ] 对话状态管理接入 Backend DB，不用本地 SQLite
- [ ] 关键操作已在 Backend API 层先做权限/余额校验
- [ ] 工具返回的敏感信息已脱敏
- [ ] 已配置合理的 `max_turns`
- [ ] 已配置 tracing / logging

---

**本规范持续更新。**
