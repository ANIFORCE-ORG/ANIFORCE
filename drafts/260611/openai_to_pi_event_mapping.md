# openai-agents-python 到旧 Pi/Home 前端协议映射草案

## 已验证样本

产物：

- `drafts/260611/openai_event_dump.py`
- `drafts/260611/openai_event_dump.out`

验证结论：

```text
openai-agents-python version: 0.17.5
model: claude-opus-4-6 via OpenAIChatCompletionsModel
stream API: Runner.run_streamed(...).stream_events()
```

实际事件顺序：

```text
agent_updated_stream_event
raw_response_event response.created
raw_response_event response.output_item.added
raw_response_event response.content_part.added
raw_response_event response.output_text.delta
...
raw_response_event response.content_part.done
raw_response_event response.output_item.done
raw_response_event response.completed
run_item_stream_event message_output_item
```

usage 位置：

```json
{
  "usage": {
    "input_tokens": 1505,
    "output_tokens": 51,
    "total_tokens": 1556
  }
}
```

usage 不在每个 delta 上，只在 completed/raw response 结果上可靠出现。

## 旧 Pi/Home 前端需要的事件

旧 Home 不是为裸 delta 写的，而是为以下业务事件写的：

```text
runtime.started
message.started
message.updated
message.completed
runtime.completed
runtime.error
```

工具相关事件后续再接：

```text
tool.started
tool.updated
tool.completed
```

## 映射规则 v0

### 1. 启动

OpenAI:

```text
Runner.run_streamed() 被创建
```

映射：

```json
{
  "type": "runtime.started",
  "payload": {
    "sessionId": "chat_xxx",
    "runId": "run_xxx",
    "provider": "https://www.codefoxai.top/v1",
    "model": "claude-opus-4-6"
  }
}
```

### 2. assistant 消息开始

OpenAI:

```text
response.output_item.added 或本地 run start 后立即创建
```

映射：

```json
{
  "type": "message.started",
  "payload": {
    "message": {
      "id": "msg_xxx",
      "role": "assistant",
      "content": "",
      "provider": "https://www.codefoxai.top/v1",
      "model": "claude-opus-4-6",
      "timestamp": 1781185714393
    }
  }
}
```

### 3. 文本增量

OpenAI:

```text
raw_response_event response.output_text.delta
```

注意：delta 可能是空字符串，也可能是多字符块，例如：

```text
"我没"
"有关"
"于 ANIFORCE 的"
```

映射：

```json
{
  "type": "message.updated",
  "payload": {
    "message": {
      "id": "msg_xxx",
      "role": "assistant",
      "content": "累计后的完整文本",
      "provider": "https://www.codefoxai.top/v1",
      "model": "claude-opus-4-6"
    },
    "assistantMessageEvent": {
      "type": "text_delta",
      "delta": "本次新增文本"
    }
  }
}
```

前端若想要更明显打字机效果，不应依赖模型 delta 粒度；应该把 `assistantMessageEvent.delta` 放入本地字符队列，以 15-30ms 节奏吐字。

### 4. 完成与 usage

OpenAI:

```text
response.completed
result.raw_responses[].usage
```

映射：

```json
{
  "type": "message.completed",
  "payload": {
    "message": {
      "id": "msg_xxx",
      "role": "assistant",
      "content": "最终文本",
      "provider": "https://www.codefoxai.top/v1",
      "model": "claude-opus-4-6",
      "usage": {
        "input": 1505,
        "output": 51,
        "totalTokens": 1556
      }
    }
  }
}
```

然后：

```json
{
  "type": "runtime.completed",
  "payload": {
    "messages": ["final assistant message"],
    "usage": {
      "input": 1505,
      "output": 51,
      "totalTokens": 1556
    }
  }
}
```

## Pi 与 OpenAI SDK 差异

| 维度 | 旧 Pi runtime | openai-agents-python |
|---|---|---|
| 文本流 | message_update 携带 message/assistantMessageEvent | raw_response_event response.output_text.delta |
| 前端协议 | 业务事件 | SDK raw event |
| 工具事件 | tool_execution_* | run_item_stream_event/tool call item，需另映射 |
| usage | 旧消息 usage 或 runtime state | completed response/raw_responses usage |
| token速度 | 前端基于 streamingMessage 文本长度估算 | 同样要前端估算；SDK 不直接给实时 t/s |
| 完成语义 | agent_end/message_end | stream_events iterator 结束 + result.is_complete |
| shell能力 | Pi 可真实调用工具 | 当前 openai Agent 未注册工具，不能假装 shell |

## 正式实现原则

1. 后端隐藏 SDK raw event。
2. 后端输出旧 Home 能消费的业务事件。
3. 普通 chat 不创建 business task。
4. usage 在完成事件补齐。
5. 前端本地实现打字机队列，不能依赖供应商 delta 粒度。
6. 不注册工具前，system prompt 必须禁止假装执行工具。
