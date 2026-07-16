# Core 核心组件模块技术文档

> 本文档为 `backend/core/` 模块的详细技术说明，涵盖 Agent 编译组装、模型管理、中间件链、工具集、子智能体等核心能力。

---

## 概述

Core 模块是 Index RAG 项目的 **Agent 核心层**，负责将模型、工具、中间件、后端、记忆、技能等组件组装为完整的 LangGraph Agent。

在整体架构中的位置：

```
API 层（backend/api/）    → 路由分发、请求响应
        ↓
Core 层（backend/core/）  → Agent 编译、模型管理、中间件、工具集
        ↓
配置/数据层               → YAML 配置、SQLite、Chroma、文件系统
```

核心职责：
- **Agent 编译**：`create_deep_agent` 将 10+ 组件组装为 LangGraph CompiledStateGraph
- **模型热切换**：运行时切换 DeepSeek / 阿里云 / Ollama / OpenAI，带故障转移
- **中间件链**：4 层中间件（摘要 → 截断 → 代码解释器 → Rubric 评估）
- **工具集管理**：记忆工具、RAG 检索、MCP 外部工具、账单分析
- **子智能体**：LangGraph 图定义 + RAG 子智能体工厂；配置管理见 [SubAgent 子代理管理模块](./SubAgent子代理管理模块.md)

---

## 模块结构

```
backend/core/
├── __init__.py
├── main_agent.py                    # 主 Agent 编译入口（init_graph 上下文管理器）
├── assembled/                       # 后端与中间件组装
│   ├── backends.py                  # CompositeBackend 路由表
│   └── middleware.py                # 中间件链配置
├── custom_middleware/               # 自定义中间件
│   ├── model_switcher.py            # 模型动态切换与故障转移
│   └── truncate_toolmessage.py      # 工具消息截断
├── models/                          # 模型管理层
│   ├── model_factory.py             # LLM 工厂（4 种模型 + 嵌入 + Reranker）
│   ├── llm_settings.py              # model_config.yaml 配置加载
│   ├── env_api_key.py               # API Key 管理（.env.api_key）
│   └── reranker.py                  # DashScope Reranker 封装
├── prompts/                         # 提示词
│   ├── prompt.py                    # 提示词加载器
│   └── system_prompt.txt            # 系统提示词正文
├── skill_manager/                   # 技能管理
│   ├── filtered_backend.py          # 技能过滤后端
│   └── skills_config.yaml           # 技能开关配置
├── subagent/                        # 子智能体
│   ├── langgraph_subagent/          # LangGraph 子智能体（账单分析）
│   │   ├── graph_compile.py         # 图编译
│   │   ├── nodes.py                 # 节点工厂
│   │   ├── prompt.py                # 子智能体提示词
│   │   └── state_config.py          # 状态定义
│   └── rag_subagent/                # RAG 检索子智能体
│       └── rag_factory.py           # create_deep_agent 工厂
└── utils/                           # 工具集
    ├── __init__.py                  # 工具统一导出
    ├── retrieval/                   # RAG 检索工具
    │   ├── retrieve_tool.py         # 检索管道（向量召回 + 重排序）
    │   └── prompt.py
    ├── tools/                       # 长期记忆工具
    │   └── memory_tool.py           # 5 个记忆工具 + MemoryStore 封装
    ├── mcp/                         # MCP 协议集成
    │   ├── mcp_tool.py              # MCP 工具加载器
    │   ├── mcp_server.json          # MCP 服务配置
    │   ├── fastmcp_search.py        # URL 抓取工具
    │   └── local_mcp.py             # 本地数学工具
    └── bill_subagent/               # 账单分析
        └── billing/
            ├── analyze_billing.py   # 收支总览
            ├── analyze_monthly.py   # 月度趋势分析
            ├── analyze_expense.py   # 支出明细分析
            ├── analyze_monthly_categories.py  # 分类月度对比
            ├── calculate.py         # 基础运算（add/multiply/subtract/divide）
            ├── save_bill.py         # 账单记录保存
            └── import_csv_to_sqlite.py  # CSV 导入
```

---

## 主 Agent 编译（`main_agent.py`）

### `init_graph()` 异步上下文管理器

这是 Agent 的核心入口。每次 Graph 热重载时进入此上下文，确保读取最新配置。

