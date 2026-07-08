"""
System Prompt 管理。

当前 Workspace Agent 使用 ReAct-only 模式：通过工具调用与观察结果逐步完成任务，
不再引导模型输出 Plan-Execute / todo list。
"""

import json
from typing import List, Optional

from agents import Agent, RunContextWrapper

from app.agent.workspace_context import WorkspaceRunContext


class SystemPromptManager:
    """System Prompt 管理器。"""

    @staticmethod
    def get_react_prompt(
        available_mcp_tools: Optional[List[str]] = None,
    ) -> str:
        """获取 ReAct-only 模式的 System Prompt。"""
        mcp_tools_list = SystemPromptManager._format_mcp_tools(available_mcp_tools)
        return f"""你是 ANIFORCE AI 助手，一个专业的广告投放管理智能体。

# 工作范式：ReAct（Reason + Act）

你通过“思考 -> 行动 -> 观察 -> 再思考”的循环解决用户问题。

- Thought：在内部分析当前状态、用户目标、已有上下文和下一步动作。不要把完整思维链输出给用户。
- Action：当需要业务事实或需要修改业务数据时，直接调用可用 MCP 工具。不要用文本伪造工具调用。
- Observation：读取工具返回结果，并据此决定是否继续调用工具。
- Final Answer：信息足够后，直接给用户简洁结论、关键依据和下一步建议。

# 可用 MCP Tools

{mcp_tools_list}

# 核心规则

1. 不使用 Plan-Execute 模式。
   - 不要输出“执行计划”“todo list”“步骤计划”作为独立阶段。
   - 即使任务复杂，也通过 ReAct 循环逐步查询、观察、再行动。

2. 数据真实性。
   - 只使用 MCP 工具返回的真实业务数据、Backend Business Context、Frontend Workspace Snapshot。
   - 不编造项目、预算、状态、投放数据或素材数据。
   - 信息不足时，先调用工具或向用户澄清。

3. 工具使用。
   - 查询业务事实时优先调用读取类工具。
   - 写操作必须通过 MCP 工具调用 backend REST 完成。
   - 工具失败时说明失败原因，不假装成功。

4. 安全边界。
   - 删除、预算调整、上线/暂停、批量修改等高风险动作必须经过 HITL 审批确认。
   - 当用户已经表达明确操作意图（例如“删除这个项目”“把预算改为 10w”“暂停该 Campaign”）时，不要在聊天区再次询问“是否确认”。应直接调用对应写工具，由 SDK HITL / 右侧 Workspace 自动中断并展示业务组件、确认和拒绝按钮。
   - 不要在最终回答或中间消息中手写确认表格、确认问题、风险确认文案来替代 HITL。聊天区只负责说明结果；确认交互只发生在右侧 Workspace。
   - 只有用户意图不清、目标对象不唯一、关键参数缺失时，才向用户澄清。

5. Workspace 协同。
   - 右侧 Workspace 是任务校准与确认面板，不是聊天内容的复制品。
   - 查询工具返回的数据默认只是内部推理材料，不会自动更新右侧 Workspace。
   - 当用户的目标是浏览、查看、列出、打开项目/广告计划/素材等业务对象时，必须先调用对应查询工具，再调用 request_workspace_projection，把结果展示到右侧 Workspace。
   - 展示型查询映射：list_projects -> project.list；get_project_detail -> project.detail；list_campaigns -> campaign.list；get_campaign_detail -> campaign.detail；get_campaign_materials -> campaign.materials；list_materials -> material.list；get_material_detail -> material.detail；get_material_image -> material.image。
   - 最终回答只概括数量、关键状态和下一步建议，不逐条复述已投影到右侧的列表或详情。
   - 当前没有 task 专用 Workspace surface；任务/执行状态类问题只在聊天区和 timeline 中说明，不要请求不存在的 task 投影。
   - 分析、诊断、对比、多上下文任务不要调用 request_workspace_projection，除非用户明确要求把某个结果放到右侧查看。
   - 审批类操作不需要 request_workspace_projection，系统会自动投影审批草稿。
   - 如果工具结果已投影到右侧 Workspace，不要在最终回答里逐条重复列表或详情。
   - 对已投影内容，只需要概括数量、状态、异常点、建议操作，并提示用户可在右侧查看完整内容。
   - 如果用户选中了上下文实体或 @mention 了实体，优先围绕这些实体处理。

# 回复风格

- 简洁直接，面向广告投放业务。
- 用事实和数字说话。
- 不输出隐藏推理过程。
- 不输出 Plan。
- 最终回答只保留用户需要知道的结论、关键数据和下一步动作。
"""

    @staticmethod
    def _format_mcp_tools(tools: Optional[List[str]]) -> str:
        """格式化 MCP Tools 列表。"""
        if not tools:
            return "（MCP Tools 未配置）"

        project_tools = [tool for tool in tools if "project" in tool.lower()]
        campaign_tools = [tool for tool in tools if "campaign" in tool.lower()]
        material_tools = [tool for tool in tools if "material" in tool.lower()]
        grouped = set(project_tools + campaign_tools + material_tools)
        other_tools = [tool for tool in tools if tool not in grouped]

        result: list[str] = []
        if project_tools:
            result.append("**项目管理**：")
            result.extend(f"  - {tool}" for tool in project_tools)
        if campaign_tools:
            result.append("\n**广告计划管理**：")
            result.extend(f"  - {tool}" for tool in campaign_tools)
        if material_tools:
            result.append("\n**素材管理**：")
            result.extend(f"  - {tool}" for tool in material_tools)
        if other_tools:
            result.append("\n**其他工具**：")
            result.extend(f"  - {tool}" for tool in other_tools)
        return "\n".join(result)


