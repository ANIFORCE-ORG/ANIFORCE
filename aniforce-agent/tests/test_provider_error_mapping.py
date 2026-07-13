import httpx
from openai import APITimeoutError

from app.agent.openai_adapter import map_provider_exception
from app.core.errors import AgentErrorCode, ErrorCategory, get_http_status


def test_provider_timeout_is_user_safe_and_retryable():
    error = APITimeoutError(request=httpx.Request("POST", "https://provider.invalid/v1/responses"))
    mapped = map_provider_exception(error)
    payload = mapped.to_dict()

    assert mapped.code == AgentErrorCode.UPSTREAM_TIMEOUT
    assert mapped.category == ErrorCategory.UPSTREAM_ERROR
    assert payload["message"] == "模型服务响应超时，本次未完成任务，请稍后重试。"
    assert payload["data"]["retryable"] is True
    assert "SDK" not in payload["message"]
    assert "provider.invalid" not in payload["message"]
    assert get_http_status(mapped.code) == 504


def test_unknown_provider_error_does_not_expose_exception_detail():
    mapped = map_provider_exception(RuntimeError("private provider payload sk-secret"))
    assert mapped.code == AgentErrorCode.SDK_ERROR
    assert "private" not in mapped.message
    assert "sk-secret" not in mapped.message