```python
@asynccontextmanager
async def init_graph():
    agent = create_deep_agent(
        name="index_agent",
        model = get_active_llm(),         # 动态获取当前激活模型
        system_prompt=load_system_prompt(), # 每次重新读取
        tools=tools_list,                 # 14+ 个工具
        interrupt_on=interrupt_on,        # HITL 中断配置
        backend=backend,                  # CompositeBackend
        middleware=add_middleware,         # 4 层中间件
        memory=memory_config,             # ["/AGENT.md"]
        skills=skills_config,             # ["/active_skills/"]
        context_schema=ModelContext,      # 模型切换上下文
        subagents=subagents_config,       # 子智能体配置
        checkpointer=checkpointer_sql,    # AsyncSqliteSaver
        store=store_sql,                  # AsyncSqliteStore
    )
    yield agent
```

### create_deep_agent 参数详解

| 参数 | 值 | 说明 |
|------|-----|------|
| `name` | `"index_agent"` | Agent 标识名 |
| `model` | `get_active_llm()` | 按 `active_provider` 动态选择 LLM |
| `system_prompt` | `load_system_prompt()` | 从 `system_prompt.txt` 每次读取（热更新） |
| `tools` | 14+ 工具 | 记忆(5) + RAG检索(1) + MCP工具 + 账单分析(5) + 基础运算(4) |
| `interrupt_on` | `{}`（当前无配置） | HITL 风险分级中断，例：`{"read_file": {"allowed_decisions": ["approve","reject","edit"]}}` |
| `backend` | `CompositeBackend` | 多路由文件后端，见下文 |
| `middleware` | 4 个中间件 | 手动摘要 → 截断 → 代码解释器 → Rubric |
| `memory` | `["/AGENT.md"]` | 持久化记忆文件路径 |
| `skills` | `["/active_skills/"]` | 动态技能加载路径 |
| `context_schema` | `ModelContext` | 模型切换上下文类型 |
| `subagents` | 动态加载 | 从 `backend/memory_skill/skill/subagents/scripts/subagent_loader.py` 热加载（详见 [SubAgent 子代理管理模块](./SubAgent子代理管理模块.md)） |
| `checkpointer` | `AsyncSqliteSaver` | SQLite 异步检查点 |
| `store` | `AsyncSqliteStore` | SQLite 异步状态存储 |

### 配置热更新机制

`init_graph()` 内部使用**动态 import**（非顶层 import）确保每次进入上下文都重新读取最新配置：

```python
# 动态导入以避免模块缓存，确保读最新配置
from backend.core.models.model_factory import get_active_llm
from backend.core.prompts.prompt import load_system_prompt
from backend.memory_skill.skill.subagents.scripts.subagent_loader import load_subagents
```

### 工具列表组装

```python
tools_list = [
    save_memory, search_memory, delete_memory, get_memory, list_memory_keys,  # 记忆(5)
    retriever_row_doc_tool,                                                   # RAG检索(1)
    *mcp_tools,                                                               # MCP外部工具(动态)
    save_bill, analyze_billing, analyze_monthly,                              # 账单分析(5)
    analyze_expense, analyze_monthly_categories,
]
```

---

## 后端组装（`assembled/`）

### `backends.py` — CompositeBackend 路由表

使用 `CompositeBackend` 为不同路径前缀分配不同的后端实现：

| 路由前缀 | 后端类型 | 根目录 | 说明 |
|----------|----------|--------|------|
| `default` | `LocalShellBackend` | `WORKSPACE_DIR` | 提供 shell 执行能力，`virtual_mode=True` |
| `/memory/` | `FilesystemBackend` | `MEMORY_DIR` | 虚拟记忆文件写入 |
| `/active_skills/` | `SkillFilteredBackend` | `SKILLS_DIR` | 动态过滤未启用技能 |
| `/knowledge/` | `FilesystemBackend` | `DOC_INDEX` | 虚拟知识库文件写入 |

**Shell Backend 环境配置**：

```python
LocalShellBackend(
    root_dir=WORKSPACE_DIR,
    virtual_mode=True,           # 虚拟模式（写入内存页面，不落盘？）
    inherit_env=True,            # 继承系统环境变量
    env={"PATH": merged_path},   # 合并 Python/Node 到 PATH
)
```

