# Pi Runtime 与 openai-agents-python 协议差异调试

## 目标

先在 drafts 中确认两个 SDK 的输入、事件、消息、usage、工具调用、完成语义差异，再决定正式后端如何映射给旧版 Home 前端。

## 旧 Pi / GrowthAgentService 前端期望

前端不是直接消费裸 token，而是消费一组业务事件 / 消息对象：

```text
runtime.started
message.started
message.updated
message.completed
tool.started
tool.updated
tool.completed
runtime.completed
runtime.error
```

旧 Pi 原始事件在 `businessEventMapper.ts` 中映射：

```text
agent_start            -> runtime.started
message_start          -> message.started
message_update         -> message.updated
message_end            -> message.completed
tool_execution_start   -> tool.started
tool_execution_update  -> tool.updated
tool_execution_end     -> tool.completed
agent_end              -> runtime.completed
error                  -> runtime.error
```

旧前端 `MessageView.vue` 期望 message 结构大致是：

```ts
interface AgentMessage {
  id?: string
  role: 'user' | 'assistant' | 'toolResult' | ...
  content?: string | ContentBlock[]
  timestamp?: number | string
  created_at?: string
  provider?: string
  model?: string
  usage?: {
    input?: number
    output?: number
    cacheRead?: number
    cacheWrite?: number
    totalTokens?: number
    cost?: { total?: number }
  }
  toolCallId?: string
  toolName?: string
}
```

流式打字机不是只靠最终 message，而是靠 streamingMessage 持续变化：

```text
message.started  -> 创建 streamingMessage
message.updated  -> 更新 streamingMessage.content / assistantMessageEvent.delta
message.completed -> streamingMessage 落入 messages，清空 streamingMessage
```

## openai-agents-python 已观察到的事件

通过 `Runner.run_streamed().stream_events()` 可见：

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

`RunResultStreaming` 完成后可取：

```text
final_output
new_items
raw_responses
to_input_list()
to_state()
is_complete
current_agent
```

usage 通常在 raw response 或 completed response 上：

```text
raw_responses[].usage.input_tokens
raw_responses[].usage.output_tokens
```

## 必须做的映射层

不能把 openai raw event 直接丢给前端；要映射成旧前端可理解的业务事件：

```text
openai stream start
  -> runtime.started
  -> message.started { message: assistant skeleton }

response.output_text.delta
  -> message.updated {
       message: { role:'assistant', content: accumulatedText, provider, model },
       assistantMessageEvent: { type:'text_delta', delta }
     }

stream iterator end
  -> message.completed { message: final assistant message with usage }
  -> runtime.completed { messages:[final assistant message] }
```

## 当前缺口

1. 裸 `message_delta` 不能完全复现旧前端协议。
2. 前端需要 `message.updated` 语义，才能统一展示 token 速度、copy、usage。
3. 需要在最终 message 上补 `usage.input/output/totalTokens`。
4. openai SDK 没有 Pi 的 shell/tool 事件；不能让模型假装工具调用。
5. 当前普通 Chat 不应该显示真实 Task/Workspace 状态，除非后续接业务 Task。

## 下一步正式实现建议

先实现 `AgentBusinessEvent` SSE：

```text
event: runtime.started
data: { session_id, run_id, model, provider }

event: message.started
data: { message: { id, role:'assistant', content:'', provider, model } }

event: message.updated
data: { message: { id, role:'assistant', content:'累计文本' }, assistantMessageEvent:{ type:'text_delta', delta:'新增文本' } }

event: message.completed
data: { message: { id, role:'assistant', content:'最终文本', usage:{input,output,totalTokens} } }

event: runtime.completed
data: { messages:[...], usage:{...} }
```

前端 `useAgentSession` 只消费这个业务协议，不关心 SDK 是 Pi 还是 openai-agents-python。
