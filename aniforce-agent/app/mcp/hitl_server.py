"""
HITL（Human-in-the-Loop）确认 MCP Server

核心设计（路径 B：自定义 MCP 工具）：
- Agent 调用 confirm_action 工具请求用户确认
- 工具内部创建 pending 的 HITL Output（落 task_outputs 表）
- 工具阻塞等待 asyncio.Event
- 前端通过 POST /api/agent/hitl/{id}/respond 响应
- 后端 set Event → 工具唤醒 → 返回用户选择给 Agent

为什么用路径 B 而非 SDK 原生 AskUserQuestion：
- HITL 请求就是一种 Output，复用 task_outputs 表和事件流
- 前端协议统一（都是 TaskOutputProduced 事件）
- 可审计（每次确认都有 DB 记录）
- 超时/取消/拒绝可控（asyncio.wait_for）
- 不耦合 SDK 内部机制

关键约束：
- SDK MCP 工具函数签名固定（只收 args），task_id 通过环境变量 ANIFORCE_TASK_ID 传入
- DB 连接在工具内临时打开（工具函数无法访问 FastAPI 依赖注入）
- HITL 请求通过 business_event_adapter 已有的事件流出 SSE
  （工具调用产生 ToolUseBlock → adapter 推 TaskProgressUpdated；
   但 HITL 需要单独的 TaskOutputProduced 事件，所以工具内部直接写 DB，
   前端通过轮询 GET /tasks/{id}/outputs 或 SSE 的 TaskProgressUpdated 感知）
"""

import asyncio
import json
import logging
import os
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

import aiosqlite
from claude_agent_sdk import create_sdk_mcp_server, tool

from app.config.settings import get_settings
from app.models.output import OutputStatus, OutputType, TaskOutput
from app.repositories.output_repo import OutputRepository

logger = logging.getLogger(__name__)

# 全局 HITL 等待表：hitl_id -> (Event, result_dict)
# 工具阻塞在这里，HTTP 响应端点 set Event 并填 result
_pending_hitl: Dict[str, tuple[asyncio.Event, dict]] = {}

# 当前 task/user 上下文（SDK MCP 工具在主进程执行，读不了 subprocess 的 env）
# 用模块级全局变量 + Runtime 的 per-session 锁保证安全（query 顺序执行）
# 注意：不支持同一进程并发多 task（当前架构每个 SSE 请求独立 query，顺序执行）
_current_task_id: Optional[str] = None
_current_user_id: Optional[str] = None

# HITL 超时（秒）
HITL_TIMEOUT = 300


def set_hitl_context(task_id: str, user_id: str) -> None:
    """设置当前 HITL 上下文（由 AgentRuntime.query 在每次 query 前调用）

    ⚠️ 用全局变量而非 contextvars：SDK MCP 工具在独立 asyncio task 执行，
    contextvars 跨 task 不传递。靠 Runtime 的 per-session 锁保证不串。
    """
    global _current_task_id, _current_user_id
    _current_task_id = task_id
    _current_user_id = user_id


def _get_task_id() -> str:
    """获取当前 task_id"""
    if _current_task_id:
        return _current_task_id
    # 兜底：读环境变量（subprocess 工具场景）
    task_id = os.environ.get("ANIFORCE_TASK_ID")
    if not task_id:
        raise RuntimeError("task_id not set in HITL context (call set_hitl_context before query)")
    return task_id


def _get_user_id() -> str:
    """获取当前 user_id"""
    if _current_user_id:
        return _current_user_id
    user_id = os.environ.get("ANIFORCE_USER_ID")
    if not user_id:
        raise RuntimeError("user_id not set in HITL context")
    return user_id


