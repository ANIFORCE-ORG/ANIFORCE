"""
Sandbox 隔离管理器

核心设计：
- 目录隔离：每个 session 独立工作目录（runtime/sessions/{session_id}/）
- 进程管理：记录 Agent 进程 ID，支持任务取消
- 无需容器：基于进程 + 目录隔离，简单可靠
- 资源清理：会话结束后清理目录和进程
"""

import os
import signal
import asyncio
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SandboxManager:
    """Sandbox 隔离管理器"""

    def __init__(self, runtime_dir: str | Path):
        """
        Args:
            runtime_dir: 运行时会话根目录（runtime/sessions/）
        """
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        # 进程追踪：session_id -> process_id
        self._processes: dict[str, int] = {}

    def create_session_dir(self, session_id: str) -> Path:
        """
        创建会话工作目录

        Args:
            session_id: 会话 ID

        Returns:
            会话目录路径
        """
        session_dir = self.runtime_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # 创建标准子目录
        (session_dir / ".claude").mkdir(exist_ok=True)
        (session_dir / "workspace").mkdir(exist_ok=True)
        (session_dir / "logs").mkdir(exist_ok=True)

        logger.info(f"Created session directory: {session_dir}")
        return session_dir

    def get_session_dir(self, session_id: str) -> Path:
        """获取会话目录路径（不创建）"""
        return self.runtime_dir / session_id

    def register_process(self, session_id: str, pid: int):
        """
        注册会话进程

        Args:
            session_id: 会话 ID
            pid: 进程 ID
        """
        self._processes[session_id] = pid
        logger.info(f"Registered process {pid} for session {session_id}")

    def unregister_process(self, session_id: str):
        """注销会话进程"""
        if session_id in self._processes:
            del self._processes[session_id]
            logger.info(f"Unregistered process for session {session_id}")

    async def kill_process(self, session_id: str, timeout: float = 5.0):
        """
        终止会话进程

        Args:
            session_id: 会话 ID
            timeout: 等待超时时间（秒）
        """
        pid = self._processes.get(session_id)
        if not pid:
            logger.warning(f"No process found for session {session_id}")
            return

        try:
            # 先尝试 SIGTERM（优雅终止）
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to process {pid} (session {session_id})")

            # 等待进程退出
            for _ in range(int(timeout * 10)):
                try:
                    os.kill(pid, 0)  # 检查进程是否存在
                    await asyncio.sleep(0.1)
                except ProcessLookupError:
                    logger.info(f"Process {pid} terminated gracefully")
                    self.unregister_process(session_id)
                    return

            # 超时后强制 SIGKILL
            logger.warning(f"Process {pid} did not terminate, sending SIGKILL")
            os.kill(pid, signal.SIGKILL)
            self.unregister_process(session_id)

        except ProcessLookupError:
            logger.info(f"Process {pid} already terminated")
            self.unregister_process(session_id)
        except Exception as e:
            logger.error(f"Failed to kill process {pid}: {e}")

    def cleanup_session_dir(self, session_id: str):
        """
        清理会话目录

        Args:
            session_id: 会话 ID
        """
        session_dir = self.get_session_dir(session_id)
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)
            logger.info(f"Cleaned up session directory: {session_dir}")

    async def cleanup_session(self, session_id: str):
        """
        完整清理会话（进程 + 目录）

        Args:
            session_id: 会话 ID
        """
        # 先终止进程
        await self.kill_process(session_id)

        # 再清理目录
        self.cleanup_session_dir(session_id)

    def list_sessions(self) -> list[str]:
        """列出所有会话目录"""
        if not self.runtime_dir.exists():
            return []

        sessions = []
        for item in self.runtime_dir.iterdir():
            if item.is_dir():
                sessions.append(item.name)

        return sorted(sessions)

    def get_process_id(self, session_id: str) -> Optional[int]:
        """获取会话进程 ID"""
        return self._processes.get(session_id)

    def is_process_running(self, session_id: str) -> bool:
        """检查会话进程是否运行中"""
        pid = self._processes.get(session_id)
        if not pid:
            return False

        try:
            os.kill(pid, 0)  # 不发送信号，仅检查进程是否存在
            return True
        except ProcessLookupError:
            return False
