import sqlite3
from backend.config.env_settings import CHECKPOINT_DB


def list_all_threads(username: str) -> list[dict]:
    """从 SQLite checkpoints 表查询指定用户的线程 ID 及消息数。

    Args:
        username: 用户名，用于按前缀过滤线程（username:thread_id）。
    """
    prefix = f"{username}:%"
    conn = sqlite3.connect(CHECKPOINT_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT thread_id, COUNT(*) AS cnt
            FROM checkpoints
            WHERE thread_id LIKE ?
            GROUP BY thread_id
            ORDER BY MIN(rowid) DESC
        """, (prefix,))
        rows = cursor.fetchall()
        prefix_len = len(username) + 1  # 去掉 "username:" 前缀
        return [
            {
                "thread_id": row[0][prefix_len:],
                "message_count": row[1],
            }
            for row in rows
        ]
    finally:
        conn.close()
