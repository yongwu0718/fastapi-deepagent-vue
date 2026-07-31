"""支出专项分析 — 层级结构、细类拆解、项目明细、消费频次、类别深度追踪"""
import sqlite3
from collections import defaultdict

try:
    from .common import DB_PATH, build_date_filter
except ImportError:
    from common import DB_PATH, build_date_filter  # type: ignore
AMOUNT_BUCKETS = [
    ("0-20",    0,   20),
    ("20-50",   20,  50),
    ("50-100",  50,  100),
    ("100-200", 100, 200),
    ("200-500", 200, 500),
    ("500+",    500, float("inf")),
]


# ═══════════════════════════════════════════════════════════
# 数据加载
# ═══════════════════════════════════════════════════════════

def load_data(db_path: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    """从 records_view 加载支出数据，返回结构化的原始数据包。

    records_view 列: id, 名称, 大类, 细类, 金额, 平台, 日期, 收支类型, 分类, 年月
    金额约定: 支出为负, 收入为正
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 支出
    where, params = build_date_filter("金额 < 0", start_date, end_date)
    cur.execute(f"SELECT * FROM records_view WHERE {where} ORDER BY 日期", params)
    rows = cur.fetchall()

    records = []
    for r in rows:
        expense_abs = abs(r["金额"])
        records.append({
            "date":         r["日期"],
            "item":         r["名称"],
            "cat":          r["大类"],
            "subcat":       r["细类"] or "未分类",
            "amt":          expense_abs,
            "plat":         r["平台"],
            "expense_type": r["分类"] or "未分类",
        })

    # 收入总额（用于头部的收支对比）
    inc_where, inc_params = build_date_filter("金额 > 0", start_date, end_date)
    cur.execute(f"SELECT SUM(金额) FROM records_view WHERE {inc_where}", inc_params)
    income_total = cur.fetchone()[0] or 0.0
    conn.close()

    return {
        "records":       records,
        "total_expense": sum(r["amt"] for r in records),
        "n":             len(records),
        "income_total":  income_total,
    }


# ═══════════════════════════════════════════════════════════
# 各 section 构建函数
# ═══════════════════════════════════════════════════════════

def _build_header(data: dict) -> dict:
    records = data["records"]
    total = data["total_expense"]
    n = data["n"]
    return {
        "date_start":    records[0]["date"] if records else None,
        "date_end":      records[-1]["date"] if records else None,
        "record_count":  n,
        "total_expense": round(total, 2),
        "income_total":  round(data["income_total"], 2),
    }


def _build_category_breakdown(data: dict) -> list[dict]:
    """各支出大类按金额排名，含细类拆解"""
    records = data["records"]
    total = data["total_expense"]

    # 预聚合：大类 + 细类
    cat_amt  = defaultdict(float)
    cat_cnt  = defaultdict(int)
    cat_sub_amt = defaultdict(lambda: defaultdict(float))
    cat_sub_cnt = defaultdict(lambda: defaultdict(int))

    for r in records:
        cat_amt[r["cat"]] += r["amt"]
        cat_cnt[r["cat"]] += 1
        cat_sub_amt[r["cat"]][r["subcat"]] += r["amt"]
        cat_sub_cnt[r["cat"]][r["subcat"]] += 1

    layers = []
    for cat, amt in sorted(cat_amt.items(), key=lambda x: x[1], reverse=True):
        cnt = cat_cnt[cat]

        sub_details = [
            {
                "name":           sub,
                "amount":         round(sub_amt, 2),
                "count":          cat_sub_cnt[cat][sub],
                "sub_percentage": f"{round(sub_amt / amt * 100)}%" if amt else "0%",
            }
            for sub, sub_amt in sorted(
                cat_sub_amt[cat].items(), key=lambda x: x[1], reverse=True
            )
        ]

        layers.append({
            "category":       cat,
            "amount":         round(amt, 2),
            "count":          cnt,
            "percentage":     f"{round(amt / total * 100, 1)}%" if total else "0%",
            "subcategories":  sub_details,
        })

    return layers


def _build_item_breakdown(data: dict) -> list[dict]:
    """项目明细：全量输出，按类别 + 金额排序"""
    records = data["records"]
    total = data["total_expense"]

    item_agg = defaultdict(lambda: {"amount": 0.0, "count": 0, "cat": "", "subcategories": defaultdict(float), "expense_types": defaultdict(float)})
    for r in records:
        name = r["item"]
        item_agg[name]["amount"] += r["amt"]
        item_agg[name]["count"]  += 1
        item_agg[name]["cat"]     = r["cat"]
        item_agg[name]["subcategories"][r["subcat"]] += r["amt"]
        et = r["expense_type"]
        item_agg[name]["expense_types"][et] += r["amt"]

    sorted_items = sorted(item_agg.items(), key=lambda x: (x[1]["cat"], -x[1]["amount"]))

    return [
        {
            "rank":              idx,
            "item_name":         name,
            "category":          info["cat"],
            "subcategory":       next(iter(sorted(info["subcategories"].items(), key=lambda x: x[1], reverse=True)))[0],
            "amount":            round(info["amount"], 2),
            "count":             info["count"],
            "avg_per_transaction": round(info["amount"] / info["count"], 2),
            "total_percentage":  f"{round(info['amount'] / total * 100, 1)}%" if total else "0%",
            "刚性固定":           round(info["expense_types"].get("刚性固定", 0), 2),
            "刚性必要":           round(info["expense_types"].get("刚性必要", 0), 2),
            "弹性支出":           round(info["expense_types"].get("弹性支出", 0), 2),
        }
        for idx, (name, info) in enumerate(sorted_items, 1)
        if info["amount"] > 50 or info["count"] > 10
    ]


def _build_consumption_frequency(data: dict) -> list[dict]:
    """消费频次分布（按金额区间）"""
    records = data["records"]
    total_count = data["n"]

    buckets = {label: {"count": 0, "刚性固定": 0, "刚性必要": 0, "弹性支出": 0}
               for label, _, _ in AMOUNT_BUCKETS}

    for r in records:
        for label, lo, hi in AMOUNT_BUCKETS:
            if lo <= r["amt"] < hi:
                buckets[label]["count"] += 1
                et = r["expense_type"]
                if et in ("刚性固定", "刚性必要", "弹性支出"):
                    buckets[label][et] += 1
                break

    return [
        {
            "range":       f"¥{label}",
            "count":       b["count"],
            "刚性固定":      b["刚性固定"],
            "刚性必要":      b["刚性必要"],
            "弹性支出":      b["弹性支出"],
            "percentage":  f"{round(b['count'] / total_count * 100, 1)}%" if total_count else "0%",
        }
        for label, _, _ in AMOUNT_BUCKETS
        for b in [buckets[label]]
    ]


def _build_category_tracking(data: dict, top_n: int = 3) -> list[dict]:
    """支出 top N 大类深度拆解"""
    records = data["records"]

    cat_totals = defaultdict(float)
    for r in records:
        cat_totals[r["cat"]] += r["amt"]
    top_cats = [c for c, _ in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]]

    result = []
    for cat_name in top_cats:
        cat_records = [r for r in records if r["cat"] == cat_name]
        cat_total = sum(r["amt"] for r in cat_records)

        subcat_agg = defaultdict(lambda: {"amount": 0.0, "count": 0})
        for r in cat_records:
            subcat_agg[r["subcat"]]["amount"] += r["amt"]
            subcat_agg[r["subcat"]]["count"]  += 1

        subcat_breakdown = [
            {"subcategory": sc, "amount": round(d["amount"], 2), "count": d["count"],
             "percentage": f"{round(d['amount'] / cat_total * 100, 1)}%"}
            for sc, d in sorted(subcat_agg.items(), key=lambda x: x[1]["amount"], reverse=True)
        ]

        result.append({
            "category":             cat_name,
            "total_amount":         round(cat_total, 2),
            "record_count":         len(cat_records),
            "subcategory_breakdown": subcat_breakdown,
        })

    return result


def _build_subcategory_ranking(data: dict) -> list[dict]:
    """按大类分组，每大类内细类排名，含 expense_type 标注"""
    records = data["records"]
    total = data["total_expense"]

    cat_amt  = defaultdict(float)
    cat_sub_amt = defaultdict(lambda: defaultdict(float))
    cat_sub_cnt = defaultdict(lambda: defaultdict(int))
    cat_sub_et  = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    for r in records:
        cat_amt[r["cat"]] += r["amt"]
        cat_sub_amt[r["cat"]][r["subcat"]] += r["amt"]
        cat_sub_cnt[r["cat"]][r["subcat"]] += 1
        et = r["expense_type"]
        cat_sub_et[r["cat"]][r["subcat"]][et] += r["amt"]

    result = []
    for cat, cat_amount in sorted(cat_amt.items(), key=lambda x: x[1], reverse=True):
        sub_list = [
            {
                "rank":        j,
                "subcategory": sc,
                "amount":      round(sc_amt, 2),
                "count":       cat_sub_cnt[cat][sc],
                "percentage":  f"{round(sc_amt / cat_amount * 100, 1)}%",
                "刚性固定":      round(cat_sub_et[cat][sc].get("刚性固定", 0), 2),
                "刚性必要":      round(cat_sub_et[cat][sc].get("刚性必要", 0), 2),
                "弹性支出":      round(cat_sub_et[cat][sc].get("弹性支出", 0), 2),
            }
            for j, (sc, sc_amt) in enumerate(
                sorted(cat_sub_amt[cat].items(), key=lambda x: x[1], reverse=True), 1
            )
        ]
        result.append({
            "category":       cat,
            "total_amount":   round(cat_amount, 2),
            "total_percentage": f"{round(cat_amount / total * 100, 1)}%" if total else "0%",
            "subcategories":  sub_list,
        })

    return result


def _build_high_frequency_items(data: dict, top_n: int = 10) -> list[dict]:
    """高频消费项目 TOP N"""
    records = data["records"]
    item_agg = defaultdict(lambda: {"count": 0, "total": 0.0, "subcategories": defaultdict(float)})
    for r in records:
        item_agg[r["item"]]["count"] += 1
        item_agg[r["item"]]["total"] += r["amt"]
        item_agg[r["item"]]["subcategories"][r["subcat"]] += r["amt"]

    sorted_items = sorted(item_agg.items(), key=lambda x: x[1]["count"], reverse=True)

    return [
        {
            "rank":        i,
            "item":        item,
            "subcategory": next(iter(sorted(d["subcategories"].items(), key=lambda x: x[1], reverse=True)))[0],
            "count":       d["count"],
            "total":       round(d["total"], 2),
            "avg":         round(d["total"] / d["count"], 2),
        }
        for i, (item, d) in enumerate(sorted_items[:top_n], 1)
    ]


# ═══════════════════════════════════════════════════════════
# 核心入口
# ═══════════════════════════════════════════════════════════

def _run_analysis(db_path: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    data = load_data(db_path, start_date, end_date)

    if not data["records"]:
        return {"title": "支出专项分析", "header": {"record_count": 0}, "error": "无支出记录"}

    return {
        "title":                  "支出专项分析",
        "header":                 _build_header(data),
        "subcategory_ranking":    _build_subcategory_ranking(data),
        "item_breakdown":         _build_item_breakdown(data),
        "consumption_frequency":  _build_consumption_frequency(data),
        "high_frequency_items":   _build_high_frequency_items(data),
    }


def analyze_expense(start_date: str | None = None, end_date: str | None = None) -> dict:
    """支出专项分析 — 层级结构、项目明细、消费频次、高频消费、类别深度追踪。

    从 records_view 读取，金额约定：支出 < 0，收入 > 0。

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
