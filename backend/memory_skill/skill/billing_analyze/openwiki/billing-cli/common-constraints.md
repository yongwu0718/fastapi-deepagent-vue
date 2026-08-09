---
type: concept
title: common.py — Canonical Constraints and Validation
description: The single source of truth for category, subcategory, expense-type, direction, and platform option lists, plus the validators and date-filter helpers every writer and analyzer uses.
tags: [billing-analyze, cli, constraints]
---

# common.py — Canonical Constraints and Validation

`scripts/billing/common.py` is the **canonical source** for all constrained values and shared helpers. Every writer (`save_bill.py`, `save_income.py`, `import_csv.py`), the Streamlit editor (`billing_view.py`), and the ledger SPA's `config.js` mirror these lists. The mirror is not exact — see the divergence table below.

It also defines the database path:

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "billing.db"))  # scripts/data/billing.db
```

## Option lists (verbatim)

**消费大类 `CATEGORY_OPTIONS`** (9, mutually exclusive by purpose/scene):

| Value | Intent |
|-------|--------|
| 餐饮 | 正餐、外卖、堂食、食材、零食、饮品 |
| 交通 | 公交地铁、打车、加油、停车、大巴、车辆维护 |
| 住房 | 房租、房贷、水电、燃气、物业、维修 |
| 购物 | 日用消耗、服饰鞋包、数码电子、护肤美妆 |
| 居家 | 家具、家电、装修、家纺、厨具 |
| 娱乐 | 电影、游戏、旅游、健身、聚会 |
| 医疗 | 药品、检查、挂号、牙科 |
| 通讯 | 话费、宽带、AI服务 |
| 其他 | 人情红包、教育培训、杂项等兜底 |

**消费类型 `EXPENSE_TYPE_OPTIONS`**: 刚性固定 / 刚性必要 / 弹性支出 / 未分类

**收支类型 `DIRECTION_OPTIONS`**: 支出 / 收入

**支付平台 `PLATFORM_OPTIONS`**: 微信 / 支付宝 / 银行卡 / 现金 / 其他

**消费细类 `SUBCATEGORY_OPTIONS`** (keyed by category):

| 大类 | 细类 |
|------|------|
| 餐饮 | 外卖, 堂食, 食材, 零食, 饮料, 奶茶咖啡 |
| 交通 | 公交地铁, 打车, 大巴, 车辆维护, 电池 |
| 住房 | 房租, 水电, 燃气, 物业, 维修 |
| 购物 | 日用消耗, 服饰鞋包, 数码电子, 护肤美妆 |
| 居家 | 家具, 家电, 装修, 家纺, 厨具 |
| 娱乐 | 电影, 游戏充值, 健身, 旅游, 聚会 |
| 医疗 | 药品, 检查, 挂号, 牙科, 保险 |
| 通讯 | 话费, 宽带, AI服务, 会员续费 |
| 其他 | 人情红包, 教育培训, 杂项 |

**收入来源 `INCOME_CATEGORY_OPTIONS`**: 工资 / 兼职 / 理财收益 / 转账收款 / 红包 / 报销 / 退款 / 其他

**收入细类 `INCOME_SUBCATEGORY_OPTIONS`**:

| 来源 | 细类 |
|------|------|
| 工资 | 月薪, 年终奖, 绩效奖金 |
| 兼职 | 副业, 零工 |
| 理财收益 | 余额宝, 基金, 股票, 银行利息 |
| 转账收款 | 他人转账 |
| 红包 | 微信红包 |
| 报销 | 差旅报销, 加班报销 |
| 退款 | 购物退款, 押金退还 |
| 其他 | (none) |

## Validators

| Function | Semantics |
|----------|-----------|
| `validate_category(c)` | `c in CATEGORY_OPTIONS` |
| `validate_platform(p)` | empty string is valid; otherwise `p in PLATFORM_OPTIONS` |
| `validate_expense_type(t)` | `t in EXPENSE_TYPE_OPTIONS` |
| `validate_income_category(c)` | `c in INCOME_CATEGORY_OPTIONS` |
| `validate_subcategory(cat, sub)` | **Strict**: if `cat` is not a known category, returns `False` (no partial match); otherwise `sub in SUBCATEGORY_OPTIONS[cat]`. Callers should validate the category first |
| `get_subcategory_options(cat)` | returns `SUBCATEGORY_OPTIONS.get(cat, [])` |

## Shared helpers

**`build_date_filter(base_where, start_date, end_date, date_column="日期") -> (where_clause, params)`**
Composes an AND-joined WHERE clause with optional inclusive date bounds, e.g. `("金额 < 0 AND 日期 >= ? AND 日期 <= ?", ('2026-01-01', '2026-06-30'))`. Used by all analysis modules against `records_view`.

**`get_expense_type(r) -> str`**
Resolves the expense-type from a row, trying keys in order `分类` (records_view name), `expense_type`, `expenseType`; returns `未分类` when absent. This compatibility shim lets one code path handle `sqlite3.Row` rows from `records_view` and legacy English field names.

## Cross-surface divergence (common.py vs ledger config.js)

`scripts/ledger/js/config.js` mirrors these lists for the SPA dropdowns. The current divergence (JS has extras the Python validators reject; Python has extras JS never offers):

| 大类 | Python `common.py` only | JS `config.js` only |
|------|------------------------|---------------------|
| 餐饮 | — | 酒水 |
| 交通 | 电池 | 加油, 停车 |
| 医疗 | 保险 | — |
| 通讯 | 会员续费 | — |

Everything else matches. This matters because the ledger SPA accepts values (e.g. 酒水) that `save_bill`/`import_csv` would reject. See [ledger-app/frontend.md](/openwiki/ledger-app/frontend.md).

## Related pages

- [billing-cli/records-import.md](/openwiki/billing-cli/records-import.md) — how `save_bill`/`save_income` apply these validators in order
- [architecture/data-model.md](/openwiki/architecture/data-model.md) — which columns these constraints govern
- [ledger-app/frontend.md](/openwiki/ledger-app/frontend.md) — the JS mirror
