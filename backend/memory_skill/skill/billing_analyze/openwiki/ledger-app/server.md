---
type: concept
title: ledger_server.py — REST Bridge and Reconciliation
description: The stdlib HTTP server that serves the ledger SPA and exposes state, records, settings, and monthly-analysis endpoints over one SQLite database.
tags: [billing-analyze, ledger, api]
---

# ledger_server.py — REST Bridge and Reconciliation

`scripts/ledger_server.py` is a `ThreadingHTTPServer` bound to `127.0.0.1:8230` (configurable with `--port`). It provides static file serving (with path-traversal protection) and a small JSON REST API. It imports the CLI analysis modules directly — analysis logic is **not** re-implemented:

```python
from billing.analyze_monthly import analyze_monthly
from billing.analyze_category_monthly import analyze_category_monthly
```

## Endpoint reference

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/api/state` | — | `{"ok": true, "records": [...], "savings": [...], "debts": {...}}` |
| GET | `/api/analyze-monthly?year=&month=` | year (4-digit), month 1–12 | `{"ok": true, "result": <analyze_monthly JSON>}` |
| GET | `/api/analyze-category-monthly?year=&month=` | same | `{"ok": true, "result": <analyze_category_monthly JSON>}` |
| POST | `/api/records` | `{"records": [<record>, ...]}` | `{"ok": true, "records": [...merged with _dbId...]}` |
| POST | `/api/settings` | `{"savings": [...], "debts": {...}}` | `{"ok": true}` |
| GET | static | path under `scripts/` | file bytes with MIME type |

Errors always use the shape `{"ok": false, "error": "<message>"}` with status 400 (bad input), 403 (forbidden path), 404 (unknown), or 500 (analysis/DB failure). `OPTIONS` returns 204 with CORS headers; all responses carry `Access-Control-Allow-Origin: *`.

The analyze endpoints compute the month bounds (`start = YYYY-MM-01`, `end = last day of month`) and call the CLI module functions; invalid `year`/`month` returns a 400.

## Record field contract (bridge ↔ SPA ↔ DB)

The bridge converts between DB rows and the SPA record shape. SPA record:

```
{ _dbId, _src, id, date, itemName, category, subcategory, direction,
  expenseType, platform, amount, note }
```

- `_src`: `"bill"` (billing_records) or `"income"` (income_records) — backfilled by the server.
- `_dbId`: the DB primary key — also backfilled by the server. **The SPA must never fabricate `_dbId`/`_src` on new records** (that would make the server treat them as existing rows).
- `direction`: `支出` / `收入`; `expenseType` only meaningful for expenses (income table has no such column).
- `amount`: absolute value.

## Full-reconciliation write (`POST /api/records` → `save_records`)

Each sync sends the **entire** record set; the server reconciles rather than diffing:

| SPA record state | Server action |
|------------------|---------------|
| Has `_dbId` and the row exists in its target table | UPDATE that row |
| Has `_dbId` but the row is gone (previously deleted) | INSERT as a new record, backfill `_dbId`/`id`/`_src` |
| No `_dbId` (new record) | INSERT into the target table, backfill `_dbId` |
| DB row not present anywhere in the sent array | DELETE (the SPA removed it) |

**Table routing**: `direction === "收入"` **and** `_src !== "bill"` → `income_records`; everything else → `billing_records`. The server tracks `seen_bill` / `seen_income` id sets and deletes only rows in `(bill_ids ∪ income_ids) − seen`. A deleted-then-reinserted row inside one payload therefore gets a fresh `_dbId`.

## Settings persistence (`GET/POST /api/settings`, `load_settings` / `save_settings`)

- `ledger_settings.json` (path `scripts/data/ledger_settings.json`) stores `savings` and `debts`.
- `load_settings()` returns `{"savings": [...], "debts": {balances: [...], debts: [...]}}`; missing keys fall back to defaults (`savings: []`, `debts: {balances: [], debts: []}`), and `_deep_merge_debts` guarantees `balances`/`debts` are lists. Corrupt JSON is treated as empty.
- `save_settings(savings, debts)` writes both keys with `ensure_ascii=False, indent=2`.
- `fund`/`budget` keys were **fully removed** — `load_settings()` and `save_settings()` no longer accept or return them, and the JSON file no longer contains them (see [architecture/data-model.md](/openwiki/architecture/data-model.md)).

## Security posture (local-only app)

- Bound to `127.0.0.1` only.
- Static file handler normalizes paths and rejects anything escaping `scripts/` (403) — prevents path traversal.
- CORS `*` is intentionally permissive because the page and API are same-origin anyway (retained so the page also works if opened from another origin).
- Writes are not authenticated; the app is single-user local by design ("单用户，本地").

## Duplicated DDL — keep in sync

`get_db()` executes the same `CREATE TABLE`/`CREATE VIEW` statements as `init_db.py` on every call (idempotent). A schema change must be applied to **both** files; see [architecture/data-model.md](/openwiki/architecture/data-model.md) and [architecture/overview.md](/openwiki/architecture/overview.md).

## Frontend pairing

The SPA calls exactly these endpoints from `storage.js`: `GET /api/state` (`initFromServer`), `POST /api/records` and `POST /api/settings` (`_flushSync`), `GET /api/analyze-monthly` and `GET /api/analyze-category-monthly` (`loadMonthAnalysis` / `loadCategoryAnalysis`). See [ledger-app/frontend.md](/openwiki/ledger-app/frontend.md).
