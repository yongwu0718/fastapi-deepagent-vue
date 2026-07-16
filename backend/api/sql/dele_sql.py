import sqlite3
from backend.config.env_settings import CHECKPOINT_DB

# 要删除的线程ID
def delete_thread_messages_history(thread_id: str):
    DB_PATH = CHECKPOINT_DB
    TABLE_NAMES = ["checkpoints", "writes"]   # 多张表
    THREAD_ID_COL = "thread_id"               # 列名

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_deleted = 0
    deleted_details = {}

    try:
        for table in TABLE_NAMES:
            cursor.execute(
                f"DELETE FROM {table} WHERE {THREAD_ID_COL} = ?",
                (thread_id,)
            )
            rowcount = cursor.rowcount
            deleted_details[table] = rowcount
            total_deleted += rowcount
            print(f"表 [{table}] 已删除线程ID: {thread_id}，影响行数: {rowcount}")

        conn.commit()
        # ✅ 返回删除结果
        return {
            "status": "success",
            "message": "会话历史记录已删除",
        }
    except Exception as e:
        conn.rollback()  # 发生错误时回滚
        return {
            "status": "error",
            "message": f"删除失败: {str(e)}"
        }
    finally:
        conn.close()