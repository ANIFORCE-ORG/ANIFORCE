# OpenAI Agents SDK - Runner 学习笔记

本文档记录 OpenAI Agents SDK 中 Runner 模块的学习和调试经验。

---

## 1. 流式传输（Streaming）

### 1.1 基础用法

```python
from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent

result = Runner.run_streamed(agent, "查询素材 M001 的指标")

async for event in result.stream_events():
    # 监听最终输出文本 delta
    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
        if event.data.delta:
            print(event.data.delta, end="", flush=True)
```

**关键点：**
- 必须完整消费 `result.stream_events()` 直到迭代器结束
- 流式传输结束后，SDK 才会完成会话持久化、审批记账、历史压缩等后处理
- `result.is_complete` 反映最终运行状态

### 1.2 事件类型

OpenAI Agents SDK 提供三种层级的流式事件：

#### 1.2.1 原始响应事件（RawResponsesStreamEvent）

直接来自 LLM 的原始事件，采用 OpenAI Responses API 格式。

**事件统计（典型的工具调用场景）：**
```text
agent_updated_stream_event: 1 次
raw_response_event: 341 次      ← 大量的 delta 事件
run_item_stream_event: 6 次
```

**raw_response_event 的 6 种子类型：**

##### 1. response.created

模型响应开始时触发。

```python
if event.type == "raw_response_event" and event.data.type == "response.created":
    print(f"响应开始: {event.data.response.id}")
    print(f"序号: {event.data.sequence_number}")  # 0
```

##### 2. response.output_item.added

新的输出项开始（reasoning、message、tool_call）。

```python
if event.data.type == "response.output_item.added":
    print(f"新输出项: {event.data.item.type}")  # "reasoning" 或 "message"
    print(f"输出索引: {event.data.output_index}")
```

##### 3. response.reasoning_text.delta ⭐

**DeepSeek reasoning 的逐字流式输出。**

```python
from openai.types.responses import ResponseReasoningTextDeltaEvent

if isinstance(event.data, ResponseReasoningTextDeltaEvent):
    if event.data.delta:
        print(f"🧠 {event.data.delta}", end="", flush=True)
```

**字段：**
- `delta`: 思考过程的文本片段（"用户"、"想要"、"查询"...）
- `content_index`: 内容索引（通常为 0）
- `output_index`: 输出索引（reasoning 的索引）
- `sequence_number`: 严格递增的序号

##### 4. response.output_text.delta ⭐

**最终输出文本的逐字流式输出。**

```python
from openai.types.responses import ResponseTextDeltaEvent

if isinstance(event.data, ResponseTextDeltaEvent):
    if event.data.delta:
        print(f"📝 {event.data.delta}", end="", flush=True)
```

**字段：**
- `delta`: 最终输出的文本片段（"素材"、" M001"、"的指标"...）
- `content_index`: 内容索引（通常为 1）
- `output_index`: 输出索引（message 的索引）
- `logprobs`: 对数概率（通常为空列表）

**⚠️ 关键发现：reasoning 和 output 是互斥的**

DeepSeek 模型同时发送两种 delta，但在不同阶段：

```text
【Reasoning 阶段】
  response.reasoning_text.delta: "用户"、"想要"、"查询"... ✅ 有内容
  response.output_text.delta: ''、''、''...              ❌ 全是空字符串

【Output 阶段（reasoning 结束后）】
  response.reasoning_text.delta: （不再发送）
  response.output_text.delta: "素材"、"M001"、"的指标"... ✅ 有内容
```

**原因：** 模型在 reasoning 阶段还在思考，还没开始生成最终输出。

**前端处理：**

```typescript
let reasoningBuffer = "";
let outputBuffer = "";
let inReasoning = false;

for await (const event of result.streamEvents()) {
  if (event.type === 'raw_response_event') {
    // Reasoning delta（思考过程）
    if (event.data.type === 'response.reasoning_text.delta' && event.data.delta) {
      inReasoning = true;
      reasoningBuffer += event.data.delta;
      updateReasoningBox(reasoningBuffer);  // 显示在思考区域
    }
    
    // Output delta（最终输出）
    else if (event.data.type === 'response.output_text.delta' && event.data.delta) {
      if (inReasoning) {
        inReasoning = false;
        collapseReasoningBox();  // 折叠思考区域
      }
      outputBuffer += event.data.delta;
      updateOutputBox(outputBuffer);  // 逐字追加到主输出区
    }
  }
}
```

