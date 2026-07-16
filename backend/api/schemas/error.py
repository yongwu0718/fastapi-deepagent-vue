"""错误响应 schema —— 统一的结构化错误体。"""

from typing import Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """API 统一错误响应格式。

    Example:
        {"error_code": "THREAD_NOT_FOUND", "detail": "线程 'abc' 不存在"}
    """

    error_code: str = Field(..., description="业务错误码，如 THREAD_NOT_FOUND")
    detail: str = Field(..., description="人类可读的错误描述")
