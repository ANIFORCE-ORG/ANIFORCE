"""Process-wide request pacing for user-triggered Meta Insights batches."""

from __future__ import annotations

import asyncio
import time


class MetaInsightsBatchGate:
    """Space page requests shared by concurrent batch syncs in this API process."""

    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval_seconds = max(0.0, min_interval_seconds)
        self._lock = asyncio.Lock()
        self._last_started_at = 0.0

    async def wait_turn(self) -> None:
        async with self._lock:
            elapsed = time.monotonic() - self._last_started_at
            remaining = self.min_interval_seconds - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_started_at = time.monotonic()


_gate: MetaInsightsBatchGate | None = None
_gate_interval: float | None = None


def get_meta_insights_batch_gate(min_interval_seconds: float) -> MetaInsightsBatchGate:
    global _gate, _gate_interval
    interval = max(0.0, min_interval_seconds)
    if _gate is None or _gate_interval != interval:
        _gate = MetaInsightsBatchGate(interval)
        _gate_interval = interval
    return _gate
