---
type: concept
title: Agent Workflows — SKILL.md Orchestration
description: "The agent-facing contract for personal-bill analysis: data-entry gates, analysis modes A/B/C, seven analysis rules with thresholds, budget prediction math, and integrity checks."
tags: [billing-analyze, agent-workflow]
---

# Agent Workflows — SKILL.md Orchestration

`SKILL.md` at the repository root defines the behavior of the **billing analysis agent** — the consumer of the CLI, the references, and the report template. This page is the ground truth for that orchestration layer (the CLI mechanics live in [billing-cli/overview.md](/openwiki/billing-cli/overview.md); the JSON contracts in [billing-cli/analysis-modes.md](/openwiki/billing-cli/analysis-modes.md)).

## Step 0 — Data entry (strict gates)

1. Before analysis, ensure the DB exists (create via `init_db.py` if missing — see [billing-cli/records-import.md](/openwiki/billing-cli/records-import.md)) and that it contains records.
2. **Always run `list-categories` first**; every `--category`, `--subcategory`, `--expense-type`, `--platform`, `--direction` value must come from that output. Inventing category names is forbidden.
3. **Per-record saves need user confirmation**: parse the fields, present them as a table, wait for approval, then run `save-bill`.
4. **Batch imports need preview**: parse the file, show the first few rows, confirm field mapping, then import. Direct SQL writes, taskkill, parameter guessing, and hand-written replacement scripts are all forbidden.
5. **Failure rule (command铁律)**: if a CLI command returns non-zero or prints `❌`, retry **at most once** after cleaning WAL/SHM/journal lock files; if it still fails, stop and report. Never bypass the CLI.

## Step 1 — Analysis mode selection

| Mode | Trigger | Tool combination |
|------|---------|------------------|
| A 快速总览 | "花了多少 / 钱去哪了" | `analyze billing` + `analyze expense` |
| B 时序趋势 | "哪个月花最多 / 怎么超了" | `analyze monthly` + `analyze expense` |
| C 预算预测 | "下月预算 / 如何省钱" | `analyze monthly` + `analyze billing` + `analyze expense` |

Never conclude from a single tool. Empty first response (zero totals / no records) → stop immediately and tell the user to record or import data first.

## Step 2 — Tool calls

Run the chosen combination; add `--start`/`--end` for date ranges. The JSON returned is the **only legitimate data source** — fabricating numbers is forbidden.

## Step 3 — Data-integrity checks (mandatory only for mode C)

| Check | Rule | Flag |
|-------|------|------|
| Fixed-item check | A core item in `rigid_fixed_monthly` drops > 40% month-over-month | ⚠️ suspected data gap / billing-period shift |
| Structural-shift check | Food share spikes to 45%+ while rigid-fixed collapses | ⚠️ total-expense base distorted |
| Income-match check | Latest month income < 70% of historical monthly average | ⚠️ income cliff warning |

## Step 4 — Math (Python, not eval)

All arithmetic is done in Python (per `SKILL.md`). **Conflict note**: `references/budget_prediction.md` contains a JavaScript `eval`-based calculation block; that instruction contradicts SKILL.md's "所有数学运算…直接使用 Python 完成" — the SKILL.md (Python) mandate is authoritative; the JS block is a legacy artifact. Budget formulas:

| Bucket | Formula |
|--------|---------|
| 刚性固定 | Median of the last 3 months (anomaly-excluding) |
| 刚性必要 | Last 3 months weighted 0.5 / 0.3 / 0.2 |
| 弹性支出 | Mean of the last 3 months; ideal compression target = 85% |
| Trend | Recent 3 months vs prior 3 months |

## Step 5 — Dual-track output

- With detected gaps/anomalies: output **two budgets** — algorithm baseline + manually corrected (restoring missing fixed items).
- Without anomalies: one budget, but must cite merchant-level data from `analyze expense`.
- Output follows `assets/report_template.md` (algorithm table with 中位数还原/3月加权/3月均值 methods and trend arrows, plus a "人工修正" version and advice bound to specific merchants).

## The seven analysis rules (apply in every mode)

| # | Rule | Trigger | Action |
|---|------|---------|--------|
| 1 | Outlier stripping | single expense > 30% of total spending | separate it, state its share, compute daily-spend excluding it; structural analysis uses the adjusted base |
| 2 | Takeout/dine-in health | takeout > 50% of dine-in | ⚠️ "外卖依赖偏高"; takeout > dine-in → "外卖主导型餐饮" |
| 3 | High-frequency flag | same merchant ≥ 4 times in a cycle | 🔁 "高黏度习惯消费"; monthly estimate = avg per transaction × estimated frequency |
| 4 | Small-amount stacking | ¥0-20 frequency bucket > 60% | compute hidden monthly total (daily small spend × 30) and warn |
| 5 | Expense-structure diagnosis | flexible-share thresholds | <15% healthy; 15-25% normal; 25-35% ⚠️ compressible; >35% 🔴 needs immediate limits |
| 6 | Deficit warning | spending > income in a period | report deficit, source (one-off vs persistent), compressible flexible amount; ≥ 2 consecutive months → ⚠️ "收支失衡" |
| 7 | Dining structure health | single meal > ¥50 | mark "高客单餐饮"; drinks + milk-tea-coffee > 20% of food total → "饮料类占比偏高" |

## Step 6 — Actionable advice

Recommendations must bind to **specific merchants** from `analyze expense` (`item_breakdown` / `high_frequency_items`), e.g. "橙子便利近 4 个月花了 444 元，若减少一半频次，月均可省 55 元". If income-side warning exists, state the exact flexible-spending cap to hit.

## Streaming/web-view rules

- The agent must **never** run `streamlit run` on its own initiative; only when the user explicitly asks to start the web view. On exit code 0, reply "Web 视图已启动 ✅" and do not tail logs.
- The ledger SPA is a user-facing tool (see [ledger-app/overview.md](/openwiki/ledger-app/overview.md)); the agent is not required to interact with it.

## References map

| File | Load when |
|------|-----------|
| `scripts/billing/common.py` | Step 0 — only source of category constraints |
| `references/analysis_workflows.md` | Step 1 — mode details |
| `openwiki/billing-cli/analysis-modes.md` | Step 1 — authoritative JSON contract for each `analyze` command (the former `references/tools_reference.md` was removed) |
| `references/data_conventions.md` | Step 3 — integrity checks, real-income definition, three-tier definitions |
| `references/budget_prediction.md` | Step 4 — budget formulas (ignore the JS eval block) |
| `assets/report_template.md` | Step 5 — report layout |

## Data conventions (from SKILL.md + references)

- `records_view.金额` is negative for expenses, positive for income; tool outputs report expenses as positive absolutes.
- 真实收入 = 总收入 − 转账收款; prefer the real-income basis for net analysis.
- Three-tier definitions: 刚性固定 (fixed amount: rent, phone installment, insurance) → watch for anomalies/new items; 刚性必要 (necessary but variable: transport, medical, phone, utilities) → watch efficiency; 弹性支出 (optional: food, drink, shopping, entertainment) → the main saving lever.