### `middleware.py` — 中间件链

4 层中间件按以下顺序组装：

```
[手动摘要] → [工具消息截断] → [代码解释器] → [Rubric评估]
```

| 顺序 | 中间件 | 配置 | 作用 |
|------|--------|------|------|
| 1 | `SummarizationToolMiddleware` | 封装 `SummarizationMiddleware` | 手动摘要工具，750k tokens 触发自动摘要，保留 150k |
| 2 | `TruncateToolMessagesMiddleware` | `keep_recent=15` | 截断旧工具消息，保留最近 15 条 |
| 3 | `CodeInterpreterMiddleware` | 默认配置 | QuickJS 代码解释器沙箱 |
| 4 | `RubricMiddleware` | `model=llm_deepseek`, `max_iterations=10` | Loop Engineering 条件驱动循环评估 |

**摘要中间件详细配置**：

| 参数 | 值 | 说明 |
|------|-----|------|
| `model` | `llm_deepseek` | 摘要生成模型 |
| `trigger` | `("tokens", 750_000)` | 750k tokens 触发自动摘要 |
| `keep` | `("tokens", 150_000)` | 保留 150k tokens |
| `trim_tokens_to_summarize` | `40_000` | 每次摘要处理的 token 数 |
| `truncate_args_settings.trigger` | `("tokens", 190_000)` | 参数截断触发阈值 |
| `truncate_args_settings.max_length` | `4000` | 参数最大长度 |

---

## 自定义中间件（`custom_middleware/`）

### 1. 模型动态切换（`model_switcher.py`）

**双机制**：主动选择 + 被动故障转移。

#### ModelContext 上下文

用户通过 `invoke` 时传入 `ModelContext(model="ali")` 指定目标模型：

```python
@dataclass
class ModelContext:
    model: str = ""  # "deepseek" / "ali" / "ollama" / "moonshot"
```

#### 模型注册表

| 名称 | 模型实例 | 说明 |
|------|----------|------|
| `deepseek` | `ChatDeepSeek` | 主模型 |
| `ali` | `ChatQwen` | 阿里云备用 |
| `ollama` | `ChatOllama` | 本地兜底 |

#### 故障转移链

```
deepseek → ali → ollama（本地兜底）
```

执行逻辑：
1. 从 `ModelContext.model` 解析用户指定的模型
2. 尝试用当前模型调用，失败后同模型重试 **2 次**（应对瞬时网络抖动）
3. 重试耗尽后切换到下一个备用模型
4. 所有模型均失败后抛出最终异常

### 2. 工具消息截断（`truncate_toolmessage.py`）

`TruncateToolMessagesMiddleware` 防止旧的检索结果/MCP 输出持续占用上下文窗口。

**策略**：从历史消息末尾向前扫描，保留最近 `keep_recent=15` 个 `ToolMessage`，其余替换为占位符：

```
"[Earlier tool outputs are omitted for context management.]"
```

---

## 模型管理（`models/`）

### `model_factory.py` — LLM 工厂

支持 4 种模型提供商，每种提供 **静态实例** 和 **工厂函数** 两种访问方式。

#### LLM 模型

| 提供商 | 类 | 静态实例 | 工厂函数 | 特殊配置 |
|--------|-----|----------|----------|----------|
| DeepSeek | `ChatDeepSeek` | `llm_deepseek` | `create_llm_deepseek()` | `reasoning_effort`, `extra_body` |
| DeepSeek JSON | `ChatDeepSeek` | `llm_json` | — | 结构化输出专用 |
| 阿里云 | `ChatQwen` | `llm_ali` | `create_llm_ali()` | `enable_thinking` |
| Ollama | `ChatOllama` | `llm_ollama` | `create_llm_ollama()` | `reasoning` |
| OpenAI | `ChatOpenAI` | `llm_openai` | `create_llm_openai()` | — |

#### 嵌入模型 & Reranker

| 模型 | 类 | 实例 |
|------|-----|------|
| 嵌入 | `OllamaEmbeddings` | `embeddings` |
| 重排序 | `DashScopeRerank` | `rerank_model` |

#### `get_active_llm()` — 激活模型选择

