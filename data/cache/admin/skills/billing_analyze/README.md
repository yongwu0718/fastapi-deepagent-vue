# billing_analyze - 个人账单分析智能体

基于 Python CLI 的个人账单数据分析工具，支持收支总览、消费分类排名、各平台支出占比、食品消费习惯追踪以及基于历史趋势的下月预算预测。

## 功能特性

| 功能 | 说明 |
|------|------|
| **综合分析** (`analyze billing`) | 收支总览、收入分类、平台使用分布 |
| **支出专项** (`analyze expense`) | 细类排名（含消费类型）、项目明细、消费频次、高频消费 |
| **逐月分析** (`analyze monthly`) | 三层逐月：总额 + 负担率 + 环比 + 异常标记 + 细类拆解 |
| **数据录入** (`save-bill` / `save-income`) | 逐条记账，支持分类约束校验 |
| **可视化界面** (`billing_view.py`) | Streamlit Web UI，支持浏览、编辑、新增、删除、筛选、导出 |
| **预算预测** | 基于历史趋势的下月预算预测（刚性固定/刚性必要/弹性支出分别计算） |

## 目录结构

```
billing_analyze/
├── SKILL.MD                          # 技能定义文件（分析流程、规则、提示词）
├── README.md                         # 本文件
├── requirements.txt                  # Python 依赖（仅 Streamlit 可视化 UI 需要）
├── assets/
│   └── report_template.md            # 预算预测报告模板
├── references/
│   ├── analysis_workflows.md         # 三种分析模式详细说明
│   ├── budget_prediction.md          # 预算预测计算公式
│   ├── data_conventions.md           # 数据完整性校验规则
│   └── tools_reference.md            # 工具返回结构说明
└── scripts/
    ├── __init__.py
    └── billing/
        ├── __init__.py
        ├── cli.py                    # CLI 入口，统一命令行接口
        ├── common.py                 # 公共模块：路径、分类约束、校验函数
        ├── analyze_billing.py        # 综合分析（收支总览 + 平台分布）
        ├── analyze_expense.py        # 支出专项分析（细类排名 + 高频消费）
        ├── analyze_monthly.py        # 三层逐月分析
        ├── save_bill.py              # 账单记录保存
        ├── save_income.py            # 收入记录保存
        └── billing_view.py           # Streamlit 可视化编辑器
```

## 安装

### 基本使用（CLI 分析）

CLI 分析工具纯 Python 实现，零外部依赖，仅需 Python 3.11+。

### 可视化编辑器（可选）

```bash
pip install -r requirements.txt
```

依赖项：`streamlit`、`pandas`、`sqlite-utils`、`openpyxl`

## 快速开始

所有操作通过 `cli.py` 进行：

```bash
cd scripts/billing

# 查看可用分类
python cli.py list-categories

# 记一笔支出
python cli.py save-bill \
  --item-name "胜香斋" \
  --category "餐饮" \
  --amount 25 \
  --date 2026-07-24 \
  --platform "微信" \
  --subcategory "午餐" \
  --expense-type "刚性必要"

# 记一笔收入
python cli.py save-income \
  --item-name "工资" \
  --category "工资" \
  --amount 15000 \
  --date 2026-07-01 \
  --platform "银行卡" \
  --subcategory "月薪"

# 分析：综合总览
python cli.py analyze billing

# 分析：支出专项
python cli.py analyze expense

# 分析：逐月趋势
python cli.py analyze monthly

# 按日期范围筛选
python cli.py analyze expense --start 2026-01-01 --end 2026-06-30

# 启动可视化编辑器（需先安装依赖）
streamlit run billing_view.py
```

## 分析模式

| 模式 | 触发词 | 工具组合 |
|------|--------|----------|
| **A 快速总览** | "花了多少""钱去哪了" | `analyze billing` + `analyze expense` |
| **B 时序趋势** | "哪个月花最多""怎么超了" | `analyze monthly` + `analyze expense` |
| **C 预算预测** | "下月预算""如何省钱" | `analyze monthly` + `analyze billing` + `analyze expense` |

## 分类体系

### 消费大类

| 大类 | 细类选项 |
|------|----------|
| 餐饮 | 外卖、堂食、食材、零食、饮料、奶茶咖啡、酒水 |
| 交通 | 公交地铁、打车、加油、停车、大巴、车辆维护 |
| 住房 | 房租、房贷、水电、燃气、物业、维修 |
| 购物 | 日用消耗、服饰鞋包、数码电子、护肤美妆 |
| 居家 | 家具、家电、装修、家纺、厨具 |
| 娱乐 | 电影、游戏充值、健身、旅游、聚会 |
| 医疗 | 药品、检查、挂号、牙科 |
| 通讯 | 话费、宽带、AI服务 |
| 其他 | 人情红包、教育培训、杂项 |

### 消费类型

- **刚性固定**：房租、房贷等每月固定不变
- **刚性必要**：通勤等必须但金额可变
- **弹性支出**：吃饭、娱乐、购物等可选消费
- **未分类**：缺失/未识别

### 支付平台

微信、支付宝、银行卡、现金、其他

### 收入来源

工资、兼职、理财收益、转账收款、红包、报销、退款、其他

## 数据库

数据存储在 `scripts/data/billing.db`（SQLite），包含以下表/视图：

| 表/视图 | 说明 |
|---------|------|
| `billing_records` | 账单流水平面表 |
| `income_records` | 收入记录表 |
| `records_view` | 统一查询视图（合并收支，金额：正=收入，负=支出） |

## 核心分析规则

分析过程中强制执行以下规则以保证输出深度和侧重点稳定：

1. **异常值剥离**：单笔消费 > 总支出 30% → 剥离为偶发大额异常
2. **外卖/堂食比健康阈值**：外卖 > 堂食 50% 标记"外卖依赖偏高"
3. **高频消费异常标记**：同一商户 >= 4 次/周期 → "高黏度习惯消费"
4. **小额高频叠加效应**：¥0-20 区间占比 > 60% 计算隐形大额
5. **消费类型结构诊断**：弹性支出 > 25% 警告，> 35% 红色预警
6. **赤字预警**：支出 > 收入时标注赤字金额及来源
7. **餐饮结构健康度**：单顿饭 > ¥50 标记"高客单餐饮"
