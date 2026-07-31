"""认证模块 Pydantic Schema。"""

from pydantic import BaseModel, Field


# ── 登录 ──
class LoginRequest(BaseModel):
    """登录请求体。"""

    username: str = Field(min_length=1, description="用户名")
    password: str = Field(min_length=1, description="密码")


class TokenResponse(BaseModel):
    """登录成功返回的 Token。"""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token 类型")


# ── 用户信息 ──
class UserOut(BaseModel):
    """公开的用户信息（不暴露密码）。"""

    username: str
    is_active: bool = True
    is_admin: bool = False


class UserListItem(BaseModel):
    """用户列表项。"""

    username: str
    is_active: bool
    is_admin: bool
    created_at: str


class OperationResult(BaseModel):
    """通用操作结果响应。"""

    success: bool = Field(description="操作是否成功")
    message: str = Field(description="结果描述")


# ── 用户管理 ──
class CreateUserRequest(BaseModel):
    """创建用户请求体。"""

    username: str = Field(min_length=2, max_length=64, description="新用户名")
    password: str = Field(min_length=4, description="密码（至少4位）")
    is_admin: bool = Field(default=False, description="是否设为管理员")


class DeleteUserRequest(BaseModel):
    """删除用户请求体。"""

    username: str = Field(min_length=1, description="要删除的用户名")


class ToggleUserRequest(BaseModel):
    """启用/禁用用户请求体。"""

    username: str = Field(min_length=1, description="目标用户名")
    active: bool = Field(description="是否启用")


class ChangePasswordRequest(BaseModel):
    """修改密码请求体。"""

    old_password: str = Field(min_length=1, description="旧密码")
    new_password: str = Field(min_length=4, description="新密码（至少4位）")


# ── 注册（公开端点，无需登录） ──
class RegisterRequest(BaseModel):
    """新用户注册请求体。"""

    username: str = Field(min_length=2, max_length=64, description="用户名")
    password: str = Field(min_length=4, description="密码（至少4位）")
