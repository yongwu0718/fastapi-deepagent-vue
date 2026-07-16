# SubAgent 子代理管理模块

> 本文档为 `backend/memory_skill/skill/subagents/` 模块的技术说明，涵盖子代理的 Python 字典定义方式、importlib 热加载机制、以及主代理委派调用的完整流程。

---

## 概述

SubAgent（子代理）是 DeepAgents 框架中实现**任务委派**和**上下文隔离**的核心机制。主代理通过 `task` 工具将复杂任务委派给子代理，子代理在独立上下文中执行并返回简洁结果，避免主代理上下文被中间结果填满。

本模块是子代理的**配置与管理层**，位于 Core Agent 编译和子代理实现之间：

```
subagents_config.py  →  load_subagents() (热加载)
                              ↓
              init_graph() → create_deep_agent(subagents=...)
                              ↓
                   POST /settings/rebuild → 零停机更新
```

**核心设计原则**：
- 子代理配置与加载器分离（对标 MCP 工具加载模式）
- 通过 `importlib` 实现零停机热重载
- 加载失败不影响主 Agent 正常运行

---

## 模块结构

```
backend/memory_skill/skill/subagents/
├── SKILL.md                         # 子代理技能说明文档（DeepAgents 规范）
└── scripts/
    ├── subagents_config.py          # 子代理 Python 字典定义
    └── subagent_loader.py           # importlib 热加载器
```

---

## 配置文件（`subagents_config.py`）

### 配置结构

每个子代理是一个 Python 字典，必须包含三个核心字段，可选六个扩展字段：

```python
my_subagent = {
    "name": "my-subagent",              # 必需：唯一标识符
    "description": "描述子代理的功能",    # 必需：主代理据此决定何时委派
    "system_prompt": "子代理的指令",     # 必需：定义行为和工作流
    "tools": [tool_func1, tool_func2],  # 可选：指定则完全覆盖继承
    "model": llm_instance,              # 可选：覆盖主代理模型
    "middleware": [...],                # 可选：额外中间件
    "skills": ["/skills/xxx/"],         # 可选：技能源路径
    "interrupt_on": {...},              # 可选：人机协同配置
    "response_format": ResponseFormat,  # 可选：结构化输出模式
    "permissions": [...],               # 可选：文件系统权限规则
}

subagents = [
    my_subagent,   # 注释掉即禁用
]
```

### 字段详解

| 字段 | 类型 | 必需 | 说明 |
|------|------|:--:|------|
| `name` | `str` | ✅ | 唯一标识符，主代理通过此名称调用，同时出现在流式元数据中 |
| `description` | `str` | ✅ | 功能描述，**要具体面向操作**。主代理根据 string 匹配决定委派给谁 |
| `system_prompt` | `str` | ✅ | 子代理的系统指令，包含工具使用指导、工作流程和输出格式要求 |
| `tools` | `list[Callable]` | ❌ | 子代理可用工具列表。指定后**完全覆盖**继承，不填则继承主代理全部工具 |
| `model` | `str \| BaseChatModel` | ❌ | 覆盖主代理模型。字符串格式 `"provider:model"`（如 `"openai:gpt-4o"`） |
| `middleware` | `list` | ❌ | 额外中间件列表，不从主代理继承 |
| `skills` | `list[str]` | ❌ | 技能源路径列表，子代理拥有独立的 `SkillsMiddleware` 实例 |
| `interrupt_on` | `dict` | ❌ | 人机协同中断配置，格式同主代理的 `interrupt_on` |
| `response_format` | `ResponseFormat` | ❌ | 结构化输出模式，父代理收到 JSON 而非自由文本 |
| `permissions` | `list` | ❌ | 文件系统权限规则列表 |

### 工具继承规则

- **不指定 `tools`**：子代理继承主代理的全部工具
- **指定 `tools`**：完全覆盖，只拥有列表中指定的工具（推荐：最小化工具集）

---

### 已有子代理

#### bill-analyzer（账单分析子代理）

