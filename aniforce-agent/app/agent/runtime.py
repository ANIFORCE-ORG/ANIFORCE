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
        创建 ClaudeSDKClient 实例（每次 query 新建，用 resume 恢复上下文）

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

        说明：
            SDK 的 session_id 和 resume 是两个不同参数：
            - session_id: 新建会话时用的 ID
            - resume: 指定要恢复的 session ID
            本方法通过 session_store 判断该 session 是否已存在：
            - 不存在 → 用 session_id 新建
            - 已存在 → 用 resume 恢复
            每次 query 完成后销毁 client（见 query 方法的 finally）
        """
        # 获取锁（防止同一 session 并发创建）
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()

        async with self._locks[session_id]:
            # 创建新 client
            logger.info(f"Creating client: session_id={session_id}, user_id={user_id}")

            # 创建会话目录
            session_dir = self.sandbox_manager.create_session_dir(session_id)

            # 初始化 Skills
            self.skill_manager.init_session_skills(session_id)

            # 判断是新建还是 resume：检查 session_store 是否已有该 session 的记录
            has_history = await self._session_has_history(session_id)
            logger.info(f"Session {session_id} has_history={has_history}")

            # 构造 Options
            # 从 context 获取 JWT（用于闭包注入到 MCP 工具，并发安全）
            jwt_token = get_jwt_token()
            options = self._build_options(
                session_id=session_id,
                user_id=user_id,
                task_id=task_id,
                session_dir=session_dir,
                model=model,
                max_turns=max_turns,
                mcp_servers=mcp_servers,
                allowed_tools=allowed_tools,
                jwt_token=jwt_token,
                resume=session_id if has_history else None,
            )

            # 创建 client
            client = ClaudeSDKClient(options)
            await client.connect()

            logger.info(f"Client created and connected: session_id={session_id}, resume={has_history}")
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
        finally:
            # 每轮 query 完成后断开 client，避免下轮同 session_id 报 "already in use"
            # SDK 会从 session_store resume 上下文，无需长期持有 client
            logger.info(f"Disconnecting client after query: session_id={session_id}")
            await self.disconnect_client(session_id)

    async def _session_has_history(self, session_id: str) -> bool:
        """检查 session_store 中是否已有该 session 的对话记录"""
        try:
            import sqlite3
            from app.config.settings import settings as _settings
            db_path = _settings.SESSION_DB_PATH
            if not Path(db_path).exists():
                return False
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sessions WHERE session_id = ?", (session_id,))
            count = cur.fetchone()[0]
            conn.close()
            return count > 0
        except Exception as e:
            logger.debug(f"Check session history failed (treat as no history): {e}")
            return False

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
        jwt_token: Optional[str],
        resume: Optional[str] = None,
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
            jwt_token: 本次请求用户的 JWT（闭包注入到 MCP 工具）
            resume: 恢复的 session ID

        Returns:
            ClaudeAgentOptions
        """
        # 工具集：收敛到广告投放场景最小集（移除代码开发专用工具）
        # tools: 限制可用工具集（SDK 会从上下文中移除未列出的工具）
        # - Read/Write: 生成分析报告
        # - Skill: 调用业务 Skill
        # - AskUserQuestion: HITL 确认
        # - WebFetch/WebSearch: 竞品分析（可选）
        base_tools = [
            "Read",
            "Write",
            "Skill",
            "WebFetch",
            "WebSearch",
        ]
        # 注意：不包含 AskUserQuestion —— 它依赖 SDK permission callback，
        # 在 SSE 架构里无法响应。HITL 改用 mcp__hitl__confirm_action（路径 B）

        # 合并用户指定的工具
        final_tools = list(set(base_tools + (allowed_tools or [])))

        # MCP 工具免确认（backend 业务工具直接允许调用，不弹权限确认）
        mcp_allowed = [
            "mcp__backend__list_projects",
            "mcp__backend__get_project",
            "mcp__backend__create_project",
            "mcp__backend__list_campaigns",
            "mcp__backend__get_campaign",
            "mcp__backend__create_campaign",
            "mcp__backend__update_campaign_budget",
            "mcp__backend__list_materials",
            "mcp__backend__get_material",
            # Mock 工具（长程任务能力展示）
            "mcp__backend__create_material",
            "mcp__backend__generate_material_ai",
            "mcp__backend__update_campaign_status",
            "mcp__backend__get_campaign_performance",
            "mcp__hitl__confirm_action",
        ]
        final_allowed_tools = list(set(final_tools + mcp_allowed))

        # 明确禁用干扰工具（DesignSync / Task 系列 / Cron / Git worktree / Bash）
        disallowed_tools = [
            "DesignSync",
            "Task",
            "TaskCreate",
            "TaskGet",
            "TaskList",
            "TaskOutput",
            "TaskStop",
            "TaskUpdate",
            "EnterPlanMode",
            "ExitPlanMode",
            "EnterWorktree",
            "ExitWorktree",
            "CronCreate",
            "CronDelete",
            "CronList",
            "ScheduleWakeup",
            "Workflow",
            "Bash",
            "Edit",
            "Glob",
            "Grep",
            "NotebookEdit",
            "AskUserQuestion",
        ]

        # 环境变量：只带 ANTHROPIC_*/CLAUDE_* 前缀，避免父进程污染（AGENTS.md 配置污染排查）
        env = {
            key: value
            for key, value in os.environ.items()
            if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_")
        }
        env["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
        env["ANTHROPIC_AUTH_TOKEN"] = settings.ANTHROPIC_AUTH_TOKEN or settings.ANTHROPIC_API_KEY  # Claude SDK 需要
        env["ANIFORCE_USER_ID"] = user_id  # 传递用户信息给工具
        env["ANIFORCE_TASK_ID"] = task_id
        env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-agent/1.0"
        # CLAUDE_CONFIG_DIR 隔离：指向 session 目录下的空配置目录，避免加载本机 /root/.claude 的 hooks/plugins/skills
        # （AGENTS.md「Claude SDK 调用必须做的三件事」实证：不隔离会触发 api_retry）
        claude_config_dir = session_dir / ".claude_config"
        claude_config_dir.mkdir(parents=True, exist_ok=True)
        env["CLAUDE_CONFIG_DIR"] = str(claude_config_dir)

        # 添加可选配置
        if getattr(settings, "ANTHROPIC_BASE_URL", None):
            env["ANTHROPIC_BASE_URL"] = settings.ANTHROPIC_BASE_URL

        # ✅ 自动配置 Backend SDK MCP Server + HITL MCP Server
        # 并发安全：每次 query 创建独立实例，jwt/user/task 通过闭包注入
        final_mcp_servers = mcp_servers
        if not final_mcp_servers:
            logger.info(f"Building options: jwt_token={'<present>' if jwt_token else '<missing>'}, backend_url={settings.BACKEND_URL}")
            if jwt_token and settings.BACKEND_URL:
                from app.mcp.backend_sdk_server import get_backend_mcp_config
                from app.mcp.hitl_server import get_hitl_mcp_config
                final_mcp_servers = get_backend_mcp_config(jwt_token, user_id, task_id)
                final_mcp_servers.update(get_hitl_mcp_config(task_id, user_id))
                logger.info(f"Auto-configured MCP Servers: backend_url={settings.BACKEND_URL}, servers={list(final_mcp_servers.keys())}")
            elif not settings.BACKEND_URL:
                logger.warning("BACKEND_URL not configured, skipping Backend MCP")
            else:
                logger.warning("JWT Token not found, skipping Backend MCP")

        # 构造 ClaudeAgentOptions 对象（不是 dict！）
        options = ClaudeAgentOptions(
            cwd=str(session_dir),
            model=model or getattr(settings, "CLAUDE_AGENT_MODEL", "claude-opus-4"),
            max_turns=max_turns,
            permission_mode="default",
            tools=final_tools,  # 限制可用工具集（从上下文移除未列出的工具）
            allowed_tools=final_allowed_tools,  # 免确认工具（含 MCP 工具）
            disallowed_tools=disallowed_tools,  # 明确禁用干扰工具
            env=env,
            session_store=self.session_store,
            session_id=session_id if not resume else None,  # 新建时设 session_id
            resume=resume,  # 恢复时设 resume
            session_store_flush="eager",  # 确保 Session 数据及时持久化
            # 流式配置（参考学习手册第 6 章）
            include_partial_messages=True,  # ✅ P0 修正：启用真正的流式输出
            # 优化配置（参考学习手册第 5 章）
            thinking={"type": "disabled"},  # 降低延迟
            effort="low",  # 轻量任务优先速度
        )

        # 添加 MCP 服务器配置
        if final_mcp_servers:
            options.mcp_servers = final_mcp_servers
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
