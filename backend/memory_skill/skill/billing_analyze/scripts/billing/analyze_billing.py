import sqlite3
import sys
import json
from collections import defaultdict

try:
    from .common import DB_PATH, build_date_filter
except ImportError:
    from common import DB_PATH, build_date_filter  # type: ignore


def _run_analysis(db_path: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    """核心分析逻辑，返回 json_output，从 billing_records + income_records 读取

    Args:
        db_path: 数据库路径
        start_date: 可选，起始日期（含），格式 "YYYY-MM-DD"
        end_date: 可选，结束日期（含），格式 "YYYY-MM-DD"
    """
    # ─── 数据读取 ───────────────────────────────────────────
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 支出来自 billing_records（金额为负，收支类型=支出，分类=消费类型）
    _exp_where, _exp_params = build_date_filter("类型 = '支出'", start_date, end_date)
    cursor.execute(f"SELECT * FROM billing_records WHERE {_exp_where} ORDER BY 日期", _exp_params)
    rows = [
        {
            "日期": r["日期"],
            "名称": r["消费名称"],
            "大类": r["消费大类"],
            "细类": r["消费细类"] or "未分类",
            "金额": -abs(r["金额"]),
            "平台": r["支付平台"],
            "收支类型": "支出",
            "分类": r["消费类型"] or "未分类",
            "年月": r["日期"][:7],
        }
        for r in cursor.fetchall()
    ]

    # 收入来自 income_records（金额为正，收支类型=收入，无"消费类型"列分类置空）
    _inc_where, _inc_params = build_date_filter("类型 = '收入'", start_date, end_date)
    cursor.execute(f"SELECT * FROM income_records WHERE {_inc_where} ORDER BY 日期", _inc_params)
    for r in cursor.fetchall():
        rows.append({
            "日期": r["日期"],
            "名称": r["消费名称"],
            "大类": r["消费大类"],
            "细类": r["消费细类"] or "未分类",
            "金额": abs(r["金额"]),
            "平台": r["支付平台"],
            "收支类型": "收入",
            "分类": "",
            "年月": r["日期"][:7],
        })

    conn.close()
    total = len(rows)

    # ─── 预处理 ────────────────────────────────────────────
    income_total = 0.0
    expense_total = 0.0
    rigid_fixed_total = 0.0
    rigid_necessary_total = 0.0
    flexible_total = 0.0
    transfer_income_total = 0.0

    # 大类维度
    category_expense = defaultdict(float)
    category_income = defaultdict(float)

    # 收入维度 — 大类和细类映射
    category_subcategory_income = defaultdict(lambda: defaultdict(float))    # 大类 → {细类: 金额}

    # 平台维度
    platform_stats = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0})

    # 日期范围
    date_range = [None, None]

    for r in rows:
        amt = r["金额"]           # 支出为负, 收入为正
        big_cat = r["大类"]
        sub_cat = r["细类"] or "未分类"
        dt = r["日期"]
        plat = r["平台"]
        is_expense = r["收支类型"] == "支出"

        # 日期范围
        if date_range[0] is None:
            date_range[0] = dt
        date_range[1] = dt

        if not is_expense:  # 收入
            income_total += amt
            category_income[big_cat] += amt
            category_subcategory_income[big_cat][sub_cat] += amt
            platform_stats[plat]["income"] += amt

            if big_cat == "转账收款":
                transfer_income_total += amt
        else:  # 支出
            expense_abs = abs(amt)
            expense_total += expense_abs
            category_expense[big_cat] += expense_abs
            platform_stats[plat]["expense"] += expense_abs

            et = r["分类"] or "未分类"
            if et == "刚性固定":
                rigid_fixed_total += expense_abs
            elif et == "刚性必要":
                rigid_necessary_total += expense_abs
            elif et == "弹性支出":
                flexible_total += expense_abs

        platform_stats[plat]["count"] += 1

    # ─── 汇总计算 ──────────────────────────────────────────
    real_income_total = income_total - transfer_income_total
    net = income_total - expense_total
    real_net = real_income_total - expense_total

    # 核心支出（去掉住房和交通 — 最必要的刚性支出类别）
    core_expense_total = expense_total - category_expense.get("交通", 0) - category_expense.get("住房", 0)

    # ─── 预聚合：平台维度 ──────────────────────────────────
    platform_expense_type = defaultdict(lambda: {"刚性固定": 0.0, "刚性必要": 0.0, "弹性支出": 0.0})
    platform_category = defaultdict(lambda: defaultdict(float))
    platform_transfer = defaultdict(float)
    for r in rows:
        if r["收支类型"] == "支出":
            et = r["分类"] or "未分类"
            if et in platform_expense_type[r["平台"]]:
                platform_expense_type[r["平台"]][et] += abs(r["金额"])
            platform_category[r["平台"]][r["大类"]] += abs(r["金额"])
        if not r["收支类型"] == "支出" and r["大类"] == "转账收款":
            platform_transfer[r["平台"]] += r["金额"]

    # ─── 排序 ─────────────────────────────────────────────
    sorted_inc = sorted(category_income.items(), key=lambda x: x[1], reverse=True) if category_income else []

    # ─── JSON 输出 ────────────────────────────────────────
    json_output = {
        "title": "个人账单综合分析报告",
        "date_range": {"start": date_range[0], "end": date_range[1]},
        "total_records": total,

        # ── 一、收支总览 ──
        "section_1_收支总览": {
            "收入": {
                "总收入": round(income_total, 2),
                "真实收入_去转账": round(real_income_total, 2),
                "真实收入_占总收入比例": f"{round(real_income_total/income_total*100, 1)}%" if income_total > 0 else "N/A",
                "转账收入": round(transfer_income_total, 2),
                "转账收入_占总收入比例": f"{round(transfer_income_total/income_total*100, 1)}%" if income_total > 0 else "N/A",
            },
            "支出": {
                "总支出": round(expense_total, 2),
                "刚性固定": round(rigid_fixed_total, 2),
                "刚性固定_占比": f"{round(rigid_fixed_total/expense_total*100, 1)}%" if expense_total > 0 else "N/A",
                "刚性必要": round(rigid_necessary_total, 2),
                "刚性必要_占比": f"{round(rigid_necessary_total/expense_total*100, 1)}%" if expense_total > 0 else "N/A",
                "弹性支出": round(flexible_total, 2),
                "弹性支出_占比": f"{round(flexible_total/expense_total*100, 1)}%" if expense_total > 0 else "N/A",
            },
            "净收支": {
                "净收支_总收入口径": round(net, 2),
                "净收支_真实收入口径": round(real_net, 2),
            },
            "核心支出_去掉住房交通": {
                "金额": round(core_expense_total, 2),
                "占总支出比例": f"{round(core_expense_total / expense_total * 100, 1)}%" if expense_total > 0 else "N/A",
                "说明": "总支出扣除住房和交通后的弹性核心消费",
            },
        },

        # ── 二、收入分类（含细类拆解） ──
        "section_2_收入分类": [
            {
                "category": cat,
                "amount": round(amt, 2),
                "percentage": f"{round(amt / income_total * 100, 1)}%" if income_total > 0 else "N/A",
                "subcategories": [
                    {
                        "subcategory": sub,
                        "amount": round(sub_amt, 2),
                    }
                    for sub, sub_amt in sorted(
                        category_subcategory_income.get(cat, {}).items(),
                        key=lambda x: x[1], reverse=True
                    )
                ],
            }
            for cat, amt in sorted_inc
        ],

        # ── 三、平台使用分布 ──
        "section_3_平台使用分布": [
            {
                "rank": i,
                "platform": plat,
                "expense": round(stats["expense"], 2),
                "刚性固定": round(platform_expense_type[plat]["刚性固定"], 2),
                "刚性必要": round(platform_expense_type[plat]["刚性必要"], 2),
                "弹性支出": round(platform_expense_type[plat]["弹性支出"], 2),
                "income": round(stats["income"], 2),
                "transfer_income": round(platform_transfer.get(plat, 0), 2),
                "count": stats["count"],
                "percentage": f"{round(stats['count'] / total * 100, 1)}%" if total > 0 else "N/A",
                "top_3_categories": [
                    {"category": c, "amount": round(a, 2)}
                    for c, a in sorted(platform_category[plat].items(), key=lambda x: x[1], reverse=True)[:3]
                ],
            }
            for i, (plat, stats) in enumerate(
                sorted(platform_stats.items(), key=lambda x: x[1]["count"], reverse=True), 1
            )
        ],

    }

    return json_output


def analyze_billing(start_date: str | None = None, end_date: str | None = None) -> dict:
    """账单综合分析 - 收支总览、支出分类排名（含细类）、收入分类（含细类）、
    支出细类排名、平台使用分布、金额分布、高频消费。

    金额约定：支出 < 0，收入 > 0（构建 rows 时统一）。
    数据来源：支出=billing_records，收入=income_records。

    Args:
        start_date: 可选，起始日期（含），格式 "YYYY-MM-DD"
        end_date: 可选，结束日期（含），格式 "YYYY-MM-DD"
    """
    return _run_analysis(DB_PATH, start_date=start_date, end_date=end_date)


if __name__ == "__main__":

    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date = sys.argv[2] if len(sys.argv) > 2 else None

    json_output = _run_analysis(DB_PATH, start_date=start_date, end_date=end_date)
    print(json.dumps(json_output, ensure_ascii=False, indent=2))