##### 5. response.content_part.added

新的内容部分开始。

```python
if event.data.type == "response.content_part.added":
    print(f"新内容部分: {event.data.part.type}")  # "output_text"
    print(f"内容索引: {event.data.content_index}")
```

##### 6. response.completed

一次模型响应完成。

```python
if event.data.type == "response.completed":
    print(f"响应完成: {event.data.response.id}")
    print(f"最终序号: {event.data.sequence_number}")  # 例如 109
```

**注意：** 多步运行（工具调用后再次生成）会有多个 `response.completed` 事件。

**适用场景：** 需要逐 token 展示输出，构建打字机效果。

---

#### 1.2.2 运行项事件（RunItemStreamEvent）

更高层级的事件，当某个项**完全生成后**通知（不是逐字触发）。

**RunItemStreamEvent 的 4 种主要事件：**

##### 1. reasoning_item_created

**Reasoning 完成时触发**（整个思考过程结束）。

```python
if event.name == "reasoning_item_created":
    # 提取完整的 reasoning 文本
    content = event.item.raw_item.content or []
    reasoning_text = "".join(part.text for part in content)
    print(f"🧠 Reasoning: {reasoning_text[:80]}...")
```

**字段：**
- `event.item.type`: `"reasoning_item"`
- `event.item.raw_item`: `ResponseReasoningItem`
- `event.item.agent`: 当前 Agent

**示例内容：**
```text
"用户想要查询素材 M001 的指标。我需要调用 get_material_metrics 工具，传入 material_id 为 'M001'。"
```

##### 2. tool_called

**工具被调用时触发**。

```python
if event.name == "tool_called":
    tool_name = event.item.raw_item.name
    arguments = event.item.raw_item.arguments
    call_id = event.item.raw_item.call_id
    print(f"🔧 工具调用: {tool_name}({arguments})")
```

**字段：**
- `event.item.type`: `"tool_call_item"`
- `event.item.raw_item.name`: 工具名称（如 `"get_material_metrics"`）
- `event.item.raw_item.arguments`: JSON 字符串（如 `'{"material_id": "M001"}'`）
- `event.item.raw_item.call_id`: 唯一调用 ID（如 `"call_00_..."`）
- `event.item.description`: 工具描述
- `event.item.tool_origin.type`: 工具来源（`ToolOriginType.FUNCTION`）

##### 3. tool_output

**工具返回结果时触发**。

```python
if event.name == "tool_output":
    output = event.item.output
    print(f"✅ 工具返回: {output}")
```

**字段：**
- `event.item.type`: `"tool_call_output_item"`
- `event.item.output`: 工具返回的字符串（如 `"素材 M001：CTR=2.8%，CVR=8.1%，ROI=3.4。"`）
- `event.item.tool_origin`: 工具来源信息
- `event.item.custom_data`: 自定义数据（通常为 `None`）

##### 4. message_output_created

**最终消息生成完成时触发**。

```python
if event.name == "message_output_created":
    from agents import ItemHelpers
    text = ItemHelpers.text_message_output(event.item)
    print(f"💬 消息: {text}")
```

**字段：**
- `event.item.type`: `"message_output_item"`
- `event.item.raw_item`: `ResponseOutputMessage(role="assistant", content=[...])`
- `event.item.agent`: 当前 Agent

**其他 RunItemStreamEvent 事件名称：**
- `handoff_requested` - 请求任务转移
- `handoff_occured` - 任务转移发生（有意拼写错误，向后兼容）
- `tool_search_called` - 托管工具搜索请求
- `tool_search_output_created` - 托管工具搜索结果
- `mcp_approval_requested` - MCP 审批请求
- `mcp_approval_response` - MCP 审批响应
- `mcp_list_tools` - MCP 工具列表

**适用场景：** 向用户展示进度更新（"正在查询..."、"分析完成"），而非逐 token 展示。

---

#### 1.2.3 Agent 更新事件（AgentUpdatedStreamEvent）

**运行开始或任务转移时触发**。

