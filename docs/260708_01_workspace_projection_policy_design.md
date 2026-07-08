# Workspace Projection Policy 设计说明

日期：2026-07-08

## 1. 问题定义

Workspace 不应该覆盖所有 tool 调用结果。

从第一性原理看，Workspace 的价值不是展示工具日志，而是承载用户需要看见、校准、选择、编辑、确认的业务焦点。因此：

```text
tool_output != workspace_projection
```

更准确的关系是：

```text
需要用户视觉注意 / 交互 / 确认的结果 -> workspace_projection
Agent 内部推理材料 -> 不投影
```

尤其在多上下文联合分析中，Agent 会调用多个查询工具获取事实。如果每个查询都投影，会造成右侧面板不断跳动、覆盖前一个焦点，并让用户误以为最后一次工具调用就是任务焦点。

## 2. 设计目标

1. 审批类操作必须投影。
2. 明确浏览、查看、选择、校准类任务可以投影。
3. 分析、诊断、对比、多上下文任务默认不投影中间查询结果。
4. 不依赖中文关键词匹配判断意图。
5. 不引入复杂聚合看板。
6. Workspace 继续复用 SaaS 页面组件，不新建第二套业务 UI。

## 3. 已验证的 SDK 机制

### 3.1 Dynamic Instructions

来源：`notebooks/06-context/study_note.md`

SDK 支持 `Agent.instructions` 使用动态函数：

```python
def workspace_instructions(ctx: RunContextWrapper[WorkspaceRunContext], agent: Agent) -> str:
    snapshot = ctx.context.ui_snapshot
    return f"""
    # Frontend Workspace Snapshot
    - 当前路由：{snapshot.get("route")}
    - 当前选中实体：{snapshot.get("selectedEntities")}
    """
```

运行时通过：

```python
Runner.run_streamed(agent, input=user_input, context=workspace_context)
```

把 `WorkspaceRunContext` 传入。

结论：

```text
Dynamic instructions 是让模型理解“当前 workspace 是否适合投影”的主通道。
```

但它只影响模型行为，不应该直接做 UI 状态变更。

### 3.2 RunContextWrapper / WorkspaceRunContext

来源：`notebooks/06-context/study_note.md`

`RunContextWrapper.context` 是本地运行上下文，LLM 默认看不到，但工具、hooks、tool_filter 可以读取。

适合放：

```python
@dataclass
class WorkspaceRunContext:
    user_id: str
    session_id: str
    run_id: str
    ui_snapshot: dict
    session_state: dict
    business_context_summary: str
    workspace_projection_policy: dict
```

结论：

```text
WorkspaceRunContext 适合承载投影策略，不适合直接当作模型可见内容。
```

模型需要知道的部分，再由 dynamic instructions 摘要注入。

### 3.3 RunHooks / ToolContext

来源：`notebooks/01-agents/01-agents-hooks-workspace-summary.md`、`notebooks/06-context/study_note.md`

`RunHooks` 可以观察生命周期：

```text
on_agent_start
on_llm_start
on_tool_start
on_tool_end
on_agent_end
```

`ToolContext` 可以拿到：

```text
tool_name
tool_call_id
tool_arguments
qualified_tool_name
ctx.context
```

结论：

```text
Hooks 适合做审计、记录工具调用、生成 timeline、执行投影策略。
Hooks 不适合让模型决定业务意图。
```

也就是说：

```text
模型/上下文决定是否应该投影
Hooks/Event Processor 执行投影策略
```

### 3.4 Stream Events

来源：`notebooks/04-runner/study_note.md`

SDK 流式事件里有：

```text
run_item_stream_event/tool_called
run_item_stream_event/tool_output
runtime.requires_action
runtime.completed
```

当前前端就是基于 `tool_called/tool_output` 做 Workspace projection。

结论：

```text
事件流适合作为投影执行时机，但不应该把每个 tool_output 自动当作投影命令。
```

### 3.5 MCP require_approval

来源：`notebooks/07-mcp/study_note.md`、`notebooks/04-runner/260702_08_hitl_approval_debug.py`

MCP 支持高风险工具审批：

```python
MCPServerStreamableHttp(
    require_approval={
        "always": {"tool_names": HIGH_RISK_TOOLS},
        "never": {"tool_names": SAFE_TOOLS},
    },
)
```

审批会产生 `result.interruptions`，runtime 再发出：

```text
runtime.requires_action
```

结论：

```text
审批类 Workspace 投影不需要额外意图判断。
runtime.requires_action 就是明确的投影信号。
```

### 3.6 call_model_input_filter

