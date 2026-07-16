"""账单数据库综合分析 - 输出 Markdown 文档和 JSON
金额约定：支出 < 0，收入 > 0

用法：
  1. 作为 LangChain Tool：from analyze_billing import analyze_billing
  2. 作为脚本：python analyze_billing.py （生成 MD + JSON 文件）
"""
import sqlite3
import json
import os
from collections import defaultdict
from langchain.tools import tool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "billing.db"))
OUTPUT_DIR = r"F:\index_rag\knowledge-base\billing"


def _run_analysis(db_path: str, start_date: str | None = None, end_date: str | None = None) -> tuple[str, dict]:
    """核心分析逻辑，返回 (markdown, json_output)
    
    Args:
        db_path: 数据库路径
        start_date: 可选，起始日期（含），格式 "YYYY-MM-DD"
        end_date: 可选，结束日期（含），格式 "YYYY-MM-DD"
    """

    # ─── 数据读取 ───────────────────────────────────────────
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if start_date and end_date:
        cursor.execute(
            "SELECT * FROM records WHERE date >= ? AND date <= ? ORDER BY date",
            (start_date, end_date)
        )
    elif start_date:
        cursor.execute(
            "SELECT * FROM records WHERE date >= ? ORDER BY date",
            (start_date,)
        )
    elif end_date:
        cursor.execute(
            "SELECT * FROM records WHERE date <= ? ORDER BY date",
            (end_date,)
        )
    else:
        cursor.execute("SELECT * FROM records ORDER BY date")
    
    rows = cursor.fetchall()
    total = len(rows)

    # 预处理
    income_total = 0.0
    expense_total = 0.0
    income_count = 0
    expense_count = 0
    rigid_fixed_total = 0.0
    rigid_necessary_total = 0.0
    flexible_total = 0.0
    transfer_income_total = 0.0
    category_expense = defaultdict(float)
    category_income = defaultdict(float)
    category_count = defaultdict(int)
    monthly_expense = defaultdict(float)
    monthly_income = defaultdict(float)
    monthly_real_income = defaultdict(float)
    monthly_count = defaultdict(int)
    monthly_discretionary = defaultdict(float)
    monthly_discretionary_count = defaultdict(int)
    platform_stats = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0})
    amount_buckets = {"0-20": 0, "20-50": 0, "50-100": 0, "100-500": 0, "500-1000": 0, "1000+": 0}
    item_freq = defaultdict(lambda: {"count": 0, "total": 0.0})
    date_range = [None, None]

    for r in rows:
        amt = r["amount"]       # 负数=支出, 正数=收入
        cat = r["category"]
        dt = r["date"]
        plat = r["platform"]
        ym = r["year_month"]

        if date_range[0] is None:
            date_range[0] = dt
        date_range[1] = dt

        if amt > 0:  # 收入
            income_total += amt
            income_count += 1
            category_income[cat] += amt
            monthly_income[ym] += amt
            platform_stats[plat]["income"] += amt
            if cat == "转账收款":
                transfer_income_total += amt
            else:
                monthly_real_income[ym] += amt
        else:  # 支出 (amt < 0)
            expense_abs = abs(amt)
            expense_total += expense_abs
            expense_count += 1
            category_expense[cat] += expense_abs
            monthly_expense[ym] += expense_abs
            platform_stats[plat]["expense"] += expense_abs

            # 弹性消费（去掉刚性固定和刚性必要）
            et = r["expense_type"]
            if et == "刚性固定":
                rigid_fixed_total += expense_abs
            elif et == "刚性必要":
                rigid_necessary_total += expense_abs
            elif et == "弹性可选":
                flexible_total += expense_abs
            if et is None or et not in ("刚性固定", "刚性必要"):
                monthly_discretionary[ym] += expense_abs
                monthly_discretionary_count[ym] += 1

            # 金额分布（用绝对值）
            if expense_abs <= 20:
                amount_buckets["0-20"] += 1
            elif expense_abs <= 50:
                amount_buckets["20-50"] += 1
            elif expense_abs <= 100:
                amount_buckets["50-100"] += 1
            elif expense_abs <= 500:
                amount_buckets["100-500"] += 1
            elif expense_abs <= 1000:
                amount_buckets["500-1000"] += 1
            else:
                amount_buckets["1000+"] += 1

            item_key = r["item_name"]
            item_freq[item_key]["count"] += 1
            item_freq[item_key]["total"] += expense_abs

        category_count[cat] += 1
        monthly_count[ym] += 1
        platform_stats[plat]["count"] += 1

    conn.close()

    # 真实收入 = 总收入 - 转账收入
    real_income_total = income_total - transfer_income_total

    # 核心支出（去掉房租和交通出行）
    core_expense_total = expense_total - category_expense["交通出行"]
    for r in rows:
        if r["amount"] < 0 and "房租" in r["item_name"]:
            core_expense_total -= abs(r["amount"])

    net = income_total - expense_total
    months = sorted(set(list(monthly_expense.keys()) + list(monthly_income.keys())))

    # ─── 数据计算 ───────────────────────────────────────────
    real_net = real_income_total - expense_total

    # 预聚合：每个类别下的 expense_type 分布
    category_expense_type = defaultdict(lambda: {"刚性固定": 0.0, "刚性必要": 0.0, "弹性可选": 0.0})
    for r in rows:
        if r["amount"] < 0:
            et = r["expense_type"] or "未分类"
            if et in category_expense_type[r["category"]]:
                category_expense_type[r["category"]][et] += abs(r["amount"])

    sorted_cats = sorted(category_expense.items(), key=lambda x: x[1], reverse=True)
    sorted_inc = sorted(category_income.items(), key=lambda x: x[1], reverse=True) if category_income else []

    # 预聚合：每个平台的 expense_type 和 category 分布
    platform_expense_type = defaultdict(lambda: {"刚性固定": 0.0, "刚性必要": 0.0, "弹性可选": 0.0})
    platform_category = defaultdict(lambda: defaultdict(float))
    platform_transfer = defaultdict(float)
    for r in rows:
        if r["amount"] < 0:
            et = r["expense_type"] or "未分类"
            if et in platform_expense_type[r["platform"]]:
                platform_expense_type[r["platform"]][et] += abs(r["amount"])
            platform_category[r["platform"]][r["category"]] += abs(r["amount"])
        if r["amount"] > 0 and r["category"] == "转账收款":
            platform_transfer[r["platform"]] += r["amount"]

    # ─── Markdown 输出构建 ──────────────────────────────────
    md = []

    # 标题
    md.append("# 📊 个人账单综合分析报告\n\n")
    md.append(f"> 数据范围: {date_range[0]} ~ {date_range[1]}  |  总记录数: {total} 条\n\n")

    # ─── 一、收支总览
    md.append("---\n\n## 一、收支总览\n\n")

    md.append("### 💰 收入\n\n")
    md.append("| 项目 | 金额 | 占比 |\n")
    md.append("|------|------|------|\n")
    md.append(f"| 总收入 | ¥{income_total:,.2f} | — |\n")
    if income_total > 0:
        md.append(f"| **真实收入（去转账）** | **¥{real_income_total:,.2f}** | **{real_income_total / income_total * 100:.1f}%** |\n")
        md.append(f"| 　其中：转账收入 | ¥{transfer_income_total:,.2f} | {transfer_income_total / income_total * 100:.1f}% |\n")
    else:
        md.append(f"| **真实收入（去转账）** | **¥{real_income_total:,.2f}** | N/A |\n")
        md.append(f"| 　其中：转账收入 | ¥{transfer_income_total:,.2f} | N/A |\n")
    md.append("\n")

    md.append("### 💳 支出\n\n")
    md.append("| 项目 | 金额 | 占比 |\n")
    md.append("|------|------|------|\n")
    md.append(f"| 总支出 | ¥{expense_total:,.2f} | — |\n")
    if expense_total > 0:
        md.append(f"| 刚性固定 | ¥{rigid_fixed_total:,.2f} | {rigid_fixed_total / expense_total * 100:.1f}% |\n")
        md.append(f"| 刚性必要 | ¥{rigid_necessary_total:,.2f} | {rigid_necessary_total / expense_total * 100:.1f}% |\n")
        md.append(f"| 弹性可选 | ¥{flexible_total:,.2f} | {flexible_total / expense_total * 100:.1f}% |\n")
    else:
        md.append(f"| 刚性固定 | ¥{rigid_fixed_total:,.2f} | N/A |\n")
        md.append(f"| 刚性必要 | ¥{rigid_necessary_total:,.2f} | N/A |\n")
        md.append(f"| 弹性可选 | ¥{flexible_total:,.2f} | N/A |\n")
    md.append("\n")

    md.append("### 📊 净收支\n\n")
    md.append("| 口径 | 金额 |\n")
    md.append("|------|------|\n")
    md.append(f"| 总收入口径 | ¥{net:,.2f} |\n")
    md.append(f"| 真实收入口径（去转账） | ¥{real_net:,.2f} |\n")
    md.append("\n")

    # ─── 二、支出分类排名
    md.append("---\n\n## 二、支出分类排名\n\n")
    md.append("| 排名 | 类别 | 金额 | 刚性固定 | 刚性必要 | 弹性可选 | 笔数 | 占比 |\n")
    md.append("|------|------|------|------|------|------|------|------|\n")
    for i, (cat, amt) in enumerate(sorted_cats, 1):
        cnt = sum(1 for r in rows if r["category"] == cat and r["amount"] < 0)
        pct = amt / expense_total * 100 if expense_total > 0 else 0
        et_data = category_expense_type[cat]
        items = [
            str(i), cat,
            f"¥{amt:,.2f}",
            f"¥{et_data['刚性固定']:,.0f}" if et_data['刚性固定'] > 0 else "—",
            f"¥{et_data['刚性必要']:,.0f}" if et_data['刚性必要'] > 0 else "—",
            f"¥{et_data['弹性可选']:,.0f}" if et_data['弹性可选'] > 0 else "—",
            str(cnt),
            f"{pct:.1f}%",
        ]
        md.append("| " + " | ".join(items) + " |\n")
    md.append("\n")

    # ─── 收入分类
    if sorted_inc:
        md.append("### 💵 收入分类\n\n")
        md.append("| 类别 | 金额 | 占比 |\n")
        md.append("|------|------|------|\n")
        for cat, amt in sorted_inc:
            pct = amt / income_total * 100 if income_total > 0 else 0
            md.append(f"| {cat} | ¥{amt:,.2f} | {pct:.1f}% |\n")
        md.append("\n")

    # ─── 三、平台使用分布
    md.append("---\n\n## 三、平台使用分布\n\n")
    md.append("| 平台 | 支出金额 | 刚性固定 | 刚性必要 | 弹性可选 | 收入金额 | 转账 | 笔数 | 占比 | 主要类别 |\n")
    md.append("|------|------|------|------|------|------|------|------|------|------|\n")
    for plat, stats in sorted(platform_stats.items(), key=lambda x: x[1]["count"], reverse=True):
        pct = stats["count"] / total * 100 if total > 0 else 0
        et_data = platform_expense_type[plat]
        top_cats = sorted(platform_category[plat].items(), key=lambda x: x[1], reverse=True)[:3]
        cat_str = "<br>".join([f"{c} ¥{a:,.0f}" for c, a in top_cats]) if top_cats else "—"
        items = [
            plat,
            f"¥{stats['expense']:,.2f}",
            f"¥{et_data['刚性固定']:,.0f}" if et_data['刚性固定'] > 0 else "—",
            f"¥{et_data['刚性必要']:,.0f}" if et_data['刚性必要'] > 0 else "—",
            f"¥{et_data['弹性可选']:,.0f}" if et_data['弹性可选'] > 0 else "—",
            f"¥{stats['income']:,.2f}",
            f"¥{platform_transfer[plat]:,.0f}" if platform_transfer.get(plat, 0) > 0 else "—",
            str(stats["count"]),
            f"{pct:.1f}%",
            cat_str,
        ]
        md.append("| " + " | ".join(items) + " |\n")
    md.append("\n")

    # ─── JSON 输出 ────────────────────────────────────────────
    json_output = {
        "title": "个人账单综合分析报告",
        "date_range": {"start": date_range[0], "end": date_range[1]},
        "total_records": total,

        # ── 一、收支总览（对应终端三栏面板布局） ──
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
                "弹性可选": round(flexible_total, 2),
                "弹性可选_占比": f"{round(flexible_total/expense_total*100, 1)}%" if expense_total > 0 else "N/A",
            },
            "净收支": {
                "净收支_总收入口径": round(net, 2),
                "净收支_真实收入口径": round(real_net, 2),
            },
        },

        # ── 二、支出分类排名 ──
        "section_2_支出分类排名": [
            {
                "rank": i,
                "category": cat,
                "amount": round(amt, 2),
                "刚性固定": round(category_expense_type[cat]["刚性固定"], 2),
                "刚性必要": round(category_expense_type[cat]["刚性必要"], 2),
                "弹性可选": round(category_expense_type[cat]["弹性可选"], 2),
                "count": cnt,
                "percentage": f"{round(amt / expense_total * 100, 1)}%" if expense_total > 0 else "0%",
            }
            for i, (cat, amt) in enumerate(sorted_cats, 1)
            for cnt in [sum(1 for r in rows if r["category"] == cat and r["amount"] < 0)]
        ],

        # ── 三、收入分类 ──
        "section_3_收入分类": [
            {
                "category": cat,
                "amount": round(amt, 2),
                "percentage": f"{round(amt / income_total * 100, 1)}%" if income_total > 0 else "N/A",
            }
            for cat, amt in sorted_inc
        ],

        # ── 四、平台使用分布 ──
        "section_4_平台使用分布": [
            {
                "rank": i,
                "platform": plat,
                "expense": round(stats["expense"], 2),
                "刚性固定": round(platform_expense_type[plat]["刚性固定"], 2),
                "刚性必要": round(platform_expense_type[plat]["刚性必要"], 2),
                "弹性可选": round(platform_expense_type[plat]["弹性可选"], 2),
                "income": round(stats["income"], 2),
                "transfer_income": round(platform_transfer.get(plat, 0), 2),
                "count": stats["count"],
                "percentage": f"{round(stats['count'] / total * 100, 1)}%" if total > 0 else "N/A",
                "top_3_categories": [
                    {"category": c, "amount": round(a, 2)}
                    for c, a in sorted(platform_category[plat].items(), key=lambda x: x[1], reverse=True)[:3]
                ],
            }
            for i, (plat, stats) in enumerate(sorted(platform_stats.items(), key=lambda x: x[1]["count"], reverse=True), 1)
        ],
    }

    return "".join(md), json_output


