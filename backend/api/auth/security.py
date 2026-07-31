"""安全工具：密码哈希 + JWT 签发/验证。"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt import PyJWTError

from backend.api.auth.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY


# ═══════════════════════════════════════════════════════
#  密码操作
# ═══════════════════════════════════════════════════════


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希（用于存储）。

    bcrypt 密码最长 72 字节，超长部分自动截断。
    """
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希是否匹配。"""
    plain_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(plain_bytes, hashed_password.encode("utf-8"))


# ═══════════════════════════════════════════════════════
#  Token 操作
# ═══════════════════════════════════════════════════════


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """签发 JWT access token。

    Args:
        data: 要编码到 token 中的数据（至少包含 ``sub`` 字段）。
        expires_delta: 自定义过期时间，默认使用配置值。

    Returns:
        编码后的 JWT 字符串。
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """解码并验证 JWT token。

    Args:
        token: JWT 字符串。

    Returns:
        解码后的 payload 字典，解析失败返回 None。
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        return None
