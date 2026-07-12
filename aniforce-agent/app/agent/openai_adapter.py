"""
OpenAI Agents SDK 适配器

遵循 Block 0 规范：
- 业务代码不直接依赖 SDK
- 封装 SDK 调用和事件转换
- 统一错误处理
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, AsyncIterator, Optional
from loguru import logger
from openai import AsyncOpenAI

from agents import (
    Agent,
    Runner,
    set_default_openai_api,
    set_default_openai_client,
    set_default_openai_key,
    set_tracing_disabled,
)
from agents.extensions.memory import SQLAlchemySession
from agents.memory.session import SessionABC
from agents.run import RunResult
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from agents.models.chatcmpl_converter import Converter

from app.agent.event_serializer import extract_usage, serialize_sdk_event, to_jsonable
from app.agent.model_factory import create_sdk_model
from app.core.errors import AppError, AgentErrorCode, ErrorCategory
from app.core.tracing import get_tracer


_ORIGINAL_ITEMS_TO_MESSAGES = Converter.items_to_messages


def _is_empty_assistant_output_message(item) -> bool:
    """Return True for SDK's empty assistant placeholder after tool calls."""
    if not isinstance(item, dict):
        return False
    if item.get("type") != "message" or item.get("role") != "assistant":
        return False
    content = item.get("content")
    if not content:
        return True
    if not isinstance(content, list):
        return False
    for part in content:
        if not isinstance(part, dict):
            return False
        if part.get("type") != "output_text":
            return False
        if str(part.get("text") or ""):
            return False
    return True


def _sanitize_chat_completion_items(items):
    """Remove SDK empty assistant placeholders that break ChatCompletions tool order."""
    if isinstance(items, str):
        return items

    normalized = list(items)
    sanitized = []
    removed = 0

    for index, item in enumerate(normalized):
        if not _is_empty_assistant_output_message(item):
            sanitized.append(item)
            continue

        previous_item = normalized[index - 1] if index > 0 else None
        next_item = normalized[index + 1] if index + 1 < len(normalized) else None
        previous_call_id = previous_item.get("call_id") if isinstance(previous_item, dict) and previous_item.get("type") == "function_call" else None
        next_call_id = next_item.get("call_id") if isinstance(next_item, dict) and next_item.get("type") == "function_call_output" else None

        if previous_call_id and previous_call_id == next_call_id:
            removed += 1
            continue

        sanitized.append(item)

    if removed:
        logger.warning(
            "[SDK] Removed {} empty assistant placeholder(s) between function_call and function_call_output for ChatCompletions compatibility",
            removed,
        )

    return sanitized


@classmethod
def _patched_items_to_messages(cls, items, *args, **kwargs):
    return _ORIGINAL_ITEMS_TO_MESSAGES(_sanitize_chat_completion_items(items), *args, **kwargs)


Converter.items_to_messages = _patched_items_to_messages


