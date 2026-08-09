---
type: concept
title: Analysis Modes — JSON Contracts of the Four analyze Commands
description: Ground-truth JSON output structure of analyze billing, expense, monthly, and category, with aggregation rules, sign conventions, and the stale-reference catalog.
tags: [billing-analyze, cli, analysis]
---

# Analysis Modes — JSON Contracts

All four analysis modules read `records_view` (see [architecture/data-model.md](/openwiki/architecture/data-model.md)) and accept optional inclusive `start_date` / `end_date` (`YYYY-MM-DD`). The JSON below reflects the **actual code** in `scripts/billing/analyze_*.py`. The former agent-facing reference `references/tools_reference.md` (now removed) described a different, older contract — the stale catalog at the bottom of this page lists what must **not** be propagated.

## `analyze billing` — comprehensive overview

Entrypoint: `analyze_billing._run_analysis()` / `python cli.py analyze billing`. Top-level keys:

```
title: "个人账单综合分析报告"
date_range: { start, end }          # first/last date actually seen, or None
total_records: int
section_1_收支总览:
  收入:    { 总收入, 真实收入_去转账, 真实收入_占总收入比例, 转账收入, 转账收入_占总收入比例 }
  支出:    { 总支出, 刚性固定, 刚性固定_占比, 刚性必要, 刚性必要_占比, 弹性支出, 弹性支出_占比 }
  净收支:  { 净收支_总收入口径, 净收支_真实收入口径 }
  核心支出_去掉住房交通: { 金额, 占总支出比例, 说明 }
section_2_收入分类: [ { category, amount, percentage, subcategories: [ { subcategory, amount } ] } ]
section_3_平台使用分布: [ { rank, platform, expense, 刚性固定, 刚性必要, 弹性支出,
                            income, transfer_income, count, percentage,
                            top_3_categories: [ { category, amount } ] } ]
```

Aggregation rules implemented here:

- **真实收入** = 总收入 − 转账收款; both net metrics are emitted (`净收支_总收入口径`, `净收支_真实收入口径`).
- **核心支出** = 总支出 − 交通 − 住房 (excludes the "rigid necessary" housing/transport categories).
- Expense-type buckets: 刚性固定 / 刚性必要 / 弹性支出 tallied from the `分类` column; anything else (including empty) falls outside all three.
- Percentages are formatted strings like `"42.5%"` or `"N/A"` when the denominator is zero.
- `section_2_收入分类` is ordered by amount descending and includes a per-category subcategory breakdown.
- `section_3_平台使用分布` is ordered by transaction count descending; each platform lists its top 3 categories by amount and its transfer income.

## `analyze expense` — expense deep-dive

Entrypoint: `analyze_expense._run_analysis()` / `python cli.py analyze expense`. Top-level keys:

```
title: "支出专项分析"
header: { date_start, date_end, record_count, total_expense, income_total }
subcategory_ranking: [ { category, total_amount, total_percentage,
                         subcategories: [ { rank, subcategory, amount, count, percentage,
                                            刚性固定, 刚性必要, 弹性支出 } ] } ]
item_breakdown: [ { rank, item_name, category, subcategory, amount, count,
                    avg_per_transaction, total_percentage,
                    刚性固定, 刚性必要, 弹性支出 } ]
consumption_frequency: [ { range, count, 刚性固定, 刚性必要, 弹性支出, percentage } ]
high_frequency_items: [ { rank, item, subcategory, count, total, avg } ]   # top 10
```

Rules:

- Only expense rows (`金额 < 0`) are loaded; `income_total` is fetched separately for the header.
- **`item_breakdown` filters**: only items with `amount > 50` **or** `count > 10` are emitted. Items are grouped by exact `itemName`; `subcategory` is the item's dominant subcategory; the three expense-type totals are per item.
- **`consumption_frequency`** buckets: ¥0-20, ¥20-50, ¥50-100, ¥100-200, ¥200-500, ¥500+ (half-open `[lo, hi)`); each bucket also counts how many of its transactions are 刚性固定 / 刚性必要 / 弹性支出.
- **`high_frequency_items`** is the top 10 by transaction count.
- **Empty data** returns `{ "title": "支出专项分析", "header": {"record_count": 0}, "error": "无支出记录" }`.

## `analyze monthly` — three-tier monthly series

Entrypoint: `analyze_monthly._run_analysis()` / `python cli.py analyze monthly`. Top-level keys:

```
title: "三层逐月分析"
month_count: int
summary: { total_expense, total_income, net, rigid_fixed_total, rigid_necessary_total, flexible_total }
monthly_income_expense: [ { month, total_income, real_income, expense, rigid_fixed, rigid_necessary,
                            flexible, flexible_burden_rate, rigid_burden_rate, net,
                            expense_ratio, evaluation } ]
rigid_fixed_monthly: [ { month, total, items: [ { name, amount } ], anomaly_flags } ]
rigid_necessary_monthly: [ { month, total, mom_change, efficiency_evaluation } ]
flexible_monthly: [ { month, total, high_frequency_items, large_amount_items } ]
```

