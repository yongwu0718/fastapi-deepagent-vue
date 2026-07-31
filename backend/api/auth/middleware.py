"""认证日志中间件 —— 从请求中提取用户信息，绑定到日志上下文。

每条日志自动携带 ``username``，供 RoutingFileHandler 按用户隔离日志文件。
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.api.auth.security import decode_access_token
from backend.config.logger import bind_context, clear_context


class AuthLogMiddleware(BaseHTTPMiddleware):
    """从 Authorization header 解析 username，注入日志上下文。

    对所有请求生效：
    - 携带有效 JWT 的请求 → bind_context(username=...)
    - 无 token / token 无效 → 不绑定（系统日志）
    - 请求结束后 → clear_context()

    注意：此中间件仅负责日志上下文的 username 注入；
          实际鉴权仍由路由层 Depends(get_current_user) 完成。
    """

    async def dispatch(self, request: Request, call_next):
        username = self._extract_username(request)
        if username:
            bind_context(username=username)

        try:
            response: Response = await call_next(request)
            return response
        finally:
            clear_context()

    @staticmethod
    def _extract_username(request: Request) -> str | None:
        """从 Authorization header 中提取用户名。"""
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None

        token = auth[len("Bearer "):].strip()
        if not token:
            return None

        payload = decode_access_token(token)
        if payload is None:
            return None

        return payload.get("sub")
