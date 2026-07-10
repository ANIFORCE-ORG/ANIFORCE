"""Database-backed Agent run worker."""

from __future__ import annotations

import asyncio
import os
import socket
from datetime import datetime, timedelta, timezone
from time import perf_counter

from jose import jwt
from loguru import logger

from app.api.v1.agent_routes import _consume_agent_run_background
from app.config.database import get_session_maker
from app.config.settings import get_settings
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.services.agent_gateway import AgentGatewayService
from app.services.agent_run_event_bus import agent_run_event_bus


class AgentRunWorker:
    def __init__(self, worker_id: str | None = None, poll_seconds: float = 0.2):
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}"
        self.poll_seconds = poll_seconds
        self.session_maker = get_session_maker()
        self.gateway = AgentGatewayService()

    def _authorization(self, user_id: str) -> str:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": user_id,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=10)).timestamp()),
                "token_type": "agent_worker",
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        return f"Bearer {token}"

    async def _heartbeat(self, run_id: str, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=20.0)
                return
            except asyncio.TimeoutError:
                pass
            async with self.session_maker() as session:
                owned = await SqliteAgentRunRepository(session).heartbeat(run_id, self.worker_id)
                await session.commit()
            if not owned:
                logger.warning("Agent run lease lost: run_id={} worker_id={}", run_id, self.worker_id)
                return

    async def run_once(self) -> bool:
        async with self.session_maker() as session:
            repo = SqliteAgentRunRepository(session)
            run = await repo.claim_next(self.worker_id)
            await session.commit()
        if not run:
            return False

        run_id = run["run_id"]
        session_id = run["session_id"]
        user_id = run["user_id"]
        context = run.get("execution_context") or {}
        authorization = self._authorization(user_id)
        await agent_run_event_bus.create_run(run_id, session_id, user_id)
        payload = {
            "run_id": run_id,
            "prompt": run["input_text"],
            "session_id": session_id,
            "user_id": user_id,
            "task_type": context.get("task_type", "conversation"),
            "business_context_summary": context.get("business_context_summary", ""),
            "ui_snapshot": context.get("ui_snapshot") or {},
            "session_state": context.get("session_state") or {},
            "run_meta": {"run_id": run_id, "user_id": user_id},
        }
        heartbeat_stop = asyncio.Event()
        heartbeat_task = asyncio.create_task(self._heartbeat(run_id, heartbeat_stop))
        try:
            await _consume_agent_run_background(
                run_id=run_id,
                session_id=session_id,
                user_id=user_id,
                authorization=authorization,
                agent_payload=payload,
                changelog_start_index=int(context.get("changelog_start_index") or 0),
                gateway=self.gateway,
                perf_start=perf_counter(),
            )
        finally:
            heartbeat_stop.set()
            await heartbeat_task
            async with self.session_maker() as session:
                await SqliteAgentRunRepository(session).release_lease(run_id, self.worker_id)
                await session.commit()
        return True

    async def run_forever(self) -> None:
        logger.info("Agent run worker started: {}", self.worker_id)
        while True:
            try:
                claimed = await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Agent run worker iteration failed")
                claimed = False
            if not claimed:
                await asyncio.sleep(self.poll_seconds)
