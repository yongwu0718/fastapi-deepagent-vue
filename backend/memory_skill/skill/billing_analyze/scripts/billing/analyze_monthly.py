import sqlite3
from collections import defaultdict

try:
    from .common import DB_PATH, build_date_filter
except ImportError:
    from common import DB_PATH, build_date_filter  # type: ignore


def _run_analysis(db_path: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    """核心分析逻辑，返回 json_output"""

    # ─── 数据读取 ───────────────────────────────────────────
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 支出（类型 = '支出'，表中金额为绝对值，转正存储）
    _exp_where, _exp_params = build_date_filter("类型 = '支出'", start_date, end_date)
    cursor.execute(f"SELECT * FROM billing_records WHERE {_exp_where} ORDER BY 日期", _exp_params)
    exp_records = []
    for r in cursor.fetchall():
        exp_records.append({
            "日期": r["日期"],
            "年月": r["日期"][:7],
            "名称": r["消费名称"],
            "大类": r["消费大类"],
            "细类": r["消费细类"] or "未分类",
            "金额": abs(r["金额"]),
            "平台": r["支付平台"],
            "分类": r["消费类型"] or "未分类",
        })

    # 收入（来源 income_records，无"消费类型"列，分类置空）
    _inc_where, _inc_params = build_date_filter("类型 = '收入'", start_date, end_date)
    cursor.execute(f"SELECT * FROM income_records WHERE {_inc_where} ORDER BY 日期", _inc_params)
    inc_records = []
    for r in cursor.fetchall():
        inc_records.append({
            "日期": r["日期"],
            "年月": r["日期"][:7],
            "名称": r["消费名称"],
            "大类": r["消费大类"],
            "细类": r["消费细类"] or "未分类",
            "金额": abs(r["金额"]),
            "平台": r["支付平台"],
            "分类": "",
        })

    conn.close()

    months = sorted(set(r["年月"] for r in exp_records))
    month_count = len(months)
    total_exp = sum(r["金额"] for r in exp_records)
    total_inc = sum(r["金额"] for r in inc_records)

    # ===== 分层统计 =====
    # 三层支出
    rigid_fixed = [r for r in exp_records if (r.get("分类") or "未分类") == "刚性固定"]
    rigid_necessary = [r for r in exp_records if (r.get("分类") or "未分类") == "刚性必要"]
    flexible = [r for r in exp_records if (r.get("分类") or "未分类") == "弹性支出"]

    # ─── JSON 输出 ────────────────────────────────────────────
    income_by_month_json = defaultdict(float)
    real_income_by_month_json = defaultdict(float)
    expense_by_month_json = defaultdict(float)
    rigid_fixed_json = defaultdict(float)
    rigid_necessary_json = defaultdict(float)
    flex_exp_json = defaultdict(float)

    for r in inc_records:
        ym = r["年月"]
        income_by_month_json[ym] += r["金额"]
        if r.get("大类", "") != "转账收款":
            real_income_by_month_json[ym] += r["金额"]

    for r in exp_records:
        ym = r["年月"]
        expense_by_month_json[ym] += r["金额"]
        etype = r.get("分类") or "未分类"
        if etype == "刚性固定":
            rigid_fixed_json[ym] += r["金额"]
        elif etype == "刚性必要":
            rigid_necessary_json[ym] += r["金额"]
        elif etype == "弹性支出":
            flex_exp_json[ym] += r["金额"]

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

    rigid_fixed_by_month_detail = {}
    for m in months:
        items = [r for r in rigid_fixed if r["年月"] == m]
        detail = defaultdict(float)
        for r in items:
            detail[r["名称"][:12]] += r["金额"]
        rigid_fixed_by_month_detail[m] = {
            "total": sum(r["金额"] for r in items),
            "detail": dict(detail),
        }

    fixed_norm_dict = {}
    for item_name in set(k for m in months for k in rigid_fixed_by_month_detail[m]["detail"]):
        amounts = [rigid_fixed_by_month_detail[m]["detail"].get(item_name, 0) for m in months]
        non_zero = [a for a in amounts if a > 0]
        fixed_norm_dict[item_name] = {
            "avg": round(sum(non_zero) / len(non_zero), 2) if non_zero else 0,
            "months_active": len(non_zero),
        }

    rigid_fixed_items = sorted(set(r["名称"][:12] for r in rigid_fixed))
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

    rigid_necessary_monthly = []
    prev_nec_total = None
    for m in months:
        m_necessary = [r for r in rigid_necessary if r["年月"] == m]
        m_total = sum(r["金额"] for r in m_necessary)

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

        # 效率评估（仅按大类总额判断，不展开细类）
        cat_totals = defaultdict(float)
        for r in m_necessary:
            cat_totals[r["大类"]] += r["金额"]

        efficiency_flags = []
        for cat, total in cat_totals.items():
            if cat == "交通" and total > 500:
                efficiency_flags.append("交通偏高")
            if cat == "医疗" and total > 100:
                efficiency_flags.append("医疗偏高")
            if cat == "其他" and total > 300:
                efficiency_flags.append("其他偏高")

        rigid_necessary_monthly.append({
            "month": m,
            "total": round(m_total, 2),
            "mom_change": mom_str,
            "efficiency_evaluation": " | ".join(efficiency_flags) if efficiency_flags else "基本正常",
        })

    flexible_monthly = []
    for m in months:
        m_flex = [r for r in flexible if r["年月"] == m]
        total_flex = sum(r["金额"] for r in m_flex)

        item_counts = defaultdict(int)
        for r in m_flex:
            item_counts[r["名称"]] += 1

        high_freq_list = [item for item, cnt in item_counts.items() if cnt > 10]
        high_freq_str = " | ".join(high_freq_list[:8]) if high_freq_list else "—"
        if len(high_freq_list) > 8:
            high_freq_str += f" (等{len(high_freq_list)}项)"

        large_list = [(r["名称"][:12], r["金额"]) for r in m_flex if r["金额"] > 50]
        large_list.sort(key=lambda x: x[1], reverse=True)
        large_str = "\n".join([f"{name} ¥{amt:,.0f}" for name, amt in large_list]) if large_list else "—"

        flexible_monthly.append({
            "month": m,
            "total": round(total_flex, 2),
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
            "rigid_fixed_total": round(sum(r["金额"] for r in rigid_fixed), 2),
            "rigid_necessary_total": round(sum(r["金额"] for r in rigid_necessary), 2),
            "flexible_total": round(sum(r["金额"] for r in flexible), 2),
        },
        "monthly_income_expense": monthly_income_expense,
        "rigid_fixed_monthly": rigid_fixed_monthly,
        "rigid_necessary_monthly": rigid_necessary_monthly,
        "flexible_monthly": flexible_monthly,
    }

    return json_output


def analyze_monthly(start_date: str | None = None, end_date: str | None = None) -> dict:
    """三层逐月分析 - 逐月收支、刚性固定监控、刚性必要效率追踪、弹性可选行为追踪。
    数据来源 billing_records 表，金额约定：表中"金额"为绝对值，方向由"类型"区分。

    Args:
        start_date: 可选，起始日期（含），格式 "YYYY-MM-DD"，如 "2025-01-01"
        end_date: 可选，结束日期（含），格式 "YYYY-MM-DD"，如 "2025-06-30"
    """
    json_output = _run_analysis(DB_PATH, start_date=start_date, end_date=end_date)
    return json_output


if __name__ == "__main__":
    import sys
    import json as _json

    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date = sys.argv[2] if len(sys.argv) > 2 else None

    json_output = _run_analysis(DB_PATH, start_date=start_date, end_date=end_date)
    print(_json.dumps(json_output, ensure_ascii=False, indent=2))