```python
bill_analyzer = {
    "name": "bill-analyzer",
    "description": (
        "分析个人账单数据：收支总览、消费分类排名、各平台支出占比、"
        "食品消费习惯追踪、基于历史趋势的下月预算预测。"
        "当用户询问花了多少钱、钱花在哪、消费是否健康、下月该预算多少时使用此代理。"
    ),
    "system_prompt": (
        "你是一位专业的个人财务分析师...\n"
        "工作流程：\n"
        "1. 使用 analyze_billing 获取整体收支概览\n"
        "2. 使用 analyze_monthly 查看月度变化趋势\n"
        "3. 使用 analyze_expense 获取消费分类明细\n"
        "4. 使用 analyze_monthly_categories 分析各类消费的月度变化\n"
        "5. 需要时使用 save_bill 保存分析结果\n"
        "输出要求：简洁，控制在 500 字以内"
    ),
    "tools": [
        analyze_billing, analyze_monthly, analyze_expense,
        analyze_monthly_categories, save_bill,
    ],
    "model": llm_ali,       # 阿里云 Qwen 模型
}
```

| 属性 | 值 |
|------|-----|
| 名称 | `bill-analyzer` |
| 模型 | `llm_ali`（阿里云 ChatQwen） |
| 工具数 | 5 个（4 分析 + 1 保存） |
| 触发条件 | 用户询问账单、消费、预算相关 |

---

## 热加载器（`subagent_loader.py`）

### `load_subagents()` 函数

每次调用都通过 `importlib` 强制重新加载 `subagents_config.py` 模块，确保修改后立即生效：

```python
async def load_subagents() -> list[dict[str, Any]]:
    # 1. 移除已缓存的模块，强制重新加载
    if "subagents_config" in sys.modules:
        del sys.modules["subagents_config"]

    # 2. 通过文件路径创建模块规范
    spec = importlib.util.spec_from_file_location("subagents_config", config_path)

    # 3. 创建新模块并执行
    module = importlib.util.module_from_spec(spec)
    sys.modules["subagents_config"] = module
    spec.loader.exec_module(module)

    # 4. 提取 subagents 列表
    return getattr(module, "subagents", [])
```

### 容错设计

| 异常场景 | 处理策略 |
|----------|----------|
| 找不到配置文件 | 返回空列表 `[]`，不影响主 Agent |
| 模块加载失败 | 返回空列表 `[]`，记录警告日志 |
| `subagents` 变量不存在 | `getattr(module, "subagents", [])` 兜底 |
| 单个子代理定义错误 | 不会在加载阶段报错（由 DeepAgents 在编译时校验） |

### 与 MCP 工具加载的对比

| 特性 | MCP 工具（`mcp_tool.py`） | 子代理（`subagent_loader.py`） |
|------|--------------------------|-------------------------------|
| 配置格式 | JSON (`mcp_server.json`) | Python 字典 (`subagents_config.py`) |
| 加载方式 | `MultiServerMCPClient` | `importlib` 动态模块 |
| 热重载 | 每次调用重新读取 JSON | 每次调用 `del sys.modules` |
| 容错 | 单个 MCP 服务失败不影响其他 | 整个配置失败返回空列表 |
| 加载时机 | `init_graph()` 中 `await mcp_tool()` | `init_graph()` 中 `await load_subagents()` |

---

## 热重载全链路

```
subagents_config.py 修改
        ↓
load_subagents() 通过 importlib 强制重载
        ↓
init_graph() → create_deep_agent(subagents=新配置)
        ↓
POST /settings/rebuild → Agent 重新编译生效
```

**操作步骤**：

1. 编辑 `backend/memory_skill/skill/subagents/scripts/subagents_config.py`
2. 修改 `subagents` 列表（添加/修改/注释掉子代理）
3. 调用 `POST /settings/rebuild` 或重启服务
4. 新配置即时生效，无需完整重启

---

## 子代理与 Core 模块的关系

### 数据流向

```
┌─────────────────────────────────────────────────────────────┐
│                      main_agent.py                          │
│                          init_graph()                       │
│  subagents_config = await load_subagents()  ← 热加载        │
│  agent = create_deep_agent(                                  │
│      subagents=subagents_config,  ← 传入 DeepAgents         │
│      ...                                                     │
│  )                                                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  DeepAgents 框架                             │
│                                                              │
│  自动注册 SubAgentMiddleware → 扫描 subagents 列表           │
│  为每个子代理编译独立的 LangGraph 图                         │
│  主代理自动获得 task(name=..., task=...) 工具                │
└──────────────────────────────────────────────────────────────┘
```

