"""
本地 MCP 工具 - 任务管理

核心功能：
- list_tasks: 列出用户的任务
- get_task: 获取任务详情
- set_task_title: 设置任务标题
- output_task_result: 输出任务结果（结构化输出）

设计原则：
- 工具通过环境变量获取 user_id 和 task_id（由 AgentRuntime 注入）
- 直接访问 Repository 层，无需 HTTP 调用
- 权限通过 user_id 自动过滤
"""

import os
import json
from typing import Any, Optional
import logging

from app.repositories.task_repo import TaskRepository
from app.models.task import TaskStatus

logger = logging.getLogger(__name__)


class TaskTools:
    """任务管理工具集"""

    def __init__(self, task_repo: TaskRepository):
        self.task_repo = task_repo

    def _get_user_id(self) -> str:
        """从环境变量获取当前用户 ID"""
        user_id = os.environ.get("ANIFORCE_USER_ID")
        if not user_id:
            raise ValueError("ANIFORCE_USER_ID not set in environment")
        return user_id

    def _get_task_id(self) -> str:
        """从环境变量获取当前任务 ID"""
        task_id = os.environ.get("ANIFORCE_TASK_ID")
        if not task_id:
            raise ValueError("ANIFORCE_TASK_ID not set in environment")
        return task_id

    async def list_tasks(self, task_type: Optional[str] = None, limit: int = 20) -> str:
        """
        列出用户的任务

        Args:
            task_type: 任务类型过滤（可选）
            limit: 最多返回数量

        Returns:
            JSON 格式的任务列表
        """
        user_id = self._get_user_id()

        try:
            tasks = await self.task_repo.list_by_user(
                user_id=user_id, task_type=task_type, limit=limit
            )

            result = [
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "status": task.status.value,
                    "title": task.title,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                }
                for task in tasks
            ]

            return json.dumps({"tasks": result}, ensure_ascii=False)

        except Exception as e:
            logger.error(f"list_tasks failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    async def get_task(self, task_id: Optional[str] = None) -> str:
        """
        获取任务详情

        Args:
            task_id: 任务 ID（为空则使用当前任务）

        Returns:
            JSON 格式的任务详情
        """
        user_id = self._get_user_id()
        target_task_id = task_id or self._get_task_id()

        try:
            task = await self.task_repo.get_by_id(target_task_id, user_id)

            if not task:
                return json.dumps(
                    {"error": f"Task not found: {target_task_id}"}, ensure_ascii=False
                )

            result = {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status.value,
                "title": task.title,
                "session_id": task.session_id,
                "input_data": task.input_data,
                "result": task.result,
                "error": task.error,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }

            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            logger.error(f"get_task failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    async def set_task_title(self, title: str, task_id: Optional[str] = None) -> str:
        """
        设置任务标题

        Args:
            title: 新标题
            task_id: 任务 ID（为空则使用当前任务）

        Returns:
            操作结果
        """
        user_id = self._get_user_id()
        target_task_id = task_id or self._get_task_id()

        try:
            success = await self.task_repo.update_title(target_task_id, user_id, title)

            if success:
                return json.dumps(
                    {"success": True, "task_id": target_task_id, "title": title},
                    ensure_ascii=False,
                )
            else:
                return json.dumps(
                    {"error": f"Task not found: {target_task_id}"}, ensure_ascii=False
                )

        except Exception as e:
            logger.error(f"set_task_title failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    async def output_task_result(
        self, result: dict, task_id: Optional[str] = None
    ) -> str:
        """
        输出任务结果（结构化输出）

        Args:
            result: 结果数据（字典）
            task_id: 任务 ID（为空则使用当前任务）

        Returns:
            操作结果
        """
        user_id = self._get_user_id()
        target_task_id = task_id or self._get_task_id()

        try:
            # 更新任务结果
            success = await self.task_repo.update_result(
                target_task_id, user_id, result
            )

            if success:
                # 更新状态为完成
                await self.task_repo.update_status(
                    target_task_id, user_id, TaskStatus.COMPLETED
                )

                return json.dumps(
                    {"success": True, "task_id": target_task_id}, ensure_ascii=False
                )
            else:
                return json.dumps(
                    {"error": f"Task not found: {target_task_id}"}, ensure_ascii=False
                )

        except Exception as e:
            logger.error(f"output_task_result failed: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)


# MCP 工具定义（供 SDK 注册使用）
def create_task_tools_mcp_config(task_repo: TaskRepository) -> dict:
    """
    创建任务工具 MCP 配置

    Args:
        task_repo: TaskRepository 实例

    Returns:
        MCP 工具配置字典
    """
    tools = TaskTools(task_repo)

    return {
        "list_tasks": {
            "description": "List user's tasks with optional type filter",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "Filter by task type (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tasks to return",
                        "default": 20,
                    },
                },
            },
            "handler": tools.list_tasks,
        },
        "get_task": {
            "description": "Get task details by ID (defaults to current task)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID (optional, defaults to current task)",
                    },
                },
            },
            "handler": tools.get_task,
        },
        "set_task_title": {
            "description": "Set task title",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "New task title",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task ID (optional, defaults to current task)",
                    },
                },
                "required": ["title"],
            },
            "handler": tools.set_task_title,
        },
        "output_task_result": {
            "description": "Output structured task result",
            "input_schema": {
                "type": "object",
                "properties": {
                    "result": {
                        "type": "object",
                        "description": "Task result data (any JSON object)",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task ID (optional, defaults to current task)",
                    },
                },
                "required": ["result"],
            },
            "handler": tools.output_task_result,
        },
    }
