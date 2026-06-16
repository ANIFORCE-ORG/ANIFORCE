"""
AgentRuntime - Claude SDK 封装层（ClaudeSDKClient 有状态架构）

核心设计：
- 每个 session_id 对应一个长期持有的 ClaudeSDKClient 实例
- 用户每轮消息 → await client.query(prompt)
- SSE 流式推送 → async for msg in client.receive_response()
- 生命周期管理：session 超时/用户离线时 disconnect
- 实例池管理：存储/复用/清理 client 实例

参考学习手册第 5 章：路线 A（Client 有状态）
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, AsyncGenerator, Any, Dict
import logging

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from app.config.settings import settings
from app.agent.session_store import SQLiteSessionStore
from app.agent.skill_manager import SkillManager
from app.agent.sandbox import SandboxManager
from app.mcp.remote import create_backend_mcp_servers
from app.core.context import get_jwt_token

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Agent 运行时管理器（ClaudeSDKClient 实例池）"""

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

        # Client 实例池：session_id -> ClaudeSDKClient
        self._clients: Dict[str, ClaudeSDKClient] = {}

        # Client 锁：防止并发创建
        self._locks: Dict[str, asyncio.Lock] = {}

    async def get_or_create_client(
        self,
        *,
        session_id: str,
        user_id: str,
        task_id: str,
        model: Optional[str] = None,
        max_turns: int = 20,
        mcp_servers: Optional[dict] = None,
        allowed_tools: Optional[list[str]] = None,
    ) -> ClaudeSDKClient:
        """
        获取或创建 ClaudeSDKClient 实例

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            task_id: 任务 ID
            model: Claude 模型
            max_turns: 最大轮数
            mcp_servers: MCP 服务器配置
            allowed_tools: 允许的工具

        Returns:
            ClaudeSDKClient 实例
        """
        # 已存在则直接返回
        if session_id in self._clients:
            logger.debug(f"Reusing existing client: session_id={session_id}")
            return self._clients[session_id]

        # 获取锁（防止并发创建）
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()

        async with self._locks[session_id]:
            # 双重检查
            if session_id in self._clients:
                return self._clients[session_id]

            # 创建新 client
            logger.info(f"Creating new client: session_id={session_id}, user_id={user_id}")

            # 创建会话目录
            session_dir = self.sandbox_manager.create_session_dir(session_id)

            # 初始化 Skills
            self.skill_manager.init_session_skills(session_id)

            # 构造 Options
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

            # 创建 client（不用 async with，手动管理生命周期）
            client = ClaudeSDKClient(options)
            await client.connect()

            # 存入池
            self._clients[session_id] = client

            logger.info(f"Client created and connected: session_id={session_id}")
            return client

    async def query(
        self,
        *,
        session_id: str,
        user_id: str,
        task_id: str,
        prompt: str,
        model: Optional[str] = None,
        max_turns: int = 20,
        mcp_servers: Optional[dict] = None,
        allowed_tools: Optional[list[str]] = None,
    ) -> AsyncGenerator[Any, None]:
        """
        执行查询（流式返回消息）

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            task_id: 任务 ID
            prompt: 用户输入
            model: Claude 模型
            max_turns: 最大轮数
            mcp_servers: MCP 服务器配置
            allowed_tools: 允许的工具

        Yields:
            Claude SDK 消息流
        """
        # 获取或创建 client
        client = await self.get_or_create_client(
            session_id=session_id,
            user_id=user_id,
            task_id=task_id,
            model=model,
            max_turns=max_turns,
            mcp_servers=mcp_servers,
            allowed_tools=allowed_tools,
        )

        logger.info(f"Sending query: session_id={session_id}, prompt_len={len(prompt)}")

        try:
            # 发送用户消息
            await client.query(prompt)

            # 接收响应（流式）
            async for message in client.receive_response():
                yield message

            logger.info(f"Query completed: session_id={session_id}")

        except Exception as e:
            logger.error(f"Query error: session_id={session_id}, error={e}", exc_info=True)
            raise

    async def disconnect_client(self, session_id: str):
        """
        断开并清理 client

        Args:
            session_id: 会话 ID
        """
        client = self._clients.pop(session_id, None)
        if client:
            try:
                await client.disconnect()
                logger.info(f"Client disconnected: session_id={session_id}")
            except Exception as e:
                logger.error(f"Error disconnecting client: {e}", exc_info=True)

        # 清理锁
        self._locks.pop(session_id, None)

    async def cleanup_session(self, session_id: str):
        """
        完整清理会话（Client + Sandbox + Skills）

        Args:
            session_id: 会话 ID
        """
        # 断开 client
        await self.disconnect_client(session_id)

        # 清理 Sandbox
        await self.sandbox_manager.cleanup_session(session_id)

        # 清理 Skills
        self.skill_manager.cleanup_session_skills(session_id)

        logger.info(f"Session fully cleaned up: session_id={session_id}")

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
            "ANIFORCE_USER_ID": user_id,  # 传递用户信息给工具
            "ANIFORCE_TASK_ID": task_id,
        }

        # 添加可选配置
        if hasattr(settings, "ANTHROPIC_BASE_URL") and settings.ANTHROPIC_BASE_URL:
            env["ANTHROPIC_BASE_URL"] = settings.ANTHROPIC_BASE_URL

        # ✅ P0 修正：自动配置 HTTP MCP（连接后端服务）
        final_mcp_servers = mcp_servers
        if not final_mcp_servers:
            # 从 Context 获取 JWT Token
            jwt_token = get_jwt_token()
            if jwt_token and settings.BACKEND_URL:
                # 自动配置后端 MCP
                final_mcp_servers = create_backend_mcp_servers(auth_token=jwt_token)
                logger.info(f"Auto-configured backend MCP: backend_url={settings.BACKEND_URL}")
            elif not settings.BACKEND_URL:
                logger.warning("BACKEND_URL not configured, skipping HTTP MCP")
            else:
                logger.warning("JWT Token not found in context, skipping HTTP MCP")

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
            "session_store_flush": True,  # 确保 Session 数据及时持久化
            # 流式配置（参考学习手册第 6 章）
            "include_partial_messages": True,  # ✅ P0 修正：启用真正的流式输出
            # 优化配置（参考学习手册第 5 章）
            "thinking": {"type": "disabled"},  # 降低延迟
            "effort": "low",  # 轻量任务优先速度
        }

        # 添加 MCP 服务器配置
        if final_mcp_servers:
            options["mcp_servers"] = final_mcp_servers
            logger.debug(f"MCP servers configured: {list(final_mcp_servers.keys())}")

        return options

    def list_sessions(self) -> list[str]:
        """列出所有活跃会话"""
        return list(self._clients.keys())

    def get_session_info(self, session_id: str) -> dict:
        """
        获取会话信息

        Args:
            session_id: 会话 ID

        Returns:
            会话信息字典
        """
        has_client = session_id in self._clients
        return {
            "session_id": session_id,
            "has_client": has_client,
            "session_dir": str(self.sandbox_manager.get_session_dir(session_id)),
            "skills_dir": str(self.skill_manager.get_session_skills_dir(session_id)),
        }

    async def cleanup_all(self):
        """清理所有会话（用于服务关闭）"""
        session_ids = list(self._clients.keys())
        logger.info(f"Cleaning up {len(session_ids)} active sessions")

        for session_id in session_ids:
            try:
                await self.cleanup_session(session_id)
            except Exception as e:
                logger.error(f"Error cleaning session {session_id}: {e}")
