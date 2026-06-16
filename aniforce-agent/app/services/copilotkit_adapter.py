"""
CopilotKit Adapter - AG-UI 协议适配器

核心职责：
- 将 Claude SDK 消息流转换为 AG-UI 协议事件
- 支持 CopilotKit 前端组件
- 实现 SSE 流式推送

AG-UI 事件类型：
- TEXT_MESSAGE_START - 文本消息开始
- TEXT_MESSAGE_CONTENT - 文本内容块
- TEXT_MESSAGE_END - 文本消息结束
- TOOL_CALL_START - 工具调用开始
- TOOL_CALL_ARGS - 工具参数
- TOOL_CALL_RESULT - 工具结果
- RUN_FINISHED - 运行完成
- ERROR - 错误事件

参考：学习手册第 6 章 Streaming
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict
from uuid import uuid4

logger = logging.getLogger(__name__)


class CopilotKitAdapter:
    """CopilotKit AG-UI 协议适配器"""

    @staticmethod
    async def stream_ag_ui_events(
        task_id: str,
        sdk_messages: AsyncGenerator[Any, None],
    ) -> AsyncGenerator[str, None]:
        """
        将 Claude SDK 消息流转换为 AG-UI SSE 事件

        Args:
            task_id: 任务 ID（用作 runId）
            sdk_messages: Claude SDK 消息流

        Yields:
            SSE 格式字符串（"event: TYPE\ndata: JSON\n\n"）
        """
        try:
            async for message in sdk_messages:
                # 转换消息为 AG-UI 事件
                events = CopilotKitAdapter._message_to_ag_ui_events(
                    message=message, run_id=task_id
                )

                # 发送每个事件
                for event in events:
                    yield CopilotKitAdapter._format_sse(event)

            # 发送运行完成事件
            yield CopilotKitAdapter._format_sse(
                {
                    "event": "RUN_FINISHED",
                    "data": {"runId": task_id},
                }
            )

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            # 发送错误事件
            yield CopilotKitAdapter._format_sse(
                {
                    "event": "ERROR",
                    "data": {
                        "runId": task_id,
                        "error": str(e),
                    },
                }
            )

    @staticmethod
    def _message_to_ag_ui_events(message: Any, run_id: str) -> list[dict]:
        """
        将 Claude SDK 消息转换为 AG-UI 事件列表

        Args:
            message: Claude SDK 消息
            run_id: 运行 ID

        Returns:
            AG-UI 事件列表
        """
        events = []
        msg_type = message.get("type")

        if msg_type == "assistant":
            # Assistant 消息
            msg_id = message.get("id", f"msg_{uuid4().hex[:8]}")
            content = message.get("content", [])

            # TEXT_MESSAGE_START
            events.append(
                {
                    "event": "TEXT_MESSAGE_START",
                    "data": {
                        "id": msg_id,
                        "runId": run_id,
                    },
                }
            )

            # 处理 content blocks
            for block in content:
                block_type = block.get("type")

                if block_type == "text":
                    # 文本内容
                    events.append(
                        {
                            "event": "TEXT_MESSAGE_CONTENT",
                            "data": {
                                "id": msg_id,
                                "content": block.get("text", ""),
                            },
                        }
                    )

                elif block_type == "tool_use":
                    # 工具调用
                    tool_id = block.get("id", f"tool_{uuid4().hex[:8]}")
                    tool_name = block.get("name", "unknown")
                    tool_input = block.get("input", {})

                    events.append(
                        {
                            "event": "TOOL_CALL_START",
                            "data": {
                                "id": tool_id,
                                "name": tool_name,
                            },
                        }
                    )

                    events.append(
                        {
                            "event": "TOOL_CALL_ARGS",
                            "data": {
                                "id": tool_id,
                                "args": json.dumps(tool_input),
                            },
                        }
                    )

                elif block_type == "thinking":
                    # 思考块（可选展示）
                    logger.debug(f"Thinking block: {block.get('thinking', '')[:100]}")
                    # 暂不发送给前端

            # TEXT_MESSAGE_END
            events.append(
                {
                    "event": "TEXT_MESSAGE_END",
                    "data": {
                        "id": msg_id,
                    },
                }
            )

        elif msg_type == "user":
            # User 消息（工具结果）
            content = message.get("content", [])
            for block in content:
                if block.get("type") == "tool_result":
                    tool_use_id = block.get("tool_use_id")
                    content_blocks = block.get("content", [])

                    # 提取结果文本
                    result_text = ""
                    for c in content_blocks:
                        if c.get("type") == "text":
                            result_text = c.get("text", "")
                            break

                    events.append(
                        {
                            "event": "TOOL_CALL_RESULT",
                            "data": {
                                "id": tool_use_id,
                                "result": result_text,
                            },
                        }
                    )

        elif msg_type == "result":
            # Result 消息（最终结果）
            subtype = message.get("subtype", "unknown")
            is_error = message.get("is_error", False)

            if is_error:
                events.append(
                    {
                        "event": "ERROR",
                        "data": {
                            "runId": run_id,
                            "error": f"Task failed: {subtype}",
                            "subtype": subtype,
                        },
                    }
                )

        elif msg_type == "system":
            # System 消息（内部事件，可选记录）
            subtype = message.get("subtype", "")
            logger.debug(f"System message: {subtype}")
            # 不发送给前端

        return events

    @staticmethod
    def _format_sse(event: dict) -> str:
        """
        格式化为 SSE 格式

        Args:
            event: 事件字典 {"event": "TYPE", "data": {...}}

        Returns:
            SSE 格式字符串
        """
        event_type = event.get("event", "message")
        data = event.get("data", {})

        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def get_copilotkit_info() -> dict:
    """
    获取 CopilotKit 配置信息

    返回 Agent 元信息（符合 CopilotKit /info 协议）
    """
    return {
        "agents": [
            {
                "name": "default",
                "description": "ANIFORCE AI Agent - 智能广告投放助手",
                "capabilities": [
                    "project_management",
                    "campaign_management",
                    "material_management",
                    "platform_authorization",
                ],
            }
        ]
    }