```python
def get_active_llm():
    settings = _reload_settings()                    # 重新加载 YAML
    provider = settings.LLM_ACTIVE_PROVIDER or "deepseek"
    factory = _PROVIDER_FACTORIES.get(provider)      # 查表获取工厂
    return factory()                                 # 创建新实例（热更新）
```

工厂映射表：

```python
_PROVIDER_FACTORIES = {
    "deepseek": create_llm_deepseek,
    "ali": create_llm_ali,
    "ollama": create_llm_ollama,
    "openai": create_llm_openai,
}
```

### `llm_settings.py` — 配置加载

**三级配置优先级**：

```
环境变量 > YAML 配置 > 默认值
```

`_env_or_yaml(env_key, *yaml_path, default)` 封装此逻辑。

**`reload_model_config()` 函数**：重新读取 `model_config.yaml`，更新所有模块级变量（20+ 个配置项）。

**自动发现项目根目录**：从当前文件向上查找 `model_config.yaml`。

### `env_api_key.py` — API Key 管理

从 `.env.api_key` 文件加载，使用 `load_dotenv(override=True)`：

| 环境变量 | 用途 |
|----------|------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope（LLM + Reranker） |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `OPENAI_API_KEY` | OpenAI |

自动发现机制：向上查找 `.env.api_key` 标记文件确定项目根目录。

### `reranker.py` — DashScope Rerank 封装

`DashScopeRerank` 继承 `BaseDocumentCompressor`，实现 `compress_documents`：

- **API**：DashScope `TextReRank` 服务
- **模型**：`gte-rerank-v2`（可配置）
- **默认 top_n**：10（可配置）
- 返回 `relevance_score` 写入 `doc.metadata`

---

## 提示词（`prompts/`）

### `system_prompt.txt` — 系统提示词

完整的 Agent 行为规范，核心内容：

#### 复杂任务确认流程

当任务满足以下条件时，要求在**执行前先说明计划步骤并等待确认**：
- 涉及多个步骤（需要规划）
- 可能产生不可逆结果（文件写入、删除、外部操作）
- 用户只描述了目标，未给明确执行指令

确认流程：列出步骤清单 → 询问"是否按此方案执行？" → 等待确认后执行。

#### 长期记忆工具使用规则

| 工具 | 使用场景 |
|------|----------|
| `search_memory` | 用户问题涉及历史信息、偏好、过往决策时**先检索再回答** |
| `get_memory` | 已知 `memory_key` 时需要精确读取 |
| `list_memory_keys` | 用户要求列出或需要概览时（最多 1000 条） |
| `delete_memory` | 用户明确要求删除时，需先确认 |

核心规则：主动搜索 → 精确获取 → 删除需确认 → 失败如实告知 → 无关时不调用。

### `prompt.py` — 提示词加载器

```python
def load_system_prompt() -> str:
    """每次调用重新读取文件，支持热更新"""
    prompt_file = Path(__file__).parent / "system_prompt.txt"
    return prompt_file.read_text(encoding="utf-8")
```

---

## 技能管理（`skill_manager/`）

### SkillFilteredBackend

包装 `FilesystemBackend`，在 `ls`/`als` 时按 `skills_config.yaml` 过滤结果。

**过滤逻辑**：
1. 读取 `skills_config.yaml` 中的 `enabled` 列表
2. 对 `ls` 返回的 `entries` 按目录名过滤
3. 只在 `enabled` 中的技能目录才展示
4. 其他所有方法/属性透传给内部后端（`__getattr__`）

**skills_config.yaml 示例**：

```yaml
enabled:
- billing_analyze
- gonghao-baowen-writing
- subagents
- task-planner
- vocab-tutor
- vue-best-practices
```
---

## 工具集（`utils/`）

### 工具清单

| 分类 | 工具 | 来源 |
|------|------|------|
| RAG 检索 | `retriever_row_doc_tool` | `retrieval/retrieve_tool.py` |
| 长期记忆 | `save_memory` | `tools/memory_tool.py` |
| | `search_memory` | |
| | `get_memory` | |
| | `delete_memory` | |
| | `list_memory_keys` | |
| MCP 外部工具 | 动态加载 | `mcp/mcp_tool.py` |
| 账单分析 | `analyze_billing` | `bill_subagent/billing/` |
| | `analyze_monthly` | |
| | `analyze_expense` | |
| | `analyze_monthly_categories` | |
| | `save_bill` | |
| 基础运算 | `add`, `multiply`, `subtract`, `divide` | `bill_subagent/billing/calculate.py` |

