#!/usr/bin/env python3
# %%
"""调试 Agent + Workspace 模式下的动态 instructions 上下文注入。

运行：
  UV_CACHE_DIR=./uv_cache uv run python notebooks/06-context/260702_01_dynamic_instructions_workspace_context_debug.py

验证点：
1. dynamic instructions 能否把 workspace 当前页面、面板、草稿编辑注入给 LLM
2. RunContextWrapper.context 是否能在工具中读取同一份本地上下文
3. ToolContext 是否能拿到 tool_name / tool_call_id / tool_arguments 元数据
4. 对照组：不注入 workspace context 时，模型是否无法准确感知工作台状态
5. 流式 run_streamed 下 dynamic instructions 是否同样生效
"""

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

from openai import AsyncOpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from agents import Agent, ModelSettings, RunContextWrapper, Runner, function_tool, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from agents.tool_context import ToolContext
from app.services.business_context_builder import BusinessContextBuilder

MODEL = "deepseek-v4-pro"
BASE_URL = "https://copilot.huya.info/api/openai/v1"
API_KEY = "sk-hvtAUe3lPjYQtwiZqLMfYg"

set_tracing_disabled(True)


class FakeProjectRepo:
    async def get_by_id(self, project_id: str) -> dict | None:
        projects = {
            "P001": {
                "id": "P001",
                "user_id": "user_001",
                "name": "ANIFORCE 双十一买量项目",
                "game_type": "二次元 RPG",
                "total_budget": 50000,
                "status": "draft",
            }
        }
        return projects.get(project_id)


class FakeCampaignRepo:
    async def get_by_id(self, campaign_id: str) -> dict | None:
        campaigns = {
            "C001": {
                "id": "C001",
                "name": "抖音信息流首测",
                "platform": "Douyin",
                "budget": 12000,
                "status": "running",
            },
            "C002": {
                "id": "C002",
                "name": "B站预约转化测试",
                "platform": "Bilibili",
                "budget": 8000,
                "status": "paused",
            },
        }
        return campaigns.get(campaign_id)


class FakeMaterialRepo:
    async def get_by_id(self, material_id: str) -> dict | None:
        materials = {
            "M001": {"id": "M001", "name": "角色 PV 15s", "type": "video"},
            "M002": {"id": "M002", "name": "战斗卖点横版图", "type": "image"},
        }
        return materials.get(material_id)


@dataclass
class WorkspaceRunContext:
    """本次 Agent run 的本地运行上下文。

    注意：这个对象本身不会自动发给 LLM；只有 dynamic instructions、input 或工具返回
    才能让 LLM 看到其中的内容。
    """

    user_id: str
    session_id: str
    run_id: str
    ui_snapshot: dict[str, Any]
    session_state: dict[str, Any]
    business_context_summary: str
    audit_events: list[dict[str, Any]] = field(default_factory=list)


def make_model() -> OpenAIChatCompletionsModel:
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIChatCompletionsModel(model=MODEL, openai_client=client)


def print_section(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88 + "\n")


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def workspace_instructions(ctx: RunContextWrapper[WorkspaceRunContext], agent: Agent[WorkspaceRunContext]) -> str:
    """动态 instructions：把当前 workspace 状态注入 LLM 可见上下文。"""
    snapshot = ctx.context.ui_snapshot
    draft_edits = snapshot.get("draftEdits") or {}
    selected_entities = snapshot.get("selectedEntities") or []
    return f"""
你是 ANIFORCE 的 Agent + Workspace 助手。

你正在和用户共同操作一个营销 SaaS 工作台。回答必须结合当前工作台状态，不要脱离用户所在页面。

# Backend Business Context
以下内容由 backend Session State Manager / BusinessContextBuilder 构建，是当前业务现场摘要：
{ctx.context.business_context_summary}

# Frontend Workspace Snapshot
- 当前路由：{snapshot.get("route")}
- 当前面板：{snapshot.get("activePanel")}
- 当前项目 ID：{snapshot.get("activeProjectId")}
- 当前 Campaign ID：{snapshot.get("activeCampaignId")}
- 当前选中实体：{pretty_json(selected_entities)}
- 当前草稿编辑：{pretty_json(draft_edits)}

# 行为规则
- 如果用户问“当前状态”“下一步”“缺什么”，必须优先分析当前 workspace snapshot。
- 如果草稿字段缺失，要明确指出缺失字段和建议补充项。
- 如果需要读取本地运行上下文，可调用 inspect_workspace_context 工具。
- 如果需要查看工具调用元数据，可调用 log_workspace_tool_context 工具。
- 不要编造 backend DB 中不存在的数据。
- 写操作、预算、上线、删除等高风险动作需要用户确认。
""".strip()


def plain_instructions(_ctx: RunContextWrapper[WorkspaceRunContext], _agent: Agent[WorkspaceRunContext]) -> str:
    """对照组：不注入 workspace 状态。"""
    return "你是 ANIFORCE 营销助手。请简洁回答用户问题。"