来源：`notebooks/04-runner/260701_05_call_model_input_filter_debug.py`

`call_model_input_filter` 可以在模型调用前裁剪、脱敏、修改 instructions。

结论：

```text
它适合做安全过滤和上下文裁剪，不适合做 Workspace 投影决策。
```

原因是投影是工具调用后的 UI 状态变更，input filter 发生在模型调用前。

## 4. 不建议的方案

### 4.1 关键词匹配

例如：

```ts
if (message.includes('查看') || message.includes('展示')) allowProjection = true
```

问题：

- 中文表达太多样。
- 英文、多语言、口语表达无法覆盖。
- “帮我看看这两个项目为什么不行”包含“看看”，但它是分析，不是浏览。
- 后续维护会变成规则堆积。

结论：不采用。

### 4.2 所有 tool_output 自动投影

问题：

- 多工具分析会覆盖 Workspace 焦点。
- 中间查询结果会污染右侧面板。
- 聊天区和 Workspace 重复展示。
- 用户无法判断右侧内容是最终产物还是中间步骤。

结论：不采用。

### 4.3 复杂聚合看板

例如为多上下文分析生成 `multi.context` 大看板。

问题：

- 设计复杂。
- 容易变成第二套业务管理页。
- 和“复用 SaaS 页面组件”冲突。
- 当前阶段收益不确定。

结论：当前不做。

## 5. 推荐方案：投影策略上下文 + 显式投影信号

### 5.1 核心原则

```text
默认不投影查询结果。
审批必投影。
查询结果只有在本轮 run 的 projection policy 允许时才投影。
```

### 5.2 投影策略不是关键词判断，而是 Agent 可见的任务约束

前端和 backend 不直接用关键词猜测用户意图。

更稳妥的做法是：

1. 前端提交当前 workspace snapshot。
2. backend 构建 `WorkspaceRunContext`。
3. dynamic instructions 告诉模型 Workspace 的定位和投影规则。
4. 模型通过工具调用完成 ReAct。
5. runtime/event processor 根据明确策略决定是否投影。

第一版策略可以用结构化字段表达：

```python
workspace_projection_policy = {
    "query_projection": "explicit_only",
    "approval_projection": "always",
    "multi_context_projection": "suppress",
    "current_focus_surface": None,
}
```

### 5.3 推荐增加一个显式本地工具：request_workspace_projection

为了避免关键词匹配，也避免所有工具自动投影，可以给 Agent 一个轻量本地工具：

```python
@function_tool
async def request_workspace_projection(
    ctx: RunContextWrapper[WorkspaceRunContext],
    surface: Literal["project.list", "project.detail", "campaign.list", "material.list"],
    reason: str,
) -> str:
    """当且仅当用户需要在右侧 Workspace 查看/选择/校准业务结果时，请求投影当前任务焦点。"""
```

这个工具不直接修改业务数据，只记录投影意图：

```python
ctx.context.workspace_projection_requests.append({
    "surface": surface,
    "reason": reason,
    "created_at": now,
})
```

然后 event processor 在工具结果到达时判断：

```text
如果存在匹配的 workspace_projection_request
  -> 投影对应 tool result
否则
  -> 只进入 timeline / chat，不更新 Workspace
```

这个方案的优点：

- 不靠关键词。
- 模型基于语义和动态 instructions 决定是否请求投影。
- Runtime/Event Processor 仍是最终执行者。
- 查询工具可以继续作为 Agent 内部推理材料。
- 审批流程保持原有 `runtime.requires_action`。

### 5.4 更简单的第一版实现

如果不想立即增加新工具，可以先做较小版本：

```text
查询类 tool_output 默认不投影。
只有 projection registry 中标记为 requiresApproval 的工具继续走审批投影。
右侧浏览投影后续由 request_workspace_projection 补齐。
```

但这个版本会让“查看项目列表”暂时不更新右侧 Workspace，因此不建议作为最终状态。

建议第一版直接增加显式投影工具。

## 6. 推荐运行链路

### 6.1 浏览任务

用户：

```text
我想看一下项目列表
```

运行：

```text
Thought 内部判断：这是浏览/选择任务，Workspace 有价值
Action: list_projects
Observation: 返回项目列表
Action: request_workspace_projection(surface="project.list", reason="用户需要浏览项目列表")
Final Answer: 已在右侧展示项目库，共 N 个项目。你可以在右侧选择或 @mention 项目。
```

前端表现：

```text
右侧 Workspace 展示 ProjectCollectionView
聊天区只给概括，不逐条列项目
```

### 6.2 多上下文分析任务

用户：

