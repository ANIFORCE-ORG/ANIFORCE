from pydantic import BaseModel
from typing import TypeVar, Generic, Optional
from datetime import datetime

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: str = "操作成功"
    timestamp: int = 0

    def __init__(self, **kwargs):
        if "timestamp" not in kwargs or kwargs["timestamp"] == 0:
            kwargs["timestamp"] = int(datetime.now().timestamp())
        super().__init__(**kwargs)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    timestamp: int = 0

    def __init__(self, **kwargs):
        if "timestamp" not in kwargs or kwargs["timestamp"] == 0:
            kwargs["timestamp"] = int(datetime.now().timestamp())
        super().__init__(**kwargs)
