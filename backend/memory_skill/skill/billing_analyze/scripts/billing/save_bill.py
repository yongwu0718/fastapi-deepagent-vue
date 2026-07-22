"""保存单条账单记录"""
import sqlite3

try:
    from .common import (
        DB_PATH, CATEGORY_OPTIONS, EXPENSE_TYPE_OPTIONS,
        DIRECTION_OPTIONS, PLATFORM_OPTIONS, INCOME_CATEGORY_OPTIONS,
        SUBCATEGORY_OPTIONS, INCOME_SUBCATEGORY_OPTIONS,
        validate_category, validate_expense_type, validate_income_category,
        validate_subcategory,
    )
except ImportError:
    from common import (  # type: ignore
        DB_PATH, CATEGORY_OPTIONS, EXPENSE_TYPE_OPTIONS,
        DIRECTION_OPTIONS, PLATFORM_OPTIONS, INCOME_CATEGORY_OPTIONS,
        SUBCATEGORY_OPTIONS, INCOME_SUBCATEGORY_OPTIONS,
        validate_category, validate_expense_type, validate_income_category,
        validate_subcategory,
    )


def save_bill(
    item_name: str,
    category: str,
    amount: float,
    date: str,
    platform: str = "",
    subcategory: str = "",
    expense_type: str = "",
    direction: str = "支出",
    note: str = "",
) -> str:
    """保存一条记录到 billing_records。

    Args:
        item_name:   消费名称，如 "鑫面客皖北正宗板面"
        category:    消费大类，必须属于 CATEGORY_OPTIONS
        amount:      金额（绝对值）
        date:        日期 "YYYY-MM-DD"
        platform:    支付平台，如 "微信"
        subcategory: 消费细类
        expense_type: 消费类型，必须属于 EXPENSE_TYPE_OPTIONS
        direction:   "支出" 或 "收入"
        note:        备注

    分类约束：
        消费大类: {CATEGORY_OPTIONS}
        消费细类: 必须属于对应大类的 SUBCATEGORY_OPTIONS[category]
        消费类型: {EXPENSE_TYPE_OPTIONS}
        支付平台: {PLATFORM_OPTIONS}

    Returns:
        成功/失败的描述字符串
    """
    # 校验
    if not validate_category(category):
        return f"❌ 消费大类 '{category}' 无效，允许: {CATEGORY_OPTIONS}"
    if expense_type and not validate_expense_type(expense_type):
        return f"❌ 消费类型 '{expense_type}' 无效，允许: {EXPENSE_TYPE_OPTIONS}"
    if subcategory and not validate_subcategory(category, subcategory):
        return (f"❌ 消费细类 '{subcategory}' 不属于 '{category}'，"
                f"允许: {SUBCATEGORY_OPTIONS.get(category, [])}")
    if direction not in DIRECTION_OPTIONS:
        return f"❌ 类型 '{direction}' 无效，允许: {DIRECTION_OPTIONS}"

    abs_amount = abs(amount)

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO billing_records
               ("消费名称", "消费大类", "消费细类", "类型", "金额", "支付平台", "日期", "消费类型", "备注")
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item_name, category, subcategory or None,
             direction, abs_amount, platform or None,
             date, expense_type or None, note or None),
        )
        conn.commit()
        return (
            f"已保存: id={cursor.lastrowid} | {item_name} | "
            f"{category}" + (f" > {subcategory}" if subcategory else "") +
            f" | {direction} ¥{abs_amount:.2f} | {date}"
            + (f" | {platform}" if platform else "") +
            (f" | {expense_type}" if expense_type else "")
        )
    except sqlite3.Error as e:
        return f"❌ 保存失败: {e}"
    finally:
        conn.close()


# ─── 分类查询辅助 ──────────────────────────────────────────

def list_categories() -> dict:
    """返回所有分类选项，供模型参考"""
    return {
        "消费大类": CATEGORY_OPTIONS,
        "消费细类": SUBCATEGORY_OPTIONS,
        "消费类型": EXPENSE_TYPE_OPTIONS,
        "收支类型": DIRECTION_OPTIONS,
        "支付平台": PLATFORM_OPTIONS,
        "收入来源": INCOME_CATEGORY_OPTIONS,
        "收入细类": INCOME_SUBCATEGORY_OPTIONS,
    }