---

### 1. RAG 检索工具（`retrieval/retrieve_tool.py`）

`retriever_row_doc_tool` 是 Agent 进行知识库检索的唯一入口。

#### 两阶段检索管道

```
[用户查询] → 向量召回(k=50) → 重排序过滤(threshold=0.5) → [相关文档]
```

**步骤 1：向量召回**

- Chroma `similarity_search(question, k=50)`
- 使用 `OllamaEmbeddings`（`my-qwen3-embed` 模型）

**步骤 2：重排序 + 过滤**

- DashScope `gte-rerank-v2` 对 50 篇候选重排序
- 按 `relevance_score ≥ 0.5` 过滤低质量结果
- 输出 top_n=10 篇（Reranker 默认）

**降级与兜底策略**：

| 场景 | 策略 |
|------|------|
| 重排序失败 | 降级为纯向量排序，取前 top_n 篇 |
| 重排序后无文档达标 | 兜底返回重排序最高分的一篇 |
| 召回为空 | 直接返回空结果 + 错误信息 |

**性能日志**：记录每个步骤的耗时（ms）。

---

### 2. 长期记忆工具（`tools/memory_tool.py`）

独立的记忆向量存储，与 RAG 文档库分离。

#### MemoryStore 封装

| 方法 | 功能 |
|------|------|
| `upsert(key, value)` | 插入或覆盖记忆（将扩展字段打包为 JSON → Chroma metadata） |
| `search(query, k=5, threshold=0.4)` | 语义搜索，超阈值自动过滤 |
| `get(key)` | 精确获取并反序列化完整字段 |
| `delete(key)` | 按 key 删除 |
| `list_keys(page_size=100, max=1000)` | 分页列出所有 key |

**存储策略**：
- `page_content` = 自然语言记忆内容
- `metadata` = JSON 字符串打包所有扩展字段（`key`, `category`, `timestamp`, `importance`, `metadata`）
- 使用 `doc.id` 作为 memory_key

**记忆条目结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `content` | `str` | 核心记忆内容（自然语言） |
| `category` | `str` | 分类，如 "用户偏好"、"决策历史"、"事实" |
| `timestamp` | `str` | ISO 格式时间戳（`save_memory` 自动填充） |
| `importance` | `float` | 0~1 重要性（默认 0.5） |
| `metadata` | `dict` | 扩展元数据 |

#### 5 个 LangChain 工具

| 工具 | 函数签名 | 说明 |
|------|----------|------|
| `save_memory` | `(memory_key, memory_value) → str` | 支持 dict 或 JSON 字符串输入 |
| `search_memory` | `(query) → str` | 默认 k=5, threshold=0.4 |
| `get_memory` | `(memory_key) → str` | 精确获取，不存在返回 ⚠️ |
| `delete_memory` | `(memory_key) → str` | 删除确认 |
| `list_memory_keys` | `() → str` | 最多 1000 条 |

---

### 3. MCP 工具集成（`mcp/`）

#### `mcp_tool.py` — MCP 工具加载器

异步加载 `mcp_server.json` 中配置的所有 MCP 服务工具：

**加载流程**：
1. 读取 `mcp_server.json` 配置
2. 递归替换占位符（`{VAR_NAME}` → 环境变量或内置映射）
3. 逐服务创建 `MultiServerMCPClient`
4. 单个服务加载失败不影响其他服务

**内置占位符**：

| 占位符 | 值 | 说明 |
|--------|-----|------|
| `{PYTHON_EXECUTABLE}` | `sys.executable` | Python 解释器路径 |
| `{MCP_SERVER_DIR}` | 配置文件所在目录 | MCP 服务目录 |

**废弃传输警告**：`sse` 传输已弃用，建议使用 `http` (streamable-http)。

#### `fastmcp_search.py` — URL 抓取工具

基于 FastMCP，提供 `fetch_url_content(url)` 工具：
- 发送 HTTP GET 请求
- 设置 User-Agent 避免被拒绝
- 10 秒超时
- 返回纯文本内容或错误信息

#### `local_mcp.py` — 本地数学工具

基于 FastMCP 的本地 MCP 服务，提供 `add(a, b)` 和 `multiply(a, b)` 工具，通过 `stdio` 传输运行。