```python
if event.type == "agent_updated_stream_event":
    print(f"Agent 切换: {event.new_agent.name}")
    print(f"Agent 指令: {event.new_agent.instructions[:80]}...")
    print(f"Agent 工具数量: {len(event.new_agent.tools)}")
```

**字段：**
- `event.new_agent`: 新的活跃 Agent
- `event.type`: `"agent_updated_stream_event"`

**用途：**
- 前端展示当前活跃的 Agent
- 任务转移时更新 UI

---

### 1.3 流式事件分层与统计

**典型的工具调用场景事件统计：**

```text
agent_updated_stream_event: 1 次
raw_response_event: 341 次      ← 占绝大多数（包含所有 delta）
run_item_stream_event: 6 次
```

**事件分层：**

```text
高层级（适合前端进度展示）
  ├─ agent_updated_stream_event（Agent 切换）
  └─ run_item_stream_event（reasoning/tool_called/tool_output/message）
        ↑ 只在项目完全生成后触发，不是逐字触发

低层级（适合逐字打印）
  └─ raw_response_event（占大多数）
       ├─ response.created（响应开始）
       ├─ response.output_item.added（新输出项开始）
       ├─ response.reasoning_text.delta（思考过程逐字）
       ├─ response.output_text.delta（最终输出逐字）
       ├─ response.content_part.added（新内容部分开始）
       └─ response.completed（响应完成）
```

**关键点：**
- `raw_response_event` 数量远超其他事件（逐字发送）
- `run_item_stream_event` 只在完整项生成后触发一次
- 每个事件都有 `sequence_number`（严格递增，用于排序）

---

### 1.4 前端集成方案

#### 方案1：逐字打印（打字机效果）

```typescript
async function streamWithTypingEffect(input: string) {
  const result = await runStreamed(agent, input);
  
  let reasoningBuffer = "";
  let outputBuffer = "";
  let inReasoning = false;
  
  for await (const event of result.streamEvents()) {
    if (event.type === 'raw_response_event') {
      // Reasoning delta（思考过程）
      if (event.data.type === 'response.reasoning_text.delta' && event.data.delta) {
        inReasoning = true;
        reasoningBuffer += event.data.delta;
        updateReasoningBox(reasoningBuffer);  // 更新 reasoning 区域
      }
      
      // Output delta（最终输出）
      else if (event.data.type === 'response.output_text.delta' && event.data.delta) {
        if (inReasoning) {
          inReasoning = false;
          collapseReasoningBox();  // 折叠或隐藏 reasoning
        }
        outputBuffer += event.data.delta;
        updateOutputBox(outputBuffer);  // 逐字追加
      }
    }
  }
}
```

#### 方案2：进度更新（工具调用状态）

```typescript
async function streamWithProgress(input: string) {
  const result = await runStreamed(agent, input);
  
  for await (const event of result.streamEvents()) {
    if (event.type === 'run_item_stream_event') {
      if (event.name === 'reasoning_item_created') {
        showStatus('🧠 正在思考...');
      }
      else if (event.name === 'tool_called') {
        const toolName = event.item.raw_item.name;
        showStatus(`🔧 调用工具: ${toolName}`);
      }
      else if (event.name === 'tool_output') {
        showStatus('✅ 工具执行完成');
      }
      else if (event.name === 'message_output_created') {
        showStatus('📝 生成完成');
        showFinalMessage(event.item);
      }
    }
  }
}
```

#### 方案3：混合模式（推荐）

结合逐字打印和进度更新：

```typescript
async function streamHybrid(input: string) {
  const result = await runStreamed(agent, input);
  
  let currentStatus = '';
  let outputBuffer = '';
  
  for await (const event of result.streamEvents()) {
    // 高层级进度（显示在状态栏）
    if (event.type === 'run_item_stream_event') {
      if (event.name === 'tool_called') {
        currentStatus = `🔧 ${event.item.raw_item.name}`;
        showStatusBadge(currentStatus);
      }
      else if (event.name === 'reasoning_item_created') {
        hideStatusBadge();
      }
    }
    
    // 逐字输出（显示在主输出区）
    if (event.type === 'raw_response_event' 
        && event.data.type === 'response.output_text.delta' 
        && event.data.delta) {
      outputBuffer += event.data.delta;
      updateOutputBox(outputBuffer);
    }
  }
}
```

### 1.5 ItemHelpers 辅助函数

