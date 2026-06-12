from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from agents import Agent, OpenAIChatCompletionsModel, Runner, SQLiteSession, set_tracing_disabled
from openai import AsyncOpenAI

from app.config.settings import get_settings
from app.schemas.agent import AgentChatMessage, AgentChatSessionResponse, AgentUsage

SYSTEM_PROMPT = """
你是 ANIFORCE 的 Agent 助手，帮助用户完成游戏广告投放相关工作。
当前阶段你只有普通对话能力，没有文件系统工具、Shell 工具、数据库查询工具、投放平台写入工具。
严禁假装执行 ls、cat、curl、数据库查询、项目扫描或任何真实工具调用。
当用户问“现在有哪些项目”等需要业务数据的问题时，必须明确说明：当前最小版本尚未接入项目数据库查询工具；可以建议下一步接入项目查询 API。
回答要清晰、简洁、可执行。不要假装已经创建了投放计划、素材、项目或后台任务。
如果用户提出复杂业务目标，可以先澄清目标、预算、平台、地区、素材类型等关键信息。
""".strip()


class AgentRuntime:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.model_name = getattr(self.settings, "OPENAI_AGENTS_MODEL", "gpt-4.1-mini")
        self.base_url = getattr(self.settings, "OPENAI_BASE_URL", "") or None
        self.sessions: dict[str, AgentChatSessionResponse] = {}
        self.messages: dict[str, list[AgentChatMessage]] = {}
        self.sdk_sessions: dict[str, SQLiteSession] = {}
        self.session_dir = Path("runtime/agent/sdk-sessions")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        set_tracing_disabled(True)

    def health(self) -> dict[str, str | bool]:
        return {
            "status": "ok",
            "provider": self.base_url or "openai",
            "model": self.model_name,
            "streaming": True,
        }

    def create_session(self, title: str | None = None) -> AgentChatSessionResponse:
        now = datetime.utcnow()
        session = AgentChatSessionResponse(
            id=f"chat_{uuid4().hex}",
            title=title or "新对话",
            created_at=now,
            updated_at=now,
        )
        self.sessions[session.id] = session
        self.messages[session.id] = []
        self.sdk_sessions[session.id] = self._create_sdk_session(session.id)
        return session

    def list_sessions(self) -> list[AgentChatSessionResponse]:
        return sorted(self.sessions.values(), key=lambda item: item.updated_at, reverse=True)

    def get_session(self, session_id: str) -> AgentChatSessionResponse | None:
        return self.sessions.get(session_id)

    def get_messages(self, session_id: str) -> list[AgentChatMessage]:
        return self.messages.get(session_id, [])

    async def stream_chat(self, session_id: str, message: str) -> AsyncIterator[str]:
        session = self.sessions.get(session_id)
        if not session:
            session = self.create_session()
            session_id = session.id

        user_message = self._append_message(session_id, "user", message)
        assistant_message_id = f"msg_{uuid4().hex}"
        assistant_text = ""
        sequence = 0

        yield self._sse("runtime.started", {
            "session_id": session_id,
            "sequence": sequence,
            "provider": self.base_url or "openai",
            "model": self.model_name,
        })
        sequence += 1
        yield self._sse("message.started", {
            "session_id": session_id,
            "sequence": sequence,
            "message": user_message.model_dump(mode="json"),
            "assistantMessageEvent": {
                "id": assistant_message_id,
                "role": "assistant",
                "content": "",
                "provider": self.base_url or "openai",
                "model": self.model_name,
                "created_at": datetime.utcnow().isoformat(),
            },
        })
        sequence += 1

        try:
            result = Runner.run_streamed(
                self._build_agent(),
                message,
                session=self._get_sdk_session(session_id),
            )
            async for event in result.stream_events():
                delta = self._event_delta(event)
                if not delta:
                    continue
                assistant_text += delta
                yield self._sse("message.updated", {
                    "session_id": session_id,
                    "sequence": sequence,
                    "assistantMessageEvent": {
                        "id": assistant_message_id,
                        "role": "assistant",
                        "delta": delta,
                        "content": assistant_text,
                        "provider": self.base_url or "openai",
                        "model": self.model_name,
                    },
                })
                sequence += 1

            usage = self._extract_usage(result)
            assistant_message = self._append_message(
                session_id,
                "assistant",
                result.final_output or assistant_text,
                message_id=assistant_message_id,
                usage=usage,
            )
            yield self._sse("message.completed", {
                "session_id": session_id,
                "sequence": sequence,
                "assistantMessageEvent": assistant_message.model_dump(mode="json"),
                "usage": usage.model_dump(mode="json"),
            })
            sequence += 1
            yield self._sse("runtime.completed", {
                "session_id": session_id,
                "sequence": sequence,
                "usage": usage.model_dump(mode="json"),
                "provider": self.base_url or "openai",
                "model": self.model_name,
            })
        except Exception as exc:
            yield self._sse("runtime.error", {
                "session_id": session_id,
                "sequence": sequence,
                "message": str(exc),
            })

    def _build_agent(self) -> Agent:
        return Agent(
            name="ANIFORCE Assistant",
            instructions=SYSTEM_PROMPT,
            model=self._build_model(),
        )

    def _build_model(self) -> str | OpenAIChatCompletionsModel:
        if self.base_url:
            client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.settings.OPENAI_API_KEY,
            )
            return OpenAIChatCompletionsModel(
                model=self.model_name,
                openai_client=client,
                strict_feature_validation=False,
            )
        return self.model_name

    def _create_sdk_session(self, session_id: str) -> SQLiteSession:
        return SQLiteSession(session_id, db_path=str(self.session_dir / "chat_sessions.db"))

    def _get_sdk_session(self, session_id: str) -> SQLiteSession:
        if session_id not in self.sdk_sessions:
            self.sdk_sessions[session_id] = self._create_sdk_session(session_id)
        return self.sdk_sessions[session_id]

    def _append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        message_id: str | None = None,
        usage: AgentUsage | None = None,
    ) -> AgentChatMessage:
        item = AgentChatMessage(
            id=message_id or f"msg_{uuid4().hex}",
            role=role,
            content=content,
            created_at=datetime.utcnow(),
            provider=self.base_url or "openai" if role == "assistant" else None,
            model=self.model_name if role == "assistant" else None,
            usage=usage,
        )
        self.messages.setdefault(session_id, []).append(item)
        if session_id in self.sessions:
            current = self.sessions[session_id]
            self.sessions[session_id] = current.model_copy(update={"updated_at": datetime.utcnow()})
        return item

    def _extract_usage(self, result: object) -> AgentUsage:
        input_tokens = 0
        output_tokens = 0
        raw_responses = getattr(result, "raw_responses", []) or []
        for response in raw_responses:
            usage = getattr(response, "usage", None)
            if usage is None:
                continue
            input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
            output_tokens += int(getattr(usage, "output_tokens", 0) or 0)
        return AgentUsage(
            input=input_tokens,
            output=output_tokens,
            totalTokens=input_tokens + output_tokens,
        )

    def _event_delta(self, event: object) -> str:
        if getattr(event, "type", None) != "raw_response_event":
            return ""
        data = getattr(event, "data", None)
        if getattr(data, "type", None) != "response.output_text.delta":
            return ""
        delta = getattr(data, "delta", "")
        return delta if isinstance(delta, str) else ""

    def _sse(self, event: str, payload: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


agent_runtime = AgentRuntime()
