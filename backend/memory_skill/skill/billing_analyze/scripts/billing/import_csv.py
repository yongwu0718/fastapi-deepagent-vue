"""把清洗后的微信账单 CSV 导入 billing.db 数据库。

- 类型=支出  → billing_records（含"消费类型"列）
- 类型=收入  → income_records（无"消费类型"列）
CSV 列：消费名称, 消费大类, 消费细类, 类型, 金额, 支付平台, 日期, 消费类型, 备注
"""
import csv
import os
import sqlite3

try:
    from .common import DB_PATH
except ImportError:  # 直接运行
    DB_PATH = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "billing.db")
    )

DEFAULT_CSV = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "微信账单_清洗后.csv")
)


def import_csv(csv_path: str = DEFAULT_CSV, db_path: str = DB_PATH) -> str:
    """导入 CSV，返回结果描述。"""
    if not os.path.isfile(csv_path):
        return f"❌ 找不到 CSV: {csv_path}"

    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    inserted_expense = 0
    inserted_income = 0
    errors = []

    try:
        cur = conn.cursor()
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("消费名称") or "").strip()
                category = (row.get("消费大类") or "").strip()
                subcategory = (row.get("消费细类") or "").strip()
                direction = (row.get("类型") or "").strip()
                amount = float(row.get("金额") or 0)
                platform = (row.get("支付平台") or "").strip()
                date = (row.get("日期") or "").strip()
                expense_type = (row.get("消费类型") or "").strip()
                note = (row.get("备注") or "").strip()

                if direction == "收入":
                    cur.execute(
                        """INSERT INTO income_records
                           ("消费名称", "消费大类", "消费细类", "类型", "金额", "支付平台", "日期", "备注")
                           VALUES (?, ?, ?, '收入', ?, ?, ?, ?)""",
                        (name, category, subcategory or None,
                         abs(amount), platform or None, date, note or None),
                    )
                    inserted_income += 1
                else:
                    cur.execute(
                        """INSERT INTO billing_records
                           ("消费名称", "消费大类", "消费细类", "类型", "金额", "支付平台", "日期", "消费类型", "备注")
                           VALUES (?, ?, ?, '支出', ?, ?, ?, ?, ?)""",
                        (name, category, subcategory or None,
                         abs(amount), platform or None, date, expense_type or None, note or None),
                    )
                    inserted_expense += 1
        conn.commit()
    except (sqlite3.Error, ValueError, KeyError) as e:
        errors.append(str(e))
        conn.rollback()
    finally:
        conn.close()

    if errors:
        return f"❌ 导入失败（已回滚）: {errors}"

    return (
        f"✅ 导入完成\n"
        f"   支出(billing_records): {inserted_expense} 条\n"
        f"   收入(income_records): {inserted_income} 条\n"
        f"   数据源: {csv_path}"
    )


if __name__ == "__main__":
    import sys
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    print(import_csv(csv_arg))