SDK 提供了 `ItemHelpers` 简化数据提取：

```python
from agents import ItemHelpers

# 提取消息文本（推荐）
text = ItemHelpers.text_message_output(event.item)

# 手动提取（不推荐，代码冗长）
content = event.item.raw_item.content or []
text = "".join(part.text for part in content)
```

---

## 2. 流式传输 + 工具审批（Human-in-the-loop）

### 2.1 审批流程

```python
from agents import function_tool, Runner

@function_tool(needs_approval=True)
def delete_campaign(campaign_id: str) -> str:
    """删除投放活动（需要审批）。"""
    return f"活动 {campaign_id} 已删除。"

agent = Agent(
    name="Campaign Manager",
    instructions="你是活动管理助手。",
    tools=[delete_campaign],
)

# 阶段1：流式消费到审批点
result = Runner.run_streamed(agent, "删除活动 C001")
async for event in result.stream_events():
    pass  # 消费完所有事件

# 检查是否有待审批项
if result.interruptions:
    for interruption in result.interruptions:
        print(f"待审批: {interruption.tool_name}({interruption.arguments})")
    
    # 阶段2：批准并恢复运行
    state = result.to_state()
    for interruption in result.interruptions:
        state.approve(interruption)  # 批准
        # 或 state.reject(interruption, "拒绝理由")  # 拒绝
    
    # 恢复流式运行
    result = Runner.run_streamed(agent, state)
    async for event in result.stream_events():
        pass
```

### 2.2 ToolApprovalItem 结构

`result.interruptions` 返回 `list[ToolApprovalItem]`，包含以下属性：

| 属性 | 类型 | 说明 |
|------|------|------|
| `type` | `str` | 固定为 `"tool_approval_item"` |
| `tool_name` | `str` | 工具名称，如 `"delete_campaign"` |
| `arguments` | `str` | JSON 字符串，如 `'{"campaign_id": "C001"}'` |
| `call_id` | `str` | 工具调用 ID，用于追踪 |
| `tool_namespace` | `str \| None` | 工具命名空间 |
| `tool_origin` | `ToolOrigin` | 工具来源（function/mcp/agent） |

**注意：** ToolApprovalItem **没有** `item` 属性，直接访问 `tool_name`、`arguments` 等。

### 2.3 审批状态机

```text
用户输入
   ↓
模型请求工具（needs_approval=True）
   ↓
流式暂停，返回 result.interruptions
   ↓
前端展示审批弹窗
   ↓
用户批准 → state.approve(interruption)
   ↓
Runner.run_streamed(agent, state) 恢复
   ↓
工具执行 → 最终输出
```

### 2.4 前端集成示例

```typescript
// 前端处理审批
async function handleAgentRun(input: string) {
  let result = await runStreamed(agent, input);
  
  // 消费流式事件
  for await (const event of result.streamEvents()) {
    displayEvent(event);
  }
  
  // 检查审批
  if (result.interruptions.length > 0) {
    for (const item of result.interruptions) {
      const approved = await showApprovalDialog({
        tool: item.tool_name,
        args: JSON.parse(item.arguments),
      });
      
      if (approved) {
        state.approve(item);
      } else {
        state.reject(item, "用户拒绝");
      }
    }
    
    // 恢复运行
    result = await runStreamed(agent, state);
    for await (const event of result.streamEvents()) {
      displayEvent(event);
    }
  }
}
```

---

## 3. 流式取消（Cancel）

### 3.1 立即取消

```python
result = Runner.run_streamed(agent, "写一篇 1000 字的文章")

delta_count = 0
async for event in result.stream_events():
    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
        if event.data.delta:
            delta_count += 1
            print(event.data.delta, end="", flush=True)
            
            if delta_count >= 5:
                result.cancel()  # 立即取消
                break

print(f"\nresult.is_complete: {result.is_complete}")  # True
print(f"result.final_output: {result.final_output}")  # None 或部分内容
```

**特点：**
- 立即停止流式传输
- 可能中断到一半，数据不完整
- `result.is_complete` 仍为 `True`（取消也是一种完成）
- `result.final_output` 可能为空或部分内容

**适用场景：** 用户点击"停止生成"按钮。

### 3.2 当前轮次完成后取消

