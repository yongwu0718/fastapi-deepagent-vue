# 打工人小账本 · 开发指导文档

> 本文档用于指导理解、维护与扩展 `ledger` 记账应用的代码结构与业务逻辑。

## 1. 项目概述

「打工人小账本」是一个**纯前端 SPA + 本地 SQLite 桥接**的个人记账应用。当前包含两个页面：

- **首页**：概览与提醒（今日待办、月度概览、最近记录、自由基金、存款曲线）。
- **记账页**：10 秒快速记账、全部记录列表、月度收支总结。

> 注：时薪、情景模拟功能已移除（页面、算法 `calc.js`、相关换算与渲染模块均不再保留）。

### 1.1 目录结构

```
scripts/
├── ledger.html                    # 页面骨架（SPA 布局 + 按依赖序引入 JS）
├── ledger_server.py               # 本地桥接服务器（静态服务 + REST API + SQLite 读写）
└── ledger/
    ├── css/
    │   ├── base.css               # 基础样式（变量、布局）
    │   └── page.css               # 页面样式
    └── js/
        ├── storage.js             # 数据层：内存缓存 + 后端桥接同步
        ├── config.js              # 静态配置：分类/图标
        ├── ui.js                  # UI基础：页面切换/Toast/Modal/导入导出/进度环
        ├── record.js              # 记账逻辑：收支/分类/保存/删除
        ├── render-home.js         # 首页渲染
        ├── render-ledger.js       # 记账页渲染
        └── main.js                # 主入口：初始化/事件绑定/全量渲染
```

### 1.2 启动方式

```bash
.venv\Scripts\activate;cd backend/memory_skill/skill/billing_analyze/scripts;python ledger_server.py
```

启动后浏览器访问：`http://127.0.0.1:8230/ledger.html`

> 必须通过 HTTP 访问，不能直接双击 `ledger.html` 用 `file://` 打开，否则 `fetch` 会被浏览器 CORS 策略拦截。

---

## 2. 前端架构（JS 模块依赖顺序）

JS 按**依赖顺序**引入，不可随意调整：

```
storage.js → config.js → ui.js → record.js
→ render-home.js → render-ledger.js → main.js
```

| 层次 | 模块 | 职责 |
|------|------|------|
| 数据层 | `storage.js` | 数据读写、后端同步 |
| 配置层 | `config.js` | 分类/图标定义 |
| 基础层 | `ui.js` | 通用 UI 组件 |
| 业务层 | `record.js` | 记账交互逻辑 |
| 渲染层 | `render-*.js` | 各页面视图渲染 |
| 入口层 | `main.js` | 初始化与事件绑定 |

---

## 3. 核心数据模型

所有数据以内存对象 `DB` 缓存，通过 `getXxx()` / `setXxx()` 便捷函数读写。

### 3.1 五大数据结构

| 数据 | 关键字段 | 默认值 |
|------|---------|--------|
| `fund` | 自由基金 | 目标6万、当前1.85万、安全月6个月 |
| `budget` | 预算 | 月收入1.2万、固定支出[住房3000/通讯180]、弹性预算3500 |
| `records` | 记账明细 | 8条演示数据 |
| `savings` | 存款曲线 | 近6个月 |
| `meta` | 元数据 | 首次打开标记 |

### 3.2 记录（records）字段约定

每条记录字段与后端 `save_bill` / `save_income` 及 `billing.db` 对齐：

```js
{
  id: "唯一ID",                 // 前端生成：Date.now().toString(36)+随机
  _dbId: 123,                   // 后端数据库自增主键（同步后回填）
  _src: "bill"|"income",        // 来源表标识
  date: "2026-08-08",           // 日期
  itemName: "消费名称",          // 空时回退为细类/大类
  category: "餐饮",             // 大类
  subcategory: "外卖",          // 细类
  direction: "支出"|"收入",
  expenseType: "弹性支出",       // 仅支出有，收入表无此列
  platform: "微信",             // 支付平台
  amount: 32,                   // 金额（绝对值）
  note: "备注",
  demo: false                   // 是否演示数据
}
```

---

## 4. 数据持久化：内存缓存 + 后端桥接

### 4.1 双向数据流

```
启动加载  : initFromServer() → GET /api/state → 填充 DB
写入同步  : save() → 写内存 DB → 防抖400ms → POST /api/records 或 /api/settings
立即落库  : flushSync()（保存/删除记录后调用）→ 立即同步
```

### 4.2 同步机制（storage.js）

- **防抖**：`_scheduleSync()` 用 `setTimeout 400ms` 合并连续写入，避免频繁请求。
- **脏标记**：`_dirtyRecords`（记录改动）、`_dirtySettings`（设置改动），二者独立同步。
- **并发保护**：`_syncing` 标志防止同步过程中重复触发。
- **失败重试**：同步失败后若有脏标记，自动重新调度。

