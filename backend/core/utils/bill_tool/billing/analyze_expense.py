"""支出专项分析 - 输出 Markdown 文档和 JSON
金额约定：支出 < 0，收入 > 0

用法：
  1. 作为 LangChain Tool：from analyze_expense import analyze_expense
  2. 作为脚本：python analyze_expense.py （生成 MD + JSON 文件）
"""
import sqlite3
import json
import os
from collections import defaultdict
from langchain.tools import tool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "billing.db"))
OUTPUT_DIR = r"F:\index_rag\knowledge-base\billing"

# 展示层分组（将原始 category 归入大类，仅用于第一节层级展示）
LAYER_GROUPS = {
    "🏠 住房相关": ["生活缴费"],
    "🍚 食品": ["食品", "饮品"],
    "🚌 交通出行": ["交通出行"],
    "🛒 购物消费": ["购物消费"],
    "📱 数码电子": ["数码电子"],
    "🎮 娱乐休闲": ["娱乐休闲"],
    "🏥 医疗健康": ["医疗健康", "保险保障"],
    "📦 其他支出": ["其他支出"],
}

# 金额分桶（第四节单笔消费画像）
AMOUNT_BUCKETS = [
    ("0-5元", 0, 5), ("5-10元", 5, 10), ("10-15元", 10, 15),
    ("15-20元", 15, 20), ("20-30元", 20, 30), ("30-50元", 30, 50),
    ("50-100元", 50, 100), ("100-200元", 100, 200), ("200-500元", 200, 500),
    ("500+元", 500, float("inf")),
]

# ──────────────────────────────────────────────────────────
# 数据层
# ──────────────────────────────────────────────────────────

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
    """获取统一 expense_type，兼容 None / 缺失"""
    et = r["expense_type"] if r["expense_type"] is not None else None
    return et if et else "未分类"