class OpenAISDKAdapter:
    """OpenAI Agents SDK 适配器"""
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        enable_tracing: bool = True,
        api_mode: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.enable_tracing = enable_tracing
        self.tracer = get_tracer() if enable_tracing else None
        self._agent_db_engines: dict[str, AsyncEngine] = {}
        
        self.api_mode = (api_mode or os.environ.get("OPENAI_AGENTS_API") or "responses").strip().lower()
        if self.api_mode in {"chat", "chat_completions", "chat-completions"}:
            self.api_mode = "chat_completions"
        else:
            self.api_mode = "responses"

        set_default_openai_api(self.api_mode)
        # 项目使用本地 JSONL tracing，禁用 OpenAI 官方 trace export。
        set_tracing_disabled(True)
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            set_default_openai_key(api_key, use_for_tracing=False)
        else:
            # fallback：从环境变量读，避免 AsyncOpenAI 报 Missing credentials
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY missing: set it in .env or env var")
        if base_url:
            os.environ["OPENAI_BASE_URL"] = base_url

        self.openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        set_default_openai_client(self.openai_client, use_for_tracing=False)
        
    
    def create_agent(
        self,
        name: str,
        instructions,
        mcp_servers: list = None,
        tools: list | None = None,
    ) -> Agent:
        """创建 WorkspaceAgent。当前主链路固定使用普通 Agent。

        instructions 可以是字符串或 dynamic instructions 函数
        (RunContextWrapper, Agent) -> str。
        """
        
        sdk_model = create_sdk_model(
            api_mode=self.api_mode,
            model=self.model,
            openai_client=self.openai_client,
        )
        
        return Agent(
            name=name,
            instructions=instructions,
            model=sdk_model,
            mcp_servers=mcp_servers or [],
            tools=tools or [],
        )
    
    def create_session(
        self,
        session_id: str,
        db_url: str = "sqlite+aiosqlite:///runtime/agent/agent.db",
        create_tables: bool = True,
    ) -> SQLAlchemySession:
        """创建 SDK SQLAlchemy Session，用于管理原生对话历史。"""
        sdk_session_id = session_id
        if self.api_mode == "chat_completions":
            sdk_session_id = f"chat_completions:{session_id}"

        self._ensure_sqlite_parent_dir(db_url)
        engine = self._get_agent_db_engine(db_url)
        return SQLAlchemySession(
            sdk_session_id,
            engine=engine,
            create_tables=create_tables,
        )

    def _get_agent_db_engine(self, db_url: str) -> AsyncEngine:
        engine = self._agent_db_engines.get(db_url)
        if engine is None:
            engine = create_async_engine(db_url)
            if db_url.startswith("sqlite"):
                @event.listens_for(engine.sync_engine, "connect")
                def configure_sqlite(dbapi_connection, _connection_record):
                    cursor = dbapi_connection.cursor()
                    # Set lock waiting before WAL initialization, which can
                    # briefly require an exclusive lock during cold startup.
                    cursor.execute("PRAGMA busy_timeout=5000")
                    try:
                        cursor.execute("PRAGMA journal_mode=WAL")
                    except sqlite3.OperationalError as exc:
                        if "database is locked" not in str(exc):
                            raise
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.close()
            self._agent_db_engines[db_url] = engine
        return engine

    async def close(self) -> None:
        """释放 adapter 持有的 SDK runtime 资源。"""
        for engine in self._agent_db_engines.values():
            await engine.dispose()
        self._agent_db_engines.clear()

    @staticmethod
    def _ensure_sqlite_parent_dir(db_url: str) -> None:
        """SQLAlchemy 不会自动创建 SQLite 文件的父目录。"""
        prefix = "sqlite+aiosqlite:///"
        if not db_url.startswith(prefix):
            return
        db_path = db_url.removeprefix(prefix)
        if not db_path or db_path == ":memory:":
            return
        Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    
    async def run_streamed(
        self,
        agent: Agent,
        input_text: Any,
        session: Optional[SessionABC] = None,
        context: Any = None,
        hooks: Any = None,
    ) -> RunResult:
        """
        流式执行 Agent
        
        Args:
            agent: Agent 实例
            input_text: 用户输入或 SDK RunState
            session: SDK Session（可选）
            context: RunContextWrapper.context 本地上下文（可选）
            hooks: Agents SDK RunHooks（可选）
            
        Returns:
            RunResult（可以流式读取事件）
        """
        # Trace SDK 调用
        if self.tracer:
            self.tracer.log_sdk_call(
                method="run_streamed",
                agent_name=getattr(agent, "name", "unknown"),
                input_text=input_text if isinstance(input_text, str) else type(input_text).__name__,
                session_id=getattr(session, "session_id", None) if session else None,
            )
        
        try:
            return Runner.run_streamed(
                agent,
                input=input_text,
                session=session,
                context=context,
                hooks=hooks,
            )
        except Exception as e:
            logger.exception(f"SDK run_streamed error: {e}")
            raise AppError(
                code=AgentErrorCode.SDK_ERROR,
                message=f"SDK execution failed: {str(e)}",
                category=ErrorCategory.RUNTIME_ERROR,
            )
    
    async def stream_events(self, result: RunResult) -> AsyncIterator[dict]:
        """流式读取 Agents SDK 原生事件 envelope。"""
        try:
            async for event in result.stream_events():
                sdk_event = self._serialize_sdk_event(event)
                if self.tracer:
                    self.tracer.log_sdk_event(
                        event_type=sdk_event.get("type", "unknown"),
                        event_data=sdk_event,
                    )
                yield sdk_event

            final_output = getattr(result, "final_output", None) or ""
            if self.tracer:
                self.tracer.log_llm_response(
                    model=self.model,
                    response=final_output,
                )
        except Exception as e:
            logger.exception(f"SDK stream error: {e}")
            raise AppError(
                code=AgentErrorCode.SDK_ERROR,
                message=f"SDK stream error: {str(e)}",
                category=ErrorCategory.RUNTIME_ERROR,
            )
    
    def _serialize_sdk_event(self, sdk_event) -> dict:
        return serialize_sdk_event(sdk_event)

    def _to_jsonable(self, value, depth: int = 0):
        return to_jsonable(value, depth)

    def _extract_usage(self, result: RunResult) -> dict:
        return extract_usage(result)