@function_tool
async def inspect_workspace_context(ctx: RunContextWrapper[WorkspaceRunContext]) -> str:
    """读取当前本地 WorkspaceRunContext，用于确认工具能访问页面、面板、草稿和业务摘要。"""
    snapshot = ctx.context.ui_snapshot
    draft = snapshot.get("draftEdits") or {}
    ctx.context.audit_events.append(
        {
            "event": "inspect_workspace_context",
            "route": snapshot.get("route"),
            "active_panel": snapshot.get("activePanel"),
        }
    )
    return pretty_json(
        {
            "user_id": ctx.context.user_id,
            "session_id": ctx.context.session_id,
            "run_id": ctx.context.run_id,
            "route": snapshot.get("route"),
            "active_panel": snapshot.get("activePanel"),
            "active_project_id": snapshot.get("activeProjectId"),
            "draft_edits": draft,
            "business_context_summary": ctx.context.business_context_summary,
        }
    )


@function_tool
async def log_workspace_tool_context(
    ctx: ToolContext[WorkspaceRunContext],
    note: Annotated[str, "本次记录工具上下文的原因"],
) -> str:
    """记录 ToolContext 元数据，用于对齐前端 tool_call.started/completed 时间线。"""
    event = {
        "event": "log_workspace_tool_context",
        "note": note,
        "tool_name": ctx.tool_name,
        "tool_call_id": ctx.tool_call_id,
        "tool_arguments": ctx.tool_arguments,
        "qualified_tool_name": ctx.qualified_tool_name,
        "route": ctx.context.ui_snapshot.get("route"),
        "active_panel": ctx.context.ui_snapshot.get("activePanel"),
    }
    ctx.context.audit_events.append(event)
    return pretty_json(event)


async def build_workspace_context() -> WorkspaceRunContext:
    """模拟现有链路：context_snapshot -> session_state -> BusinessContextBuilder -> run context。"""
    ui_snapshot = {
        "route": "/projects/P001?panel=project_draft",
        "activePanel": "project_draft",
        "activeProjectId": "P001",
        "activeCampaignId": None,
        "selectedEntities": [
            {"type": "campaign", "id": "C001"},
            {"type": "campaign", "id": "C002"},
        ],
        "draftEdits": {
            "project_name": "ANIFORCE 双十一买量项目",
            "campaign_name": "首发预约转化测试",
            "budget": 5000,
            "target_market": "JP",
            "channels": ["Douyin", "Bilibili"],
            "materials": [],
            "start_date": "2026-11-01",
            "end_date": None,
        },
    }
    session_state = {
        "mode": "project_management",
        "linked_entities": {
            "project_id": "P001",
            "campaign_ids": ["C001", "C002"],
            "material_ids": ["M001"],
        },
        "ui_snapshot": ui_snapshot,
        "summary": "用户正在项目管理模式中整理投放项目草稿，尚未确认落库。",
        "changelog": [
            {"entity_type": "project", "entity_id": "P001", "action": "opened"},
            {"entity_type": "campaign", "entity_id": "C001", "action": "selected"},
        ],
        "pending_actions": [
            {"id": "approve_campaign_draft", "action_type": "approval", "title": "确认创建投放草稿"}
        ],
    }
    builder = BusinessContextBuilder(
        project_repo=FakeProjectRepo(),
        campaign_repo=FakeCampaignRepo(),
        material_repo=FakeMaterialRepo(),
    )
    summary = await builder.build(session_state, user_id="user_001")
    return WorkspaceRunContext(
        user_id="user_001",
        session_id="session_workspace_debug",
        run_id="run_workspace_debug",
        ui_snapshot=ui_snapshot,
        session_state=session_state,
        business_context_summary=summary,
    )


def make_agent(instructions_fn) -> Agent[WorkspaceRunContext]:
    return Agent[WorkspaceRunContext](
        name="ANIFORCE Workspace Context Debugger",
        instructions=instructions_fn,
        model=make_model(),
        tools=[inspect_workspace_context, log_workspace_tool_context],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )


def print_new_items(result) -> None:
    print("\n【new_items】")
    for index, item in enumerate(result.new_items, 1):
        print(f"  {index}. type={item.type}")
        raw = getattr(item, "raw_item", None)
        if raw is not None:
            name = getattr(raw, "name", None)
            arguments = getattr(raw, "arguments", None)
            if name:
                print(f"     name={name}")
            if arguments:
                print(f"     arguments={arguments}")
        output = getattr(item, "output", None)
        if output:
            print(f"     output={str(output)[:300]}")