```python
result = Runner.run_streamed(agent, "查询素材 M001 并详细分析")

async for event in result.stream_events():
    if event.type == "run_item_stream_event" and event.name == "tool_called":
        # 检测到工具调用后，等当前轮次完成再停止
        result.cancel(mode="after_turn")

print(f"\nresult.is_complete: {result.is_complete}")  # True
print(f"已执行的 turns: {len(result.new_items)}")  # 完整的轮次
```

**特点：**
- 不是立即停止，而是等当前轮次（turn）完成
- 当前轮次的工具调用会正常执行并返回结果
- 数据完整，不会中断到一半
- 适合需要保证数据一致性的场景

**轮次（turn）的定义：**
一个完整的对话轮次包括：
1. 用户输入 / 上一轮的工具输出
2. 模型生成响应
3. 工具调用（如果有）
4. 工具返回结果（如果有）

**对比：**

| 方法 | 停止时机 | 数据完整性 | 适用场景 |
|------|---------|-----------|---------|
| `cancel()` | 立即 | ❌ 可能不完整 | 用户不耐烦，强制停止 |
| `cancel(mode="after_turn")` | 当前轮次完成后 | ✅ 完整 | 优雅停止，保证数据一致性 |

### 3.3 取消后的继续策略

**如果用 `result.to_input_list(mode="normalized")` 手动继续：**

```python
# cancel(mode="after_turn") 在工具轮次后停止
result.cancel(mode="after_turn")
async for event in result.stream_events():
    pass

# 继续那个未完成的轮次
normalized = result.to_input_list(mode="normalized")
result2 = Runner.run_streamed(result.last_agent, normalized)
```

**注意：** 不要立即追加新的用户轮次，应该先完成被取消的轮次。

**如果因工具审批而停止：**

```python
# 不要当作新轮次，应该从 state 恢复
if result.interruptions:
    state = result.to_state()
    for interruption in result.interruptions:
        state.approve(interruption)
    result = Runner.run_streamed(agent, state)
```

---

## 4. result.is_complete 的含义

**`result.is_complete` 表示"流式传输已结束"，不代表"任务已完成"。**

### 4.1 is_complete 为 True 的情况

| 场景 | is_complete | final_output | interruptions |
|------|-------------|--------------|---------------|
| 正常完成 | `True` | 有内容 | `[]` |
| 立即取消 | `True` | 可能为空 | `[]` |
| 轮次完成后取消 | `True` | 部分内容 | `[]` |
| 等待审批 | `True` | 可能为空 | 非空列表 |
| max_turns 超限 | `True` | 错误提示 | `[]` |

### 4.2 判断任务状态的完整逻辑

```python
result = Runner.run_streamed(agent, input)
async for event in result.stream_events():
    pass

if result.interruptions:
    # 有待审批项，需要人工介入
    handle_approvals(result.interruptions)
elif result.final_output:
    # 任务正常完成
    print(result.final_output)
else:
    # 任务被取消或异常
    print("任务未完成")
```

---

## 5. 流式粒度验证

### 5.1 测试方法

使用时间戳记录每个 delta 的到达时间：

```python
import time

start_time = time.time()
last_event_time = start_time

async for event in result.stream_events():
    current_time = time.time()
    elapsed = current_time - start_time
    delta_time = current_time - last_event_time
    last_event_time = current_time
    
    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
        if event.data.delta:
            print(f"[{elapsed:.3f}s] (+{delta_time*1000:.1f}ms) {event.data.delta!r}")
```

### 5.2 测试结果

**copilot.huya.info + deepseek-v4-pro（调试基线）：**

```text
[11.748s] (+17.8ms) '##'
[11.748s] (+0.0ms) ' 📊'
[11.764s] (+16.3ms) '素材'
[11.764s] (+0.0ms) ' M'
[11.787s] (+22.2ms) '001'
[11.790s] (+3.0ms) ' '
[11.797s] (+7.0ms) '投放'
[11.797s] (+0.0ms) '数据'
[11.822s] (+25.6ms) '\n\n'
```

**特点：**
- 小批量缓冲（micro-batching）：每批 1-3 个 token
- 平均间隔：10-60ms
- `(+0.0ms)` 表示同一时刻到达多个 token

**不是严格的 token-by-token，但对聊天应用已足够流畅。**

**对比其他供应商：**

