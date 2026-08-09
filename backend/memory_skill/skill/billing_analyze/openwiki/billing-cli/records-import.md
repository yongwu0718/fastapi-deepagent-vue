---
type: concept
title: Records, Imports, and Database Initialization
description: How single records are validated and saved, how WeChat and Alipay exports are cleaned and imported, and how the database is initialized.
tags: [billing-analyze, cli, import]
---

# Records, Imports, and Database Initialization

This page covers the write side of the CLI: `save_bill.py`, `save_income.py`, `list_categories`, `init_db.py`, the two bill-cleaning scripts, and `import_csv.py`.

## save-bill (`save_bill.save_bill`)

Signature: `save_bill(item_name, category, amount, date, platform="", subcategory="", expense_type="", direction="支出", note="")`

Validation order (first failure aborts with a `❌` message):

1. `validate_category(category)` — must be one of `CATEGORY_OPTIONS`
2. `validate_expense_type(expense_type)` — only if provided
3. `validate_subcategory(category, subcategory)` — only if provided; strict (unknown category → fail)
4. `direction in DIRECTION_OPTIONS`

Then `abs(amount)` is stored and the row is inserted into `billing_records` with columns `消费名称, 消费大类, 消费细类, 类型, 金额, 支付平台, 日期, 消费类型, 备注` (`None` for empty optional values). Success string: `已保存: id=<lastrowid> | <name> | <category> [> <subcategory>] | <direction> ¥<amount> | <date> [| <platform>] [| <expense_type>]`. Errors return `❌ 消费大类 '...' 无效，允许: [...]`-style strings (process still exits 0 — see [billing-cli/overview.md](/openwiki/billing-cli/overview.md)).

## save-income (`save_income.save_income`)

Signature: `save_income(item_name, category, amount, date, platform="", subcategory="", note="")`

Validation order: `validate_income_category(category)` → `validate_platform(platform)` (empty allowed) → subcategory must be in `INCOME_SUBCATEGORY_OPTIONS[category]` when that category has a non-empty list. Insert into `income_records` with `类型` hardcoded to `收入`; **no `消费类型` column** exists on that table.

## list-categories (`save_bill.list_categories`)

Returns a dict of all canonical option lists (消费大类, 消费细类, 消费类型, 收支类型, 支付平台, 收入来源, 收入细类). The CLI prints it as JSON. The agent contract requires calling this **before any save** and only using returned values — see [agent-workflows.md](/openwiki/agent-workflows.md).

## init_db (`init_db.py`)

Standalone initializer (`python init_db.py`), not a CLI subcommand. Creates the two tables and the `records_view` view (the same DDL duplicated in `ledger_server.py` — see [architecture/data-model.md](/openwiki/architecture/data-model.md)), then prints:

```
✅ 数据库就绪: <abs path>
   表: ['billing_records', 'income_records']
   视图: ['records_view']
   记录数: {table: count}
```

Creates the `scripts/data/` directory if missing. Failures return a `❌ 初始化失败: ...` string.

## Cleaning pipeline (raw platform exports → standard CSV)

Both cleaners convert raw bill exports into the standard 9-column CSV/Excel format: `消费名称, 消费大类, 消费细类, 类型, 金额, 支付平台, 日期, 消费类型, 备注`.

### clean_wechat_bill.py

- Input: WeChat bill XLSX (default `微信支付账单流水文件(20260718-20260807)_20260807230559.xlsx` at repo root; first positional arg overrides).
- Outputs: `微信账单_清洗后.xlsx` and `微信账单_清洗后.csv` at repo root (args 2 and 3 override).
- Steps: scans the first 30 rows for the header row containing `交易时间` + `收/支`; drops `已全额退款` (fully-refunded) hedge rows; strips bracketed nicknames from `交易对方` (e.g. `白如滨 (大白)` → `白如滨`); platform forced to `微信`; `金额` made absolute, direction from `收/支`.
- **Category mapping** is keyword-based (`RULES` list, first match wins): 汽车站/客运/大巴/公交/地铁/打车 → 交通·大巴·刚性必要; 售水站/水站/饮水 → 餐饮·饮料·弹性支出; 超市/便利/京东/百货/商超 → 购物·日用消耗·弹性支出; 美团App/外卖 → 餐饮·外卖·弹性支出; 板面/面/老豆腐/餐饮/饭店/食堂/早餐/… → 餐饮·堂食·弹性支出; 转账 → 其他·人情红包·弹性支出; fallback 其他·杂项·弹性支出.
- Income rows: `转账` transaction type → 转账收款·他人转账; `退款` → 退款·购物退款; otherwise keyword mapping. Income rows get empty `消费类型`.

### clean_alipay_bill.py

- Input: Alipay CSV in **GBK** encoding (default `scripts/支付宝交易明细(20260718-20260807).csv`; first arg overrides), `skiprows=23` to drop the header preamble.
- Outputs: `支付宝账单_清洗后.xlsx` / `.csv` at repo root (args 2/3 override).
- Steps: drops `不计收支` rows (withdrawals/deposits excluded from income/expense); strips nicknames; platform forced to `支付宝`; direction from `收/支`.
- **Category mapping** (`map_alipay`) uses Alipay's own `交易分类` + goods text: 零食 → 餐饮·零食; 外卖 → 餐饮·外卖; 餐饮美食 → 餐饮·堂食; 日用百货 → 购物·日用消耗; 交通出行 → 交通·公交地铁·刚性必要; 爱车养车 → 交通·车辆维护·刚性必要; 文化休闲 → 购物/餐饮/通讯(AI服务: 网盘/会员)/娱乐·游戏充值 fallback; 生活服务 → 其他·杂项; 其他 → 通讯·AI服务 (阿里云/云) or 其他·杂项.
- Income rows are always mapped to 转账收款·他人转账 (no per-source classification).

## import_csv (`import_csv.py`)

- Default input: `微信账单_清洗后.csv` at repo root (arg overrides). Encoding `utf-8-sig`.
- Uses `sqlite3.connect(..., timeout=30)` + `PRAGMA busy_timeout=30000` to survive concurrent access.
- Routing: row `类型 == "收入"` → `income_records`; anything else → `billing_records` (with `消费类型`).
- On any `sqlite3.Error` / `ValueError` / `KeyError`, rolls back the whole batch and returns `❌ 导入失败（已回滚）: [...]`; success prints inserted counts per table.

## Data-entry review gates (agent contract)

`SKILL.md` mandates, before any save or bulk import: call `list-categories`, show the user a table of parsed fields, and wait for confirmation before executing `save-bill` or the import script. The Streamlit editor ([ledger-app/streamlit-editor.md](/openwiki/ledger-app/streamlit-editor.md)) is the sanctioned visual review path. Direct SQL writes are forbidden — see [agent-workflows.md](/openwiki/agent-workflows.md).

## Related pages

- [billing-cli/common-constraints.md](/openwiki/billing-cli/common-constraints.md) — validation source
- [architecture/data-model.md](/openwiki/architecture/data-model.md) — target tables and column constraints
- [operations.md](/openwiki/operations.md) — journal-lock troubleshooting for `database is locked` failures
