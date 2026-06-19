"""In-process session locks for MVP Agent runs."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class SessionBusyError(Exception):
    """Raised when a session already has an active run."""


class SessionLockManager:
    """Non-blocking per-session lock manager for single-process MVP."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def _get_lock(self, session_id: str) -> asyncio.Lock:
        async with self._guard:
            if session_id not in self._locks:
                self._locks[session_id] = asyncio.Lock()
            return self._locks[session_id]

    @asynccontextmanager
    async def acquire(self, session_id: str) -> AsyncIterator[None]:
        lock = await self._get_lock(session_id)
        if lock.locked():
            raise SessionBusyError(f"Session {session_id} is already running")
        await lock.acquire()
        try:
            yield
        finally:
            lock.release()


session_lock_manager = SessionLockManager()
