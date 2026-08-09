"""每月大类/细类汇总分析 — 按月分组，输出各大类及细类的金额、笔数、占比。

数据来源 billing_records 表，列: id, 消费名称, 消费大类, 消费细类, 类型, 金额, 支付平台, 日期, 消费类型, 备注
金额约定：表中"金额"为绝对值正数，方向由"类型"区分（'支出' / '收入'）。
"""
import sqlite3
from collections import defaultdict

try:
    from .common import DB_PATH, build_date_filter
except ImportError:
    from common import DB_PATH, build_date_filter  # type: ignore


# ═══════════════════════════════════════════════════════════
# 数据加载
# ═══════════════════════════════════════════════════════════

def load_expense_records(db_path: str, start_date: str | None = None,
                         end_date: str | None = None) -> list[dict]:
    """加载支出明细，金额取绝对值。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    where, params = build_date_filter("类型 = '支出'", start_date, end_date)
    cur.execute(f"SELECT * FROM billing_records WHERE {where} ORDER BY 日期", params)
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "date":    r["日期"],
            "ym":      r["日期"][:7],
            "item":    r["消费名称"],
            "cat":     r["消费大类"],
            "subcat":  r["消费细类"] or "未分类",
            "amt":     abs(r["金额"]),
            "plat":    r["支付平台"],
            "expense_type": r["消费类型"] or "未分类",
        }
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════
# 各 section 构建函数
# ═══════════════════════════════════════════════════════════

def _build_monthly_category_breakdown(records: list[dict], months: list[str]) -> dict:
    """每月大类汇总（含细类拆解）。

    结构:
        months: 月份列表（升序）
        monthly: [
            {
                month, total, count,
                categories: [
                    {category, amount, count, percentage,
                     subcategories: [{subcategory, amount, count, percentage}]}
                ]
            }
        ]
    """
    by_month: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_month[r["ym"]].append(r)

    monthly = []
    for ym in months:
        m_records = by_month.get(ym, [])
        m_total = sum(r["amt"] for r in m_records)

        # 预聚合：大类 + 细类
        cat_amt  = defaultdict(float)
        cat_cnt  = defaultdict(int)
        cat_sub_amt = defaultdict(lambda: defaultdict(float))
        cat_sub_cnt = defaultdict(lambda: defaultdict(int))
        for r in m_records:
            cat_amt[r["cat"]] += r["amt"]
            cat_cnt[r["cat"]] += 1
            cat_sub_amt[r["cat"]][r["subcat"]] += r["amt"]
            cat_sub_cnt[r["cat"]][r["subcat"]] += 1

        categories = []
        for cat, amt in sorted(cat_amt.items(), key=lambda x: x[1], reverse=True):
            sub_details = [
                {
                    "subcategory": sub,
                    "amount":      round(sub_amt, 2),
                    "count":       cat_sub_cnt[cat][sub],
                    "percentage":  f"{round(sub_amt / amt * 100, 1)}%" if amt else "0%",
                }
                for sub, sub_amt in sorted(
                    cat_sub_amt[cat].items(), key=lambda x: x[1], reverse=True
                )
            ]
            categories.append({
                "category":      cat,
                "amount":        round(amt, 2),
                "count":         cat_cnt[cat],
                "percentage":    f"{round(amt / m_total * 100, 1)}%" if m_total else "0%",
                "subcategories": sub_details,
            })

        monthly.append({
            "month":      ym,
            "total":      round(m_total, 2),
            "count":      len(m_records),
            "categories": categories,
        })

    return {"months": months, "monthly": monthly}


def _build_subcategory_ranking_by_month(records: list[dict], months: list[str]) -> list[dict]:
    """每月细类总排名：跨大类列出当月所有细类的金额与笔数。"""
    by_month: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_month[r["ym"]].append(r)

    result = []
    for ym in months:
        m_records = by_month.get(ym, [])
        sub_amt = defaultdict(float)
        sub_cnt = defaultdict(int)
        cat_of_sub = {}
        for r in m_records:
            sub_amt[r["subcat"]] += r["amt"]
            sub_cnt[r["subcat"]] += 1
            cat_of_sub[r["subcat"]] = r["cat"]

        ranked = [
            {
                "rank":       i,
                "subcategory": sc,
                "category":    cat_of_sub[sc],
                "amount":      round(amt, 2),
                "count":       sub_cnt[sc],
            }
            for i, (sc, amt) in enumerate(
                sorted(sub_amt.items(), key=lambda x: x[1], reverse=True), 1
            )
        ]
        result.append({"month": ym, "subcategory_ranking": ranked})

    return result


def _build_category_trend(records: list[dict], months: list[str]) -> list[dict]:
    """大类跨月趋势：每个大类在各月的金额对比。"""
    cat_month_amt = defaultdict(lambda: defaultdict(float))
    for r in records:
        cat_month_amt[r["cat"]][r["ym"]] += r["amt"]

    result = []
    for cat in sorted(cat_month_amt, key=lambda c: sum(cat_month_amt[c].values()), reverse=True):
        result.append({
            "category": cat,
            "monthly_amounts": {
                ym: round(cat_month_amt[cat].get(ym, 0), 2)
                for ym in months
            },
            "total": round(sum(cat_month_amt[cat].values()), 2),
        })
    return result


# ═══════════════════════════════════════════════════════════
# 核心入口
# ═══════════════════════════════════════════════════════════

def _run_analysis(db_path: str, start_date: str | None = None,
                  end_date: str | None = None) -> dict:
    records = load_expense_records(db_path, start_date, end_date)

    if not records:
        return {
            "title": "每月大类/细类汇总",
            "months": [],
            "error": "无支出记录",
        }

    months = sorted(set(r["ym"] for r in records))
    total_expense = sum(r["amt"] for r in records)

    return {
        "title":               "每月大类/细类汇总",
        "header": {
            "date_start":   records[0]["date"],
            "date_end":     records[-1]["date"],
            "months":       months,
            "month_count":  len(months),
            "record_count": len(records),
            "total_expense": round(total_expense, 2),
        },
        "monthly_category_breakdown": _build_monthly_category_breakdown(records, months),
        "subcategory_ranking_by_month": _build_subcategory_ranking_by_month(records, months),
        "category_trend": _build_category_trend(records, months),
    }


def analyze_category_monthly(start_date: str | None = None,
                             end_date: str | None = None) -> dict:
    """每月大类/细类汇总分析。

    按月分组统计支出：各大类（含细类拆解）的金额、笔数、占比，
    细类跨大类总排名，以及大类跨月趋势。

    Args:
        start_date: 起始日期 "YYYY-MM-DD"
        end_date:   结束日期 "YYYY-MM-DD"
    """
    return _run_analysis(DB_PATH, start_date, end_date)


if __name__ == "__main__":
    import sys
    import json as _json

    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date   = sys.argv[2] if len(sys.argv) > 2 else None

    result = _run_analysis(DB_PATH, start_date, end_date)
    print(_json.dumps(result, ensure_ascii=False, indent=2))
