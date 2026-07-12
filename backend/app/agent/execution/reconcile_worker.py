"""Periodic reconciliation for expired Agent execution leases."""

import asyncio
from datetime import datetime, timedelta

from loguru import logger

from app.agent.execution.reconciliation import AgentStateReconciler
from app.config.database import get_session_maker
from app.config.metrics import AGENT_RECONCILE_ACTIONS, AGENT_RECONCILE_RUNS


class AgentReconcileWorker:
    def __init__(self, interval_seconds: float = 15.0, legacy_cutoff_minutes: int = 5):
        self.interval_seconds = interval_seconds
        self.legacy_cutoff_minutes = legacy_cutoff_minutes
        self.session_maker = get_session_maker()

    async def run_once(self) -> dict:
        async with self.session_maker() as session:
            report = await AgentStateReconciler(session).reconcile(
                cutoff=datetime.utcnow() - timedelta(minutes=self.legacy_cutoff_minutes),
                apply=True,
            )
            await session.commit()
        payload = report.to_dict()
        AGENT_RECONCILE_RUNS.labels("completed").inc()
        AGENT_RECONCILE_ACTIONS.labels("action").inc(len(payload["actions"]))
        AGENT_RECONCILE_ACTIONS.labels("conflict").inc(len(payload["conflicts"]))
        if payload["actions"] or payload["conflicts"]:
            logger.warning("Agent reconciliation: {}", payload)
        return payload

    async def run_forever(self) -> None:
        logger.info("Agent reconcile worker started")
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                AGENT_RECONCILE_RUNS.labels("failed").inc()
                logger.exception("Agent reconcile worker iteration failed")
            await asyncio.sleep(self.interval_seconds)
