# Persistence

> 这是 LangGraph 中**持久化（Persistence）**的胖索引，覆盖检查点（Checkpoints）与内存存储（Store）两大支柱，线程与超级步骤模型、状态获取/更新/重放、存储的语义搜索与跨线程共享、序列化与加密，以及完整的 checkpointer 库选型指南。
> 阅读本文档可一次性掌握持久化层的全部概念及其关联，为构建有状态、可恢复、支持人机协同和长期记忆的 Agent 提供基础设施决策支撑。

---

## 概念全景

LangGraph 的持久化层由两个互补系统构成：**检查点（Checkpoints）** 负责保存图执行的时间点快照，实现暂停/恢复、时间旅行和容错；**内存存储（Store）** 负责跨线程（对话）持久化任意信息，实现长期记忆。

| 系统            | 用途                                         | 组织单位               | 生命周期                 | 典型后端                          |
| --------------- | -------------------------------------------- | ---------------------- | ------------------------ | --------------------------------- |
| **Checkpointer** | 保存图状态快照，支持中断、重放、分支         | 线程 (`thread_id`)     | 单线程内，多个检查点     | `InMemorySaver`, `SqliteSaver`, `PostgresSaver`, `CosmosDBSaver` |
| **Store**        | 跨线程持久化记忆、用户偏好等任意 JSON 文档   | 命名空间 + 键          | 跨线程/跨会话            | `InMemoryStore`, `PostgresStore`, `MongoDBStore`, `RedisStore` |

两者协同工作：Checkpointer 负责短期、线程级状态；Store 负责长期、跨线程信息。通过 `Runtime` 对象可在节点内同时访问两者。

核心决策点：**选择哪种 checkpointer 和 store 后端、如何设计 store 的命名空间以实现多租户隔离、是否启用语义搜索及如何配置嵌入、是否需要序列化加密**。

---

## 1. Checkpointer

### 线程 (Threads)

每条对话或会话对应一个 `thread_id`，是 checkpointer 存取状态的主键。调用图时必须在 `config["configurable"]["thread_id"]` 中提供。

### 检查点与超级步骤

- **检查点**：每个超级步骤（super-step）结束时自动保存的状态快照（`StateSnapshot`）。
- **超级步骤**：图的一次“滴答”，调度该步骤内所有节点并行执行。顺序图 `START -> A -> B -> END` 会在输入、A 节点后、B 节点后各产生一个检查点。

### StateSnapshot 关键字段

| 字段           | 描述                                                   |
| -------------- | ------------------------------------------------------ |
| `values`       | 此检查点的状态通道值                                   |
| `next`         | 接下来要执行的节点（空元组表示图已完成）               |
| `config`       | 含 `thread_id`、`checkpoint_ns`、`checkpoint_id`       |
| `metadata`     | `source`（input/loop/update）、`writes`、`step`        |
| `parent_config`| 前一个检查点配置，用于追溯                             |
| `tasks`        | 待执行的任务，可含 `interrupts` 信息                   |

### 获取状态

- `graph.get_state(config)` 获取最新状态或指定 `checkpoint_id` 的状态。
- `graph.get_state_history(config)` 返回检查点列表（最新在前），可按步骤、中断、来源筛选。

### 重放与更新时间

- **重放**：使用历史 `checkpoint_id` 重新调用图，该检查点之后的节点重新执行（LLM、API 等会再次触发）。
- **更新状态**：`graph.update_state(config, values, as_node=...)` 创建新检查点，不修改原检查点；`as_node` 决定下次从哪个节点继续。Reducer 字段会累积而非覆盖。

### 检查点命名空间

通过 `checkpoint_ns` 区分父图（空字符串）与子图（`"node_name:uuid"`），嵌套子图使用 `|` 分隔。可在节点内通过 `config["configurable"]["checkpoint_ns"]` 获取。

### Checkpointer 库选型

| 库                              | 适用场景                           |
| ------------------------------- | ---------------------------------- |
| `InMemorySaver`                 | 开发、测试                         |
| `SqliteSaver` / `AsyncSqliteSaver` | 本地实验                         |
| `PostgresSaver` / `AsyncPostgresSaver` | 生产环境（推荐）             |
| `CosmosDBSaver`                 | Azure 生产环境                     |

所有 checkpointer 实现 `BaseCheckpointSaver` 接口（`put`、`get_tuple`、`list` 及对应异步版本）。

---

## 2. Memory Store

