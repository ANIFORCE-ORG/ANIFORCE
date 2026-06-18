# 第 2 章 Record 直观解读

> 数据来源：`outputs/02_agent_loop_success.jsonl`、`outputs/02_agent_loop_max_turns.jsonl`
> 每行 JSONL = 一条 `MessageRecord`，结构是 `{index, class_name, summary}`。
> 本文把这些 record 翻译成人话，方便直观对照。

## MessageRecord 是什么

脚本把 SDK 吐出的每条消息，统一压成同一个壳子（`sdk_learning_common.py` 的 `MessageRecord`）：

| 字段 | 含义 |
|---|---|
| `index` | 第几条消息，从 0 开始，记录到达顺序 |
| `class_name` | 消息类型：`SystemMessage` / `AssistantMessage` / `UserMessage` / `ResultMessage` / `ProbeException` |
| `summary` | 该类型的关键字段（不同类型字段不同） |

下面五种 `class_name`，就是 agent loop 里会出现的全部角色。

## 五种 record 速查

| class_name | 谁产生的 | summary 关键字段 | 给前端看吗 |
|---|---|---|---|
| `SystemMessage` | SDK / CLI 后台 | `subtype`(init/thinking_tokens...)、`data` | ❌ 进 trace/debug |
| `AssistantMessage` | 模型 | `content`(text 或 tool_use)、`usage`、`stop_reason` | ✅ 业务事件 |
| `UserMessage` | 工具结果回填 | `content`(ToolResultBlock 字符串) | ✅ 工具结果 |
| `ResultMessage` | SDK（终态） | `subtype`、`is_error`、`num_turns`、`session_id`、`total_cost_usd` | ✅ 任务终态 |
| `ProbeException` | 你的脚本兜底 | `error_type`、`message` | ❌ 仅排查用 |

---

## 样本 A：success（max_turns=8，自然结束）

6 条 record，完整走完一个循环：

| # | class_name | 这条在说什么 |
|---|---|---|
| 0 | `SystemMessage(init)` | 循环启动。`cwd=02_agent_loop_sandbox`、`model=claude-opus-4-6`、`permissionMode=dontAsk`、`plugins=[]`(配置隔离生效)、`session_id=8817328d…` |
| 1 | `AssistantMessage(text)` | 模型开口：`"I'll read the utils.py file and review it..."` |
| 2 | `AssistantMessage(tool_use)` | 模型决定调工具：`Read(file_path="utils.py")`，`tool_use_id=tooluse_VntW…` |
| 3 | `UserMessage(tool_result)` | utils.py 内容回填（注意：工具结果用 UserMessage 装），`tool_use_id` 与上面对应 |
| 4 | `AssistantMessage(text)` | 模型读完，输出完整 bug 分析：Bug1 除零、Bug2 KeyError/TypeError/AttributeError |
| 5 | `ResultMessage(success)` | 终态。见下表 |

**第 5 条 ResultMessage 关键字段：**

| 字段 | 值 | 含义 |
|---|---|---|
| `subtype` | `success` | 正常结束 |
| `is_error` | `false` | 没出错 |
| `stop_reason` | `end_turn` | 模型自己说完了，主动收尾 |
| `num_turns` | `2` | 模型说了 2 轮话（中间夹 1 次工具） |
| `duration_ms` | `41931` | 约 42s |
| `total_cost_usd` | `0.2178` | 这次花了约 ¥1.5 |
| `result` | 完整 bug 分析文本 | 终态里带最终答案 |

---

## 样本 B：max_turns（max_turns=1，被强制掐断）

同样 6 条，但结局不同：

| # | class_name | 这条在说什么 |
|---|---|---|
| 0 | `SystemMessage(init)` | 启动，`session_id=5e4f171c…`（每次 run 新 session） |
| 1 | `AssistantMessage(text)` | 模型开口，同样说"我来读文件" |
| 2 | `AssistantMessage(tool_use)` | 调 `Read(utils.py)` |
| 3 | `UserMessage(tool_result)` | 文件内容回填 |
| 4 | `ResultMessage(error_max_turns)` | **没有第 4 条总结文本**，直接撞上限收尾。见下表 |
| 5 | `ProbeException` | SDK 抛异常，脚本兜底记录：`"Reached maximum number of turns (1)"` |

**第 4 条 ResultMessage 关键字段：**

| 字段 | 值 | 含义 |
|---|---|---|
| `subtype` | `error_max_turns` | 撞 turn 上限 |
| `is_error` | `true` | 标记为失败 |
| `stop_reason` | `tool_use` | 卡在工具阶段，还没进总结就被截断 |
| `num_turns` | `2` | turn 计到 2 |
| `session_id` | `5e4f171c…` | **失败也有 session_id，可追踪/恢复** |
| `result` | `null` | 没有最终答案 |
| `errors` | `["Reached maximum number of turns (1)"]` | 失败原因 |

---

## 两个样本并排对比

| 维度 | success | max_turns |
|---|---|---|
| 消息总数 | 6 | 6（条数一样，但结局完全不同） |
| 第 4 条 | AssistantMessage(总结) | ResultMessage(失败) |
| `subtype` | `success` | `error_max_turns` |
| `is_error` | false | true |
| `stop_reason` | `end_turn`（自己说完） | `tool_use`（被掐断） |
| `result` | 有完整答案 | null |
| `session_id` | 有 | 有（失败照样有） |
| 多出来的 record | 无 | ProbeException 兜底 |

---

## 从 record 直接得出的三条迁移规则

1. **判成败看 `subtype`，不看"有没有 ResultMessage"。** 两个样本都有 ResultMessage，一个 success 一个 error。
2. **`max_turns` 限制 turn（工具回合），不是消息条数。** 两边都是 6 条消息，但 turn 行为不同。
3. **失败任务也带 `session_id`。** error_max_turns 的终态里 session_id 完好，所以失败任务能续接、能排查，不会丢。

> 附带观察：init 里 `plugins=[]`，证明 `CLAUDE_CONFIG_DIR` 隔离生效，没继承宿主机 hooks/plugins/skills。但 init 的 `tools` 列表仍包含 Task/WebSearch 等一堆默认工具——真正限制靠的是 `allowed_tools=[Read,Glob,Grep]` + `disallowed_tools=[Write,Edit,Bash]`，不是 init 里列了什么。

