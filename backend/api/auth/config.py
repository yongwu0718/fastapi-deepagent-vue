"""认证模块配置。

从环境变量读取 JWT 密钥和管理员初始化凭据。
"""

import os

from dotenv import load_dotenv

# ── 加载 .env ──
load_dotenv(override=True)

# JWT 配置
SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

# 管理员初始凭据（可选，仅首次启动时用于创建管理员）
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")

# 是否开放公开注册（False 时 /auth/register 端点禁用）
ALLOW_REGISTRATION: bool = os.getenv("ALLOW_REGISTRATION", "true").lower() in ("1", "true", "yes")

# ── 启动时校验 ──
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY 环境变量未设置，请在 .env 中配置一个安全的密钥。"
        "可使用 python -c \"import secrets; print(secrets.token_urlsafe(32))\" 生成。"
    )

# 用户数据存储路径
USERS_DB_PATH: str = os.getenv("USERS_DB_PATH", "data/users.db")
