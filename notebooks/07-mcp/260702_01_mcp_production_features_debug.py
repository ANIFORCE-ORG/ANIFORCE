"""MCP 生产特性调试

重点验证 3 个生产级特性：
1. require_approval - 高风险工具触发 HITL 审批
2. tool_filter - 基于角色动态筛选工具
3. failure_error_function - 自定义错误格式化 + 脱敏 + 日志

调试基线：
- 模型：deepseek-v4-pro
- 供应商：copilot.huya.info
- MCP Server：本地 FastMCP mock server
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from agents import Agent, Runner
from agents.mcp import (
    MCPServerStreamableHttp,
    MCPToolMetaContext,
    ToolFilterContext,
    create_static_tool_filter,
)
from agents.model_settings import ModelSettings
from mcp.server.fastmcp import Context, FastMCP
from openai import AsyncOpenAI
from starlette.applications import Starlette
from starlette.routing import Mount
from uvicorn import Config, Server


# ============ 调试基线配置 ============

MODEL = "deepseek-v4-pro"
BASE_URL = "https://copilot.huya.info/api/openai/v1"
API_KEY = "sk-hvtAUe3lPjYQtwiZqLMfYg"


def make_model():
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=0)
    return OpenAIChatCompletionsModel(model=MODEL, openai_client=client)


# ============ Mock FastMCP Server ============

mcp_mock = FastMCP("MCP Production Features Test")


@mcp_mock.tool()
async def list_projects(ctx: Context, limit: int = 20) -> str:
    """列出项目（安全的查询操作）"""
    try:
        meta = ctx.request_context.meta if hasattr(ctx.request_context, 'meta') else {}
        if hasattr(meta, '__dict__'):
            meta = meta.__dict__
        user_id = meta.get("user_id", "anonymous") if isinstance(meta, dict) else "anonymous"
    except:
        user_id = "anonymous"
    return json.dumps(
        {
            "status": "success",
            "user_id": user_id,
            "projects": [
                {"id": "P001", "name": "ANIFORCE 双十一买量项目"},
                {"id": "P002", "name": "新游戏预约转化测试"},
            ],
        },
        ensure_ascii=False,
    )


@mcp_mock.tool()
async def get_project_detail(ctx: Context, project_id: str) -> str:
    """获取项目详情（安全的查询操作）"""
    try:
        meta = ctx.request_context.meta if hasattr(ctx.request_context, 'meta') else {}
        if hasattr(meta, '__dict__'):
            meta = meta.__dict__
        user_id = meta.get("user_id", "anonymous") if isinstance(meta, dict) else "anonymous"
    except:
        user_id = "anonymous"
    return json.dumps(
        {
            "status": "success",
            "user_id": user_id,
            "project": {
                "id": project_id,
                "name": "ANIFORCE 双十一买量项目",
                "budget": 50000,
                "status": "draft",
            },
        },
        ensure_ascii=False,
    )


@mcp_mock.tool()
async def create_project(ctx: Context, name: str, budget: float) -> str:
    """创建项目（高风险写操作，需要审批）"""
    try:
        meta = ctx.request_context.meta if hasattr(ctx.request_context, 'meta') else {}
        if hasattr(meta, '__dict__'):
            meta = meta.__dict__
        user_id = meta.get("user_id", "anonymous") if isinstance(meta, dict) else "anonymous"
    except:
        user_id = "anonymous"
    return json.dumps(
        {
            "status": "success",
            "message": f"项目已创建：{name}，预算 ¥{budget}",
            "user_id": user_id,
            "project_id": "P003",
        },
        ensure_ascii=False,
    )


@mcp_mock.tool()
async def delete_project(ctx: Context, project_id: str) -> str:
    """删除项目（高风险操作，需要审批）"""
    try:
        meta = ctx.request_context.meta if hasattr(ctx.request_context, 'meta') else {}
        if hasattr(meta, '__dict__'):
            meta = meta.__dict__
        user_id = meta.get("user_id", "anonymous") if isinstance(meta, dict) else "anonymous"
    except:
        user_id = "anonymous"
    return json.dumps(
        {
            "status": "success",
            "message": f"项目 {project_id} 已删除",
            "user_id": user_id,
        },
        ensure_ascii=False,
    )


@mcp_mock.tool()
async def simulate_failure(ctx: Context, error_type: str = "generic") -> str:
    """模拟工具调用失败，用于测试 failure_error_function"""
    if error_type == "unauthorized":
        raise PermissionError("Unauthorized: 当前用户无权限执行此操作")
    if error_type == "notfound":
        raise ValueError("NotFound: 资源不存在")
    raise RuntimeError("模拟的通用错误")


# Mock server app（直接用 FastMCP 的 streamable_http_app，不再包装）
starlette_app = mcp_mock.streamable_http_app()


# ============ RunContext ============


@dataclass
class MockRunContext:
    user_id: str
    user_role: str  # viewer / editor / admin
    session_id: str


# ============ 辅助函数 ============


def print_section(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def print_new_items(result) -> None:
    print("\n【new_items】")
    for idx, item in enumerate(result.new_items, 1):
        print(f"  {idx}. type={item.type}")
        if item.type == "tool_call_item":
            print(f"     tool_name={item.tool_name}")
            print(f"     call_id={item.call_id}")
        elif item.type == "tool_call_output_item":
            output_str = str(item.output)
            if len(output_str) > 200:
                output_str = output_str[:200] + "..."
            print(f"     output={output_str}")


async def start_mock_server():
    """启动 Mock MCP Server"""
    config = Config(app=starlette_app, host="127.0.0.1", port=18888, log_level="error")
    server = Server(config)
    await server.serve()


# ============ 场景1：require_approval - 高风险工具触发审批 ============


async def scenario_require_approval():
    print_section("场景1：require_approval - 高风险工具触发 HITL 审批")

    ctx = MockRunContext(user_id="user_001", user_role="admin", session_id="session_001")

    def meta_resolver(mcp_ctx: MCPToolMetaContext) -> dict[str, str] | None:
        return {"user_id": ctx.user_id, "session_id": ctx.session_id}

    async with MCPServerStreamableHttp(
        name="Test MCP",
        params={"url": "http://127.0.0.1:18888/mcp", "timeout": 10},
        cache_tools_list=True,
        tool_meta_resolver=meta_resolver,
        require_approval={
            "always": {"tool_names": ["create_project", "delete_project"]},
            "never": {"tool_names": ["list_projects", "get_project_detail"]},
        },
    ) as server:
        agent = Agent[MockRunContext](
            name="MCP Approval Test Agent",
            instructions="你是一个项目管理助手。用户要求创建项目时，调用 create_project 工具。",
            mcp_servers=[server],
            model=make_model(),
            model_settings=ModelSettings(parallel_tool_calls=False),
        )

        print("\n【子场景1.1：安全工具，不触发审批】")
        result = await Runner.run(agent, "列出我的项目", context=ctx, max_turns=3)
        print(f"【final_output】\n{result.final_output}")
        print(f"【interruptions】{result.interruptions}")
        print_new_items(result)

        print("\n【子场景1.2：高风险工具，触发审批 - 批准】")
        result = Runner.run_streamed(
            agent, "创建一个名为'测试项目'预算5000的新项目", context=ctx, max_turns=3
        )

        # 流式消费到审批暂停
        async for event in result.stream_events():
            if event.type == "run_item_stream_event" and event.item.type == "tool_call_item":
                print(f"【工具调用】{event.item.tool_name}")

        # 检查是否暂停
        if result.interruptions:
            print(f"【暂停】需要审批: {len(result.interruptions)} 个")
            for i, interruption in enumerate(result.interruptions):
                print(f"  {i+1}. tool={interruption.tool_name}")
                print(f"     arguments={interruption.arguments}")

            # 批准
            state = result.to_state()
            for item in result.interruptions:
                state.approve(item)
            print("【批准】已批准所有工具调用，继续运行...")

            # 继续运行
            result = Runner.run_streamed(agent, state, context=ctx)
            async for event in result.stream_events():
                pass

        print(f"【final_output】\n{result.final_output}")
        print(f"【is_complete】{result.is_complete}")
        print_new_items(result)

        print("\n【子场景1.3：高风险工具，触发审批 - 拒绝】")
        result = Runner.run_streamed(
            agent, "删除项目 P001", context=ctx, max_turns=3
        )

        async for event in result.stream_events():
            if event.type == "run_item_stream_event" and event.item.type == "tool_call_item":
                print(f"【工具调用】{event.item.tool_name}")

        if result.interruptions:
            print(f"【暂停】需要审批: {len(result.interruptions)} 个")
            for i, interruption in enumerate(result.interruptions):
                print(f"  {i+1}. tool={interruption.tool_name}")

            # 拒绝
            state = result.to_state()
            for item in result.interruptions:
                state.reject(item, rejection_message="管理员拒绝了删除操作，该项目正在使用中。")
            print("【拒绝】已拒绝所有工具调用，继续运行...")

            result = Runner.run_streamed(agent, state, context=ctx)
            async for event in result.stream_events():
                pass

        print(f"【final_output】\n{result.final_output}")
        print(f"【is_complete】{result.is_complete}")
        print_new_items(result)


# ============ 场景2：tool_filter - 基于角色动态筛选工具 ============


async def scenario_tool_filter():
    print_section("场景2：tool_filter - 基于角色动态筛选工具（RBAC）")

    def meta_resolver(mcp_ctx: MCPToolMetaContext) -> dict[str, str] | None:
        run_ctx = mcp_ctx.run_context.context
        return {"user_id": run_ctx.user_id, "session_id": run_ctx.session_id}

    async def role_based_filter(filter_ctx: ToolFilterContext, tool) -> bool:
        """基于用户角色动态筛选工具"""
        run_ctx = filter_ctx.run_context.context
        user_role = run_ctx.user_role

        # viewer 只能查询
        if user_role == "viewer":
            return tool.name.startswith("list_") or tool.name.startswith("get_")

        # editor 可以创建，但不能删除
        if user_role == "editor":
            return not tool.name.startswith("delete_")

        # admin 全部工具
        return True

    async with MCPServerStreamableHttp(
        name="Test MCP",
        params={"url": "http://127.0.0.1:18888/mcp", "timeout": 10},
        cache_tools_list=True,
        tool_meta_resolver=meta_resolver,
        tool_filter=role_based_filter,
    ) as server:
        print("\n【子场景2.1：viewer 角色，只能看到查询工具】")
        ctx_viewer = MockRunContext(
            user_id="user_viewer", user_role="viewer", session_id="session_viewer"
        )

        agent_viewer = Agent[MockRunContext](
            name="Viewer Agent",
            instructions="你是一个只读助手。",
            mcp_servers=[server],
            model=make_model(),
            model_settings=ModelSettings(parallel_tool_calls=False),
        )

        # 列出可用工具（需要通过 Runner 触发 tool_filter）
        result = await Runner.run(
            agent_viewer,
            "列出我的项目",
            context=ctx_viewer,
            max_turns=3,
        )
        # 从 new_items 中提取工具名
        tools = []
        for item in result.new_items:
            if item.type == "tool_call_item":
                tools.append(item.tool_name)
        print(f"【可用工具】{tools}")
        print(f"【验证】viewer 是否只能看到 list_* / get_* 工具：", end="")
        if tools and all(t.startswith("list_") or t.startswith("get_") for t in tools):
            print("✅ 通过")
        else:
            print(f"❌ 失败 (tools={tools})")

        print("\n【子场景2.2：editor 角色，可以创建但不能删除】")
        ctx_editor = MockRunContext(
            user_id="user_editor", user_role="editor", session_id="session_editor"
        )

        agent_editor = Agent[MockRunContext](
            name="Editor Agent",
            instructions="你是一个编辑助手。",
            mcp_servers=[server],
            model=make_model(),
            model_settings=ModelSettings(parallel_tool_calls=False),
        )

        result = await Runner.run(
            agent_editor,
            "创建一个名为'测试项目A'预算1000的项目",
            context=ctx_editor,
            max_turns=3,
        )
        tools = []
        for item in result.new_items:
            if item.type == "tool_call_item":
                tools.append(item.tool_name)
        print(f"【可用工具】{tools}")
        print(f"【验证】editor 是否能看到 create_* 但看不到 delete_*：", end="")
        has_create = any(t.startswith("create_") for t in tools)
        has_delete = any(t.startswith("delete_") for t in tools)
        if has_create and not has_delete:
            print("✅ 通过")
        else:
            print(f"❌ 失败 (has_create={has_create}, has_delete={has_delete})")

        print("\n【子场景2.3：admin 角色，可以看到全部工具】")
        ctx_admin = MockRunContext(
            user_id="user_admin", user_role="admin", session_id="session_admin"
        )

        agent_admin = Agent[MockRunContext](
            name="Admin Agent",
            instructions="你是一个管理员助手。",
            mcp_servers=[server],
            model=make_model(),
            model_settings=ModelSettings(parallel_tool_calls=False),
        )

        result = await Runner.run(
            agent_admin,
            "删除项目 P999",
            context=ctx_admin,
            max_turns=3,
        )
        tools = []
        for item in result.new_items:
            if item.type == "tool_call_item":
                tools.append(item.tool_name)
        print(f"【可用工具】{tools}")
        print(f"【验证】admin 是否能看到所有工具（包括 delete_*）：", end="")
        has_delete = any(t.startswith("delete_") for t in tools)
        if has_delete:
            print("✅ 通过")
        else:
            print("❌ 失败")


# ============ 场景3：failure_error_function - 自定义错误格式化 ============


async def scenario_failure_error_function():
    print_section("场景3：failure_error_function - 自定义错误格式化 + 脱敏 + 日志")

    ctx = MockRunContext(user_id="user_001", user_role="admin", session_id="session_001")

    def meta_resolver(mcp_ctx: MCPToolMetaContext) -> dict[str, str] | None:
        return {"user_id": ctx.user_id, "session_id": ctx.session_id}

    error_logs = []

    def custom_error_formatter(error: Exception, tool_name: str, arguments: dict) -> str:
        """自定义错误格式化器"""
        # 记录日志
        error_logs.append(
            {
                "tool_name": tool_name,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "arguments": arguments,
            }
        )
        print(
            f"【错误日志】tool={tool_name}, error={type(error).__name__}, message={str(error)}"
        )

        # 脱敏 + 用户友好提示
        if "Unauthorized" in str(error) or isinstance(error, PermissionError):
            return "当前用户无权限执行此操作，请联系管理员。"
        if "NotFound" in str(error):
            return "资源未找到，请检查 ID 是否正确。"
        return "工具调用失败，请稍后重试或联系技术支持。"

    async with MCPServerStreamableHttp(
        name="Test MCP",
        params={"url": "http://127.0.0.1:18888/mcp", "timeout": 10},
        cache_tools_list=True,
        tool_meta_resolver=meta_resolver,
        failure_error_function=custom_error_formatter,
    ) as server:
        agent = Agent[MockRunContext](
            name="Error Handling Agent",
            instructions="你是一个测试助手。调用 simulate_failure 工具测试错误处理。",
            mcp_servers=[server],
            model=make_model(),
            model_settings=ModelSettings(parallel_tool_calls=False),
        )

        print("\n【子场景3.1：Unauthorized 错误】")
        result = await Runner.run(
            agent, "调用 simulate_failure 工具，error_type=unauthorized", context=ctx, max_turns=3
        )
        print(f"【final_output】\n{result.final_output}")
        print_new_items(result)

        print("\n【子场景3.2：NotFound 错误】")
        result = await Runner.run(
            agent, "调用 simulate_failure 工具，error_type=notfound", context=ctx, max_turns=3
        )
        print(f"【final_output】\n{result.final_output}")
        print_new_items(result)

        print("\n【子场景3.3：通用错误】")
        result = await Runner.run(
            agent, "调用 simulate_failure 工具，error_type=generic", context=ctx, max_turns=3
        )
        print(f"【final_output】\n{result.final_output}")
        print_new_items(result)

        print("\n【错误日志汇总】")
        for i, log in enumerate(error_logs, 1):
            print(f"  {i}. {log}")


# ============ 场景4：静态工具筛选 ============


async def scenario_static_tool_filter():
    print_section("场景4：静态工具筛选（create_static_tool_filter）")

    ctx = MockRunContext(user_id="user_001", user_role="admin", session_id="session_001")

    def meta_resolver(mcp_ctx: MCPToolMetaContext) -> dict[str, str] | None:
        return {"user_id": ctx.user_id, "session_id": ctx.session_id}

    print("\n【子场景4.1：allowed_tool_names - 只允许查询工具】")
    async with MCPServerStreamableHttp(
        name="Test MCP",
        params={"url": "http://127.0.0.1:18888/mcp", "timeout": 10},
        cache_tools_list=True,
        tool_meta_resolver=meta_resolver,
        tool_filter=create_static_tool_filter(
            allowed_tool_names=["list_projects", "get_project_detail"]
        ),
    ) as server:
        agent = Agent[MockRunContext](
            name="Static Filter Agent",
            instructions="你是一个测试助手。",
            mcp_servers=[server],
            model=make_model(),
        )
        tools = []
        if agent.mcp_servers:
            for s in agent.mcp_servers:
                try:
                    mcp_tools = await s.list_tools()
                    tools.extend([t.name for t in mcp_tools])
                except:
                    pass
        print(f"【可用工具】{tools}")
        print(f"【验证】是否只有 list_projects 和 get_project_detail：", end="")
        if set(tools) == {"list_projects", "get_project_detail"}:
            print("✅ 通过")
        else:
            print(f"❌ 失败")

    print("\n【子场景4.2：blocked_tool_names - 阻止删除工具】")
    async with MCPServerStreamableHttp(
        name="Test MCP",
        params={"url": "http://127.0.0.1:18888/mcp", "timeout": 10},
        cache_tools_list=True,
        tool_meta_resolver=meta_resolver,
        tool_filter=create_static_tool_filter(blocked_tool_names=["delete_project"]),
    ) as server:
        agent = Agent[MockRunContext](
            name="Static Filter Agent",
            instructions="你是一个测试助手。",
            mcp_servers=[server],
            model=make_model(),
        )
        tools = []
        if agent.mcp_servers:
            for s in agent.mcp_servers:
                try:
                    mcp_tools = await s.list_tools()
                    tools.extend([t.name for t in mcp_tools])
                except:
                    pass
        print(f"【可用工具】{tools}")
        print(f"【验证】是否没有 delete_project：", end="")
        if "delete_project" not in tools:
            print("✅ 通过")
        else:
            print("❌ 失败")


# ============ 主流程 ============


async def run_safely(name: str, fn) -> None:
    try:
        await fn()
    except Exception as exc:
        print_section(f"{name} 执行失败")
        print(f"错误类型: {type(exc).__name__}")
        print(f"错误信息: {exc}")


async def main() -> None:
    # 启动 Mock MCP Server
    print("启动 Mock MCP Server（127.0.0.1:18888）...")
    server_task = asyncio.create_task(start_mock_server())
    await asyncio.sleep(1)  # 等待 server 启动

    try:
        scenarios = [
            ("场景1：require_approval", scenario_require_approval),
            ("场景2：tool_filter", scenario_tool_filter),
            ("场景3：failure_error_function", scenario_failure_error_function),
            ("场景4：静态工具筛选", scenario_static_tool_filter),
        ]
        for name, fn in scenarios:
            await run_safely(name, fn)

        print("\n" + "=" * 88)
        print("所有场景调试流程结束")
        print("=" * 88)
        print("\n关键结论：")
        print("1. require_approval 可以在高风险工具上触发 HITL 审批，支持批准/拒绝。")
        print("2. tool_filter 支持动态筛选，可实现基于角色的工具权限（RBAC）。")
        print("3. failure_error_function 可以自定义错误格式化、记录日志、脱敏敏感信息。")
        print("4. create_static_tool_filter 适合简单场景，动态 filter 适合复杂 RBAC。")

    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