@tool(
    "confirm_action",
    "请求用户确认一个操作（写操作前必须调用）。Agent 会暂停等待用户响应。",
    {
        "action": {"type": "string", "description": "要确认的操作类型：create_campaign/update_budget/等"},
        "summary": {"type": "string", "description": "操作的简要描述，给用户看的"},
        "details": {
            "type": "object",
            "description": "操作的具体参数，如 {campaign_name, budget, platform}",
        },
    },
)
async def confirm_action(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    请求用户确认操作

    Agent 调用此工具后会被阻塞，直到用户响应或超时。

    Returns:
        MCP 标准响应：{"content": [...], "isError": bool}
        content 里的 text 包含用户的选择：approved/rejected/timeout
    """
    task_id = _get_task_id()
    user_id = _get_user_id()
    hitl_id = f"hitl_{uuid.uuid4().hex[:16]}"

    action = args.get("action", "unknown")
    summary = args.get("summary", "")
    details = args.get("details", {})

    logger.info(f"[HITL {hitl_id}] Task {task_id} 请求确认: {action} - {summary}")

    # 1. 落库：创建 pending 的 HITL Output
    settings = get_settings()
    try:
        async with aiosqlite.connect(settings.TASK_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            output_repo = OutputRepository(db)
            output = TaskOutput(
                output_id=hitl_id,
                task_id=task_id,
                output_type=OutputType.HITL_REQUEST,
                category=action,
                content={
                    "action": action,
                    "summary": summary,
                    "details": details,
                    "hitlId": hitl_id,
                    "taskId": task_id,
                },
                confidence=None,
                importance="high",
                actionable=True,
                requires_review=True,
                status=OutputStatus.PENDING_REVIEW,
            )
            await output_repo.create(output)
            logger.info(f"[HITL {hitl_id}] 已落库，等待用户响应（超时 {HITL_TIMEOUT}s）")
    except Exception as e:
        logger.error(f"[HITL {hitl_id}] 落库失败: {e}", exc_info=True)
        return {
            "content": [{"type": "text", "text": f"HITL 落库失败: {e}"}],
            "isError": True,
        }

    # 2. 阻塞等待用户响应
    event = asyncio.Event()
    _pending_hitl[hitl_id] = (event, {})
    try:
        await asyncio.wait_for(event.wait(), timeout=HITL_TIMEOUT)
        result = _pending_hitl[hitl_id][1]
        approved = result.get("approved", False)
        feedback = result.get("feedback", "")

        if approved:
            msg = f"用户已确认操作：{action}。{('反馈：' + feedback) if feedback else ''}"
            logger.info(f"[HITL {hitl_id}] 用户确认通过")
        else:
            msg = f"用户拒绝了操作：{action}。{('原因：' + feedback) if feedback else ''}"
            logger.info(f"[HITL {hitl_id}] 用户拒绝")

        # 更新 Output 状态
        async with aiosqlite.connect(settings.TASK_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            output_repo = OutputRepository(db)
            new_status = OutputStatus.VERIFIED if approved else OutputStatus.CONFLICTED
            await output_repo.update_status(hitl_id, new_status, verified_by=user_id)

        return {
            "content": [{"type": "text", "text": msg}],
            "isError": not approved,
        }
    except asyncio.TimeoutError:
        logger.warning(f"[HITL {hitl_id}] 用户响应超时（{HITL_TIMEOUT}s）")
        # 更新为超时状态
        async with aiosqlite.connect(settings.TASK_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            output_repo = OutputRepository(db)
            await output_repo.update_status(hitl_id, OutputStatus.OUTDATED, verified_by=None)
        return {
            "content": [{"type": "text", "text": f"用户确认超时（{HITL_TIMEOUT}s），操作未执行"}],
            "isError": True,
        }
    finally:
        _pending_hitl.pop(hitl_id, None)


def respond_to_hitl(hitl_id: str, approved: bool, feedback: str = "") -> bool:
    """
    响应 HITL 请求（由 HTTP 端点调用）

    Args:
        hitl_id: HITL 请求 ID
        approved: 是否确认
        feedback: 用户反馈

    Returns:
        是否成功响应（HITL 请求存在且未超时）
    """
    if hitl_id not in _pending_hitl:
        logger.warning(f"[HITL {hitl_id}] 响应失败：请求不存在或已超时")
        return False

    event, result = _pending_hitl[hitl_id]
    result["approved"] = approved
    result["feedback"] = feedback
    event.set()
    logger.info(f"[HITL {hitl_id}] 已响应：approved={approved}")
    return True


def create_hitl_sdk_mcp_server():
    """创建 HITL SDK MCP Server"""
    return create_sdk_mcp_server(
        name="hitl",
        version="1.0.0",
        tools=[confirm_action],
    )


def get_hitl_mcp_config():
    """获取 HITL MCP 配置（用于 Runtime）"""
    return {"hitl": create_hitl_sdk_mcp_server()}
