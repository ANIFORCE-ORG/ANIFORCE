"""Workspace 运行上下文。

本次 run 的本地上下文容器，供工具、dynamic instructions、审计使用。
LLM 默认看不到此对象，需要通过 dynamic instructions 注入 LLM 可见内容。

参见 notebooks/06-context/study_note.md §3.2 / §9。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkspaceRunContext:
    """本次 Agent run 的本地运行上下文。"""

    user_id: str
    session_id: str
    run_id: str
    auth_token: str = ""

    # LLM 可见上下文来源
    business_context_summary: str = ""
    ui_snapshot: dict[str, Any] = field(default_factory=dict)
    session_state: dict[str, Any] = field(default_factory=dict)

    # 运行元信息
    task_type: str = "conversation"

    # 当前 Run 的 Business Skill 状态。Agent/工具结构保持稳定，仅动态注入合同和裁剪工具。
    selected_skill_ids: list[str] = field(default_factory=list)
    selected_skill_versions: dict[str, str] = field(default_factory=dict)
    skill_slots: dict[str, Any] = field(default_factory=dict)
    skill_load_reason: str | None = None

    # HITL 审批用户编辑后的参数（按 tool call_id 关联）
    # MCP 工具执行前读取，覆盖原始 arguments
    approved_arguments_by_call_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    # 用户修改 diff 摘要，供 dynamic instructions 注入 LLM
    argument_diff: list[dict[str, Any]] = field(default_factory=list)

    # Agent 显式请求把某个业务结果投影到右侧 Workspace。
    # 查询工具默认只作为推理材料；只有记录了请求的 surface 才允许前端投影。
    workspace_projection_requests: list[dict[str, Any]] = field(default_factory=list)
