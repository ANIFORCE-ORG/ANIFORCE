"""HTTP client for the standalone agent-service."""

import os
from collections.abc import AsyncIterator
from typing import Any

import httpx


class AgentGatewayError(Exception):
    """Base error for agent gateway failures."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class AgentGatewayService:
    """Calls agent-service and streams SSE responses."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 300.0) -> None:
        self.base_url = (base_url or os.getenv("AGENT_SERVICE_URL") or "http://127.0.0.1:8020").rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_UNAVAILABLE", f"Agent service unavailable: {exc}", True) from exc

    async def create_session(self, authorization: str | None) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                response = await client.post(
                    f"{self.base_url}/api/agent/sessions",
                    headers=self._headers(authorization),
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_UNAVAILABLE", f"Create agent session failed: {exc}", True) from exc

    async def list_sessions(self, authorization: str | None) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                response = await client.get(
                    f"{self.base_url}/api/agent/sessions",
                    headers=self._headers(authorization),
                )
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, list) else []
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_UNAVAILABLE", f"List agent sessions failed: {exc}", True) from exc

    async def get_session(self, authorization: str | None, session_id: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                response = await client.get(
                    f"{self.base_url}/api/agent/sessions/{session_id}",
                    headers=self._headers(authorization),
                )
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else {}
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_UNAVAILABLE", f"Get agent session failed: {exc}", True) from exc

    async def cancel_task(self, authorization: str | None, task_id: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
                response = await client.post(
                    f"{self.base_url}/api/agent/tasks/{task_id}/cancel",
                    headers=self._headers(authorization),
                )
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else {}
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_UNAVAILABLE", f"Cancel agent task failed: {exc}", True) from exc

    async def stream_run(
        self,
        authorization: str | None,
        payload: dict[str, Any],
    ) -> AsyncIterator[bytes]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/agent/runs",
                    json=payload,
                    headers={**self._headers(authorization), "Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_STREAM_FAILED", f"Agent stream failed: {exc}", True) from exc

    def _headers(self, authorization: str | None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if authorization:
            headers["Authorization"] = authorization
        return headers