Rules:

- **Months are derived only from expense rows** (`months = sorted(set(年月 for expense rows))`); a month that has income but zero expenses never appears.
- `real_income` excludes the `转账收款` category per month.
- **`evaluation`** for a month: `✅ 结余` when net >= 0; `🔴 严重赤字` when income > 0 and expense/income > 150%; otherwise `⚠️ 赤字`.
- `flexible_burden_rate` and `rigid_burden_rate` are percentage strings relative to `real_income` (`"0%"` when real income is 0).
- **`rigid_fixed_monthly`**: item names truncated to 12 chars; `anomaly_flags` flag items whose amount exceeds their multi-month average by 30% (`⚠ 名称超常¥...`) and items appearing for the first time (`🆕 新增...`); joined with newlines or `—`.
- **`rigid_necessary_monthly`**: `mom_change` is a month-over-month delta string (`↑¥N (+x%)` / `↓...` / `→ 持平`); `efficiency_evaluation` flags category totals above thresholds — 交通 > 500 → "交通偏高", 医疗 > 100 → "医疗偏高", 其他 > 300 → "其他偏高" — else "基本正常".
- **`flexible_monthly`**: `high_frequency_items` lists items with more than 10 transactions that month (up to 8, then `(等N项)`); `large_amount_items` lists items over ¥50 sorted descending.

## `analyze category` — monthly category/subcategory summary

Entrypoint: `analyze_category_monthly._run_analysis()` / `python cli.py analyze category`. Top-level keys:

```
title: "每月大类/细类汇总"
header: { date_start, date_end, months, month_count, record_count, total_expense }
monthly_category_breakdown: {
   months: [ ... ],
   monthly: [ { month, total, count,
                categories: [ { category, amount, count, percentage,
                                subcategories: [ { subcategory, amount, count, percentage } ] } ] } ]
}
subcategory_ranking_by_month: [ { month, subcategory_ranking: [ { rank, subcategory, category, amount, count } ] } ]
category_trend: [ { category, monthly_amounts: { "YYYY-MM": amount }, total } ]
```

Rules:

- Expense-only (`金额 < 0`), amounts made absolute.
- `monthly_category_breakdown`: per month, categories ordered by amount; subcategories ordered by amount within each category.
- `subcategory_ranking_by_month`: subcategories ranked across all categories for that month (ties broken by amount).
- `category_trend`: categories ordered by total amount; each lists its amount per month (zero-filling missing months).
- **Empty data** returns `{ "title": "每月大类/细类汇总", "months": [], "error": "无支出记录" }`.

## Cross-command comparison

| Need | Command | Key sections |
|------|---------|-------------|
| Overall income/expense picture, where money goes | `analyze billing` | `section_1_收支总览`, `section_3_平台使用分布` |
| Merchant-level detail, spending habits, frequency | `analyze expense` | `item_breakdown`, `high_frequency_items`, `consumption_frequency` |
| Month-over-month trend and three-tier monitoring | `analyze monthly` | `monthly_income_expense`, `rigid_*_monthly`, `flexible_monthly` |
| Per-month category/subcategory drill-down | `analyze category` | `monthly_category_breakdown`, `subcategory_ranking_by_month`, `category_trend` |

## Stale-reference catalog (do NOT propagate)

The following claims existed only in the removed `references/tools_reference.md` (and partly in `SKILL.md`) and contradict the code — **do not rely on them**:

- `analyze_billing` sections `section_2_支出分类排名` and `section_4_平台使用分布` — do not exist; actual keys are `section_1_收支总览`, `section_2_收入分类`, `section_3_平台使用分布`.
- `analyze_expense` sections `layer_structure` and `food_tracking` — do not exist.
- `analyze_monthly` `flexible_monthly.category_breakdown` — does not exist; only `total` / `high_frequency_items` / `large_amount_items`.
- The "资产管理工具" table (`add_account`, `list_accounts`, `snapshot_balance`, `current_balance`, `balance_trend`, `total_assets`) — no such code exists anywhere in `scripts/`.
- `SKILL.md`'s claim of a `年月` GENERATED column — the DB has none; `年月` is derived in `records_view` (see [architecture/data-model.md](/openwiki/architecture/data-model.md)).

## How the agent consumes these outputs

The analysis rules, budget formulas, and integrity checks in [agent-workflows.md](/openwiki/agent-workflows.md) all reference fields from these JSON contracts (e.g. `rigid_fixed_monthly` for the fixed-item check, `subcategory_ranking` for the food-ratio check, `monthly_income_expense` for the income-cliff check).