def load_data(db_path: str = DB_PATH, start_date: str | None = None, end_date: str | None = None):
    """加载支出记录 + 收入总额，返回结构化数据
    
    Args:
        db_path: 数据库路径
        start_date: 可选，起始日期（含），格式 "YYYY-MM-DD"
        end_date: 可选，结束日期（含），格式 "YYYY-MM-DD"
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 支出
    _exp_where, _exp_params = _build_date_filter("amount < 0", start_date, end_date)
    cur.execute(f"SELECT * FROM records WHERE {_exp_where} ORDER BY date", _exp_params)
    rows = cur.fetchall()

    records = []
    amount_buckets = {"0-20": 0, "20-50": 0, "50-100": 0, "100-500": 0, "500-1000": 0, "1000+": 0}
    item_freq = defaultdict(lambda: {"count": 0, "total": 0.0})

    for r in rows:
        expense_abs = -r["amount"]
        records.append({
            "date": r["date"],
            "item": r["item_name"],
            "cat": r["category"],
            "amt": expense_abs,          # 转为正数便于分析
            "plat": r["platform"],
            "ym": r["year_month"],
            "expense_type": _get_expense_type(r),
        })

        # 金额分布
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

        # 高频项目统计
        item_freq[r["item_name"]]["count"] += 1
        item_freq[r["item_name"]]["total"] += expense_abs

    # 收入（一次查询完成）
    _inc_where, _inc_params = _build_date_filter("amount > 0", start_date, end_date)
    cur.execute(f"SELECT SUM(amount) as s FROM records WHERE {_inc_where}", _inc_params)
    income_total = cur.fetchone()["s"] or 0

    conn.close()

    total = sum(r["amt"] for r in records)
    n = len(records)
    months = sorted(set(r["ym"] for r in records))
    month_count = len(months)

    return records, total, n, months, month_count, income_total, amount_buckets, item_freq


def preprocess(records):
    """预处理：按 category 聚合金额 & 笔数"""
    cat_amounts = defaultdict(float)
    cat_counts = defaultdict(int)
    for r in records:
        cat_amounts[r["cat"]] += r["amt"]
        cat_counts[r["cat"]] += 1
    return cat_amounts, cat_counts


# ──────────────────────────────────────────────────────────
# 渲染函数
# ──────────────────────────────────────────────────────────

def render_header(md, records, total, n, month_count):
    """标题 & 概览面板"""
    md.append("# 💸 支出专项分析\n\n")
    md.append(
        f"> 时间: {records[0]['date']} ~ {records[-1]['date']}  "
        f"({month_count}个月)  |  "
        f"笔数: {n}  |  "
        f"总支出: **¥{total:,.2f}**  |  "
        f"月均: ¥{total / month_count:,.0f}  |  "
        f"日均: ¥{total / month_count / 30:,.0f}\n\n"
    )


def _build_category_note(records, cat_name, amt, cnt):
    """为每个子类别生成智能备注，替代无意义的笔均

    规则：
    - Top 1项占总额 > 80% → 展示"Giant占比"
    - Top 2项占总额 > 80% → 展示"Top2分解"
    - 其他情况 → "笔均 + Top项提示"
    """
    # 聚合该类别下各 item 的金额和笔数
    item_aggs = defaultdict(lambda: {"total": 0.0, "count": 0})
    for r in records:
        if r["cat"] == cat_name:
            item_aggs[r["item"]]["total"] += r["amt"]
            item_aggs[r["item"]]["count"] += 1

    sorted_items = sorted(item_aggs.items(), key=lambda x: x[1]["total"], reverse=True)
    if not sorted_items:
        return "—"

    top1_name, top1_data = sorted_items[0]
    top1_pct = top1_data["total"] / amt * 100

    # 场景1: 单笔超大项（房租、手机分期等）
    if top1_pct > 80 and cnt <= 10:
        return f"**{top1_name[:8]}** ¥{top1_data['total']:,.0f} 占{top1_pct:.0f}%"

    # 场景2: Top 2 合起来 > 80%（如其他支出、医疗）
    if len(sorted_items) >= 2:
        top2_total = top1_data["total"] + sorted_items[1][1]["total"]
        top2_pct = top2_total / amt * 100
        if top2_pct > 80:
            t2_name = sorted_items[1][0]
            return (
                f"**{top1_name[:8]}** ¥{top1_data['total']:,.0f}<br>"
                f"**{t2_name[:8]}** ¥{sorted_items[1][1]['total']:,.0f}"
            )

    # 场景3: 笔均有意义 + 首项提示（食品、饮品、购物消费）
    avg = amt / cnt
    lines = [f"笔均 ¥{avg:.1f}"]
    if top1_pct < 50:  # 分散时只标最大项
        lines.append(f"TOP: {top1_name[:8]} ¥{top1_data['total']:,.0f}")
    return "<br>".join(lines)


def render_layer_structure(md, records, total, month_count):
    """一、支出层级结构"""
    md.append("---\n\n## 一、支出层级结构\n\n")

    cat_amounts, cat_counts = preprocess(records)

    md.append("| 大类 | 子类别 | 金额 | 笔数 | 备注/细项 | 占大类 | 占总支出 | 月均 |\n")
    md.append("|------|------|------|------|------|------|------|------|\n")

    for layer_name, sub_cats in LAYER_GROUPS.items():
        layer_total = sum(cat_amounts[c] for c in sub_cats)
        layer_count = sum(cat_counts[c] for c in sub_cats)
        if layer_total == 0:
            continue

        for i, sub in enumerate(sub_cats):
            amt = cat_amounts.get(sub, 0)
            cnt = cat_counts.get(sub, 0)
            if cnt == 0:
                continue
            sub_pct = amt / layer_total * 100
            total_pct = amt / total * 100
            monthly = amt / month_count

            note = _build_category_note(records, sub, amt, cnt)
            display_name = layer_name if i == 0 else ""

            md.append(
                f"| {display_name} | {sub} | ¥{amt:,.0f} | {cnt} | "
                f"{note} | {sub_pct:.0f}% | {total_pct:.1f}% | ¥{monthly:.0f} |\n"
            )

        # 多子类时添加小计行
        if len(sub_cats) > 1:
            md.append(
                f"| **{layer_name} 小计** | | **¥{layer_total:,.0f}** | "
                f"{layer_count} | | 100% | **{layer_total / total * 100:.1f}%** | "
                f"¥{layer_total / month_count:.0f} |\n"
            )

    md.append("\n")


def render_item_breakdown(md, records, total):
    """item_name 维度聚合"""
    md.append("---\n\n## 二、item_name 明细\n\n")

    # 聚合：金额、笔数、类别、expense_type 分布、大额笔数
    item_agg = defaultdict(lambda: {"amount": 0.0, "count": 0, "high_count": 0, "category": "",
                                     "刚性固定": 0.0, "刚性必要": 0.0, "弹性可选": 0.0})
    for r in records:
        name = r["item"]
        item_agg[name]["amount"] += r["amt"]
        item_agg[name]["count"] += 1
        if r["amt"] > 50:
            item_agg[name]["high_count"] += 1
        item_agg[name]["category"] = r["cat"]
        et = r.get("expense_type", "未分类") or "未分类"
        if et in ("刚性固定", "刚性必要", "弹性可选"):
            item_agg[name][et] += r["amt"]

    # 先按 category 排序，同类内按金额降序
    sorted_items = sorted(item_agg.items(),
                          key=lambda x: (x[1]["category"], -x[1]["amount"]))

    md.append("| 排名 | 项目 | 类别 | 金额 | 笔数 | 大额消费(>¥50) | 刚性固定 | 刚性必要 | 弹性可选 | 占总支出 |\n")
    md.append("|------|------|------|------|------|------|------|------|------|------|\n")

    displayed = 0
    prev_cat = None
    for i, (name, info) in enumerate(sorted_items):
        if info["count"] < 5 and info["high_count"] == 0:
            continue

        # 类别切换时打印分隔
        if info["category"] != prev_cat and displayed > 0:
            md.append("| | | | | | | | | | |\n")  # separator row
        prev_cat = info["category"]

        displayed += 1
        pct = info["amount"] / total * 100 if total > 0 else 0
        md.append(
            f"| {displayed} | {name[:22]} | {info['category']} | "
            f"¥{info['amount']:,.2f} | {info['count']} | "
            f"{info['high_count'] if info['high_count'] > 0 else '—'} | "
            f"{'¥' + f'{info['刚性固定']:,.0f}' if info['刚性固定'] > 0 else '—'} | "
            f"{'¥' + f'{info['刚性必要']:,.0f}' if info['刚性必要'] > 0 else '—'} | "
            f"{'¥' + f'{info['弹性可选']:,.0f}' if info['弹性可选'] > 0 else '—'} | "
            f"{pct:.1f}% |\n"
        )

    md.append("\n")

    # 消费频次分布
    freq_buckets = [
        ("0-20", 0, 20), ("20-30", 20, 30), ("30-50", 30, 50),
        ("50-100", 50, 100), ("100-200", 100, 200), ("200-500", 200, 500),
        ("500+", 500, float("inf")),
    ]
    freq_counts = {label: 0 for label, _, _ in freq_buckets}
    freq_et = {label: {"刚性固定": 0, "刚性必要": 0, "弹性可选": 0} for label, _, _ in freq_buckets}
    for r in records:
        for label, lo, hi in freq_buckets:
            if lo <= r["amt"] < hi:
                freq_counts[label] += 1
                et = r.get("expense_type", "未分类") or "未分类"
                if et in freq_et[label]:
                    freq_et[label][et] += 1
                break

    total_count = len(records)
    md.append("### 消费频次分布\n\n")
    md.append("| 金额区间 | 笔数 | 刚性固定 | 刚性必要 | 弹性可选 | 占比 |\n")
    md.append("|------|------|------|------|------|------|\n")

    for label, _, _ in freq_buckets:
        count = freq_counts[label]
        et_data = freq_et[label]
        pct = count / total_count * 100 if total_count > 0 else 0
        md.append(
            f"| ¥{label} | {count} | "
            f"{et_data['刚性固定'] if et_data['刚性固定'] > 0 else '—'} | "
            f"{et_data['刚性必要'] if et_data['刚性必要'] > 0 else '—'} | "
            f"{et_data['弹性可选'] if et_data['弹性可选'] > 0 else '—'} | "
            f"{pct:.1f}% |\n"
        )

    md.append("\n")


def render_food_deep_tracking(md, records, months):
    """三、食品类深度追踪"""
    md.append("---\n\n## 三、食品类深度追踪\n\n")

    # 筛选食品 + 饮品
    food_records = [r for r in records if r["cat"] in ("食品", "饮品")]
    if not food_records:
        md.append("> 无食品/饮品消费记录\n\n")
        return

    # 按店铺统计：每月次数 + 是否有单笔>30
    food_items_monthly_count = defaultdict(lambda: defaultdict(int))
    food_items_stats = defaultdict(lambda: {"total": 0.0, "has_high": False})
    for r in food_records:
        name = r["item"]
        ym = r["ym"]
        food_items_monthly_count[name][ym] += 1
        food_items_stats[name]["total"] += r["amt"]
        if r["amt"] > 30:
            food_items_stats[name]["has_high"] = True

    for name, month_counts in food_items_monthly_count.items():
        food_items_stats[name]["max_monthly"] = max(month_counts.values())

    top_food_items = sorted(
        [(name, s["total"], s["max_monthly"]) for name, s in food_items_stats.items()
         if s["max_monthly"] > 5 or s["has_high"]],
        key=lambda x: x[1], reverse=True
    )
    top_food_items = [(name[:8], total, cnt) for name, total, cnt in top_food_items[:12]]
    top_food_names = [name for name, _, _ in top_food_items]

    # 按月汇总
    food_by_month = {}
    for m in months:
        m_food = [r for r in food_records if r["ym"] == m]
        food_by_month[m] = {
            "total": sum(r["amt"] for r in m_food),
            "count": len(m_food),
            "detail_amount": defaultdict(float),
            "detail_count": defaultdict(int),
        }
        for r in m_food:
            food_by_month[m]["detail_amount"][r["item"][:8]] += r["amt"]
            food_by_month[m]["detail_count"][r["item"][:8]] += 1

    # ---- 食品月度子类明细 ----
    highlight_names = set(top_food_names)

    md.append("### 食品月度消费明细 (单笔>¥30 或 频次>5)\n\n")
    md.append("| 月份 | 笔数 | 总额 | 笔均 | 环比 | 店铺 | 金额/笔数 |\n")
    md.append("|------|------|------|------|------|------|------|\n")

    prev_food_total = None
    for m in months:
        food_info = food_by_month.get(m, {"total": 0, "count": 0, "detail_amount": {}, "detail_count": {}})
        total_m = food_info["total"]
        count_m = food_info["count"]
        avg = total_m / count_m if count_m > 0 else 0
        detail_amount = food_info["detail_amount"]
        detail_count = food_info["detail_count"]

        # 环比
        if prev_food_total is not None and prev_food_total > 0:
            diff = total_m - prev_food_total
            pct = diff / prev_food_total * 100
            arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
            mom_str = f"{arrow}¥{abs(diff):.0f} ({pct:+.0f}%)"
        else:
            mom_str = "—"
        prev_food_total = total_m

        # 细项分类
        filtered = sorted(
            [(n, detail_amount[n], detail_count[n]) for n in detail_amount if n in highlight_names],
            key=lambda x: x[1], reverse=True
        )
        if filtered:
            names_parts = []
            amounts_parts = []
            for name, amt, cnt in filtered:
                names_parts.append(name)
                amounts_parts.append(f"¥{amt:.0f}({cnt}笔)")
            names_str = "<br>".join(names_parts)
            amounts_str = "<br>".join(amounts_parts)
        else:
            names_str = "—"
            amounts_str = "—"

        md.append(f"| {m} | {count_m} | ¥{total_m:,.0f} | ¥{avg:.1f} | {mom_str} | {names_str} | {amounts_str} |\n")

    md.append("\n")

    # ---- 食品金额分层 ----
    md.append("### 食品金额分层 · 月度消费结构\n\n")
    md.append("| 月份 | 小食 <¥10 | 正餐 ¥10-30 | 大餐 ¥30-50 | 聚餐 >¥50 | 笔均 |\n")
    md.append("|------|------|------|------|------|------|\n")

    for m in months:
        m_food = [r for r in food_records if r["ym"] == m]
        total_count = len(m_food)
        small = sum(1 for r in m_food if r["amt"] < 10)
        normal = sum(1 for r in m_food if 10 <= r["amt"] < 30)
        big = sum(1 for r in m_food if 30 <= r["amt"] < 50)
        huge = sum(1 for r in m_food if r["amt"] >= 50)
        avg_m = sum(r["amt"] for r in m_food) / total_count if total_count > 0 else 0

        md.append(
            f"| {m} | "
            f"{f'{small}笔 ({small/total_count*100:.0f}%)' if total_count > 0 else '—'} | "
            f"{f'{normal}笔 ({normal/total_count*100:.0f}%)' if total_count > 0 else '—'} | "
            f"{f'{big}笔 ({big/total_count*100:.0f}%)' if total_count > 0 else '—'} | "
            f"{f'{huge}笔 ({huge/total_count*100:.0f}%)' if total_count > 0 else '—'} | "
            f"¥{avg_m:.1f} |\n"
        )

    md.append("\n")


def _build_json_note(records, cat_name, amt, cnt):
    """为 JSON 生成备注文本，与表格备注/细项列一致"""
    item_aggs = defaultdict(lambda: {"total": 0.0, "count": 0})
    for r in records:
        if r["cat"] == cat_name:
            item_aggs[r["item"]]["total"] += r["amt"]
            item_aggs[r["item"]]["count"] += 1
    sorted_items = sorted(item_aggs.items(), key=lambda x: x[1]["total"], reverse=True)
    if not sorted_items:
        return "—"

    top1_name, top1_data = sorted_items[0]
    top1_pct = top1_data["total"] / amt * 100

    # 场景1: 单笔超大项
    if top1_pct > 80 and cnt <= 10:
        return f"{top1_name[:8]} ¥{top1_data['total']:,.0f} 占{top1_pct:.0f}%"

    # 场景2: Top 2 合起来 > 80%
    if len(sorted_items) >= 2:
        top2_total = top1_data["total"] + sorted_items[1][1]["total"]
        top2_pct = top2_total / amt * 100
        if top2_pct > 80:
            t2_name = sorted_items[1][0]
            return f"{top1_name[:8]} ¥{top1_data['total']:,.0f} | {t2_name[:8]} ¥{sorted_items[1][1]['total']:,.0f}"

    # 场景3: 笔均 + Top提示
    avg = amt / cnt
    if top1_pct < 50:
        return f"笔均 ¥{avg:.1f}, TOP: {top1_name[:8]} ¥{top1_data['total']:,.0f}"
    return f"笔均 ¥{avg:.1f}"


def _build_json(records, total, n, months, month_count, income_total, amount_buckets, item_freq, cat_amounts, cat_counts):
    """构建 JSON 数据，返回 dict"""

    # 层级结构
    layer_structure = []
    for layer_name, sub_cats in LAYER_GROUPS.items():
        layer_total = sum(cat_amounts.get(c, 0) for c in sub_cats)
        layer_count = sum(cat_counts.get(c, 0) for c in sub_cats)
        if layer_total == 0:
            continue
        subcategories = []
        for sub in sub_cats:
            amt = cat_amounts.get(sub, 0)
            cnt = cat_counts.get(sub, 0)
            if cnt == 0:
                continue
            subcategories.append({
                "name": sub,
                "amount": round(amt, 2),
                "count": cnt,
                "layer_percentage": f"{round(amt / layer_total * 100)}%",
                "total_percentage": f"{round(amt / total * 100, 1)}%",
                "monthly_avg": round(amt / month_count, 2),
                "note": _build_json_note(records, sub, amt, cnt),
            })
        layer_structure.append({
            "layer_name": layer_name,
            "total": round(layer_total, 2),
            "count": layer_count,
            "total_percentage": round(layer_total / total * 100, 1),
            "monthly_avg": round(layer_total / month_count, 2),
            "subcategories": subcategories,
        })

    # item_name 聚合（取所有项目）
    item_agg = defaultdict(lambda: {"amount": 0.0, "count": 0, "high_count": 0, "category": "",
                                     "刚性固定": 0.0, "刚性必要": 0.0, "弹性可选": 0.0})
    for r in records:
        name = r["item"]
        item_agg[name]["amount"] += r["amt"]
        item_agg[name]["count"] += 1
        if r["amt"] > 50:
            item_agg[name]["high_count"] += 1
        item_agg[name]["category"] = r["cat"]
        et = r.get("expense_type", "未分类") or "未分类"
        if et in ("刚性固定", "刚性必要", "弹性可选"):
            item_agg[name][et] += r["amt"]

    sorted_items = sorted(item_agg.items(), key=lambda x: (x[1]["category"], -x[1]["amount"]))
    item_breakdown = [
        {
            "rank": idx,
            "item_name": name,
            "category": info["category"],
            "amount": round(info["amount"], 2),
            "count": info["count"],
            "high_amount_count": info["high_count"],
            "刚性固定": round(info["刚性固定"], 2),
            "刚性必要": round(info["刚性必要"], 2),
            "弹性可选": round(info["弹性可选"], 2),
            "total_percentage": f"{round(info['amount'] / total * 100, 1)}%" if total > 0 else "0%",
        }
        for idx, (name, info) in enumerate(sorted_items, 1)
        if info["count"] >= 5 or info["high_count"] > 0
    ]

    # 消费频次分布（按金额区间）
    freq_buckets = [
        ("0-20", 0, 20), ("20-30", 20, 30), ("30-50", 30, 50),
        ("50-100", 50, 100), ("100-200", 100, 200), ("200-500", 200, 500),
        ("500+", 500, float("inf")),
    ]
    freq_counts = {label: 0 for label, _, _ in freq_buckets}
    freq_et_json = {label: {"刚性固定": 0, "刚性必要": 0, "弹性可选": 0} for label, _, _ in freq_buckets}
    for r in records:
        for label, lo, hi in freq_buckets:
            if lo <= r["amt"] < hi:
                freq_counts[label] += 1
                et = r.get("expense_type", "未分类") or "未分类"
                if et in freq_et_json[label]:
                    freq_et_json[label][et] += 1
                break
    total_count = len(records)
    consumption_frequency = [
        {
            "range": f"¥{label}",
            "count": count,
            "刚性固定": freq_et_json[label]["刚性固定"],
            "刚性必要": freq_et_json[label]["刚性必要"],
            "弹性可选": freq_et_json[label]["弹性可选"],
            "percentage": f"{round(count / total_count * 100, 1)}%" if total_count > 0 else "0%",
        }
        for label, _, _ in freq_buckets
        for count in [freq_counts[label]]
    ]

    # 食品深度追踪
    food_records = [r for r in records if r["cat"] in ("食品", "饮品")]
    food_tracking = None
    if food_records:
        # 按店铺统计
        food_items_monthly_count = defaultdict(lambda: defaultdict(int))
        food_items_stats = defaultdict(lambda: {"total": 0.0, "has_high": False})
        for r in food_records:
            name = r["item"]
            ym = r["ym"]
            food_items_monthly_count[name][ym] += 1
            food_items_stats[name]["total"] += r["amt"]
            if r["amt"] > 30:
                food_items_stats[name]["has_high"] = True
        for name, month_counts in food_items_monthly_count.items():
            food_items_stats[name]["max_monthly"] = max(month_counts.values())

        top_food_items = sorted(
            [(name, s["total"], s["max_monthly"]) for name, s in food_items_stats.items()
             if s["max_monthly"] > 5 or s["has_high"]],
            key=lambda x: x[1], reverse=True
        )[:12]
        top_food_names = [name[:8] for name, _, _ in top_food_items]

        food_by_month = {}
        prev_food_total = None
        for m in months:
            m_food = [r for r in food_records if r["ym"] == m]
            total_m = sum(r["amt"] for r in m_food) if m_food else 0
            count_m = len(m_food)
            tier_small = sum(1 for r in m_food if r["amt"] < 10)
            tier_normal = sum(1 for r in m_food if 10 <= r["amt"] < 30)
            tier_big = sum(1 for r in m_food if 30 <= r["amt"] < 50)
            tier_huge = sum(1 for r in m_food if r["amt"] >= 50)

            # 环比
            if prev_food_total is not None and prev_food_total > 0:
                diff = total_m - prev_food_total
                pct = diff / prev_food_total * 100
                arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
                mom_str = f"{arrow}¥{abs(diff):,.0f} ({pct:+.0f}%)"
            else:
                mom_str = "—"
            prev_food_total = total_m

            # 店铺详情
            store_detail = defaultdict(lambda: {"amount": 0.0, "count": 0})
            for r in m_food:
                store_detail[r["item"][:8]]["amount"] += r["amt"]
                store_detail[r["item"][:8]]["count"] += 1
            store_items = sorted(
                [(n, d["amount"], d["count"]) for n, d in store_detail.items() if n in set(top_food_names)],
                key=lambda x: x[1], reverse=True
            )

            food_by_month[m] = {
                "month": m,
                "total": round(total_m, 2),
                "count": count_m,
                "avg_per_transaction": round(total_m / count_m, 2) if count_m > 0 else 0,
                "mom_change": mom_str,
                "store_details": [
                    {"name": n, "amount": round(a, 2), "count": c}
                    for n, a, c in store_items
                ] if store_items else [],
                "tier_breakdown": {
                    "小食_lt10": f"{tier_small}笔 ({round(tier_small/count_m*100)}%)" if count_m > 0 else "—",
                    "正餐_10_30": f"{tier_normal}笔 ({round(tier_normal/count_m*100)}%)" if count_m > 0 else "—",
                    "大餐_30_50": f"{tier_big}笔 ({round(tier_big/count_m*100)}%)" if count_m > 0 else "—",
                    "聚餐_gt50": f"{tier_huge}笔 ({round(tier_huge/count_m*100)}%)" if count_m > 0 else "—",
                },
            }
    else:
        food_by_month = {}

    food_tracking = {
        "monthly_detail": list(food_by_month.values()),
        "top_items": [
            {"name": name, "total_amount": round(total_amt, 2), "max_monthly_count": max_cnt}
            for name, total_amt, max_cnt in top_food_items
        ] if food_records else [],
    }

    json_output = {
        "title": "支出专项分析",
        "header": {
            "date_start": records[0]["date"],
            "date_end": records[-1]["date"],
            "month_count": month_count,
            "record_count": n,
            "total_expense": round(total, 2),
            "monthly_avg": round(total / month_count, 2),
            "daily_avg": round(total / month_count / 30, 2),
        },
        "layer_structure": layer_structure,
        "item_breakdown": item_breakdown,
        "consumption_frequency": consumption_frequency,
        "food_tracking": food_tracking,
    }

    return json_output


# ──────────────────────────────────────────────────────────
# 核心分析 + Tool
# ──────────────────────────────────────────────────────────

def _run_analysis(db_path: str, start_date: str | None = None, end_date: str | None = None) -> tuple[str, dict]:
    """核心分析逻辑，返回 (markdown, json_output)"""
    records, total, n, months, month_count, income_total, amount_buckets, item_freq = load_data(db_path, start_date=start_date, end_date=end_date)
    cat_amounts, cat_counts = preprocess(records)

    md = []
    render_header(md, records, total, n, month_count)
    render_layer_structure(md, records, total, month_count)
    render_item_breakdown(md, records, total)
    render_food_deep_tracking(md, records, months)

    json_output = _build_json(records, total, n, months, month_count, income_total, amount_buckets, item_freq, cat_amounts, cat_counts)

    return "".join(md), json_output


@tool
def analyze_expense(start_date: str | None = None, end_date: str | None = None) -> dict:
    """支出专项分析 - 支出层级结构、item明细、消费频次分布、食品类深度追踪。
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
        md_filename = f"expense_analysis{suffix}.md"
        json_filename = f"expense_analysis{suffix}.json"
    else:
        md_filename = "expense_analysis.md"
        json_filename = "expense_analysis.json"

    md_path = os.path.join(OUTPUT_DIR, md_filename)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_str)

    json_path = os.path.join(OUTPUT_DIR, json_filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)

    print(f"报告已生成: {md_path}")
    print(f"JSON 已生成: {json_path}")
