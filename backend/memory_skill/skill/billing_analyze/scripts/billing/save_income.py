"""保存单条收入记录（列名与 billing_records 统一）"""
import sqlite3

try:
    from .common import (
        DB_PATH, INCOME_CATEGORY_OPTIONS, INCOME_SUBCATEGORY_OPTIONS,
        PLATFORM_OPTIONS, validate_income_category, validate_platform,
    )
except ImportError:
    from common import (  # type: ignore
        DB_PATH, INCOME_CATEGORY_OPTIONS, INCOME_SUBCATEGORY_OPTIONS,
        PLATFORM_OPTIONS, validate_income_category, validate_platform,
    )


def save_income(
    item_name: str,
    category: str,
    amount: float,
    date: str,
    platform: str = "",
    subcategory: str = "",
    note: str = "",
) -> str:
    """保存收入记录到 income_records。
    """
    if not validate_income_category(category):
        return f"❌ 收入来源 '{category}' 无效，允许: {INCOME_CATEGORY_OPTIONS}"
    if platform and not validate_platform(platform):
        return f"❌ 支付平台 '{platform}' 无效，允许: {PLATFORM_OPTIONS}"
    if subcategory and category in INCOME_SUBCATEGORY_OPTIONS:
        allowed = INCOME_SUBCATEGORY_OPTIONS[category]
        if allowed and subcategory not in allowed:
            return f"❌ 收入细类 '{subcategory}' 无效，{category} 允许: {allowed}"

    abs_amount = abs(amount)

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO income_records
               ("消费名称", "消费大类", "消费细类", "类型", "金额", "支付平台", "日期", "备注")
               VALUES (?, ?, ?, '收入', ?, ?, ?, ?)""",
            (item_name, category, subcategory or None, abs_amount, platform or None, date, note or None),
        )
        conn.commit()
        return (
            f"已保存: id={cursor.lastrowid} | {item_name} | "
            f"{category}" + (f" > {subcategory}" if subcategory else "")
            + f" | 收入 ¥{abs_amount:.2f} | {date}"
            + (f" | {platform}" if platform else "")
        )
    except sqlite3.Error as e:
        return f"❌ 保存失败: {e}"
    finally:
        conn.close()
