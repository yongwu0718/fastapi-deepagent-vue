"""billing_analyze 公共模块 —— 路径、日期过滤、expense_type、分类约束"""

import os
# ─── 路径常量 ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库路径：scripts/data/billing.db
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "billing.db"))

# ─── 分类约束（模型生成脚本时必须遵守）───────────────────────
# 消费大类（按"消费目的/场景"划分，大类间互斥）
CATEGORY_OPTIONS = [
    "餐饮",    # 正餐、外卖、堂食、食材、零食、饮品
    "交通",    # 公交地铁、打车、加油、停车、大巴、车辆维护
    "住房",    # 居住固定支出：房租、房贷、水电、燃气、物业、维修
    "购物",    # 实物商品：日用消耗、服饰鞋包、数码电子、护肤美妆
    "居家",    # 家居耐用品：家具、家电、装修、家纺、厨具
    "娱乐",    # 精神消费：电影、游戏、旅游、健身、聚会
    "医疗",    # 健康：药品、检查、挂号、牙科
    "通讯",    # 话费、宽带、AI服务
    "其他",    # 兜底：人情红包、教育培训、杂项等无法归入上述分类
]

# 消费类型
EXPENSE_TYPE_OPTIONS = [
    "刚性固定",   # 房租、房贷等每月固定不变
    "刚性必要",   # 通勤等必须但金额可变
    "弹性支出",   # 吃饭、娱乐、购物等可选消费
    "未分类",     # 缺失/未识别
]

# 收支类型
DIRECTION_OPTIONS = ["支出", "收入"]

# 支付平台
PLATFORM_OPTIONS = ["微信", "支付宝", "银行卡", "现金", "其他"]

# 消费细类（按大类分组）
# 维度规则：先按场景，场景不适用再按类型
SUBCATEGORY_OPTIONS: dict[str, list[str]] = {
    "餐饮": ["外卖", "堂食", "食材", "零食", "饮料", "奶茶咖啡"],
    "交通": ["公交地铁", "打车","大巴", "车辆维护","电池"],
    "住房": ["房租","水电", "燃气", "物业", "维修"],
    "购物": ["日用消耗", "服饰鞋包", "数码电子", "护肤美妆"],
    "居家": ["家具", "家电", "装修", "家纺", "厨具"],
    "娱乐": ["电影", "游戏充值", "健身", "旅游", "聚会"],
    "医疗": ["药品", "检查", "挂号", "牙科","保险"],
    "通讯": ["话费", "宽带", "AI服务","会员续费"],
    "其他": ["人情红包", "教育培训", "杂项"],
}

# 收入来源分类
INCOME_CATEGORY_OPTIONS = [
    "工资",      # 月薪、年终奖
    "兼职",      # 副业、零工
    "理财收益",   # 余额宝、基金、股票、利息
    "转账收款",   # 他人转账
    "红包",      # 微信红包、转账红包
    "报销",      # 公司报销、差旅报销
    "退款",      # 购物退款、押金退还
    "其他",      # 无法归入上述分类
]

# 收入细类（按来源分组）
INCOME_SUBCATEGORY_OPTIONS: dict[str, list[str]] = {
    "工资":     ["月薪", "年终奖", "绩效奖金"],
    "兼职":     ["副业", "零工"],
    "理财收益":  ["余额宝", "基金", "股票", "银行利息"],
    "转账收款":  ["他人转账"],
    "红包":     ["微信红包"],
    "报销":     ["差旅报销", "加班报销"],
    "退款":     ["购物退款", "押金退还"],
    "其他":     [],
}


# ─── 校验函数 ───────────────────────────────────────────────

def validate_category(category: str) -> bool:
    """验证消费大类是否在允许范围内"""
    return category in CATEGORY_OPTIONS


def validate_platform(platform: str) -> bool:
    """验证支付平台是否在允许范围内"""
    return not platform or platform in PLATFORM_OPTIONS


def validate_expense_type(expense_type: str) -> bool:
    """验证消费类型是否在允许范围内"""
    return expense_type in EXPENSE_TYPE_OPTIONS


def validate_income_category(category: str) -> bool:
    """验证收入来源是否在允许范围内"""
    return category in INCOME_CATEGORY_OPTIONS


def validate_subcategory(category: str, subcategory: str) -> bool:
    """验证消费细类是否属于对应大类。

    未知大类返回 False（严格校验，避免脏数据绕过）。
    调用方应先校验大类（validate_category）再调用本函数。
    """
    if category not in SUBCATEGORY_OPTIONS:
        return False
    return subcategory in SUBCATEGORY_OPTIONS[category]


def get_subcategory_options(category: str) -> list[str]:
    """获取指定大类的细类选项"""
    return SUBCATEGORY_OPTIONS.get(category, [])


# ─── 公共工具函数 ───────────────────────────────────────────
def build_date_filter(
    base_where: str,
    start_date: str | None = None,
    end_date: str | None = None,
    date_column: str = "日期",
) -> tuple[str, tuple]:
    """构建带日期过滤的 WHERE 子句，返回 (where_clause, params)
    
    Args:
        base_where: 基础 WHERE 条件（如 "金额 < 0"）
        start_date: 可选，起��日期（含），格式 "YYYY-MM-DD"
        end_date: 可选，结束日期（含），格式 "YYYY-MM-DD"
        date_column: 日期列名，默认 "日期"（records_view/records 视图统一使用此列名）
    """
    conditions = [base_where]
    params = []
    if start_date:
        conditions.append(f"{date_column} >= ?")
        params.append(start_date)
    if end_date:
        conditions.append(f"{date_column} <= ?")
        params.append(end_date)
    return " AND ".join(conditions), tuple(params)


def get_expense_type(r: dict) -> str:
    """获取统一 expense_type，兼容 records_view 中文列名、sqlite3.Row 和旧英文字段名"""
    # 优先取中文列名"分类"，兼容 sqlite3.Row 和普通 dict
    for key in ("分类", "expense_type", "expenseType"):
        try:
            v = r[key] if key in (r.keys() if hasattr(r, "keys") else []) else None
            if v:
                return v
        except (KeyError, TypeError):
            pass
    return "未分类"
