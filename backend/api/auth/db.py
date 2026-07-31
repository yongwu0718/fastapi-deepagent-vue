"""用户数据库层 —— SQLite 存储用户凭据（bcrypt 哈希密码）。

表结构:
    CREATE TABLE IF NOT EXISTS users (
        username       TEXT PRIMARY KEY,
        password_hash  TEXT NOT NULL,
        is_active      INTEGER DEFAULT 1,
        is_admin       INTEGER DEFAULT 0,
        created_at     TEXT DEFAULT (datetime('now'))
    )
"""

import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager

from backend.api.auth.config import ADMIN_USERNAME, ADMIN_PASSWORD, USERS_DB_PATH
from backend.api.auth.security import hash_password, verify_password
from backend.config.logger import get_logger

logger = get_logger(__name__)

DB_PATH = str(Path(USERS_DB_PATH).resolve())

_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（自动创建目录）。"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def _transaction():
    """写事务：加锁 → 连接 → commit/rollback → 关闭。"""
    with _lock:
        conn = _get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


@contextmanager
def _query():
    """只读查询：连接 → 读取 → 关闭（不 commit）。"""
    conn = _get_conn()
    try:
        yield conn
    finally:
        conn.close()


# ═══════════════════════════════════════
#  初始化
# ═══════════════════════════════════════


def init_users_db() -> None:
    """创建用户表 + 初始化管理员（仅首次）。"""
    with _transaction() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username       TEXT PRIMARY KEY,
                password_hash  TEXT NOT NULL,
                is_active      INTEGER DEFAULT 1,
                is_admin       INTEGER DEFAULT 0,
                created_at     TEXT DEFAULT (datetime('now'))
            )
        """)
        # 兼容旧表：若 is_admin 列不存在则添加
        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "is_admin" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            logger.info("已迁移: users 表新增 is_admin 列")
        logger.info("用户表初始化完成 | db=%s", DB_PATH)

    # 如果 .env 中配置了管理员凭据，创建管理员
    if ADMIN_USERNAME and ADMIN_PASSWORD:
        add_user_if_not_exists(ADMIN_USERNAME, ADMIN_PASSWORD, is_admin=True)
        logger.info("管理员用户已就绪 | username=%s", ADMIN_USERNAME)
    else:
        logger.info("未配置默认管理员，跳过自动创建")


# ═══════════════════════════════════════
#  查询
# ═══════════════════════════════════════

def get_user_by_username(username: str) -> dict | None:
    """按用户名查询用户信息。

    Returns:
        包含 username, password_hash, is_active, is_admin, created_at 的字典，不存在返回 None。
    """
    with _query() as conn:
        row = conn.execute(
            "SELECT username, password_hash, is_active, is_admin, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_all_users() -> list[dict]:
    """列出所有用户（不含密码哈希）。"""
    with _query() as conn:
        rows = conn.execute(
            "SELECT username, is_active, is_admin, created_at FROM users ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════
#  写入
# ═══════════════════════════════════════

def add_user(username: str, password: str, is_admin: bool = False) -> dict:
    """添加新用户（密码使用 bcrypt 哈希存储）。"""
    password_hash = hash_password(password)
    try:
        with _transaction() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                (username, password_hash, int(is_admin)),
            )
        logger.info("用户创建成功 | username=%s | is_admin=%s", username, is_admin)
    except sqlite3.IntegrityError:
        raise ValueError(f"用户已存在: {username}")

    return get_user_by_username(username)


def add_user_if_not_exists(username: str, password: str, is_admin: bool = False) -> dict | None:
    """如果用户不存在则创建（幂等操作）。"""
    try:
        return add_user(username, password, is_admin=is_admin)
    except ValueError:
        logger.debug("用户已存在，跳过创建 | username=%s", username)
        return None


def delete_user(username: str) -> bool:
    """删除用户。"""
    with _transaction() as conn:
        cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info("用户已删除 | username=%s", username)
    return deleted


# ═══════════════════════════════════════
#  修改
# ═══════════════════════════════════════

def set_user_active(username: str, active: bool) -> bool:
    """启用或禁用用户。"""
    with _transaction() as conn:
        cursor = conn.execute(
            "UPDATE users SET is_active = ? WHERE username = ?",
            (int(active), username),
        )
        updated = cursor.rowcount > 0
    if updated:
        logger.info("用户状态变更 | username=%s | active=%s", username, active)
    return updated


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """修改用户密码（需验证旧密码）。"""
    user = get_user_by_username(username)
    if user is None:
        raise ValueError(f"用户不存在: {username}")
    if not verify_password(old_password, user["password_hash"]):
        raise ValueError("旧密码错误")

    new_hash = hash_password(new_password)
    with _transaction() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )
    logger.info("密码已修改 | username=%s", username)
    return True
