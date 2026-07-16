"""保存单条账单记录到 SQLite 数据库"""
import os
import sqlite3
from langchain.tools import tool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "billing.db"))

@tool
def save_bill(
    item_name: str,
    category: str,
    amount: float,
    date: str,
    platform: str,
    year_month: str,
    expense_type: str = "",
) -> str:
    """保存一条账单记录到 billing.db 的 records 表中。

    Args:
        item_name: 消费项目名称，如 "胜香斋"
        category: 消费种类，如 "食品"、"生活缴费"、"交通出行"、"数码电子"、
            "购物消费"、"饮品"、"服饰鞋包"、"保险保障"、"医疗健康"、"娱乐休闲"、
            "其他支出"、"转账收款"，必须使用预定义的值.
        amount: 金额，支出为负数，收入为正数
        date: 日期，格式 "YYYY-MM-DD"
        platform: 交易平台，如 "微信"、"支付宝"、"中国银行"、"京东"、"淘宝" 等
        year_month: 年月，格式 "YYYY-MM"
        expense_type: 支出类型，"弹性可选"、"刚性固定"、"刚性必要"，收入时可为空
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO records (item_name, category, amount, date, platform, year_month, expense_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (item_name, category, amount, date, platform, year_month, expense_type),
        )
        conn.commit()
        new_id = cursor.lastrowid
        return f"已保存: id={new_id}, {item_name} | {category} | {amount}元 | {date} | {platform}"
    except sqlite3.Error as e:
        return f"保存失败: {e}"
    finally:
        conn.close()
