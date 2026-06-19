"""
Agent Platform 统一错误体系

遵循 Block 0 规范：
- 错误分类清晰
- 统一错误码
- 错误类封装
"""

from enum import Enum
from typing import Optional


class ErrorCategory(str, Enum):
    """错误分类"""
    TASK_ERROR = "task"                # 任务相关错误
    RUNTIME_ERROR = "runtime"          # 运行时错误
    UPSTREAM_ERROR = "upstream"        # 上游服务错误
    VALIDATION_ERROR = "validation"    # 参数校验错误
    BUSINESS_ERROR = "business"        # 业务错误


class AgentErrorCode(str, Enum):
    """统一错误码"""
    # Task 错误
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_STATUS_INVALID = "TASK_STATUS_INVALID"
    TASK_PERMISSION_DENIED = "TASK_PERMISSION_DENIED"
    
    # Runtime 错误
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_ABORTED = "AGENT_ABORTED"
    SDK_ERROR = "SDK_ERROR"
    
    # 上游错误
    UPSTREAM_NETWORK_ERROR = "UPSTREAM_NETWORK_ERROR"
    UPSTREAM_RATE_LIMIT = "UPSTREAM_RATE_LIMIT"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    UPSTREAM_AUTH_ERROR = "UPSTREAM_AUTH_ERROR"
    
    # 业务错误
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    INSUFFICIENT_BUDGET = "INSUFFICIENT_BUDGET"
    PLATFORM_NOT_SUPPORTED = "PLATFORM_NOT_SUPPORTED"
    
    # 通用错误
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class AppError(Exception):
    """应用异常基类"""
    
    def __init__(
        self,
        code: AgentErrorCode,
        message: str,
        category: ErrorCategory = ErrorCategory.RUNTIME_ERROR,
        data: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.category = category
        self.data = data or {}
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """转换为字典（用于 JSON 响应）"""
        return {
            "code": self.code.value,
            "message": self.message,
            "category": self.category.value,
            "data": self.data,
        }


def get_error_payload(error: AppError) -> dict:
    """获取错误载荷（用于事件）"""
    return {
        "code": error.code.value,
        "message": error.message,
        "category": error.category.value,
        "data": error.data,
    }


# 错误码到 HTTP 状态码的映射
ERROR_CODE_TO_HTTP_STATUS = {
    AgentErrorCode.TASK_NOT_FOUND: 404,
    AgentErrorCode.TASK_PERMISSION_DENIED: 403,
    AgentErrorCode.TASK_STATUS_INVALID: 400,
    AgentErrorCode.UPSTREAM_RATE_LIMIT: 429,
    AgentErrorCode.UPSTREAM_TIMEOUT: 504,
    AgentErrorCode.UPSTREAM_AUTH_ERROR: 502,
    AgentErrorCode.PROJECT_NOT_FOUND: 404,
    AgentErrorCode.INSUFFICIENT_BUDGET: 400,
    AgentErrorCode.PLATFORM_NOT_SUPPORTED: 400,
    AgentErrorCode.UNKNOWN_ERROR: 500,
    AgentErrorCode.INTERNAL_SERVER_ERROR: 500,
}


def get_http_status(code: AgentErrorCode) -> int:
    """获取错误码对应的 HTTP 状态码"""
    return ERROR_CODE_TO_HTTP_STATUS.get(code, 500)
