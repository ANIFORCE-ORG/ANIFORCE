"""HTTP client for the standalone agent-service."""

import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.agent.errors import AgentModuleError


class AgentGatewayError(AgentModuleError):
    """Base error for agent gateway failures."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(code, message, status_code=502, retryable=retryable)


class AgentGatewayService:
    """Calls agent-service and streams SSE responses."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 300.0) -> None:
        self.base_url = (base_url or os.getenv("AGENT_SERVICE_URL") or "http://127.0.0.1:18020").rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_UNAVAILABLE", f"Agent service unavailable: {exc}", True) from exc

    async def get_session_history(self, authorization: str | None, session_id: str) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                response = await client.get(
                    f"{self.base_url}/api/runtime/sessions/{session_id}/history",
                    headers=self._headers(authorization),
                )
                response.raise_for_status()
                data = response.json()
                return data.get("messages") if isinstance(data, dict) else []
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_UNAVAILABLE", f"Get session history failed: {exc}", True) from exc

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

    async def stream_checkpoint_resume(
        self,
        authorization: str | None,
        checkpoint_id: str,
        payload: dict[str, Any],
    ) -> AsyncIterator[bytes]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/runtime/checkpoints/{checkpoint_id}/resume",
                    json=payload,
                    headers={**self._headers(authorization), "Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
        except httpx.HTTPError as exc:
            raise AgentGatewayError("AGENT_UNAVAILABLE", f"Resume checkpoint failed: {exc}", True) from exc

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