@tool
def analyze_billing(start_date: str | None = None, end_date: str | None = None) -> dict:
    """账单综合分析 - 收支总览、支出分类排名、收入分类、平台使用分布。
    金额约定：支出 < 0，收入 > 0。
    
    Args:
        start_date: 可选，起始日期（含），格式 "YYYY-MM-DD"，如 "2025-01-01"
        end_date: 可选，结束日期（含），格式 "YYYY-MM-DD"，如 "2025-06-30"
    """
    _, json_output = _run_analysis(DB_PATH, start_date=start_date, end_date=end_date)
    return json_output


if __name__ == "__main__":
    import sys

    # 支持命令行参数: python analyze_billing.py [start_date] [end_date]
    # 例如: python analyze_billing.py 2025-01-01 2025-06-30
    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date = sys.argv[2] if len(sys.argv) > 2 else None

    md_str, json_output = _run_analysis(DB_PATH, start_date=start_date, end_date=end_date)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 如果指定了时间范围，文件名带上时间范围标识
    if start_date or end_date:
        suffix = f"_{start_date or 'begin'}_to_{end_date or 'end'}"
        md_filename = f"billing_report{suffix}.md"
        json_filename = f"billing_summary{suffix}.json"
    else:
        md_filename = "billing_report.md"
        json_filename = "billing_summary.json"

    md_path = os.path.join(OUTPUT_DIR, md_filename)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_str)

    json_path = os.path.join(OUTPUT_DIR, json_filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)

    print(f"报告已生成: {md_path}")
    print(f"JSON 已生成: {json_path}")