| 供应商 | 流式粒度 | 工具调用 | 评价 |
|--------|---------|---------|------|
| copilot.huya.info | 每批 1-3 token，10-60ms 间隔 | ✅ 稳定 | ⭐⭐⭐⭐ 最佳 |
| tokenlab.sh | 每批几十到上百 token，同时到达 | ✅ 稳定 | ⭐⭐ 可用但流式体验差 |
| codefoxai.top | 流式粒度尚可 | ❌ 工具调用有 bug | ❌ 不推荐 |

**如需严格 token-by-token，只能用官方 API：**
- OpenAI 官方
- Anthropic 官方
- DeepSeek 官方

---

## 6. DeepSeek Reasoning 支持

deepseek-v4-pro 支持思考过程（reasoning），流式输出包含两种 delta：

### 6.1 监听 Reasoning 和 Output

```python
from openai.types.responses import ResponseTextDeltaEvent, ResponseReasoningTextDeltaEvent

reasoning_started = False
output_started = False

async for event in result.stream_events():
    if event.type == "raw_response_event":
        # Reasoning 阶段（模型思考）
        if isinstance(event.data, ResponseReasoningTextDeltaEvent):
            if event.data.delta:
                if not reasoning_started:
                    print("\n🧠 Reasoning 开始：\n")
                    reasoning_started = True
                print(event.data.delta, end="", flush=True)
        
        # 最终输出阶段
        elif isinstance(event.data, ResponseTextDeltaEvent):
            if event.data.delta:
                if reasoning_started and not output_started:
                    print("\n\n📝 最终输出开始：\n")
                    output_started = True
                    reasoning_started = False
                print(event.data.delta, end="", flush=True)
```

### 6.2 Reasoning 的特点

1. **Reasoning 在 Output 之前**
   - 先输出 reasoning delta（思考过程）
   - 再输出 output_text delta（最终回答）

2. **前端展示策略**
   - 方案A：展示 reasoning（让用户看到模型思考，增强信任）
   - 方案B：隐藏 reasoning（只展示最终输出，界面更简洁）

3. **Reasoning 也会触发 RunItemStreamEvent**
   ```python
   if event.name == "reasoning_item_created":
       print("🧠 Reasoning 完成")
   ```

---

## 7. 生产级流式 + HITL 状态管理

流式传输和人在回路（HITL）最接近真实生产场景。用户可能中途离开、刷新页面、第二天再回来审批；后端也可能是多 worker、多实例部署。因此不能依赖内存中的 `RunResultStreaming` 或 `result.interruptions`，必须把可恢复状态持久化。

### 7.1 核心原则

**不要把每个 delta 当作长期事实写入 DB。**

错误做法：

```text
response.output_text.delta  → insert DB
response.output_text.delta  → insert DB
response.output_text.delta  → insert DB
...
```

问题：
- 一次回答可能产生几百到几千个 delta
- 高并发下会制造大量小写入，业务 DB IO 压力很高
- 历史对话通常不需要 token 级重放
- 查询、归档、审计都会变复杂

更合理的生产模型：

```text
实时层：delta / reasoning delta / typing effect
  → WebSocket / SSE / Redis PubSub
  → 可丢、可短期缓存，主要服务当前在线用户

事实层：消息、工具调用、审批、RunState、最终结果
  → DB
  → 强一致、可恢复、可审计
```

一句话：

```text
生产级不是 event sourcing every token，
而是 message snapshot + run checkpoint + approval state + realtime delta channel。
```

### 7.2 推荐事件处理策略

```text
Runner.run_streamed()
  │
  ├─ raw delta / reasoning delta
  │    ├─ 实时推送给前端
  │    ├─ 可选写 Redis 短期 buffer，用于断线重连
  │    └─ 不进长期 DB
  │
  ├─ tool_called / tool_output
  │    └─ 写 DB，作为审计事实
  │
  ├─ interruptions
  │    ├─ 写 approval 表
  │    ├─ 保存 RunState
  │    └─ run.status = awaiting_approval
  │
  └─ final_output / completed
       └─ 写 assistant message 最终内容
```

**默认生产模式只保存关键事实：**
- `message_created`
- `message_completed`
- `tool_call_started`
- `tool_call_completed`
- `approval_required`
- `approval_resolved`
- `run_completed`
- `run_failed`