async def scenario_dynamic_instructions_awareness(ctx: WorkspaceRunContext) -> None:
    print_section("场景1：动态 instructions 注入 Workspace 状态")
    agent = make_agent(workspace_instructions)
    result = await Runner.run(
        agent,
        "请基于我当前工作台状态，说明我在哪个页面、当前草稿还缺什么，以及下一步应该做什么。",
        context=ctx,
        max_turns=5,
    )
    print("【final_output】")
    print(result.final_output)
    print_new_items(result)


async def scenario_tool_reads_run_context(ctx: WorkspaceRunContext) -> None:
    print_section("场景2：工具通过 RunContextWrapper 读取同一份 WorkspaceRunContext")
    agent = make_agent(workspace_instructions)
    result = await Runner.run(
        agent,
        "请调用 inspect_workspace_context 工具，然后根据工具结果说明当前 activePanel 和 draftEdits。",
        context=ctx,
        max_turns=6,
    )
    print("【final_output】")
    print(result.final_output)
    print_new_items(result)
    print("\n【context.audit_events】")
    print(pretty_json(ctx.audit_events))


async def scenario_tool_context_metadata(ctx: WorkspaceRunContext) -> None:
    print_section("场景3：ToolContext 元数据（tool_name / call_id / arguments）")
    agent = make_agent(workspace_instructions)
    result = await Runner.run(
        agent,
        "请调用 log_workspace_tool_context 工具，note 写：对齐前端工具调用时间线。然后解释你记录到了哪些工具元数据。",
        context=ctx,
        max_turns=6,
    )
    print("【final_output】")
    print(result.final_output)
    print_new_items(result)
    print("\n【context.audit_events】")
    print(pretty_json(ctx.audit_events))


async def scenario_without_dynamic_context(ctx: WorkspaceRunContext) -> None:
    print_section("场景4：严格对照组，不注入 Workspace 状态，也不暴露工具")
    agent = Agent[WorkspaceRunContext](
        name="ANIFORCE Plain Context Control",
        instructions=plain_instructions,
        model=make_model(),
        tools=[],
        model_settings=ModelSettings(parallel_tool_calls=False, store=False),
    )
    result = await Runner.run(
        agent,
        "请基于我当前工作台状态，说明我在哪个页面、当前草稿还缺什么，以及下一步应该做什么。",
        context=ctx,
        max_turns=3,
    )
    print("【final_output】")
    print(result.final_output)
    print("\n观察点：没有 dynamic instructions、没有 input 注入、没有工具返回时，LLM 默认看不到 ctx.context。")
    print_new_items(result)


async def scenario_streamed_dynamic_instructions(ctx: WorkspaceRunContext) -> None:
    print_section("场景5：run_streamed 下 dynamic instructions 同样生效")
    agent = make_agent(workspace_instructions)
    result = Runner.run_streamed(
        agent,
        "用 3 条要点概括我当前工作台状态。",
        context=ctx,
        max_turns=5,
    )
    print("【streaming output】")
    async for event in result.stream_events():
        if event.type == "raw_response_event":
            delta = getattr(event.data, "delta", None)
            if delta:
                print(delta, end="", flush=True)
    print("\n\n【final_output】")
    print(result.final_output)
    print(f"is_complete: {result.is_complete}")
    print_new_items(result)


async def run_safely(name: str, fn, ctx: WorkspaceRunContext) -> None:
    try:
        await fn(ctx)
    except Exception as exc:
        print_section(f"{name} 执行失败")
        print(f"错误类型: {type(exc).__name__}")
        print(f"错误信息: {exc}")
        print("说明: 本场景失败不影响其他场景，常见原因是上游模型 API 连接超时。")


async def main() -> None:
    ctx = await build_workspace_context()
    print_section("准备好的 BusinessContextBuilder 摘要")
    print(ctx.business_context_summary)
    print("\n【ui_snapshot】")
    print(pretty_json(ctx.ui_snapshot))

    scenarios = [
        ("场景1：动态 instructions 注入 Workspace 状态", scenario_dynamic_instructions_awareness),
        ("场景2：工具通过 RunContextWrapper 读取上下文", scenario_tool_reads_run_context),
        ("场景3：ToolContext 元数据", scenario_tool_context_metadata),
        ("场景4：对照组，不注入 Workspace 状态", scenario_without_dynamic_context),
        ("场景5：run_streamed 动态 instructions", scenario_streamed_dynamic_instructions),
    ]
    for name, fn in scenarios:
        await run_safely(name, fn, ctx)

    print("\n" + "=" * 88)
    print("所有场景调试流程结束")
    print("=" * 88)
    print("\n关键结论：")
    print("1. RunContextWrapper.context 是本地运行上下文，LLM 默认看不到。")
    print("2. dynamic instructions 是让 LLM 感知 workspace 状态的主通道。")
    print("3. 工具函数可以通过 RunContextWrapper/ToolContext 读取同一份上下文和工具元数据。")
    print("4. 生产中应保持 context_snapshot/session_state 为持久状态源，每次 run 重建 WorkspaceRunContext。")


if __name__ == "__main__":
    asyncio.run(main())
