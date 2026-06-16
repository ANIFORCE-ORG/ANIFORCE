"""
AgentRuntime - Claude SDK 封装层

核心职责：
- 封装 claude_agent_sdk.query() 调用
- 管理 Session、Skill、Sandbox 生命周期
- 集成本地 MCP 工具和 HTTP MCP 桥接
- 提供统一的 Agent 执行接口
- 处理 AbortController 和任务取消
"""

import os
import uuid
from pathlib import Path
from typing import Optional, AsyncGenerator, Any
import logging

from claude_agent_sdk import query, ClaudeAgentOptions

from app.config.settings import settings
from app.agent.session_store import SQLiteSessionStore
from app.agent.skill_manager import SkillManager
from app.agent.sandbox import SandboxManager

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Agent 运行时管理器"""

    def __init__(self):
        # Session Store
        self.session_store = SQLiteSessionStore(settings.SESSION_DB_PATH)

        # Skill Manager
        self.skill_manager = SkillManager(
            source_dir=settings.SKILLS_SOURCE_DIR,
            runtime_dir=settings.RUNTIME_DIR,
        )

        # Sandbox Manager
        self.sandbox_manager = SandboxManager(runtime_dir=settings.RUNTIME_DIR)

    async def execute(
        self,
        *,
        prompt: str,
        session_id: Optional[str] = None,
        user_id: str,
        task_id: str,
        model: Optional[str] = None,
        max_turns: int = 20,
        mcp_servers: Optional[dict] = None,
        allowed_tools: Optional[list[str]] = None,
        abort_signal: Optional[Any] = None,
    ) -> AsyncGenerator[Any, None]:
        """
        执行 Agent 任务

        Args:
            prompt: 用户输入
            session_id: 会话 ID（为空则创建新会话）
            user_id: 用户 ID（用于权限隔离）
            task_id: 任务 ID
            model: Claude 模型名称
            max_turns: 最大对话轮数
            mcp_servers: MCP 服务器配置
            allowed_tools: 允许的工具列表
            abort_signal: 取消信号（AbortController）

        Yields:
            Claude SDK 消息流
        """
        # 生成 session_id
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:16]}"

        # 创建会话目录
        session_dir = self.sandbox_manager.create_session_dir(session_id)

        # 初始化 Skills
        self.skill_manager.init_session_skills(session_id)

        # 构造 Claude Agent Options
        options = self._build_options(
            session_id=session_id,
            user_id=user_id,
            task_id=task_id,
            session_dir=session_dir,
            model=model,
            max_turns=max_turns,
            mcp_servers=mcp_servers,
            allowed_tools=allowed_tools,
        )

        logger.info(
            f"Starting agent execution: task_id={task_id}, session_id={session_id}, user_id={user_id}"
        )

        try:
            # 调用 Claude SDK
            async for message in query(prompt, options, abort_signal=abort_signal):
                yield message

        except Exception as e:
            logger.error(f"Agent execution error: {e}", exc_info=True)
            raise

        finally:
            logger.info(f"Agent execution finished: task_id={task_id}")

    def _build_options(
        self,
        *,
        session_id: str,
        user_id: str,
        task_id: str,
        session_dir: Path,
        model: Optional[str],
        max_turns: int,
        mcp_servers: Optional[dict],
        allowed_tools: Optional[list[str]],
    ) -> ClaudeAgentOptions:
        """
        构造 Claude Agent Options

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            task_id: 任务 ID
            session_dir: 会话目录
            model: Claude 模型
            max_turns: 最大轮数
            mcp_servers: MCP 服务器配置
            allowed_tools: 允许的工具

        Returns:
            ClaudeAgentOptions
        """
        # 默认工具集（安全工具）
        default_tools = [
            "Read",
            "Glob",
            "Grep",
            "WebFetch",
            "Skill",
        ]

        # 合并用户指定的工具
        final_tools = list(set(default_tools + (allowed_tools or [])))

        # 环境变量
        env = {
            **os.environ,
            "ANTHROPIC_API_KEY": settings.ANTHROPIC_API_KEY,
            "ANTHROPIC_BASE_URL": getattr(settings, "ANTHROPIC_BASE_URL", ""),
            "ANIFORCE_USER_ID": user_id,  # 传递用户信息给工具
            "ANIFORCE_TASK_ID": task_id,
        }

        options: ClaudeAgentOptions = {
            "cwd": str(session_dir),
            "model": model or getattr(settings, "CLAUDE_AGENT_MODEL", "claude-opus-4"),
            "max_turns": max_turns,
            "permission_mode": "default",
            "allowed_tools": final_tools,
            "env": env,
            "session_store": self.session_store,
            "session_key": {
                "project_key": "aniforce",
                "session_id": session_id,
            },
        }

        # 添加 MCP 服务器配置
        if mcp_servers:
            options["mcp_servers"] = mcp_servers

        return options

    async def cancel_task(self, task_id: str, session_id: Optional[str] = None):
        """
        取消任务

        Args:
            task_id: 任务 ID
            session_id: 会话 ID
        """
        # 终止进程（如果有）
        if session_id:
            await self.sandbox_manager.kill_process(session_id)

        logger.info(f"Task cancelled: task_id={task_id}")

    async def cleanup_session(self, session_id: str):
        """
        清理会话资源

        Args:
            session_id: 会话 ID
        """
        # 清理 Sandbox（进程 + 目录）
        await self.sandbox_manager.cleanup_session(session_id)

        # 清理 Skills
        self.skill_manager.cleanup_session_skills(session_id)

        logger.info(f"Session cleaned up: session_id={session_id}")

    def list_sessions(self) -> list[str]:
        """列出所有活跃会话"""
        return self.sandbox_manager.list_sessions()

    def get_session_info(self, session_id: str) -> dict:
        """
        获取会话信息

        Args:
            session_id: 会话 ID

        Returns:
            会话信息字典
        """
        return {
            "session_id": session_id,
            "session_dir": str(self.sandbox_manager.get_session_dir(session_id)),
            "skills_dir": str(self.skill_manager.get_session_skills_dir(session_id)),
            "is_running": self.sandbox_manager.is_process_running(session_id),
            "process_id": self.sandbox_manager.get_process_id(session_id),
        }
