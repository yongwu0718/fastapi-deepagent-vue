"""全局异常处理器 & 端点错误处理装饰器。

- register_exception_handlers(app): 注册 FastAPI 全局异常处理器
- handle_endpoint_errors: 装饰器，统一处理端点 try/except 样板代码
"""

import inspect
import re
import traceback
from functools import wraps
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.api.schemas.error import ErrorResponse
from backend.api.utils.exceptions import AppException, ErrorCode
from backend.config.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册所有全局异常处理器到 FastAPI 应用实例。"""

    # 1) AppException → 携带 error_code 的结构化响应
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            "业务异常 | error_code=%s | status=%d | detail=%s | path=%s",
            exc.error_code.value,
            exc.status_code,
            exc.detail,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.error_code.value,
                detail=str(exc.detail),
            ).model_dump(mode="json"),
            headers=getattr(exc, "headers", None),
        )

    # 2) RequestValidationError → 422 校验失败
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = exc.errors()
        logger.warning(
            "请求校验失败 | path=%s | errors=%s",
            request.url.path,
            errors,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error_code=ErrorCode.VALIDATION_ERROR.value,
                detail=_format_validation_errors(errors),
            ).model_dump(mode="json"),
        )

    # 3) 兜底：所有未处理的 Exception → 500
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "未处理异常 | path=%s | type=%s",
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR.value,
                detail="服务器内部错误",
            ).model_dump(mode="json"),
        )

    logger.info("全局异常处理器已注册")


def _format_validation_errors(errors: list) -> str:
    """将 Pydantic 校验错误列表格式化为可读字符串。"""
    messages = []
    for err in errors:
        loc = " → ".join(str(p) for p in err.get("loc", []))
        msg = err.get("msg", "校验失败")
        messages.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(messages)


# ═══════════════════════════════════════════════════════════════
#  端点错误处理装饰器
# ═══════════════════════════════════════════════════════════════

_TEMPLATE_RE = re.compile(r"\{(\w+(?:\.\w+)*)\}")


def _resolve_attr(obj, name: str):
    """安全取值：支持 dict.get() 和 getattr()。"""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _format_template(template: str, params: dict) -> str:
    """将模板中的 {key} / {key.attr} 替换为实际参数值。"""

    def replacer(match: re.Match) -> str:
        expr = match.group(1)
        parts = expr.split(".")
        val = params
        for part in parts:
            if val is None:
                break
            val = _resolve_attr(val, part)
        return str(val) if val is not None else f"{{{expr}}}"

    return _TEMPLATE_RE.sub(replacer, template)


def handle_endpoint_errors(
    error_code: ErrorCode,
    log_msg: str = "",
    detail_msg: str = "",
):
    """装饰器：统一处理端点中的 try/except 样板代码。

    - AppException 及其子类 → 直接透传
    - 其他 Exception → 记录日志并包装为 ``AppException(500, error_code)``

    ``log_msg`` / ``detail_msg`` 支持 ``{param_name}`` 和 ``{param.attr}``
    占位符，运行时自动从函数参数中填充。

    示例::

        @handle_endpoint_errors(
            ErrorCode.CHAT_INVOKE_FAILED,
            log_msg="非流式聊天异常 | thread_id={thread_id}",
            detail_msg="非流式聊天失败: thread_id={thread_id}",
        )
        async def chat_endpoint(chat_request, thread_id):
            ...
    """

    def decorator(func: Callable):
        sig = inspect.signature(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AppException:
                raise
            except Exception:
                if log_msg or detail_msg:
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    params = bound.arguments
                else:
                    params = {}

                if log_msg:
                    logger.exception(_format_template(log_msg, params))
                raise AppException(
                    status_code=500,
                    error_code=error_code,
                    detail=_format_template(detail_msg, params) if detail_msg else str(error_code.value),
                )

        return wrapper

    return decorator
