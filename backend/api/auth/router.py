"""认证路由 —— 登录 + 用户管理。"""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from backend.api.auth.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALLOW_REGISTRATION
from backend.api.auth.db import (
    add_user,
    delete_user,
    get_user_by_username,
    list_all_users,
    set_user_active,
    change_password,
)
from backend.api.auth.dependencies import CurrentUserDep, AdminUserDep
from backend.api.auth.schemas import (
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    OperationResult,
    RegisterRequest,
    ToggleUserRequest,
    TokenResponse,
    UserListItem,
    UserOut,
)
from backend.api.auth.security import create_access_token, verify_password
from backend.config.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# ════════════════════ 登录 ════════════════════


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    """用户登录，从数据库验证凭据，返回 JWT access token。"""
    user = get_user_by_username(body.username)
    if user is None:
        logger.info("登录失败 | username=%s | 原因=用户不存在", body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user["is_active"]:
        logger.info("登录失败 | username=%s | 原因=账户已禁用", body.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    if not verify_password(body.password, user["password_hash"]):
        logger.info("登录失败 | username=%s | 原因=密码错误", body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("登录成功 | username=%s", user["username"])
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserOut)
def get_me(current_user: CurrentUserDep) -> UserOut:
    """获取当前登录用户信息。"""
    return current_user


# ════════════════════ 注册（公开端点） ════════════════════


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest) -> TokenResponse:
    """新用户注册（无需登录），注册成功后自动签发 JWT。

    需配置 ALLOW_REGISTRATION=true 才开放；用户名已存在时返回 409。
    """
    if not ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="公开注册已关闭",
        )
    logger.info("POST /auth/register | username=%s", body.username)
    try:
        user = add_user(body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("注册成功 | username=%s", body.username)
    return TokenResponse(access_token=access_token, token_type="bearer")


# ════════════════════ 用户管理（需管理员权限） ════════════════════


@router.get("/users", response_model=list[UserListItem])
def list_users(admin_user: AdminUserDep) -> list[UserListItem]:
    """列出所有用户。"""
    logger.info("GET /auth/users | admin=%s", admin_user.username)
    return list_all_users()


@router.post("/users", response_model=UserOut)
def create_user(body: CreateUserRequest, admin_user: AdminUserDep) -> UserOut:
    """创建新用户。"""
    logger.info("POST /auth/users | username=%s | is_admin=%s", body.username, body.is_admin)
    try:
        user = add_user(body.username, body.password, is_admin=body.is_admin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return user


@router.delete("/users/{username}", response_model=OperationResult)
def remove_user(username: str, admin_user: AdminUserDep) -> OperationResult:
    """删除用户。"""
    logger.info("DELETE /auth/users/%s | admin=%s", username, admin_user.username)
    if username == admin_user.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")
    if not delete_user(username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"用户不存在: {username}")
    return OperationResult(success=True, message=f"用户 {username} 已删除")


@router.put("/users/toggle", response_model=OperationResult)
def toggle_user(body: ToggleUserRequest, admin_user: AdminUserDep) -> OperationResult:
    """启用或禁用用户。"""
    logger.info("PUT /auth/users/toggle | username=%s | active=%s", body.username, body.active)
    if body.username == admin_user.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能禁用自己")
    if not set_user_active(body.username, body.active):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"用户不存在: {body.username}")
    state = "启用" if body.active else "禁用"
    return OperationResult(success=True, message=f"用户 {body.username} 已{state}")


@router.put("/change-password", response_model=OperationResult)
def change_my_password(
    body: ChangePasswordRequest,
    current_user: CurrentUserDep,
) -> OperationResult:
    """当前用户修改自己的密码。"""
    logger.info("PUT /auth/change-password | username=%s", current_user.username)
    try:
        change_password(current_user.username, body.old_password, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return OperationResult(success=True, message="密码修改成功")
