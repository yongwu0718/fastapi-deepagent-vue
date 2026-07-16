"""三层逐月分析框架 ─ 刚性固定(监控) · 刚性必要(效率) · 弹性可选(行为)
金额约定：支出 < 0，收入 > 0

用法：
  1. 作为 LangChain Tool：from analyze_monthly import analyze_monthly
  2. 作为脚本：python analyze_monthly.py （生成 MD + JSON 文件）
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


def get_expense_type(r):
    """兼容不同字段名"""
    return r.get("expense_type") or r.get("expenseType") or "未分类"


def _run_analysis(db_path: str, start_date: str | None = None, end_date: str | None = None) -> tuple[str, dict]:
    """核心分析逻辑，返回 (markdown, json_output)"""

    # ─── 数据读取 ───────────────────────────────────────────
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 支出（金额负数，取反后存储）
    _exp_where, _exp_params = _build_date_filter("amount < 0", start_date, end_date)
    cursor.execute(f"SELECT * FROM records WHERE {_exp_where} ORDER BY date", _exp_params)
    exp_records = [{**dict(r), "amount": -r["amount"]} for r in cursor.fetchall()]

    # 收入
    _inc_where, _inc_params = _build_date_filter("amount > 0", start_date, end_date)
    cursor.execute(f"SELECT * FROM records WHERE {_inc_where} ORDER BY date", _inc_params)
    inc_records = [dict(r) for r in cursor.fetchall()]

    conn.close()

    months = sorted(set(r["year_month"] for r in exp_records))
    month_count = len(months)
    total_exp = sum(r["amount"] for r in exp_records)
    total_inc = sum(r["amount"] for r in inc_records)

    # ===== 分层统计 =====
    # 三层支出
    rigid_fixed = [r for r in exp_records if get_expense_type(r) == "刚性固定"]
    rigid_necessary = [r for r in exp_records if get_expense_type(r) == "刚性必要"]
    flexible = [r for r in exp_records if get_expense_type(r) == "弹性可选"]

    md = []

    md.append("# 📅 三层逐月分析 · 刚性监控 + 效率追踪 + 弹性深度\n\n")
    rigid_fixed_sum = sum(r['amount'] for r in rigid_fixed)
    rigid_necessary_sum = sum(r['amount'] for r in rigid_necessary)
    flexible_sum = sum(r['amount'] for r in flexible)
    net_color = "🔴" if total_inc < total_exp else "🟢"
    md.append(f"> 共 {month_count} 个月  |  "
              f"总支出 **¥{total_exp:,.2f}**  |  "
              f"总收入 **¥{total_inc:,.2f}**  |  "
              f"净额 {net_color} ¥{total_inc - total_exp:,.2f}\n")
    md.append(f"> 刚性固定 ¥{rigid_fixed_sum:,.0f}  |  "
              f"刚性必要 ¥{rigid_necessary_sum:,.0f}  |  "
              f"弹性可选 **¥{flexible_sum:,.0f}**\n\n")

    # ─── 一、逐月分析收支（去转账后）──────────────────────
    md.append("---\n\n## 一、逐月分析收支（去转账后）\n\n")

    income_by_month = defaultdict(float)
    real_income_by_month = defaultdict(float)
    expense_by_month = defaultdict(float)

    for r in inc_records:
        ym = r["year_month"]
        income_by_month[ym] += r["amount"]
        if r.get("category", "") != "转账收款":
            real_income_by_month[ym] += r["amount"]

    for r in exp_records:
        expense_by_month[r["year_month"]] += r["amount"]

    rigid_fixed_by_month = defaultdict(float)
    rigid_necessary_by_month = defaultdict(float)
    flex_exp_by_month = defaultdict(float)
    for r in exp_records:
        etype = get_expense_type(r)
        if etype == "刚性固定":
            rigid_fixed_by_month[r["year_month"]] += r["amount"]
        elif etype == "刚性必要":
            rigid_necessary_by_month[r["year_month"]] += r["amount"]
        elif etype == "弹性可选":
            flex_exp_by_month[r["year_month"]] += r["amount"]

    md.append("| 月份 | 总收入 | 真实收入 | 支出 | 刚性固定 | 刚性必要 | 弹性可选 | 弹性负担率 | 刚性负担率 | 净额 | 收支比 | 评价 |\n")
    md.append("|------|------|------|------|------|------|------|------|------|------|------|------|\n")

    for m in months:
        inc = income_by_month.get(m, 0)
        real_inc = real_income_by_month.get(m, 0)
        exp = expense_by_month.get(m, 0)
        rigid_fixed_amt = rigid_fixed_by_month.get(m, 0)
        rigid_necessary_amt = rigid_necessary_by_month.get(m, 0)
        flex_amt = flex_exp_by_month.get(m, 0)
        flex_burden = flex_amt / real_inc * 100 if real_inc > 0 else 0
        rigid_burden = (rigid_fixed_amt + rigid_necessary_amt) / real_inc * 100 if real_inc > 0 else 0
        net = inc - exp
        ratio = exp / inc * 100 if inc > 0 else (float('inf') if exp > 0 else 0)

        ratio_str = f"{ratio:.0f}%" if real_inc > 0 else "N/A"
        net_str = f"+¥{net:,.0f}" if net >= 0 else f"-¥{abs(net):,.0f}"

        if net >= 0:
            eval_str = "✅ 结余"
        elif real_inc > 0 and ratio > 150:
            eval_str = "🔴 严重赤字"
        else:
            eval_str = "⚠️ 赤字"

        transfers = inc - real_inc
        inc_display = f"¥{inc:,.0f}"
        if transfers > 0.5:
            inc_display += f"<br>(含转账 ¥{transfers:,.0f})"

        md.append(
            f"| {m} | {inc_display} | ¥{real_inc:,.0f} | ¥{exp:,.0f} | "
            f"¥{rigid_fixed_amt:,.0f} | ¥{rigid_necessary_amt:,.0f} | "
            f"¥{flex_amt:,.0f} | {flex_burden:.0f}% | {rigid_burden:.0f}% | "
            f"{net_str} | {ratio_str} | {eval_str} |\n"
        )

    md.append("\n")

    # ─── 二、刚性固定支出月度监控 ──────────────────────────
    md.append("---\n\n## 二、刚性固定支出月度监控\n\n")

    rigid_fixed_by_month = {}
    for m in months:
        items = [r for r in rigid_fixed if r["year_month"] == m]
        rigid_fixed_by_month[m] = {
            "total": sum(r["amount"] for r in items),
            "items": items,
            "detail": defaultdict(float)
        }
        for r in items:
            rigid_fixed_by_month[m]["detail"][r["item_name"][:12]] += r["amount"]

    # 计算"正常水平"（用于异常检测）
    fixed_norm = {}
    for item_name in set(k for m in months for k in rigid_fixed_by_month[m]["detail"]):
        amounts = [rigid_fixed_by_month[m]["detail"].get(item_name, 0) for m in months]
        non_zero = [a for a in amounts if a > 0]
        fixed_norm[item_name] = {
            "avg": sum(non_zero) / len(non_zero) if non_zero else 0,
            "months_active": len(non_zero),
            "first_month": [m for m in months if rigid_fixed_by_month[m]["detail"].get(item_name, 0) > 0][0] if non_zero else None,
            "last_month": [m for m in months if rigid_fixed_by_month[m]["detail"].get(item_name, 0) > 0][-1] if non_zero else None
        }

    # 收集所有刚性固定 item_name
    rigid_fixed_items = sorted(set(r["item_name"][:12] for r in rigid_fixed))

    # Markdown 表头
    header_cols = ["月份", "总额"] + rigid_fixed_items + ["异常标记"]
    md.append("| " + " | ".join(header_cols) + " |\n")
    md.append("|" + "|".join(["------"] * len(header_cols)) + "|\n")

    for m in months:
        detail = rigid_fixed_by_month[m]["detail"]

        # 异常检测
        flags = []
        for item_name, amt in detail.items():
            norm = fixed_norm.get(item_name, {})
            if norm.get("avg", 0) > 0 and amt > norm["avg"] * 1.3:
                flags.append(f"⚠ {item_name}超常¥{amt:,.0f}")
            if norm.get("first_month") == m and amt > 0:
                flags.append(f"🆕 新增{item_name}¥{amt:,.0f}/月")

        flag_str = "<br>".join(flags) if flags else "—"

        row_data = [m, f"¥{rigid_fixed_by_month[m]['total']:,.0f}"]
        for item in rigid_fixed_items:
            amt = detail.get(item, 0)
            row_data.append(f"¥{amt:,.0f}" if amt > 0 else "—")
        row_data.append(flag_str)
        md.append("| " + " | ".join(row_data) + " |\n")

    md.append("\n")

    # ─── 三、刚性必要支出效率追踪 ──────────────────────────
    md.append("---\n\n## 三、刚性必要支出效率追踪\n\n")

    md.append("| 月份 | 总额 | 环比 | 细项分类 | 效率评价 |\n")
    md.append("|------|------|------|------|------|\n")

    prev_total = None
    for m in months:
        m_necessary = [r for r in rigid_necessary if r["year_month"] == m]
        m_total = sum(r["amount"] for r in m_necessary)

        # 环比
        if prev_total is not None and prev_total > 0:
            diff = m_total - prev_total
            pct = diff / prev_total * 100
            arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
            mom_str = f"{arrow}¥{abs(diff):,.0f} ({pct:+.0f}%)"
        else:
            mom_str = "—"
        prev_total = m_total

        # 按 category 汇总
        cat_breakdown = defaultdict(lambda: {"total": 0.0, "count": 0})
        for r in m_necessary:
            cat_breakdown[r["category"]]["total"] += r["amount"]
            cat_breakdown[r["category"]]["count"] += 1

        detail_parts = []
        for cat, info in sorted(cat_breakdown.items(), key=lambda x: x[1]["total"], reverse=True):
            detail_parts.append(f"**{cat}**:¥{info['total']:,.0f}({info['count']}笔)")

        # 交通方式细分
        transport = [r for r in m_necessary if r["category"] == "交通出行"]
        if transport:
            transport_by_item = defaultdict(float)
            for r in transport:
                transport_by_item[r["item_name"][:8]] += r["amount"]
            t_str = "<br>".join([f"{k}¥{v:,.0f}" for k, v in sorted(transport_by_item.items(), key=lambda x: x[1], reverse=True)])
            detail_parts.append(f"- {t_str}")

        # 其他支出细分
        other = [r for r in m_necessary if r["category"] == "其他支出"]
        if other:
            other_by_item = defaultdict(float)
            for r in other:
                other_by_item[r["item_name"][:8]] += r["amount"]
            o_str = "<br>".join([f"{k}¥{v:,.0f}" for k, v in sorted(other_by_item.items(), key=lambda x: x[1], reverse=True)])
            detail_parts.append(f"- {o_str}")

        detail_str = "<br>".join(detail_parts)

        # 效率评价
        flags = []
        for cat, info in cat_breakdown.items():
            if cat == "交通出行" and info["total"] > 500:
                flags.append("⚠ 交通偏高")
            if cat == "医疗健康" and info["total"] > 100:
                flags.append("💊 医疗偏高")
            if cat == "其他支出" and info["total"] > 300:
                flags.append(f"⚠ 其他支出¥{info['total']:.0f}")
        if not flags:
            flags.append("基本正常")

        efficiency = "<br>".join(flags)

        md.append(f"| {m} | ¥{m_total:,.0f} | {mom_str} | {detail_str} | {efficiency} |\n")

    md.append("\n")

    # ─── 四、弹性可选支出追踪 ──────────────────────────────
    md.append("---\n\n## 四、弹性可选支出追踪\n\n")

    # 收集所有弹性支出中的 category
    flex_categories = sorted(set(r["category"] for r in flexible))

    header_cols = ["月份", "总额"] + flex_categories + ["高频消费(>10次)", "大额消费(>¥50)"]
    md.append("| " + " | ".join(header_cols) + " |\n")
    md.append("|" + "|".join(["------"] * len(header_cols)) + "|\n")

    for m in months:
        m_flex = [r for r in flexible if r["year_month"] == m]
        total_flex = sum(r["amount"] for r in m_flex)

        # 按 category 统计金额
        cat_amounts = defaultdict(float)
        item_counts = defaultdict(int)
        for r in m_flex:
            cat_amounts[r["category"]] += r["amount"]
            item_counts[r["item_name"]] += 1

        # 高频消费（同 item_name 出现 >10 次）
        high_freq_items = [item for item, cnt in item_counts.items() if cnt > 10]
        high_freq_str = "<br>".join(high_freq_items[:8]) if high_freq_items else "—"
        if len(high_freq_items) > 8:
            high_freq_str += f" (等{len(high_freq_items)}项)"

        # 大额消费（单笔 >¥50）
        large_items = [(r["item_name"][:12], r["amount"]) for r in m_flex if r["amount"] > 50]
        if large_items:
            large_parts = [f"{name} ¥{amt:,.0f}" for name, amt in sorted(large_items, key=lambda x: x[1], reverse=True)]
            large_str = "<br>".join(large_parts)
        else:
            large_str = "—"

        # 构建行数据
        row_data = [m, f"¥{total_flex:,.0f}"]
        for cat in flex_categories:
            amt = cat_amounts.get(cat, 0)
            row_data.append(f"¥{amt:,.0f}" if amt > 0 else "—")
        row_data.append(high_freq_str)
        row_data.append(large_str)
        md.append("| " + " | ".join(row_data) + " |\n")

    md.append("\n")

    # ─── JSON 输出 ────────────────────────────────────────────

    # 重新构建逐月数据（避免被重写的 rigid_fixed_by_month 影响）
    income_by_month_json = defaultdict(float)
    real_income_by_month_json = defaultdict(float)
    expense_by_month_json = defaultdict(float)
    rigid_fixed_json = defaultdict(float)
    rigid_necessary_json = defaultdict(float)
    flex_exp_json = defaultdict(float)

    for r in inc_records:
        ym = r["year_month"]
        income_by_month_json[ym] += r["amount"]
        if r.get("category", "") != "转账收款":
            real_income_by_month_json[ym] += r["amount"]

    for r in exp_records:
        ym = r["year_month"]
        expense_by_month_json[ym] += r["amount"]
        etype = get_expense_type(r)
        if etype == "刚性固定":
            rigid_fixed_json[ym] += r["amount"]
        elif etype == "刚性必要":
            rigid_necessary_json[ym] += r["amount"]
        elif etype == "弹性可选":
            flex_exp_json[ym] += r["amount"]

    # 一、逐月收支明细
    monthly_income_expense = []
    for m in months:
        inc = income_by_month_json.get(m, 0)
        real_inc = real_income_by_month_json.get(m, 0)
        exp = expense_by_month_json.get(m, 0)
        rf = rigid_fixed_json.get(m, 0)
        rn = rigid_necessary_json.get(m, 0)
        flex = flex_exp_json.get(m, 0)
        flex_burden = f"{round(flex / real_inc * 100)}%" if real_inc > 0 else "0%"
        rigid_burden = f"{round((rf + rn) / real_inc * 100)}%" if real_inc > 0 else "0%"
        net = inc - exp
        ratio = f"{round(exp / inc * 100)}%" if inc > 0 else "N/A"

        evaluation = "✅ 结余" if net >= 0 else ("🔴 严重赤字" if real_inc > 0 and (inc > 0 and exp / inc * 100 > 150) else "⚠️ 赤字")

        monthly_income_expense.append({
            "month": m,
            "total_income": round(inc, 2),
            "real_income": round(real_inc, 2),
            "expense": round(exp, 2),
            "rigid_fixed": round(rf, 2),
            "rigid_necessary": round(rn, 2),
            "flexible": round(flex, 2),
            "flexible_burden_rate": flex_burden,
            "rigid_burden_rate": rigid_burden,
            "net": round(net, 2),
            "expense_ratio": ratio,
            "evaluation": evaluation,
        })

    # 二、刚性固定月度监控（含异常检测）
    rigid_fixed_by_month_detail = {}
    for m in months:
        items = [r for r in rigid_fixed if r["year_month"] == m]
        detail = defaultdict(float)
        for r in items:
            detail[r["item_name"][:12]] += r["amount"]
        rigid_fixed_by_month_detail[m] = {
            "total": sum(r["amount"] for r in items),
            "detail": dict(detail),
        }

    # 计算正常水平
    fixed_norm_dict = {}
    for item_name in set(k for m in months for k in rigid_fixed_by_month_detail[m]["detail"]):
        amounts = [rigid_fixed_by_month_detail[m]["detail"].get(item_name, 0) for m in months]
        non_zero = [a for a in amounts if a > 0]
        fixed_norm_dict[item_name] = {
            "avg": round(sum(non_zero) / len(non_zero), 2) if non_zero else 0,
            "months_active": len(non_zero),
        }

    rigid_fixed_items = sorted(set(r["item_name"][:12] for r in rigid_fixed))
    rigid_fixed_monthly = []
    for m in months:
        detail = rigid_fixed_by_month_detail[m]["detail"]
        anomaly_flags = []
        for item_name, amt in detail.items():
            norm = fixed_norm_dict.get(item_name, {})
            if norm.get("avg", 0) > 0 and amt > norm["avg"] * 1.3:
                anomaly_flags.append(f"⚠ {item_name}超常¥{amt:,.0f}")
            first_month = None
            for mm in months:
                if rigid_fixed_by_month_detail[mm]["detail"].get(item_name, 0) > 0:
                    first_month = mm
                    break
            if first_month == m and amt > 0:
                anomaly_flags.append(f"🆕 新增{item_name}¥{amt:,.0f}/月")

        rigid_fixed_monthly.append({
            "month": m,
            "total": round(rigid_fixed_by_month_detail[m]["total"], 2),
            "items": [
                {"name": item, "amount": round(detail.get(item, 0), 2)}
                for item in rigid_fixed_items
            ],
            "anomaly_flags": "\n".join(anomaly_flags) if anomaly_flags else "—",
        })

    # 三、刚性必要效率追踪
    rigid_necessary_monthly = []
    prev_nec_total = None
    for m in months:
        m_necessary = [r for r in rigid_necessary if r["year_month"] == m]
        m_total = sum(r["amount"] for r in m_necessary)

        # 环比
        if prev_nec_total is not None and prev_nec_total > 0:
            diff = m_total - prev_nec_total
            pct = diff / prev_nec_total * 100
            if diff > 0:
                mom_str = f"↑¥{abs(diff):,.0f} ({pct:+.0f}%)"
            elif diff < 0:
                mom_str = f"↓¥{abs(diff):,.0f} ({pct:+.0f}%)"
            else:
                mom_str = "→ 持平"
        else:
            mom_str = "—"
        prev_nec_total = m_total

        cat_breakdown = defaultdict(lambda: {"total": 0.0, "count": 0, "sub_items": defaultdict(float)})
        for r in m_necessary:
            cat_breakdown[r["category"]]["total"] += r["amount"]
            cat_breakdown[r["category"]]["count"] += 1
            cat_breakdown[r["category"]]["sub_items"][r["item_name"][:12]] += r["amount"]

        detail_list = []
        for cat, info in sorted(cat_breakdown.items(), key=lambda x: x[1]["total"], reverse=True):
            detail_list.append({
                "category": cat,
                "amount": round(info["total"], 2),
                "count": info["count"],
                "sub_items": [{"name": k, "amount": round(v, 2)}
                              for k, v in sorted(info["sub_items"].items(), key=lambda x: x[1], reverse=True)]
            })

        efficiency_flags = []
        for cat, info in cat_breakdown.items():
            if cat == "交通出行" and info["total"] > 500:
                efficiency_flags.append("交通偏高")
            if cat == "医疗健康" and info["total"] > 100:
                efficiency_flags.append("医疗偏高")
            if cat == "其他支出" and info["total"] > 300:
                efficiency_flags.append(f"其他支出偏高")

        rigid_necessary_monthly.append({
            "month": m,
            "total": round(m_total, 2),
            "mom_change": mom_str,
            "details": detail_list,
            "efficiency_evaluation": " | ".join(efficiency_flags) if efficiency_flags else "基本正常",
        })

    # 四、弹性可选消费行为
    flexible_monthly = []
    for m in months:
        m_flex = [r for r in flexible if r["year_month"] == m]
        total_flex = sum(r["amount"] for r in m_flex)

        cat_amounts = defaultdict(float)
        item_counts = defaultdict(int)
        for r in m_flex:
            cat_amounts[r["category"]] += r["amount"]
            item_counts[r["item_name"]] += 1

        # 高频消费
        high_freq_list = [item for item, cnt in item_counts.items() if cnt > 10]
        high_freq_str = " | ".join(high_freq_list[:8]) if high_freq_list else "—"
        if len(high_freq_list) > 8:
            high_freq_str += f" (等{len(high_freq_list)}项)"

        # 大额消费
        large_list = [(r["item_name"][:12], r["amount"]) for r in m_flex if r["amount"] > 50]
        large_list.sort(key=lambda x: x[1], reverse=True)
        large_str = "\n".join([f"{name} ¥{amt:,.0f}" for name, amt in large_list]) if large_list else "—"

        flexible_monthly.append({
            "month": m,
            "total": round(total_flex, 2),
            "category_breakdown": [
                {"category": cat, "amount": round(cat_amounts.get(cat, 0), 2)}
                for cat in flex_categories
            ],
            "high_frequency_items": high_freq_str,
            "large_amount_items": large_str,
        })

    json_output = {
        "title": "三层逐月分析",
        "month_count": month_count,
        "summary": {
            "total_expense": round(total_exp, 2),
            "total_income": round(total_inc, 2),
            "net": round(total_inc - total_exp, 2),
            "rigid_fixed_total": round(sum(r["amount"] for r in rigid_fixed), 2),
            "rigid_necessary_total": round(sum(r["amount"] for r in rigid_necessary), 2),
            "flexible_total": round(sum(r["amount"] for r in flexible), 2),
        },
        "monthly_income_expense": monthly_income_expense,
        "rigid_fixed_monthly": rigid_fixed_monthly,
        "rigid_necessary_monthly": rigid_necessary_monthly,
        "flexible_monthly": flexible_monthly,
    }

    return "".join(md), json_output


@tool
def analyze_monthly(start_date: str | None = None, end_date: str | None = None) -> dict:
    """三层逐月分析 - 逐月收支、刚性固定监控、刚性必要效率追踪、弹性可选行为追踪。
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
        md_filename = f"monthly_3layer{suffix}.md"
        json_filename = f"monthly_3layer{suffix}.json"
    else:
        md_filename = "monthly_3layer.md"
        json_filename = "monthly_3layer.json"

    md_path = os.path.join(OUTPUT_DIR, md_filename)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_str)

    json_path = os.path.join(OUTPUT_DIR, json_filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)

    print(f"报告已生成: {md_path}")
    print(f"JSON 已生成: {json_path}")
