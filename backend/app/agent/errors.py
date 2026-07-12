"""Shared errors for the Backend Agent module."""


class AgentModuleError(Exception):
    """Stable domain/application error consumed by Agent HTTP adapters."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        retryable: bool = False,
        *,
        details: dict | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)
