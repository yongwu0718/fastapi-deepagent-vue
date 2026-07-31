"""认证依赖注入 —— 使用 Annotated 风格。"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend.api.auth.db import get_user_by_username
from backend.api.auth.schemas import UserOut
from backend.api.auth.security import decode_access_token

# ── OAuth2 方案 ──
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> UserOut:
    """从 Bearer token 中解析当前用户，并校验 DB 中存在且激活。

    Raises:
        HTTPException(401): token 无效/过期，或用户不存在。
        HTTPException(403): 用户已禁用。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证身份凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str | None = payload.get("sub")
    if not username:
        raise credentials_exception

    user = get_user_by_username(username)
    if user is None:
        raise credentials_exception
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserOut(
        username=user["username"],
        is_active=bool(user["is_active"]),
        is_admin=bool(user["is_admin"]),
    )


# ── 类型别名（方便在路径操作中使用 Annotated 风格） ──
CurrentUserDep = Annotated[UserOut, Depends(get_current_user)]


def get_admin_user(current_user: CurrentUserDep) -> UserOut:
    """要求当前用户具有管理员权限。

    Raises:
        HTTPException(403): 非管理员用户。
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


AdminUserDep = Annotated[UserOut, Depends(get_admin_user)]
