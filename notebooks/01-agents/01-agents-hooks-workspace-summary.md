# Agents Hooks Workspace Summary

## 结论

`RunHooks` 可以作为 Agent Runtime 的事件总线，用来观察和联动 workspace 能力。它不会直接改变模型输出，但能在关键生命周期节点记录日志、审计工具调用、统计 usage、推送前端 timeline，甚至做权限控制。

## 关键执行链路

一次带工具调用的运行通常是：

```text
on_agent_start
on_llm_start
on_llm_end
on_tool_start
on_tool_end
on_llm_start
on_llm_end
on_agent_end
```

默认 `tool_use_behavior="run_llm_again"`，所以工具返回后会再次调用模型，由模型基于工具结果生成最终回答。

## Context 注入

- `Runner.run(..., context=ctx)` 会把业务上下文包装成 `RunContextWrapper`。
- `dynamic_instructions` 通过 `context.context` 读取业务数据，并生成模型可见的 system prompt。
- 工具函数也可以通过 `RunContextWrapper` 读取同一个业务上下文。
- `on_tool_start` / `on_tool_end` 中通常能拿到 `tool_call_id`、`tool_name`、`tool_arguments`。

## Workspace 可用场景

- **运行日志**：记录 Agent 开始、模型调用、工具调用、最终输出。
- **工具审计**：记录工具名、参数、返回值、call_id、workspace_id、user_id。
- **前端 Timeline**：实时展示 Thinking、Calling tool、Tool result、Final answer。
- **权限控制**：在 `on_tool_start` 检查用户是否允许执行某类 workspace 工具。
- **成本统计**：在 `on_llm_end` / `on_agent_end` 使用 `context.usage` 统计 token 和请求数。

## DeepSeek 场景建议

如果使用 DeepSeek 等非 OpenAI trace 后端，建议关闭 OpenAI tracing 导出：

```python
from agents import RunConfig

result = await Runner.run(
    agent,
    user_input,
    context=ctx,
    hooks=WorkspaceRunHooks(),
    run_config=RunConfig(tracing_disabled=True),
)
```
