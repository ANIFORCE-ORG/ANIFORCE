"""Short-lived cross-process stream for Agent SDK events."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator

import redis.asyncio as redis
from loguru import logger

from app.config.settings import get_settings


@dataclass(frozen=True)
class TransientRunEvent:
    sequence: int
    event: str
    data: dict[str, Any]


class RedisRunEventStream:
    def __init__(self, url: str | None = None) -> None:
        settings = get_settings()
        self.url = url if url is not None else settings.REDIS_URL
        self.prefix = settings.AGENT_EVENT_STREAM_PREFIX
        self.ttl_seconds = settings.AGENT_EVENT_STREAM_TTL_SECONDS
        self.max_length = settings.AGENT_EVENT_STREAM_MAX_LENGTH
        self._client: redis.Redis | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def _redis(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.url, decode_responses=True)
        return self._client

    def _stream_key(self, run_id: str) -> str:
        return f"{self.prefix}:{run_id}:events"

    def _sequence_key(self, run_id: str) -> str:
        return f"{self.prefix}:{run_id}:sequence"

    async def publish(self, run_id: str, event: str, data: dict[str, Any]) -> int | None:
        if not self.enabled:
            return None
        try:
            client = self._redis()
            sequence_key = self._sequence_key(run_id)
            stream_key = self._stream_key(run_id)
            sequence = int(await client.incr(sequence_key))
            async with client.pipeline(transaction=True) as pipe:
                pipe.xadd(
                    stream_key,
                    {"event": event, "data": json.dumps(data, ensure_ascii=False, default=str)},
                    id=f"{sequence}-0",
                    maxlen=self.max_length,
                    approximate=True,
                )
                pipe.expire(stream_key, self.ttl_seconds)
                pipe.expire(sequence_key, self.ttl_seconds)
                await pipe.execute()
            return sequence
        except Exception:
            logger.exception("Redis Agent event publish failed: run_id={} event={}", run_id, event)
            return None

    async def latest_sequence(self, run_id: str) -> int:
        if not self.enabled:
            return 0
        value = await self._redis().get(self._sequence_key(run_id))
        return int(value or 0)

    async def subscribe(
        self,
        run_id: str,
        after_sequence: int = 0,
        block_ms: int = 1000,
    ) -> AsyncIterator[TransientRunEvent]:
        if not self.enabled:
            return
        client = self._redis()
        last_id = f"{max(0, after_sequence)}-0"
        stream_key = self._stream_key(run_id)
        while True:
            batches = await client.xread({stream_key: last_id}, block=block_ms, count=200)
            if not batches:
                continue
            for _, entries in batches:
                for entry_id, fields in entries:
                    last_id = entry_id
                    sequence = int(entry_id.split("-", 1)[0])
                    payload = json.loads(fields.get("data") or "{}")
                    yield TransientRunEvent(
                        sequence=sequence,
                        event=str(fields.get("event") or "message"),
                        data=payload if isinstance(payload, dict) else {"data": payload},
                    )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
