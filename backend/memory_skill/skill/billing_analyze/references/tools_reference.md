# 工具返回结构参考

所有分析工具支持可选 `start_date` / `end_date`（格式 "YYYY-MM-DD"），不传则默认全量。

## `analyze_billing` — 收支总览 + 分类排名 + 平台分布

**返回结构：**
- `section_1_收支总览`：收入（总收入/真实收入_去转账/转账收入）、支出（刚性固定/刚性必要/弹性可选 + 占比）、净收支
- `section_2_支出分类排名`：各分类按金额排名，含刚性固定/刚性必要/弹性可选分项、笔数、占比
- `section_3_收入分类`：收入来源分布（工作收入/转账收款/奖金津贴/其他收入）
- `section_4_平台使用分布`：各平台支出/收入/转账收入、笔数、占比、top_3_categories

**适用场景**：想看整体概况、哪个类别/平台花钱最多、收支结构

---

## `analyze_expense` — 支出深度分析

**返回结构：**
- `header`：时间范围、月数、记录数、总支出、月均、日均
- `layer_structure`：按生活场景分层（🏠住房/🍚食品/🚌交通/🛒购物/📱数码/🎮娱乐/🏥医疗/📦其他），每层含子分类、笔数、占比、月均、备注
- `item_breakdown`：具体商户消费明细，含金额、笔数、高额笔数、三分类归属、占比
- `consumption_frequency`：按金额区间统计消费频次，含三分类分布
- `food_tracking`：食品消费专项追踪，含 monthly_detail 和 `top_items` 榜单

**适用场景**：深挖支出细节、食品消费习惯、高频商户分析

---

## `analyze_monthly` — 三层逐月时序分析

**返回结构：**
- `summary`：整体汇总（总支出/总收入/净收支/三分类合计）
- `monthly_income_expense`：逐月收支概览，含刚性负担率、弹性负担率、盈亏评价
- `rigid_fixed_monthly`：刚性固定逐月明细，含 `anomaly_flags`
- `rigid_necessary_monthly`：刚性必要逐月明细，含 `mom_change`、`efficiency_evaluation`
- `flexible_monthly`：弹性可选逐月明细，含 `category_breakdown`、`high_frequency_items`、`large_amount_items`

**适用场景**：时间序列趋势、月度异常监控、三类支出的动态追踪

---

## `analyze_monthly_categories` — 逐月类别排名

**返回结构：**
- `monthly_data`：按月分组，每月含 `expense_total`/`income_total`/`net`/`categories`
- 每个 category 含金额、刚性固定/刚性必要/弹性可选分项、笔数、占比
- 注意：类别列表中同时包含收入和支出项（收入类 percentage 为 "—"），分析支出时需过滤收入项

**适用场景**：对比各月类别变化、发现某类消费的月度波动

---

## `save_bill` — 保存账单记录

保存单条账单到 SQLite。参数：`item_name`, `category`, `amount`, `date`, `platform`, `year_month`, `expense_type`。
