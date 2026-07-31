"""定时任务数据库层 —— SQLite 存储用户定时任务（按 username 隔离）。

表结构:
    CREATE TABLE IF NOT EXISTS scheduled_tasks (
        id             TEXT PRIMARY KEY,
        username       TEXT NOT NULL,
        title          TEXT,
        message        TEXT NOT NULL,
        execute_hour   INTEGER NOT NULL,   -- 0-23（24小时制）
        execute_minute INTEGER NOT NULL,   -- 0-59
        is_active      INTEGER DEFAULT 1,
        last_run_at    TEXT,               -- 上次执行时间（防重复执行）
        created_at     TEXT DEFAULT (datetime('now'))
    )
"""

import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager

from backend.config.logger import get_logger

logger = get_logger(__name__)

DB_PATH = str(Path("data/scheduled_tasks.db").resolve())
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def _transaction():
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
    conn = _get_conn()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """创建定时任务表。"""
    with _transaction() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id             TEXT PRIMARY KEY,
                username       TEXT NOT NULL,
                title          TEXT,
                message        TEXT NOT NULL,
                execute_hour   INTEGER NOT NULL,
                execute_minute INTEGER NOT NULL,
                is_active      INTEGER DEFAULT 1,
                last_run_at    TEXT,
                created_at     TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_username ON scheduled_tasks(username)"
        )
        logger.info("定时任务表初始化完成 | db=%s", DB_PATH)


def create_task(task_id: str, username: str, title: str, message: str,
                execute_hour: int, execute_minute: int) -> dict | None:
    """创建定时任务。"""
    with _transaction() as conn:
        conn.execute(
            """INSERT INTO scheduled_tasks (id, username, title, message, execute_hour, execute_minute)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task_id, username, title, message, execute_hour, execute_minute),
        )
    logger.info("定时任务创建 | id=%s | username=%s | time=%02d:%02d",
                task_id, username, execute_hour, execute_minute)
    return get_task(task_id, username)


def get_task(task_id: str, username: str) -> dict | None:
    """获取指定任务（按 username 隔离）。"""
    with _query() as conn:
        row = conn.execute(
            "SELECT * FROM scheduled_tasks WHERE id = ? AND username = ?",
            (task_id, username),
        ).fetchone()
    return dict(row) if row else None


def list_tasks(username: str) -> list[dict]:
    """列出指定用户的所有定时任务。"""
    with _query() as conn:
        rows = conn.execute(
            "SELECT * FROM scheduled_tasks WHERE username = ? ORDER BY created_at DESC",
            (username,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_task(task_id: str, username: str, **fields) -> dict | None:
    """更新定时任务（仅允许特定字段）。"""
    allowed = {"title", "message", "execute_hour", "execute_minute", "is_active", "last_run_at"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_task(task_id, username)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id, username]
    with _transaction() as conn:
        conn.execute(
            f"UPDATE scheduled_tasks SET {set_clause} WHERE id = ? AND username = ?",
            values,
        )
    return get_task(task_id, username)


def delete_task(task_id: str, username: str) -> bool:
    """删除定时任务。"""
    with _transaction() as conn:
        cursor = conn.execute(
            "DELETE FROM scheduled_tasks WHERE id = ? AND username = ?",
            (task_id, username),
        )
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info("定时任务删除 | id=%s | username=%s", task_id, username)
    return deleted


def get_due_tasks(current_hour: int, current_minute: int, today_str: str) -> list[dict]:
    """获取当前时间点需要执行的任务（排除今天已执行的）。

    Args:
        current_hour: 当前小时（0-23）
        current_minute: 当前分钟（0-59）
        today_str: 今日日期字符串（YYYY-MM-DD），用于防止重复执行

    Returns:
        待执行任务列表。
    """
    with _query() as conn:
        rows = conn.execute(
            """SELECT * FROM scheduled_tasks
               WHERE is_active = 1
               AND execute_hour = ?
               AND execute_minute = ?
               AND (last_run_at IS NULL OR last_run_at != ?)
            """,
            (current_hour, current_minute, today_str),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_task_run(task_id: str, username: str, run_at: str) -> None:
    """标记任务已执行（更新 last_run_at）。"""
    with _transaction() as conn:
        conn.execute(
            "UPDATE scheduled_tasks SET last_run_at = ? WHERE id = ? AND username = ?",
            (run_at, task_id, username),
        )