---

### 4. 账单分析工具（`bill_subagent/billing/`）

#### 分析工具（4 个）

| 工具 | 功能 | 支持参数 |
|------|------|----------|
| `analyze_billing` | 收支总览 + 分类排名 + 平台分布 | `start_date`, `end_date` |
| `analyze_monthly` | 三层逐月：收支 + 刚性固定 + 效率 + 弹性 | `start_date`, `end_date` |
| `analyze_expense` | 支出层级 + item 明细 + 消费频次 + 食品追踪 | `start_date`, `end_date` |
| `analyze_monthly_categories` | 逐月各类别排名 + 刚性/弹性分布 | `start_date`, `end_date` |

#### 数据管理工具（2 个）

| 工具 | 功能 |
|------|------|
| `save_bill` | 保存单条消费记录到 `billing.db` SQLite 数据库 |
| `import_csv_to_sqlite` | 将微信/支付宝 CSV 账单导入数据库 |

#### 基础运算工具（4 个）

| 工具 | 功能 | 特性 |
|------|------|------|
| `add(*args)` | 多个数求和 | `sum(args)` |
| `multiply(*args)` | 多个数连乘 | 空参数返回 0 |
| `subtract(*args)` | 从左到右连减 | 至少 2 个参数 |
| `divide(*args)` | 从左到右连除 | 至少 2 个参数，阻止零除 |

#### 数据模型（`save_bill`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `item_name` | `str` | 消费项目名称 |
| `category` | `str` | 预定义分类（食品/交通/购物 等 12 类） |
| `amount` | `float` | 金额（支出负数，收入正数） |
| `date` | `str` | 格式 "YYYY-MM-DD" |
| `platform` | `str` | 交易平台 |
| `year_month` | `str` | 格式 "YYYY-MM" |
| `expense_type` | `str` | 弹性可选 / 刚性固定 / 刚性必要 |

---

## 设计要点

### 1. 配置热更新全链路

```
model_config.yaml 变更
    ↓
reload_model_config() 重新读取 YAML
    ↓
get_active_llm() / create_llm_*() 创建新模型实例
    ↓
init_graph() 重新编译 Agent（通过 /settings/rebuild 触发）
```

热更新触发路径：
- API：`POST /settings/rebuild` → `rebuild_graph()` → 重新进入 `init_graph()`
- Skills：`PUT /settings/skills` → 更新配置 → 自动 `rebuild_graph()`
- 启动时：每次 API 服务启动自动执行

### 2. 中间件链执行顺序

Agent 每次调用 LLM 时，中间件按注册顺序依次执行：

```
请求
  → SummarizationToolMiddleware    # 检查是否触发摘要
    → TruncateToolMessagesMiddleware   # 截断旧工具消息
      → CodeInterpreterMiddleware      # QuickJS 沙箱
        → RubricMiddleware             # 条件驱动循环
          → LLM 调用
```

### 3. 故障转移与优雅降级

| 层级 | 策略 |
|------|------|
| 模型层 | DeepSeek → 阿里云 → Ollama（本地兜底），同模型重试 2 次 |
| 检索层 | Reranker 失败 → 降级为向量排序；无文档达标 → 兜底最高分 |
| MCP 层 | 单个 MCP 服务加载失败不影响其他服务 |

### 4. Factory 模式与单例管理

- **LLM 工厂函数**：每次调用创建新实例，支持热更新
- **静态实例**：用于中间件等不需要热更新的场景（如 `llm_deepseek`）
- **模块级单例**：`MemoryStore(memory_store)`, `_markitdown`, `_vectorstore`

### 5. StateGraph + DeltaChannel 优化

子智能体使用 `DeltaChannel` + `_messages_delta_reducer`，每 50 次写入自动快照：

```python
messages: Annotated[list[AnyMessage], DeltaChannel(_messages_delta_reducer, snapshot_frequency=50)]
```

相比全量快照，DeltaChannel 仅记录增量，大幅减少检查点存储开销。

### 6. 后端虚拟模式

所有 FilesystemBackend 均启用 `virtual_mode=True`：Agent 的文件操作写入虚拟内存页面，通过 `StateBackend` 与 LangGraph 状态集成，持久化到 SQLite 检查点。