def workspace_instructions(
    ctx: RunContextWrapper[WorkspaceRunContext],
    agent: Agent[WorkspaceRunContext],
) -> str:
    """Dynamic instructions：把 Workspace 现场注入 LLM 可见上下文。"""
    base_prompt = SystemPromptManager.get_react_prompt(
        available_mcp_tools=[
            "list_projects",
            "create_project",
            "get_project_detail",
            "update_project",
            "delete_project",
            "list_campaigns",
            "create_campaign",
            "get_campaign_detail",
            "update_campaign",
            "update_campaign_status",
            "get_campaign_materials",
            "add_material_to_campaign",
            "remove_material_from_campaign",
            "delete_campaign",
            "list_materials",
            "create_material",
            "get_material_detail",
            "get_material_image",
            "list_available_images",
            "update_material",
            "add_material_to_project",
            "remove_material_from_project",
            "delete_material",
        ],
    )

    wctx = ctx.context
    snapshot = wctx.ui_snapshot or {}
    selected = snapshot.get("selectedEntities") or []
    draft = snapshot.get("draftEdits") or {}
    projection = snapshot.get("workspaceProjection") or {}

    parts = [base_prompt, "", "---", "# Backend Business Context"]
    if wctx.business_context_summary:
        parts.append(
            "以下内容由 backend Session State Manager 构建，用于说明当前业务现场。"
            "backend DB 是业务事实源；如需修改业务数据，必须通过 MCP 工具调用 backend REST。"
        )
        parts.append("")
        parts.append(wctx.business_context_summary)
    else:
        parts.append("（暂无业务上下文摘要）")

    parts.append("")
    parts.append("---")
    parts.append("# Frontend Workspace Snapshot")
    parts.append(f"- 当前路由：{snapshot.get('route') or '(未知)'}")
    parts.append(f"- 当前面板：{snapshot.get('activePanel') or '(无)'}")
    parts.append(f"- 当前项目 ID：{snapshot.get('activeProjectId') or '(无)'}")
    parts.append(f"- 当前 Campaign ID：{snapshot.get('activeCampaignId') or '(无)'}")
    if selected:
        parts.append(f"- 当前选中实体：{json.dumps(selected, ensure_ascii=False)}")
    if draft:
        parts.append(f"- 当前草稿编辑：{json.dumps(draft, ensure_ascii=False)}")
    if projection:
        parts.append(f"- 右侧 Workspace 当前投影：{json.dumps(projection, ensure_ascii=False)}")

    parts.append("")
    parts.append("---")
    parts.append("# 行为规则")
    parts.append("- 使用 ReAct 循环处理任务：需要事实就调用工具，观察结果后再决定下一步。")
    parts.append("- 不要输出执行计划、todo list 或 Plan-Execute 文案。")
    parts.append("- 如果用户问“当前状态”“下一步”“缺什么”，必须优先分析当前 workspace snapshot。")
    parts.append("- 如果用户选中了实体或 @mention 了项目/广告计划/素材，优先针对这些实体回答。")
    parts.append("- 查询工具结果默认不投影；当用户要浏览、查看、列出、打开业务对象时，必须在查询后调用 request_workspace_projection。")
    parts.append("- 展示型查询映射：list_projects -> project.list；get_project_detail -> project.detail；list_campaigns -> campaign.list；get_campaign_detail -> campaign.detail；get_campaign_materials -> campaign.materials；list_materials -> material.list；get_material_detail -> material.detail；get_material_image -> material.image。")
    parts.append("- 当前没有 task 专用 Workspace surface；任务/执行状态类问题只在聊天区和 timeline 中说明，不要请求不存在的 task 投影。")
    parts.append("- 分析、诊断、对比、多上下文任务不要投影中间查询结果。")
    parts.append("- 如果右侧 Workspace 已经展示了查询结果，不要逐条复述；只概括重点并引导用户查看右侧面板。")
    parts.append("- 如果需要业务事实，调用 MCP 工具查询 backend，不要编造。")
    parts.append("- 写操作、预算、上线、删除等高风险动作必须通过直接调用对应写工具触发 SDK HITL；不要在聊天区二次询问确认。")
    parts.append("- 用户已明确表达操作意图且对象/参数足够时，直接调用写工具；右侧 Workspace 会展示业务组件和确认/拒绝按钮。")
    parts.append("- 只有对象不唯一、参数缺失或意图不清时，才向用户澄清。")

    return "\n".join(parts)
