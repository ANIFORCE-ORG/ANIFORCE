# openai-agents-python 核心能力输入输出矩阵

## 产物索引

脚本：

- `drafts/260611/sdk_capability_probes/openai_agents_capability_probe.py`

输出：

- `drafts/260611/sdk_capability_probes/outputs/tools_stream_events.jsonl`
- `drafts/260611/sdk_capability_probes/outputs/tools_result.json`
- `drafts/260611/sdk_capability_probes/outputs/handoff_stream_events.jsonl`
- `drafts/260611/sdk_capability_probes/outputs/handoff_result.json`
- `drafts/260611/sdk_capability_probes/outputs/agent_as_tool_parent_stream_events.jsonl`
- `drafts/260611/sdk_capability_probes/outputs/agent_as_tool_nested_stream_events.jsonl`
- `drafts/260611/sdk_capability_probes/outputs/agent_as_tool_result.json`
- `drafts/260611/sdk_capability_probes/outputs/session_state_result.json`
- `drafts/260611/sdk_capability_probes/outputs/trace_events.jsonl`
- `drafts/260611/sdk_capability_probes/outputs/trace_result.json`

## 1. 普通流式输出

输入：

```python
result = Runner.run_streamed(agent, message, session=optional_session)
async for event in result.stream_events(): ...
```

核心事件：

```text
agent_updated_stream_event
raw_response_event response.created
raw_response_event response.output_item.added
raw_response_event response.content_part.added
raw_response_event response.output_text.delta
raw_response_event response.content_part.done
raw_response_event response.output_item.done
raw_response_event response.completed
run_item_stream_event message_output_item
```

关键结论：

- `response.output_text.delta` 是真实流式文本增量。
- delta 粒度由供应商决定，可能是空串、单字、多字，不保证打字机效果。
- 前端打字机应做本地字符队列。
- usage 主要在 `response.completed` 或 `result.raw_responses[].usage`。

## 2. FunctionTool

定义：

```python
@function_tool
async def list_projects() -> list[dict[str, str]]: ...

agent = Agent(..., tools=[list_projects])
```

stream 形态：

```text
run_item_stream_event tool_called
run_item_stream_event tool_output
run_item_stream_event message_output_created
```

result 形态：

```json
{
  "new_items": [
    { "type": "tool_call_item", "raw_item": { "type": "function_call", "name": "list_projects", "arguments": "..." } },
    { "type": "tool_call_output_item", "raw_item": { "type": "function_call_output", "output": "..." } },
    { "type": "message_output_item", "raw_item": { "type": "message", "content": [...] } }
  ]
}
```

映射建议：

```text
tool_called -> tool.started
tool_output -> tool.completed
message_output_created -> message.completed
```

## 3. Handoff / Multi-agent

定义：

```python
triage = Agent(
  name="triage_agent",
  handoffs=[handoff(project_agent), handoff(chat_agent)]
)
```

stream 形态：

```text
run_item_stream_event handoff_requested
run_item_stream_event handoff_occured
agent_updated_stream_event new_agent=project_agent
raw_response_event ... project_agent output ...
```

result 形态：

```json
{
  "last_agent": "project_agent",
  "new_items": [
    { "type": "handoff_call_item" },
    { "type": "handoff_output_item", "source_agent": "triage_agent", "target_agent": "project_agent" },
    { "type": "message_output_item" }
  ]
}
```

映射建议：

```text
handoff_requested -> agent.handoff.requested
handoff_occured -> agent.handoff.completed
agent_updated_stream_event -> agent.updated
```

## 4. Agent as Tool

定义：

```python
project_agent_tool = project_agent.as_tool(
  tool_name="project_lookup_agent",
  tool_description="查询项目",
  on_stream=handle_stream,
)
main_agent = Agent(..., tools=[project_agent_tool])
```

父级 stream：

```text
Main Agent sees project_lookup_agent as a function tool
```

嵌套 stream：

```text
on_stream receives AgentToolStreamEvent:
{
  "agent": nested_agent,
  "tool_call": parent_tool_call,
  "event": nested_stream_event
}
```

映射建议：

- 父级 `tool_called/tool_output` 用于业务 timeline。
- 嵌套 `on_stream` 可用于展示子 Agent 实时过程。
- 这比 handoff 更适合“主 Agent 调专业 Agent 并保留主控权”。

## 5. Session / RunState

定义：

```python
session = SQLiteSession("probe_session", db_path="...")
await Runner.run(agent, "第一轮", session=session)
await Runner.run(agent, "第二轮", session=session)
state = result.to_state()
```

结论：

- `SQLiteSession` 可以延续多轮上下文。
- `result.to_input_list()` 可拿到继续对话所需的输入列表。
- `result.to_state()` 是 HITL / interruption / resume 的基础，不等于普通消息历史。
- Session persistence 与 server-managed conversation 不应混用。

## 6. Trace

定义：

```python
processor = MemoryTraceProcessor()
add_trace_processor(processor)
with trace("workflow", group_id="..."):
    result = await Runner.run(...)
```

本地 processor 捕获：

```text
trace_start
span_start task
span_start agent
span_start turn
span_start generation
span_start function_tool
span_end ...
trace_end
```

注意：

- 当前环境出现远端 trace export 非致命失败：`Cannot assign requested address`。
- 本地 processor 仍可捕获完整 trace/span。
- 生产可关闭 OpenAI tracing，改用本地 processor 写 `agent_runs/agent_tool_calls/agent_events`。

## 7. Skill

源码位置：

```text
src/agents/sandbox/capabilities/skills.py
```

结论：

- openai-agents-python 的 Skill 不是顶层 `Agent(tools=[...])` 里的普通能力。
- Skill 属于 `sandbox` capability：通过 `SKILL.md`、manifest、sandbox session 注入说明与文件。
- 这更接近 Pi Skill 的“说明文 + 文件/脚本资产”模式。
- 第一阶段普通 Home chat 不应接 sandbox skill。
- 后续如果要做 Agentic workspace / code/file task，再评估 sandbox runtime + skills。

## 8. 对 ANIFORCE 的协议建议

后端不要暴露 SDK raw event，统一映射为 ANIFORCE Business Event：

```text
runtime.started
agent.updated
message.started
message.updated
message.completed
tool.started
tool.completed
agent.handoff.requested
agent.handoff.completed
runtime.completed
runtime.error
```

前端只消费业务事件：

```text
message.started -> 创建 streamingMessage
message.updated -> 将 delta 放入本地打字机队列
message.completed -> 补 usage/input/output，落入 messages
tool.* -> timeline / workspace
handoff.* -> multi-agent 状态
runtime.completed -> 本轮结束
```

下一步应该先实现这个映射层，再回到正式 Home 页面修流式显示、token 速度和 usage。
