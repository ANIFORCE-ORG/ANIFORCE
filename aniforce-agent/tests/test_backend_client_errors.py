from __future__ import annotations

import asyncio

import httpx
import pytest

from app.backend_client import BackendClient, BackendResponseError, BackendUnavailableError


def test_backend_client_maps_forbidden_without_exposing_body(monkeypatch, caplog) -> None:
    async def fake_request(self, **kwargs):
        request = httpx.Request(kwargs["method"], kwargs["url"])
        return httpx.Response(403, request=request, text="sk-secret private backend detail")

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)

    with pytest.raises(BackendResponseError) as caught:
        asyncio.run(BackendClient("http://backend.test").get_project("token", "project_1"))

    assert caught.value.to_dict() == {
        "error": True,
        "code": "BACKEND_FORBIDDEN",
        "message": "Backend rejected the tool request",
        "status": 403,
        "retryable": False,
    }
    assert "sk-secret" not in caplog.text
    assert "private backend detail" not in caplog.text


def test_backend_client_maps_timeout(monkeypatch) -> None:
    async def fake_request(self, **kwargs):
        raise httpx.ReadTimeout("private upstream detail")

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)

    with pytest.raises(BackendUnavailableError) as caught:
        asyncio.run(BackendClient("http://backend.test").list_projects("token"))

    assert caught.value.code == "BACKEND_TIMEOUT"
    assert caught.value.status == 504
    assert caught.value.retryable is True
