---
type: concept
title: billing CLI — Commands and Entrypoint
description: Zero-dependency Python CLI that is the agent's only sanctioned interface for bill entry and analysis, with command, argument, output, and error-contract reference.
tags: [billing-analyze, cli]
---

# billing CLI — Commands and Entrypoint

`scripts/billing/cli.py` is the agent's **only sanctioned** data-entry and analysis interface (pure Python, no external dependencies). It is invoked from the `scripts/billing/` directory:

```bash
cd scripts/billing
python cli.py analyze billing
python cli.py analyze expense --start 2026-01-01 --end 2026-06-30
python cli.py save-bill --item-name "胜香斋" --category "餐饮" --amount 25 --date 2026-07-24 --platform "微信" --subcategory "午餐" --expense-type "刚性必要"
python cli.py list-categories
```

All analysis commands print pretty-printed JSON to stdout (`json.dumps(..., ensure_ascii=False, indent=2)`).

## Command reference

| Command | Purpose | Arguments |
|---------|---------|-----------|
| `analyze billing` | Comprehensive overview: income/expense totals, real income, category breakdown, platform distribution | `--start`, `--end` (YYYY-MM-DD, inclusive) |
| `analyze expense` | Expense deep-dive: subcategory ranking, item breakdown, consumption frequency, high-frequency items | `--start`, `--end` |
| `analyze monthly` | Three-tier monthly series: monthly income/expense, rigid-fixed monitoring, rigid-necessary efficiency, flexible behavior | `--start`, `--end` |
| `analyze category` | Monthly category/subcategory summary: per-month breakdown, cross-category subcategory ranking, category trend | `--start`, `--end` |
| `save-bill` | Save one bill record into `billing_records` | `--item-name` (req), `--category` (req), `--amount` (req, float), `--date` (req), `--platform`, `--subcategory`, `--expense-type`, `--direction`, `--note` |
| `save-income` | Save one income record into `income_records` | `--item-name` (req), `--category` (req), `--amount` (req, float), `--date` (req), `--platform`, `--subcategory`, `--note` |
| `list-categories` | Print the full constraint dictionaries (categories, subcategories, expense types, directions, platforms, income sources) as JSON | — |

The date filter is inclusive on both ends; omitting `--start`/`--end` analyzes the full dataset. `年月` is derived from `日期` by the view — it is never an input.

## Dispatch architecture

`cli.py` wires argparse subparsers to functions in the sibling modules:

- `analyze billing` → `analyze_billing._run_analysis(DB_PATH, start, end)`
- `analyze expense` → `analyze_expense._run_analysis(...)`
- `analyze monthly` → `analyze_monthly._run_analysis(...)`
- `analyze category` → `analyze_category_monthly._run_analysis(...)`
- `save-bill` → `save_bill.save_bill(...)` (default `direction="支出"`)
- `save-income` → `save_income.save_income(...)`
- `list-categories` → `save_bill.list_categories()`

`DB_PATH` comes from `common.py` and resolves to `scripts/data/billing.db` (relative to `scripts/billing/` it is `../data/billing.db`). The module inserts its own directory into `sys.path` so it can be run as a plain script.

## Error contract (important for automation)

- **Uncaught exceptions** (e.g. missing DB file, bad SQL): traceback to stderr and `sys.exit(1)`.
- **Validation failures** in `save-bill` / `save-income` are **not** exceptions: the function returns a `❌`-prefixed message (e.g. `❌ 消费大类 'xx' 无效，允许: [...]`) which `cli.py` prints, and the process **exits 0**. The agent contract in `SKILL.md` therefore treats either a non-zero exit code **or** `❌` in the output as failure — see [agent-workflows.md](/openwiki/agent-workflows.md).
- **`analyze expense` and `analyze category` with zero records** return a JSON object containing `"error": "无支出记录"` (and `record_count: 0`) rather than raising.
- On `save-bill` success the printed string is `已保存: id=<lastrowid> | ...`; the row id comes from `cursor.lastrowid`.

## JSON output structure

The per-command JSON contracts are documented in [billing-cli/analysis-modes.md](/openwiki/billing-cli/analysis-modes.md). Save-command success/error message formats are in [billing-cli/records-import.md](/openwiki/billing-cli/records-import.md).

## Validation commands

```bash
python cli.py list-categories                          # canonical constraint values
python cli.py analyze billing                          # full dataset overview
python cli.py analyze expense --start 2026-07-01 --end 2026-07-31
```

See [operations.md](/openwiki/operations.md) for the recommended smoke-test sequence.