```text
对比 test111 和 test-work 的投放情况
```

运行：

```text
Action: get_project_detail(test111)
Observation: ...
Action: list_campaigns(project_id=test111)
Observation: ...
Action: get_project_detail(test-work)
Observation: ...
Action: list_campaigns(project_id=test-work)
Observation: ...
Final Answer: 给出对比结论、差异、建议
```

不调用：

```text
request_workspace_projection
```

前端表现：

```text
右侧 Workspace 保持原状，不随着中间查询跳动
聊天区输出分析结果
```

### 6.3 审批任务

用户：

```text
创建一个预算 10w 的项目
```

运行：

```text
Action: create_project
runtime.requires_action
```

前端表现：

```text
右侧 Workspace 展示审批草稿表单
用户编辑/批准/拒绝
```

不需要 `request_workspace_projection`。

## 7. 实现建议

### 7.1 Agent Runtime

在 `WorkspaceRunContext` 增加：

```python
workspace_projection_requests: list[dict[str, Any]] = field(default_factory=list)
```

注册本地 function tool：

```python
request_workspace_projection
```

注意：这个工具是 runtime 本地工具，不是业务 MCP 工具。

### 7.2 Dynamic Instructions

在 ReAct prompt 中增加：

```text
- 查询工具返回的数据默认只作为推理材料。
- 只有当用户需要在右侧 Workspace 浏览、选择、校准结果时，调用 request_workspace_projection。
- 分析、诊断、对比、多上下文任务不要调用 request_workspace_projection，除非用户明确要求把某个结果放到右侧查看。
- 审批类操作不需要 request_workspace_projection，系统会自动投影审批草稿。
```

### 7.3 Event Processor

当前逻辑：

```text
tool_called -> setProjectionLoading
tool_output -> setProjectionReady
```

建议改为：

```text
tool_called:
  - 记录 tool_call timeline
  - 不默认 setProjectionLoading

tool_output:
  - 记录 tool result timeline
  - 如果 tool_call_id/surface 命中 projection request，则 setProjectionReady
  - 否则不更新 Workspace

runtime.requires_action:
  - 永远创建 approval draft / review projection
```

如果第一版无法可靠关联 `request_workspace_projection` 和某个 tool_call_id，可以用保守规则：

```text
同一 run 内最近一次 compatible tool_output + matching surface
```

后续再把关联做精确。

### 7.4 前端

前端继续负责：

```text
SDK event -> timeline
projection event -> Workspace store
approval event -> Workspace approval draft
```

不要在前端用关键词判断是否投影。

前端可以继续传：

```ts
workspaceProjection: {
  surface,
  mode,
  itemCount,
  alreadyVisible,
}
```

用于告诉模型右侧当前已有内容，避免重复复述。

## 8. 最小验收用例

### 用例 1：查看项目列表

输入：

```text
展示一下我的项目
```

期望：

```text
- Agent 调用 list_projects
- Agent 调用 request_workspace_projection(surface="project.list")
- 右侧展示项目库
- 聊天区只概括数量和可操作建议
```

### 用例 2：多项目对比

输入：

```text
对比 test111 和 test-work，哪个更值得继续投
```

期望：

```text
- Agent 可以调用多个查询工具
- 不调用 request_workspace_projection
- 右侧 Workspace 不跳动
- 聊天区输出对比结论
```

### 用例 3：创建项目审批

输入：

```text
创建一个德国市场 RPG 项目，预算 10w
```

期望：

```text
- create_project 触发 HITL
- runtime.requires_action
- 右侧展示项目创建审批草稿
```

### 用例 4：右侧已有投影后继续提问

输入：

```text
这些项目里哪个风险最高？
```

期望：

```text
- dynamic instructions 包含当前 workspaceProjection 摘要
- Agent 不逐条复述右侧项目列表
- 必要时调用工具补充事实
- 聊天区给风险判断和原因
```

## 9. 结论

推荐采用：

```text
审批投影：由 SDK HITL / runtime.requires_action 驱动，永远投影。
查询投影：默认不投影，由 Agent 显式调用 request_workspace_projection 请求投影。
分析/对比/多上下文：默认不投影中间工具结果。
```

这比关键词匹配更可靠，也比所有 tool_output 自动投影更符合 Workspace 的定位。

关键分层：

```text
Dynamic instructions：告诉模型什么时候应该请求投影
RunContextWrapper：保存本次 run 的投影策略和投影请求
Function tool：request_workspace_projection 显式表达投影意图
RunHooks/Event Processor：观察工具事件并执行投影状态机
Frontend Workspace：只渲染被确认投影的业务结果
```
