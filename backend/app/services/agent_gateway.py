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

    async def cancel_run(self, authorization: str | None, run_id: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
                response = await client.post(
                    f"{self.base_url}/api/runtime/runs/{run_id}/cancel",
                    headers=self._headers(authorization),
                )
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else {}
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_UNAVAILABLE", f"Cancel runtime run failed: {exc}", True) from exc

    async def stream_run(
        self,
        authorization: str | None,
        payload: dict[str, Any],
    ) -> AsyncIterator[bytes]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/runtime/runs",
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
