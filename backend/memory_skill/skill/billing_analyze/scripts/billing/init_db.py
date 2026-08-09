"""初始化 billing 数据库：创建 billing_records / income_records 表 + records_view 视图。

数据表结构与 backend/.../billing/common.py 的分类约束一致；
records_view 统一字段：id, 名称, 大类, 细类, 金额, 平台, 日期, 收支类型, 分类, 年月
金额约定：支出为负，收入为正（供 analyze_*.py 使用）。
"""
import os
import sqlite3

try:
    from .common import DB_PATH
except ImportError:  # 直接运行 python init_db.py 时
    DB_PATH = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "billing.db")
    )


CREATE_BILLING_RECORDS = """
CREATE TABLE IF NOT EXISTS "billing_records" (
    "id"            INTEGER PRIMARY KEY AUTOINCREMENT,
    "消费名称"       TEXT,
    "消费大类"       TEXT,
    "消费细类"       TEXT,
    "类型"           TEXT,              -- 支出 / 收入
    "金额"           REAL,              -- 绝对值，方向由"类型"区分
    "支付平台"       TEXT,
    "日期"           TEXT,              -- YYYY-MM-DD
    "消费类型"       TEXT,              -- 刚性固定 / 刚性必要 / 弹性支出 / 未分类
    "备注"           TEXT
);
"""

CREATE_INCOME_RECORDS = """
CREATE TABLE IF NOT EXISTS "income_records" (
    "id"            INTEGER PRIMARY KEY AUTOINCREMENT,
    "消费名称"       TEXT,
    "消费大类"       TEXT,
    "消费细类"       TEXT,
    "类型"           TEXT,
    "金额"           REAL,
    "支付平台"       TEXT,
    "日期"           TEXT,              -- YYYY-MM-DD
    "备注"           TEXT
);
"""

# records_view：billing_records UNION ALL income_records
# 金额约定：支出为负，收入为正
# 列：id, 名称, 大类, 细类, 金额, 平台, 日期, 收支类型, 分类, 年月
CREATE_RECORDS_VIEW = """
CREATE VIEW IF NOT EXISTS "records_view" AS
SELECT
    id,
    "消费名称"                          AS "名称",
    "消费大类"                          AS "大类",
    "消费细类"                          AS "细类",
    CASE WHEN "类型" = '支出' THEN -"金额" ELSE "金额" END AS "金额",
    "支付平台"                          AS "平台",
    "日期"                              AS "日期",
    "类型"                              AS "收支类型",
    COALESCE("消费类型", '')            AS "分类",
    substr("日期", 1, 7)               AS "年月"
FROM "billing_records"
UNION ALL
SELECT
    id,
    "消费名称",
    "消费大类",
    "消费细类",
    "金额",
    "支付平台",
    "日期",
    '收入',
    '',
    substr("日期", 1, 7)
FROM "income_records";
"""


def init_db(db_path: str = DB_PATH) -> str:
    """创建表与视图，返回结果描述。"""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.isdir(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(CREATE_BILLING_RECORDS)
        cur.execute(CREATE_INCOME_RECORDS)
        cur.execute(CREATE_RECORDS_VIEW)
        conn.commit()

        # 汇总信息
        tables = [
            t[0] for t in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        views = [
            v[0] for v in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()
        ]
        counts = {t: cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
        return (
            f"✅ 数据库就绪: {os.path.abspath(db_path)}\n"
            f"   表: {tables}\n"
            f"   视图: {views}\n"
            f"   记录数: {counts}"
        )
    except sqlite3.Error as e:
        return f"❌ 初始化失败: {e}"
    finally:
        conn.close()


if __name__ == "__main__":
    print(init_db())
