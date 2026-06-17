"""
HITL（Human-in-the-Loop）确认 MCP Server

核心设计（路径 B：自定义 MCP 工具）：
- Agent 调用 confirm_action 工具请求用户确认
- 工具内部创建 pending 的 HITL Output（落 task_outputs 表）
- 工具阻塞等待 asyncio.Event
- 前端通过 POST /api/agent/hitl/{id}/respond 响应
- 后端 set Event → 工具唤醒 → 返回用户选择给 Agent

并发安全（P0）：
- 每次 query 创建独立的 MCP server 实例
- task_id / user_id 通过闭包注入到工具函数
- 不同请求的工具函数是不同实例，互不影响，无需锁
- _pending_hitl 按 hitl_id（唯一 UUID）索引，天然隔离

为什么用路径 B 而非 SDK 原生 AskUserQuestion：
- HITL 请求就是一种 Output，复用 task_outputs 表和事件流
- 前端协议统一（都是 TaskOutputProduced 事件）
- 可审计（每次确认都有 DB 记录）
- 超时/取消/拒绝可控（asyncio.wait_for）
- 不耦合 SDK 内部机制
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

import aiosqlite
from claude_agent_sdk import create_sdk_mcp_server, tool

from app.config.settings import get_settings
from app.models.output import OutputStatus, OutputType, TaskOutput
from app.repositories.output_repo import OutputRepository

logger = logging.getLogger(__name__)

# 全局 HITL 等待表：hitl_id -> (Event, result_dict)
# 按 hitl_id（唯一 UUID）索引，不同请求的 HITL 天然隔离，并发安全
_pending_hitl: Dict[str, tuple[asyncio.Event, dict]] = {}

# HITL 超时（秒）
HITL_TIMEOUT = 300


def get_hitl_mcp_config(task_id: str, user_id: str) -> dict:
    """
    获取 HITL MCP 配置（每次 query 调用，闭包绑定本次请求上下文）

    Args:
        task_id: 本次请求任务 ID
        user_id: 本次请求用户 ID

    Returns:
        MCP Server 配置字典: {"hitl": <server_instance>}

    并发安全：
        每次调用创建独立的 server 和工具函数实例，
        task_id/user_id 通过闭包注入，多用户并发完全隔离。
    """

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
        task_id / user_id 通过闭包捕获，与本次请求绑定。

        Returns:
            MCP 标准响应：{"content": [...], "isError": bool}
        """
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

    server = create_sdk_mcp_server(name="hitl", version="1.0.0", tools=[confirm_action])
    return {"hitl": server}


def respond_to_hitl(hitl_id: str, approved: bool, feedback: str = "") -> bool:
    """
    响应 HITL 请求（由 HTTP 端点调用）

    Args:
        hitl_id: HITL 请求 ID（唯一 UUID，天然隔离）
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
