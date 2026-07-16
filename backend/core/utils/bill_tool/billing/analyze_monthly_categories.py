"""每月类别排名（支出+收入）- 输出 Markdown 文档和 JSON
金额约定：支出 < 0，收入 > 0

用法：
  1. 作为 LangChain Tool：from analyze_monthly_categories import analyze_monthly_categories
  2. 作为脚本：python analyze_monthly_categories.py （生成 MD + JSON 文件）
"""
import sqlite3
import json
import os
from collections import defaultdict
from langchain.tools import tool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "billing.db"))
OUTPUT_DIR = r"F:\index_rag\knowledge-base\billing"


def _build_date_filter(base_where: str, start_date: str | None, end_date: str | None) -> tuple[str, tuple]:
    """构建带日期过滤的 WHERE 子句，返回 (where_clause, params)"""
    conditions = [base_where]
    params = []
    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)
    return " AND ".join(conditions), tuple(params)


def _get_expense_type(r) -> str:
    """兼容 None / 缺失"""
    et = r.get("expense_type")
    return et if et else "未分类"


def load_data(db_path: str = DB_PATH, start_date: str | None = None, end_date: str | None = None):
    """加载支出和收入记录"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 支出（金额负数，取反后存储）
    _exp_where, _exp_params = _build_date_filter("amount < 0", start_date, end_date)
    cur.execute(f"SELECT * FROM records WHERE {_exp_where} ORDER BY date", _exp_params)
    exp_records = [{**dict(r), "amount": -r["amount"]} for r in cur.fetchall()]

    # 收入
    _inc_where, _inc_params = _build_date_filter("amount > 0", start_date, end_date)
    cur.execute(f"SELECT * FROM records WHERE {_inc_where} ORDER BY date", _inc_params)
    inc_records = [dict(r) for r in cur.fetchall()]

    conn.close()

    months = sorted(set(r["year_month"] for r in exp_records))
    total_exp = sum(r["amount"] for r in exp_records)
    total_inc = sum(r["amount"] for r in inc_records)

    return exp_records, inc_records, months, total_exp, total_inc


def render_monthly_category_ranking(md, exp_records, inc_records, months):
    """每月类别排名（支出+收入）含 expense_type 分布"""

    # 预聚合：每月每个类别下的 expense_type 分布（支出+收入）
    monthly_cat_all = {}
    for m in months:
        m_exp = [r for r in exp_records if r["year_month"] == m]
        m_inc = [r for r in inc_records if r["year_month"] == m]
        m_expense_total = sum(r["amount"] for r in m_exp)
        m_income_total = sum(r["amount"] for r in m_inc)

        cat_data = defaultdict(lambda: {
            "total": 0.0, "count": 0,
            "刚性固定": 0.0, "刚性必要": 0.0, "弹性可选": 0.0,
            "is_income": False,
        })
        for r in m_exp:
            cat = r["category"]
            et = _get_expense_type(r)
            cat_data[cat]["total"] += r["amount"]
            cat_data[cat]["count"] += 1
            if et in cat_data[cat]:
                cat_data[cat][et] += r["amount"]
        for r in m_inc:
            cat = r["category"]
            cat_data[cat]["total"] += r["amount"]
            cat_data[cat]["count"] += 1
            cat_data[cat]["is_income"] = True

        monthly_cat_all[m] = {
            "expense_total": m_expense_total,
            "income_total": m_income_total,
            "categories": dict(cat_data)
        }

    for m in months:
        m_data = monthly_cat_all[m]
        m_expense_total = m_data["expense_total"]
        m_income_total = m_data["income_total"]
        cats = m_data["categories"]
        sorted_cats = sorted(cats.items(), key=lambda x: x[1]["total"], reverse=True)

        net = m_income_total - m_expense_total
        net_sign = "+" if net >= 0 else ""

        md.append(f"### 📅 {m} `总收入 ¥{m_income_total:,.2f} | 总支出 ¥{m_expense_total:,.2f} | 净额 {net_sign}¥{net:,.2f}`\n\n")
        md.append("| 排名 | 类别 | 金额 | 刚性固定 | 刚性必要 | 弹性可选 | 笔数 | 占比 |\n")
        md.append("|------|------|------|------|------|------|------|------|\n")

        for i, (cat, info) in enumerate(sorted_cats, 1):
            amt = info["total"]
            cnt = info["count"]
            is_income = info["is_income"]
            pct = amt / m_expense_total * 100 if m_expense_total > 0 else 0
            amt_label = "+" if is_income else "-"

            # 预计算各字段
            rigid_fixed = "¥{:,.0f}".format(info['刚性固定']) if info['刚性固定'] > 0 and not is_income else "—"
            rigid_nec = "¥{:,.0f}".format(info['刚性必要']) if info['刚性必要'] > 0 and not is_income else "—"
            flexible = "¥{:,.0f}".format(info['弹性可选']) if info['弹性可选'] > 0 and not is_income else "—"
            pct_str = "{:.1f}%".format(pct) if not is_income else "—"

            md.append(
                f"| {i} | **{cat}** | {amt_label}¥{amt:,.2f} | "
                f"{rigid_fixed} | {rigid_nec} | {flexible} | "
                f"{cnt} | {pct_str} |\n"
            )
        md.append("\n")


def _build_json(exp_records, inc_records, months, total_exp, total_inc):
    """构建 JSON 数据，返回 dict"""

    monthly_data = {}
    for m in months:
        m_exp = [r for r in exp_records if r["year_month"] == m]
        m_inc = [r for r in inc_records if r["year_month"] == m]
        m_expense_total = sum(r["amount"] for r in m_exp)
        m_income_total = sum(r["amount"] for r in m_inc)

        cat_data = defaultdict(lambda: {
            "total": 0.0, "count": 0,
            "刚性固定": 0.0, "刚性必要": 0.0, "弹性可选": 0.0,
            "is_income": False,
        })
        for r in m_exp:
            cat = r["category"]
            et = _get_expense_type(r)
            cat_data[cat]["total"] += r["amount"]
            cat_data[cat]["count"] += 1
            if et in cat_data[cat]:
                cat_data[cat][et] += r["amount"]
        for r in m_inc:
            cat = r["category"]
            cat_data[cat]["total"] += r["amount"]
            cat_data[cat]["count"] += 1
            cat_data[cat]["is_income"] = True

        sorted_cats_data = sorted(cat_data.items(), key=lambda x: x[1]["total"], reverse=True)

        monthly_data[m] = {
            "month": m,
            "expense_total": round(m_expense_total, 2),
            "income_total": round(m_income_total, 2),
            "net": round(m_income_total - m_expense_total, 2),
            "categories": [
                {
                    "rank": i,
                    "category": cat,
                    "amount": round(info["total"], 2),
                    "刚性固定": round(info["刚性固定"], 2) if not info["is_income"] else 0,
                    "刚性必要": round(info["刚性必要"], 2) if not info["is_income"] else 0,
                    "弹性可选": round(info["弹性可选"], 2) if not info["is_income"] else 0,
                    "count": info["count"],
                    "percentage": f"{round(info['total'] / m_expense_total * 100, 1)}%" if m_expense_total > 0 and not info["is_income"] else "—",
                }
                for i, (cat, info) in enumerate(sorted_cats_data, 1)
            ],
        }

    json_output = {
        "title": "每月类别排名（支出+收入）",
        "month_count": len(months),
        "total_expense": round(total_exp, 2),
        "total_income": round(total_inc, 2),
        "monthly_data": monthly_data,
    }

    return json_output


# ──────────────────────────────────────────────────────────
# 核心分析 + Tool
# ──────────────────────────────────────────────────────────

def _run_analysis(db_path: str, start_date: str | None = None, end_date: str | None = None) -> tuple[str, dict]:
    """核心分析逻辑，返回 (markdown, json_output)"""
    exp_records, inc_records, months, total_exp, total_inc = load_data(db_path, start_date=start_date, end_date=end_date)

    md = []
    md.append("# 📂 每月类别排名（支出+收入）\n\n")
    md.append(f"> 共 {len(months)} 个月  |  "
              f"总支出 **¥{total_exp:,.2f}**  |  "
              f"总收入 **¥{total_inc:,.2f}**\n\n")

    render_monthly_category_ranking(md, exp_records, inc_records, months)

    json_output = _build_json(exp_records, inc_records, months, total_exp, total_inc)

    return "".join(md), json_output


@tool
def analyze_monthly_categories(start_date: str | None = None, end_date: str | None = None) -> dict:
    """每月类别排名（支出+收入）- 每月各类别按金额排名，含刚性固定/刚性必要/弹性可选分布。
    金额约定：支出 < 0，收入 > 0。
    
    Args:
        start_date: 可选，起始日期（含），格式 "YYYY-MM-DD"，如 "2025-01-01"
        end_date: 可选，结束日期（含），格式 "YYYY-MM-DD"，如 "2025-06-30"
    """
    _, json_output = _run_analysis(DB_PATH, start_date=start_date, end_date=end_date)
    return json_output


if __name__ == "__main__":
    import sys

    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date = sys.argv[2] if len(sys.argv) > 2 else None

    md_str, json_output = _run_analysis(DB_PATH, start_date=start_date, end_date=end_date)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if start_date or end_date:
        suffix = f"_{start_date or 'begin'}_to_{end_date or 'end'}"
        md_filename = f"monthly_categories{suffix}.md"
        json_filename = f"monthly_categories{suffix}.json"
    else:
        md_filename = "monthly_categories.md"
        json_filename = "monthly_categories.json"

    md_path = os.path.join(OUTPUT_DIR, md_filename)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_str)

    json_path = os.path.join(OUTPUT_DIR, json_filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)

    print(f"报告已生成: {md_path}")
    print(f"JSON 已生成: {json_path}")
