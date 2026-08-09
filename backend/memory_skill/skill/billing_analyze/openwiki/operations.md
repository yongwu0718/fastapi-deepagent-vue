---
type: concept
title: Operations — Running, Validating, and Troubleshooting
description: How to run every surface, narrow validation commands for each change area, and troubleshooting for database locks and CORS.
tags: [billing-analyze, operations]
---

# Operations — Running, Validating, and Troubleshooting

There are **no automated tests** in this repository. Validation is done by executing the CLI/scripts against the SQLite database and inspecting output. This page collects the run commands, the narrowest validation for each change area, and the known failure modes.

## Running each surface

| Surface | Command (run from `scripts/billing/` unless noted) | Notes |
|---------|---------------------------------------------------|-------|
| CLI analysis | `python cli.py analyze billing` (or `expense` / `monthly` / `category`), with optional `--start YYYY-MM-DD --end YYYY-MM-DD` | Prints JSON, `ensure_ascii=False`, indent 2 |
| CLI save | `python cli.py save-bill --item-name "X" --category "餐饮" --amount 25 --date 2026-07-24 --platform "微信" --subcategory "午餐" --expense-type "刚性必要"` / `python cli.py save-income ...` | Run `list-categories` first |
| List constraints | `python cli.py list-categories` | Returns the only legal option values |
| DB init | `python init_db.py` (from `scripts/billing/`) | Creates tables + `records_view`; prints counts |
| CSV import | `python import_csv.py [path.csv]` (from `scripts/billing/`) | Default input `微信账单_清洗后.csv` at repo root |
| Bill cleaning | `python clean_wechat_bill.py [xlsx [out_xlsx [out_csv]]]` / `python clean_alipay_bill.py [csv [out_xlsx [out_csv]]]` | Needs pandas; outputs cleaned Excel/CSV |
| Ledger web | from `scripts/`: `python ledger_server.py [--port 8230]` → `http://127.0.0.1:8230/ledger.html` | Must be HTTP, never `file://` |
| Streamlit editor | from `scripts/billing/`: `streamlit run billing_view.py` | Only when the user explicitly asks for the web view |

## Narrow validation per change area

| You changed | Narrowest validation |
|-------------|----------------------|
| `common.py` options/validators | `python cli.py list-categories`; then `python cli.py save-bill` with an invalid value to confirm the `❌` rejection |
| `save_bill.py` / `save_income.py` | `python cli.py save-bill ...` then `python cli.py analyze billing` and check the record count/`total_records` and the new line in the JSON |
| An `analyze_*.py` module | Run that command with a bounded range: `python cli.py analyze expense --start 2026-07-18 --end 2026-08-07`; verify expected top-level keys (see [billing-cli/analysis-modes.md](/openwiki/billing-cli/analysis-modes.md)) |
| `init_db.py` / `ledger_server.py` DDL | Re-run `init_db.py`; check `sqlite_master` for tables/views and row counts |
| `ledger_server.py` API | Start the server; `curl http://127.0.0.1:8230/api/state`; POST a record via `/api/records` and confirm `_dbId` backfill |
| `ledger/js/*` frontend | Start the server, open the page, add/delete a record, refresh the page and confirm persistence |
| `billing_view.py` | Launch Streamlit, edit/add/delete a row, save, verify in `python cli.py analyze billing` |
| Cleaning scripts | Run against a sample export; inspect the cleaned CSV columns and category distribution printed at the end |
| DB schema check | `python -c "import sqlite3; c=sqlite3.connect('../data/billing.db'); print(c.execute(\"SELECT type,name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'\").fetchall())"` |

## Troubleshooting

**`database is locked` from `save-bill`/import** — the known cause is a stale lock file (journal/WAL/SHM) in `scripts/data/` (e.g. `billing.db-journal`). Per the skill contract: clean the WAL/SHM/journal lock files and retry **once**; do not retry repeatedly, kill processes, or write SQL directly. If it still fails, stop and report. Reference incident: `.workbuddy/memory/2026-08-09.md` (5 screenshot entries failed with `database is locked` until the journal file was removed; ids 95–99 saved).

**Ledger page blank / fetch errors** — you opened `ledger.html` via `file://`. Always go through `ledger_server.py` (`http://127.0.0.1:8230/ledger.html`); `fetch` is blocked by CORS on `file://`.

**Streamlit behavior** — `streamlit run` is long-running; once the command returns exit code 0, treat the web view as started and do not wait on or tail the live logs. The agent must not launch it unless the user asks.

**CLI validation failures** — `save-*` validation errors are returned as `❌ ...` strings **with exit code 0**; only uncaught exceptions exit 1 (with traceback). Check output text for `❌`, not just the exit code.

**`records_view` read-only** — the Streamlit editor refuses edits on views; switch to the physical table.

**Port 8230 busy** — pass `--port` to `ledger_server.py`; the SPA is same-origin so no frontend change is needed.

## Out-of-scope top-level items (documented here for completeness)

| Path | What it is | Why it is not a wiki topic |
|------|-----------|----------------------------|
| `conversation_history/` | Two large prior session transcripts (`session_4f111146.md` ~682 KB, `session_88f024f1.md` ~701 KB) | Historical agent-run narrative; not load-bearing source. Useful as incident context (e.g. journal-lock handling) |
| `skills/` | OpenWiki helper skills (`mermaid-diagrams`, `write-connector`) | OpenWiki infrastructure, not repository features |
| `.workbuddy/memory/` | Dated agent working-memory logs | Used here only as incident evidence (journal-lock entry) |
| `AGENTS.md` / `CLAUDE.md` | OpenWiki-generated agent markers | Generated files, not components |

## Related pages

- [billing-cli/overview.md](/openwiki/billing-cli/overview.md) — CLI command reference and error contract
- [agent-workflows.md](/openwiki/agent-workflows.md) — the failure/retry rules the agent follows
- [ledger-app/server.md](/openwiki/ledger-app/server.md) — server endpoints for manual curl validation
