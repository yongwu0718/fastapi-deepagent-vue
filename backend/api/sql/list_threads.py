import sqlite3
from backend.config.env_settings import CHECKPOINT_DB


def list_all_threads() -> list[dict]:
    """从 SQLite checkpoints 表查询所有线程 ID 及消息数"""
    conn = sqlite3.connect(CHECKPOINT_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT thread_id, COUNT(*) AS cnt
            FROM checkpoints
            GROUP BY thread_id
            ORDER BY MIN(rowid) DESC
        """)
        rows = cursor.fetchall()
        return [
            {
                "thread_id": row[0],
                "message_count": row[1],
            }
            for row in rows
        ]
    finally:
        conn.close()
