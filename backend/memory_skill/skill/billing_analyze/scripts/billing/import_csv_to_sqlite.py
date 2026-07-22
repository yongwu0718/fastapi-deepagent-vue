import csv
import os
from sqlite_utils import Database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "billing.db")
# 向上 6 级到项目根，再定位 CSV
PROJECT_ROOT = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "..", "..", "..", ".."))
CSV_PATH = os.path.join(PROJECT_ROOT, "billing_数据表.csv")


def create_db():
    """使用 sqlite-utils 创建 SQLite 数据库和表（id 自增）"""
    db = Database(DB_PATH)

    db["records"].create(
        {
            "id": int,
            "item_name": str,
            "category": str,
            "amount": float,
            "date": str,
            "platform": str,
            "year_month": str,
            "expense_type": str,
        },
        pk="id",
        if_not_exists=True,
    )

    # 创建索引以加速常见查询
    db["records"].create_index(["date"], if_not_exists=True)
    db["records"].create_index(["year_month"], if_not_exists=True)
    db["records"].create_index(["category"], if_not_exists=True)

    print(f"数据库已创建: {DB_PATH}")


def convert_date(date_str: str) -> str:
    """将 2025/09/03 转换为 2025-09-03"""
    return date_str.replace("/", "-")


def import_csv():
    """从 billing_数据表.csv 导入数据到 SQLite（id 自增，列名与 CSV 一致）"""
    db = Database(DB_PATH)

    # 清空旧数据
    table = db["records"]
    table.delete_where()

    records = []
    skipped = 0
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 跳过空行
            if not row.get("item_name", "").strip():
                skipped += 1
                continue

            rec = {}
            for key in row:
                if key == "id":
                    continue  # id 自增，不导入
                val = row[key].strip()
                if key == "amount":
                    rec[key] = float(val) if val else 0.0
                elif key == "date":
                    rec[key] = convert_date(val)
                else:
                    rec[key] = val
            records.append(rec)

    if skipped:
        print(f"跳过 {skipped} 条无效记录")

    # 批量插入，id 自增
    table.insert_all(records)
    print(f"导入完成: {len(records)} 条记录")


def show_stats():
    """展示导入后的基本统计"""
    db = Database(DB_PATH)

    total = db["records"].count
    days = db.execute("SELECT COUNT(DISTINCT date) FROM records").fetchone()[0]

    date_range = list(db.query("SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM records"))[0]

    expense_count = db.execute("SELECT COUNT(*) FROM records WHERE amount < 0").fetchone()[0]
    expense_total = db.execute("SELECT ROUND(SUM(amount), 2) FROM records WHERE amount < 0").fetchone()[0] or 0
    income_count = db.execute("SELECT COUNT(*) FROM records WHERE amount > 0").fetchone()[0]
    income_total = db.execute("SELECT ROUND(SUM(amount), 2) FROM records WHERE amount > 0").fetchone()[0] or 0

    platform_count = db.execute("SELECT COUNT(DISTINCT platform) FROM records").fetchone()[0]
    category_count = db.execute("SELECT COUNT(DISTINCT category) FROM records").fetchone()[0]

    print(f"\n===== 导入统计 =====")
    print(f"总记录数: {total}")
    print(f"记录天数: {days}")
    print(f"日期范围: {date_range['min_date']} ~ {date_range['max_date']}")
    print(f"支出: {expense_count} 条, 合计 {expense_total:,.2f} 元")
    print(f"收入: {income_count} 条, 合计 {income_total:,.2f} 元")
    print(f"交易平台: {platform_count} 种")
    print(f"收支类别: {category_count} 种")


if __name__ == "__main__":
    create_db()
    import_csv()
    show_stats()