### 主代理调用子代理

```
用户消息 → 主代理 → 识别任务 → task("bill-analyzer", "分析我的消费")
                              ↓
                     bill-analyzer（独立上下文）
                              ↓
                     执行 5 个分析工具 + LLM 推理
                              ↓
                     返回简洁结果给主代理
                              ↓
                    主代理展示或继续后续操作
```

### DeepAgents 通用子代理

DeepAgents 默认会自动添加一个 `general-purpose` 子代理，与主代理共享全部工具和系统提示。该子代理用于处理无法匹配到特定子代理的通用任务。

- **自定义**：添加 `name="general-purpose"` 的条目即可覆盖默认通用子代理
- **禁用**：从 `subagents` 列表中排除即可完全移除（列表为空或仅有自定义子代理时不会自动添加）

---

## 配置最佳实践

### 1. 编写清晰的描述

主代理根据 `description` 决定调用哪个子代理，描述必须**具体、面向操作**：

| 评价 | 示例 |
|:--:|------|
| ✅ 好 | `"分析财务数据并生成带有置信度分数的投资见解"` |
| ❌ 差 | `"做财务方面的事情"` |

### 2. 保持 system_prompt 结构化

包含三个关键部分：工作流程 + 工具使用顺序 + 输出格式要求：

```python
"system_prompt": (
    "角色定义\n\n"
    "工作流程：\n"
    "1. 步骤一\n"
    "2. 步骤二\n\n"
    "输出要求：\n"
    "- 格式一\n"
    "- 字数限制\n"
)
```

### 3. 最小化工具集

只给子代理完成工作所必需的工具，提高专注度和安全性：

```python
# ✅ 好：专注的工具集
email_agent = {"tools": [send_email, validate_email]}

# ❌ 差：工具过多，不专注
email_agent = {"tools": [send_email, web_search, database_query, file_upload]}
```

### 4. 按任务选择模型

不同模型擅长不同任务：

| 任务类型 | 推荐模型选择 | 原因 |
|----------|-------------|------|
| 长文档分析 | Gemini（大上下文） | 百万级 token 上下文窗口 |
| 复杂推理 | Claude / GPT-5 | 强推理能力 |
| 成本敏感 | Ollama（本地） | 零 API 费用 |
| 中文优化 | Qwen（阿里云） | 中文理解能力强 |

### 5. 控制输出简洁度

在 `system_prompt` 中明确字数限制，防止子代理输出撑满主代理上下文：

```python
"system_prompt": (
    "只返回关键摘要，不要包含原始数据和中间计算。"
    "保持回复在 300 字以内。"
)
```

---

## 常见模式

### 多子代理流水线

为不同阶段创建专门子代理，主代理负责编排：

```python
subagents = [
    {"name": "data-collector",  "tools": [web_search, api_call]},
    {"name": "data-analyzer",   "tools": [statistical_analysis]},
    {"name": "report-writer",   "tools": [format_document]},
]
```

工作流：主代理创建计划 → 委派 collection → 委派 analysis → 委派 report → 汇总输出。

### 上下文传播

父代理运行时上下文（`context_schema`）自动传播到所有子代理，子代理工具可通过 `ToolRuntime` 访问：

```python
@tool
def search(query: str, runtime: ToolRuntime[Context]) -> str:
    max_depth = runtime.context.researcher_max_depth
    return perform_search(query, max_depth=max_depth)
```

### 识别调用者

当多个子代理共享工具时，通过 `lc_agent_name` 元数据区分：

```python
@tool
def shared_tool(query: str, runtime: ToolRuntime) -> str:
    agent_name = runtime.config["metadata"]["lc_agent_name"]
    if agent_name == "fact-checker":
        return strict_mode(query)
    return normal_mode(query)
```

---

## 故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| 子代理未被调用 | description 不够具体 | 使描述更具体，说明何时使用；在主代理 system_prompt 中指示委派 |
| 上下文膨胀 | 子代理输出过长 | 在 system_prompt 中明确字数限制（如 500 字）；使用文件系统暂存大量数据 |
| 选错子代理 | description 边界模糊 | 在描述中明确区分各子代理的能力边界 |
| 热重载不生效 | 未调用 rebuild | 编辑配置后调用 `POST /settings/rebuild` 使修改即时生效 |