### 基本操作

Store 按 `(namespace, key)` 组织 JSON 文档，支持 `put`、`get`、`search`、`delete`。命名空间通常包含用户 ID 以隔离数据。

### 语义搜索

配置嵌入模型和维度后，可按语义查询记忆：

```python
store = InMemoryStore(
    index={
        "embed": init_embeddings("openai:text-embedding-3-small"),
        "dims": 1536,
        "fields": ["food_preference", "$"]  # "$" 表示嵌入所有文本字段
    }
)
```

可控制每个记忆的索引字段或禁用索引。

### 在 LangGraph 节点中使用

通过 `Runtime[Context]` 注入，节点内可访问 `runtime.store` 进行 `asearch`、`aput` 等操作，结合 `runtime.context` 获取用户 ID 构建命名空间。

### 生产环境与 LangSmith

- 本地使用 `InMemoryStore`；生产使用 `PostgresStore`、`MongoDBStore`、`RedisStore`。
- 通过 LangGraph API / LangSmith 部署时，基础存储自动提供，无需手动配置；语义搜索需在 `langgraph.json` 的 `store.index` 中配置。

---

## 3. 优化与安全

### DeltaChannel

对于大量追加的通道（如消息列表），`DeltaChannel` 仅存储增量而非完整值，可显著减小检查点大小。需 `langgraph>=1.2`。

### 序列化与加密

- 默认使用 `JsonPlusSerializer`（基于 ormsgpack/JSON），支持 `pickle_fallback=True` 处理特殊类型。
- 通过 `EncryptedSerializer.from_pycryptodome_aes()` 可实现全状态加密，从 `LANGGRAPH_AES_KEY` 环境变量读取密钥。

---

## 4. 关键约束与最佳实践

- **必须提供 `thread_id`**：无此 ID 无法保存或恢复状态。
- **生产环境使用持久化 checkpointer**：`InMemorySaver` 仅用于开发，重启即丢失。
- **Store 命名空间设计**：按用户、租户、应用语境分层，确保隔离且易于搜索。
- **语义搜索需提前规划嵌入**：维度、字段、嵌入模型选定后不易更改。
- **检查点存储增长管理**：长时间对话考虑使用 `DeltaChannel` 或总结中间件压缩状态。
- **加密密钥管理**：生产环境务必设置 `LANGGRAPH_AES_KEY` 环境变量，切勿硬编码。
- **重放会重新触发副作用**：LLM 调用、API 请求等会再次执行，需注意幂等性。
- **`as_node` 控制恢复路径**：更新状态时合理指定，避免意外跳过节点。

---

## 5. 与全局概念的关联

- **中断 (Interrupts)**：中断依赖 checkpointer 暂停并保存状态，恢复时从同一检查点继续。
- **人机协同 (Human-in-the-loop)**：HITL 工作流直接基于 checkpointer 实现审查、批准和编辑。
- **短期记忆 (Short-term memory)**：`AgentState` 通过 checkpointer 持久化到线程，实现对话记忆。
- **长期记忆 (Long-term memory)**：Store 提供跨线程的持久记忆，由节点通过 `Runtime` 访问。
- **上下文工程**：Runtime 注入的 Store 和 Context 允许动态提示、消息注入、工具筛选。
- **流式传输 (Streaming)**：v2 格式的 `GraphOutput.interrupts` 依赖检查点传递中断负载。
- **子图 (Subgraphs)**：检查点命名空间区分父子图，子图中断时各自独立恢复。
- **容错**：超级步骤中部分节点失败时，成功节点的写入被保留，恢复时不会重复执行。

---

## 链接原文

### 语义检索（聚焦查询）

- `线程 thread_id checkpointer` → 线程与检查点关系
- `超级步骤 检查点 StateSnapshot` → 何时创建检查点
- `get_state get_state_history 重放` → 状态查询与回溯
- `update_state as_node` → 状态更新与分支
- `Store 命名空间 键 语义搜索 embed dims` → 记忆存储与检索
- `Runtime store asearch aput` → 节点内访问记忆
- `DeltaChannel 增量` → 检查点优化
- `JsonPlusSerializer pickle_fallback EncryptedSerializer` → 序列化与加密
- `SqliteSaver PostgresSaver CosmosDBSaver` → 后端选型

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 核心概念`、`### 获取状态`、`### 内存存储`、`### 语义搜索`），可用 `read_file` 精确定位对应章节。