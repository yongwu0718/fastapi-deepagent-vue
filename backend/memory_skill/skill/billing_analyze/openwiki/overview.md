---
type: concept
title: billing_analyze — Project Overview
description: Personal bill-analysis agent skill with a zero-dependency Python CLI, a Streamlit database editor, and a local ledger SPA bridged over HTTP to one SQLite store.
tags: [billing-analyze, overview]
---

# billing_analyze — Project Overview

`billing_analyze` is an **agent skill** (not a standalone service) that analyzes personal bill data and produces financial reports: income/expense overview, category rankings, per-platform spending shares, food-consumption habit tracking, and next-month budget predictions driven by historical trends. It lives at `backend/memory_skill/skill/billing_analyze` inside a larger `fastapi-deepagent-vue` monorepo and is activated when a user asks how much they spent, where the money went, whether spending is healthy, or how much to budget next month.

The skill contract for the calling agent is defined in the repository root `SKILL.md` (see [agent-workflows.md](/openwiki/agent-workflows.md)). The agent must do all data entry and analysis through the CLI below; it is explicitly forbidden from writing SQL directly or substituting its own scripts.

## Four runtime surfaces over one database

The skill exposes four surfaces that all read and write the same SQLite database `scripts/data/billing.db` (122 records at wiki time: 107 in `billing_records`, 15 in `income_records`):

| # | Surface | Entrypoint | Purpose | Dependencies |
|---|---------|-----------|---------|--------------|
| 1 | **billing CLI** | `scripts/billing/cli.py` | The agent's sanctioned data-entry and analysis interface: `analyze billing\|expense\|monthly\|category`, `save-bill`, `save-income`, `list-categories` | Pure Python, zero external dependencies |
| 2 | **Ledger Web app** | `scripts/ledger_server.py` + `scripts/ledger.html` + `scripts/ledger/js/*` | Local-only personal ledger SPA (home / 记账 / 资产负债 pages) served over HTTP on port 8230, with a REST bridge that reconciles writes into the same DB | Python stdlib + `sqlite-utils` |
| 3 | **Streamlit editor** | `scripts/billing/billing_view.py` | Interactive visual editor for `billing_records` / `income_records` (add/edit/delete, filters, pagination, CSV/JSON/Excel export) | `streamlit`, `pandas`, `sqlite-utils`, `openpyxl` (see `requirements.txt`) |
| 4 | **Import/cleaning pipeline** | `clean_wechat_bill.py`, `clean_alipay_bill.py`, `import_csv.py`, `init_db.py` | Convert raw WeChat/Alipay bill exports into the standard record format and bulk-import them | `pandas`, `openpyxl` |

See [architecture/overview.md](/openwiki/architecture/overview.md) for the data flow between surfaces and [architecture/data-model.md](/openwiki/architecture/data-model.md) for the schema.

## Directory structure

```
billing_analyze/
├── SKILL.md                    # Agent behavior contract (analysis modes, 7 rules, command铁律)
├── AGENTS.md / CLAUDE.md       # OpenWiki-generated agent markers (not functional)
├── requirements.txt            # Python deps for the Streamlit editor
├── assets/
│   └── report_template.md      # Budget-prediction report output template
├── references/                 # Agent-facing references (partly stale — see note below)
│   ├── analysis_workflows.md   # Analysis modes A/B/C trigger words and tool combos
│   ├── data_conventions.md     # Amount sign conventions + data-integrity checks
│   └── budget_prediction.md    # Budget formulas (its JS-eval instructions are superseded)
├── scripts/
│   ├── billing/                # CLI + analysis + save + cleaning + Streamlit editor
│   │   ├── cli.py              # CLI entrypoint (all commands)
│   │   ├── common.py           # Path constants, category constraints, validators
│   │   ├── init_db.py          # DDL: billing_records, income_records, records_view
│   │   ├── save_bill.py        # Insert one bill record (validated)
│   │   ├── save_income.py      # Insert one income record (validated)
│   │   ├── analyze_billing.py  # Comprehensive overview analysis
│   │   ├── analyze_expense.py  # Expense deep-dive analysis
│   │   ├── analyze_monthly.py  # Three-tier monthly analysis
│   │   ├── analyze_category_monthly.py  # Monthly category/subcategory breakdown
│   │   ├── clean_wechat_bill.py  # WeChat bill → standard format
│   │   ├── clean_alipay_bill.py  # Alipay bill → standard format
│   │   ├── import_csv.py       # Cleaned CSV → billing_records / income_records
│   │   └── billing_view.py     # Streamlit database editor
│   ├── data/
│   │   ├── billing.db          # SQLite store (single source of truth)
│   │   └── ledger_settings.json  # Ledger savings/debts settings (no fund/budget)
│   ├── ledger_server.py        # HTTP bridge: static files + JSON REST API (port 8230)
│   ├── ledger.html             # Ledger SPA shell (3 pages, script load order)
│   └── ledger/
│       ├── GUIDE.md            # Ledger dev guide (partially stale — see ledger-app/overview.md)
│       ├── css/                # base.css, page.css
│       └── js/                 # storage, config, ui, record, render-home, render-ledger,
│                               #   render-calendar, render-assets, main
├── conversation_history/       # Large session transcripts (out of scope — see operations.md)
└── skills/                     # OpenWiki helper skills (out of scope)
```

## Source-grounding notes

- **No tests exist** in this repository. Validation is performed by running CLI commands against the SQLite database; concrete commands are in [operations.md](/openwiki/operations.md).
- **`references/tools_reference.md` was removed**: it had documented analysis sections and an asset-management toolset (`add_account`, `list_accounts`, …) that never existed in the code. The authoritative JSON structures are in [billing-cli/analysis-modes.md](/openwiki/billing-cli/analysis-modes.md), and SKILL.md now points there directly.
- **`scripts/ledger/GUIDE.md` is partially stale**: it still describes the removed free-fund ring and savings chart, and omits the current 资产负债 (assets) page and `render-calendar.js` / `render-assets.js`. The fund/budget feature was fully removed (backend + frontend + JSON keys). The current behavior is documented in [ledger-app/overview.md](/openwiki/ledger-app/overview.md).

## Repository history (context)

- `fb39092` — refactored `billing_analyze` into the standard skill format (SKILL.md + scripts + references).
- `1911063` — OpenWiki maintenance commit that added `analyze_category_monthly.py`, the cleaning scripts, `init_db.py`, `import_csv.py`, and the ledger app.
- The skill is operated as a single-user, local deployment ("单用户，本地").