**不长期保存：**
- `response.output_text.delta`
- `response.reasoning_text.delta`
- token 级 UI 片段

### 7.3 数据表建议

#### agent_runs

保存运行生命周期和可恢复状态。

```text
run_id
session_id
user_id
status: queued / running / awaiting_approval / resuming / completed / failed / cancelled
run_state_json          # awaiting_approval / 可恢复场景必须保存
current_message_id
usage_json
error_json
started_at
completed_at
updated_at
```

#### agent_messages

保存用户可见消息。

```text
message_id
session_id
run_id
role: user / assistant
content
status: streaming / interrupted / completed / failed
sequence
created_at
updated_at
```

流式过程中可以先创建 assistant 消息：

```text
status = streaming
content = ""
```

但不要每个 delta 更新 DB，而是：

```text
每 500ms / 1s flush 一次
或每累计 N 字符 flush 一次
或只在 interrupted / completed 时最终写一次
```

这种聚合写入称为 coalescing / batching。

#### agent_tool_calls

保存工具调用事实。

```text
tool_call_id
run_id
tool_name
arguments_json
result_json
status: called / awaiting_approval / approved / rejected / completed / failed
created_at
updated_at
```

#### agent_approvals

保存 HITL 审批状态，是人在回路的核心事实表。

```text
approval_id
run_id
tool_call_id
call_id
tool_name
arguments_json
status: pending / approved / rejected / expired
approved_by
approved_at
rejection_message
policy_json
created_at
updated_at
```

### 7.4 Redis / PubSub 的职责

Redis 不作为长期事实源，适合做两件事。

#### 实时事件通道

```text
Agent Worker → Redis PubSub / Stream → WebSocket/SSE Gateway → Frontend
```

#### 短期断线重连 buffer

```text
run:{run_id}:deltas
TTL: 10 分钟 / 30 分钟 / 2 小时
```

前端重连时携带：

```text
last_event_seq
```

后端从 Redis 补发缺失片段；如果 Redis buffer 已过期，则回退到 DB 里的 message snapshot。

### 7.5 用户离开和历史对话

#### 用户中途离开

```text
1. 前端断开 WebSocket/SSE
2. Agent Worker 继续执行
3. delta 不再需要为这个连接单独长期保存
4. 如果完成：保存 final_output
5. 如果需要审批：保存 RunState + approval
```

#### 用户回来

```text
1. 读取 agent_messages
2. 读取 agent_runs.status
3. 如果 completed：展示最终消息
4. 如果 awaiting_approval：展示审批卡片
5. 如果 running：展示当前 message snapshot，并重新订阅实时流
```

#### 第二天打开历史对话

不重放 token，只展示消息历史和审批状态：

```text
用户：删除活动 C001
助手：需要确认是否删除活动 C001。
[审批卡片：待审批 / 已批准 / 已拒绝]
```

或：

```text
助手：活动 C001 已成功删除。
```

### 7.6 多 worker / 多实例恢复

#### Worker 必须无状态

错误做法：

```python
memory_results[run_id] = result  # 不同 worker 看不到，进程重启会丢
```

正确做法：

```python
state_json = result.to_state().to_json()
save_to_db(run_id, state_json)
```

#### 审批恢复使用 CAS 状态机

审批恢复时，不要只依赖内存锁。核心应使用 DB 状态机 CAS，避免多个 worker 同时恢复同一个 run。

```sql
UPDATE agent_runs
SET status = 'resuming'
WHERE run_id = :run_id
  AND status = 'awaiting_approval';
```

如果影响行数为 0，说明别的 worker 已经抢到恢复权，当前 worker 直接退出。

#### 恢复仍然使用 run_streamed

生产恢复审批后也应该继续流式：

```python
state = await RunState.from_json(agent, run.run_state_json)
state.approve(interruption)

result = Runner.run_streamed(agent, state)
async for event in result.stream_events():
    await publish_realtime(run_id, event)
    await persist_key_event_if_needed(event)
```

### 7.7 推荐实现骨架

