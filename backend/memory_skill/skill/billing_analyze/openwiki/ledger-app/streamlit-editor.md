---
type: concept
title: Streamlit Editor — billing_view.py
description: Interactive SQLite editor for billing and income records built with Streamlit and sqlite-utils, with filters, pagination, statistics, in-place editing, ID renumbering, and CSV/JSON/Excel export.
tags: [billing-analyze, streamlit, editor]
---

# Streamlit Editor — billing_view.py

`scripts/billing/billing_view.py` is the **visual database editor** for `scripts/data/billing.db`, built with Streamlit + `sqlite-utils`. It is the sanctioned "visual review and fix" path for bill data (the agent contract explicitly forbids the agent from launching it on its own — the **user** starts it):

```bash
streamlit run billing_view.py   # run from scripts/billing/
```

Dependencies (`requirements.txt`): `streamlit`, `pandas`, `sqlite-utils`, `openpyxl`. The DB connection is opened with `check_same_thread=False` and cached via `@st.cache_resource`; schema/table listings are cached with a 5 s TTL.

## Features

| Feature | Behavior |
|---------|----------|
| Data source picker | Sidebar select of every table **and view** in the DB (e.g. `billing_records (table)`, `records_view (view)`); switching resets the editor key |
| Keyword filter | Sidebar column picker + `LIKE '%kw%'` filter on the chosen column |
| Date filter | Optional toggle filtering `日期 = YYYY-MM-DD` |
| Pagination | Page size 5–500 (default 50), page number input |
| Statistics | For each numeric column (id excluded): MIN / MAX / AVG / SUM metric cards, respecting the active filter |
| Sorting | Column + ASC/DESC selector above the data table |
| Data editor | `st.data_editor` with `num_rows="dynamic"`, per-table `SelectboxColumn` configs, `id`/`年月` disabled |
| Add form | "➕ 新增记录（级联选择）" expander: cascading category → subcategory, direction, expense type, platform, amount, date, note; validates name/category/amount before insert |
| Save | "💾 保存修改" writes added/edited/deleted rows back via `save_changes` |
| ID renumbering | "🔢 重排 ID" rewrites ids to contiguous 1..N and fixes `sqlite_sequence` |
| Export | Sidebar "📥 导出当前页" in CSV (utf-8-sig), JSON, or Excel (openpyxl) |
| View read-only | Selecting a view shows a warning and a plain dataframe instead of the editor |

## Column configuration per table

- `income_records`: category options = income sources; subcategories from `INCOME_SUBCATEGORY_OPTIONS`; direction locked to `["收入"]`.
- Any other table (e.g. `billing_records`): category options = `CATEGORY_OPTIONS`; direction `["支出", "收入"]`.
- `消费大类` and `类型` columns are `required=True` selectboxes; `消费细类`, `消费类型`, `支付平台` are optional selectboxes.

## save_changes — delete-by-id-diff algorithm

The editor tracks changes through the Streamlit session state (`edited_rows`, `added_rows`) rather than `deleted_rows`:

1. **Delete**: `orig_ids − edited_ids` (ids present in the loaded page but missing after editing) → `db[table].delete(rid)`. Note this compares only the **loaded page**, so deletions are per-page.
2. **Insert**: each `added_rows` entry is cleaned (dropping `rowid`/`id`) and inserted with `pk="id"`.
3. **Update**: each `edited_rows` entry maps back to its `df_orig` row id and calls `db[table].update(id, changes)`.
4. Errors are collected and shown with `st.warning`; a summary (新增/修改/删除 counts) is printed, and after any deletion the app offers ID renumbering (it does **not** renumber automatically).

## renumber_ids

```sql
UPDATE "<table>" SET id = (SELECT COUNT(*) FROM "<table>" AS t2 WHERE t2.id <= "<table>".id)
```

then resets `sqlite_sequence` to the row count so future AUTOINCREMENT ids continue from N. This is why `年月` is disabled in the editor: it does not exist as a physical column (it is derived in `records_view` — see [architecture/data-model.md](/openwiki/architecture/data-model.md)).

## Relationship to other surfaces

- It reads and writes the **same** `billing.db` as the CLI and the ledger server, without the CLI's validation (a human can select any option value or leave columns empty).
- The agent contract uses it as the alternate batch-review path ("备用审核路径") — the user opens it to visually proofread imported rows; see [agent-workflows.md](/openwiki/agent-workflows.md).
- View rows are read-only: the app refuses editing `records_view` because writes to the UNION view are not meaningful.

## Launch discipline

`streamlit run` is a long-running server. Per `SKILL.md`: the agent must never launch it unless the user explicitly asks to start the web view, and after the command returns exit code 0 the agent should report "Web 视图已启动 ✅" without tailing logs. Details in [operations.md](/openwiki/operations.md).