### 4.3 后端对账规则（ledger_server.py `save_records`）

每次同步是**全量对账**，非增量：

| 前端记录状态 | 后端处理 |
|-------------|---------|
| 带 `_dbId` 且目标表有该行 | UPDATE 更新该行 |
| 带 `_dbId` 但目标表无该行（已被删） | 当作新记录 INSERT |
| 无 `_dbId`（新增） | 按 `direction` 插入对应表 |
| 数据库有但 records 无 | DELETE 删除（前端已删） |

**表归属规则**：`direction === "收入"` 且 `_src !== "bill"` 进 `income_records`，其余进 `billing_records`。

### 4.4 后端 API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/state` | 返回 `{records, fund, budget, savings}` |
| POST | `/api/records` | 全量对账写记录，返回合并后 records（含 `_dbId`） |
| POST | `/api/settings` | 写 fund/budget/savings 到 settings JSON |
| GET | 静态文件 | 托管 ledger.html 及资源（有路径穿越防护） |

### 4.5 离线兜底

后端不可用时（`initFromServer` catch 分支）：
- 优先读 localStorage 历史数据；
- 无历史数据时回退 `defaultRecords()` 演示数据；
- **兜底数据不写回后端**（`meta.firstOpen`/`demoLoaded` 控制）。

---

## 5. 各页面业务逻辑

### 5.1 记账页（record.js）

- **收支切换** `setRecordType()`：收入模式隐藏"消费类型"下拉（收入表无该列）。
- **分类联动**：支出用 `CATEGORY_OPTIONS`，收入用 `INCOME_CATEGORY_OPTIONS`；大类选中后渲染对应细类。
- **保存** `saveRecord()`：
  1. 校验金额 > 0、已选分类；
  2. 构造记录（`itemName` 空则用细类/大类兜底）；
  3. `unshift` 到数组头部 → `setRecords` → `flushSync()` 立即落库；
  4. 清空表单，`renderAll()` 刷新全页。
- **删除** `deleteRecord(id)`：过滤 + 立即同步。

### 5.2 首页（render-home.js）

- **今天要处理** `renderTodayItems()`：
  - **固定支出未记提醒**：按大类匹配本月记录，未记则提醒（超期标红）；
  - **支出节奏预警**：`已花/总预算 > 时间进度 + 0.1` 时提示。
- **月度概览**：收入/固定支出/弹性支出/结余四卡。
- **自由基金环** `renderFundRing()`：进度环百分比 = `当前金额 / 目标金额`。
- **存款曲线** `renderSavingsChartMini()`：手写 SVG 折线图（面积渐变、目标虚线、Y轴刻度、末点高亮）。

---

## 6. 主入口（main.js）

```js
init()
  → initFromServer()                 // 从后端加载
  → 标记 meta.firstOpen = false
  → 后端不可用且无数据时回退演示数据
  → bindEvents()                     // 导航切换、导入
  → renderToolbar()                  // 导出/导入/清示例按钮
  → renderAll()                      // 全量渲染两页
```

`renderAll()` 依次调用 `renderHome()`、`renderLedger()`，保证每次数据变更后界面同步。

---

## 7. 常用扩展指引

### 7.1 新增消费大类

1. `config.js` 的 `CATEGORY_OPTIONS` 加名称；
2. `SUBCATEGORY_OPTIONS` 加对应细类数组；
3. `CATS` 加 `{color, icon}`（颜色 + SVG 图标）；
4. 后端 `common.py` 的校验白名单同步更新（若存在）。

### 7.2 新增收入来源

同上，但改 `INCOME_CATEGORY_OPTIONS` / `INCOME_SUBCATEGORY_OPTIONS`，收入记录**不写** `expenseType`。

### 7.3 新增设置项

1. `storage.js` 的 `defaultFund()`/`defaultBudget()` 等加字段；
2. `ledger_server.py` 对应 `DEFAULT_FUND`/`DEFAULT_BUDGET` 同步；
3. 渲染层读取使用。

---

## 8. 注意事项

- **必须经 `ledger_server.py` 访问**，否则 fetch 失败。
- `_dbId`/`_src` 是后端回填字段，前端新增记录**不要**手动设置，否则会误判为更新已有行。
- `records` 同步是全量对账，前端 `DB.records` 必须始终代表"完整记录集"，删除用 `filter` 而不是局部修改。
- 金额统一存绝对值，方向由 `direction` 区分。
- 示例数据标记 `demo: true`，`clearDemoData()` 会过滤删除它们，自定义数据不受影响。