```python
async def run_agent_streamed(run_id: str, input_data):
    agent = build_agent()
    result = Runner.run_streamed(agent, input_data)

    message_buffer = []
    last_flush_at = time.monotonic()

    async for event in result.stream_events():
        # 1. 实时推送所有需要前端展示的事件
        await publish_realtime(run_id, event)

        # 2. delta 只进入内存 buffer / Redis 短期 buffer
        if is_output_delta(event):
            message_buffer.append(extract_delta(event))
            if should_flush(message_buffer, last_flush_at):
                await flush_message_snapshot(run_id, message_buffer)
                message_buffer.clear()
                last_flush_at = time.monotonic()

        # 3. 工具调用等关键事件立即入库
        elif is_tool_call(event):
            await persist_tool_call(run_id, event)

        elif is_tool_output(event):
            await persist_tool_output(run_id, event)

    # 4. 流结束后最终 flush
    await flush_message_snapshot(run_id, message_buffer)

    # 5. 处理审批 / 完成状态
    if result.interruptions:
        state = result.to_state()
        await persist_run_state(run_id, state.to_json())
        await persist_approvals(run_id, result.interruptions)
        await update_run_status(run_id, "awaiting_approval")
        await publish_realtime(run_id, {"type": "approval_required"})
    else:
        await persist_final_output(run_id, result.final_output, result.new_items)
        await update_run_status(run_id, "completed")
        await publish_realtime(run_id, {"type": "completed"})
```

### 7.8 Debug / Audit 模式

全量保存 `stream_events` 只适合特殊场景：

- `debug=true`
- 失败运行复盘
- 采样审计（如 1%）
- 重要客户问题排查
- SDK 行为验证

此时可以保存完整事件 trace，但不作为默认生产路径。

### 7.9 最终推荐

ANIFORCE 生产应采用：

```text
实时 delta 通道
+ 消息快照持久化
+ 工具/审批事实表
+ RunState checkpoint
+ 多实例 CAS 恢复
+ Debug 模式采样保存完整事件
```

这样既能支持流式体验，又能支持用户离开、第二天回来、多 worker、多实例恢复，同时不会把 DB IO 打爆。

---

## 8. 生产部署建议

### 7.1 前端流式展示

**逐字打印（打字机效果）：**

```typescript
async function streamAgentResponse(input: string) {
  const result = await runStreamed(agent, input);
  
  for await (const event of result.streamEvents()) {
    if (event.type === 'raw_response_event' 
        && event.data.type === 'response.output_text.delta') {
      if (event.data.delta) {
        appendToChatBox(event.data.delta);  // 逐字追加
      }
    }
  }
}
```

**进度更新（工具调用状态）：**

```typescript
for await (const event of result.streamEvents()) {
  if (event.type === 'run_item_stream_event') {
    if (event.name === 'tool_called') {
      showStatus(`正在调用 ${event.item.raw_item.name}...`);
    } else if (event.name === 'tool_output') {
      showStatus('工具执行完成');
    } else if (event.name === 'message_output_created') {
      showStatus('生成完成');
    }
  }
}
```

### 7.2 错误处理

```python
try:
    result = Runner.run_streamed(agent, input)
    async for event in result.stream_events():
        handle_event(event)
except Exception as e:
    log_error(e)
    show_error_to_user("运行失败，请重试")
```

### 7.3 超时控制

虽然 SDK 没有内置流式超时，但可以用 asyncio.wait_for：

```python
import asyncio

async def run_with_timeout(agent, input, timeout=60):
    result = Runner.run_streamed(agent, input)
    
    async def consume_stream():
        async for event in result.stream_events():
            handle_event(event)
    
    try:
        await asyncio.wait_for(consume_stream(), timeout=timeout)
    except asyncio.TimeoutError:
        result.cancel()
        raise TimeoutError("流式传输超时")
```

---

## 8. 调试脚本

所有调试脚本位于 `notebooks/04-runner/`：

| 脚本 | 验证内容 |
|------|---------|
| `260701_02_runner_streaming_debug.py` | 基础流式输出（ResponseTextDeltaEvent） |
| `260702_03_official_streaming_debug.py` | 按官方教程调试流式（逐 token + 高层级事件） |
| `260702_04_full_streaming_with_reasoning_debug.py` | 完整展示 Reasoning + Output |
| `260702_05_streaming_advanced_debug.py` | 审批、取消、ItemHelpers |

运行命令：
```bash
UV_CACHE_DIR=./uv_cache uv run python notebooks/04-runner/260702_05_streaming_advanced_debug.py
```

---

**最后更新：2026-07-02**
