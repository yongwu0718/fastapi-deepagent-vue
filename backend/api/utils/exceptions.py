"""统一错误码 & 自定义 HTTP 异常类。

使用方式：
    raise AppException(status_code=404, error_code=ErrorCode.THREAD_NOT_FOUND)
    raise NotFoundException(ErrorCode.THREAD_NOT_FOUND, detail="线程不存在")
"""

from enum import Enum
from typing import Optional

from fastapi import HTTPException


# ── 错误码枚举 ──
class ErrorCode(str, Enum):
    """业务错误码，前端据此做差异化处理。"""

    # ── 通用 ──
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"

    # ── Graph ──
    GRAPH_NOT_INITIALIZED = "GRAPH_NOT_INITIALIZED"  # 503

    # ── Thread ──
    THREAD_NOT_FOUND = "THREAD_NOT_FOUND"
    THREAD_DELETE_FAILED = "THREAD_DELETE_FAILED"
    THREAD_HISTORY_FAILED = "THREAD_HISTORY_FAILED"

    # ── Checkpoint ──
    CHECKPOINT_NOT_FOUND = "CHECKPOINT_NOT_FOUND"
    CHECKPOINT_LIST_FAILED = "CHECKPOINT_LIST_FAILED"
    CHECKPOINT_REPLAY_FAILED = "CHECKPOINT_REPLAY_FAILED"
    CHECKPOINT_FORK_FAILED = "CHECKPOINT_FORK_FAILED"

    # ── Chat ──
    CHAT_INVOKE_FAILED = "CHAT_INVOKE_FAILED"
    CHAT_STREAM_FAILED = "CHAT_STREAM_FAILED"
    CHAT_RESUME_FAILED = "CHAT_RESUME_FAILED"

    # ── Stream ──
    STREAM_INTERNAL_ERROR = "STREAM_INTERNAL_ERROR"

    # ── RAG Pipeline ──
    RAG_PROCESS_FAILED = "RAG_PROCESS_FAILED"
    RAG_DELETE_FAILED = "RAG_DELETE_FAILED"
    RAG_FILE_NOT_FOUND = "RAG_FILE_NOT_FOUND"
    RAG_UNSUPPORTED_FORMAT = "RAG_UNSUPPORTED_FORMAT"
    RAG_VECTORSTORE_ERROR = "RAG_VECTORSTORE_ERROR"

    # ── File / Directory ──
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    NOT_A_DIRECTORY = "NOT_A_DIRECTORY"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FORBIDDEN_PATH = "FORBIDDEN_PATH"
    FILE_ALREADY_EXISTS = "FILE_ALREADY_EXISTS"
    DIR_ALREADY_EXISTS = "DIR_ALREADY_EXISTS"
    FILE_CREATE_FAILED = "FILE_CREATE_FAILED"
    DIR_CREATE_FAILED = "DIR_CREATE_FAILED"
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    FILE_MODIFY_FAILED = "FILE_MODIFY_FAILED"
    FILE_DELETE_FAILED = "FILE_DELETE_FAILED"
    DIR_DELETE_FAILED = "DIR_DELETE_FAILED"
    INVALID_OPERATION = "INVALID_OPERATION"


# ── 状态码 → 错误码映射表（供全局处理器使用） ──
_STATUS_TO_ERROR_CODE = {
    400: ErrorCode.VALIDATION_ERROR,
    404: ErrorCode.NOT_FOUND,
    500: ErrorCode.INTERNAL_ERROR,
    503: ErrorCode.GRAPH_NOT_INITIALIZED,
}


# ── 自定义异常基类 ──
class AppException(HTTPException):
    """应用级异常：携带业务 error_code，方便前端/客户端分类处理。

    全局异常处理器会根据 error_code 生成结构化响应。
    """

    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        detail: Optional[str] = None,
        headers: Optional[dict] = None,
    ):
        self.error_code = error_code
        super().__init__(
            status_code=status_code,
            detail=detail or error_code.value,
            headers=headers,
        )


# ── 便捷子类 ──
class NotFoundException(AppException):
    """资源不存在（404）。"""

    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None):
        super().__init__(status_code=404, error_code=error_code, detail=detail)


class InternalErrorException(AppException):
    """内部错误（500）。"""

    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None):
        super().__init__(status_code=500, error_code=error_code, detail=detail)


class UnavailableException(AppException):
    """服务不可用（503）。"""

    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None):
        super().__init__(status_code=503, error_code=error_code, detail=detail)
