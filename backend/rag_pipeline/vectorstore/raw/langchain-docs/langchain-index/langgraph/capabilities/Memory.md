# Memory

> 这是 LangGraph 中**记忆 (Memory)** 的胖索引，覆盖短期记忆与长期记忆的配置、管理策略（修剪、删除、总结、检查点操作）、语义搜索集成以及生产化部署。
> 阅读本文档可一次性掌握记忆体系的全部概念及其关联，为构建有状态、可跨会话持久化的 Agent 提供决策支撑。

---

## 概念全景

记忆分为两个层次：**短期记忆**（线程级，通过 Checkpointer 持久化对话历史）与**长期记忆**（跨线程/会话，通过 Store 持久化任意数据，支持语义搜索）。两者共同使 Agent 既能跟踪当前对话，又能跨会话累积知识。

| 维度                 | 短期记忆 (Short-term)                                        | 长期记忆 (Long-term)                                          |
| -------------------- | ------------------------------------------------------------ | ------------------------------------------------------------- |
| **存储机制**         | Checkpointer（`InMemorySaver`、`PostgresSaver`、`MongoDBSaver`） | Store（`InMemoryStore`、`PostgresStore` 等）                  |
| **作用范围**         | 单个线程 (`thread_id`)                                       | 跨线程/跨会话，按命名空间与键组织                             |
| **核心操作**         | 自动保存状态快照；通过 `get_state`、`get_state_history` 查看；通过 `RemoveMessage` 等管理 | `store.put`、`store.get`、`store.search`、`store.aput` 等     |
| **管理策略**         | 修剪消息（`trim_messages`）、删除消息（`RemoveMessage`）、总结消息、管理检查点 | 语义搜索（配置嵌入）、按需写入/读取                           |
| **启用方式**         | `graph.compile(checkpointer=...)`                             | `graph.compile(store=...)`                                    |
| **在生产环境中**     | `PostgresSaver`、`MongoDBSaver`、`AsyncPostgresSaver` 等      | `PostgresStore`、`MongoDBStore`、`RedisStore` 等               |

核心决策点：**选择何种 Checkpointer / Store 后端、如何设计命名空间以隔离用户或租户、是否启用语义搜索及如何配置嵌入、何时触发修剪/总结/删除以控制上下文长度、如何组织长期记忆的读写粒度**。

---

## 1. 短期记忆配置

### 基础启用

提供 checkpointer 并指定 `thread_id`：

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
graph.invoke({"messages": [{"role": "user", "content": "hi"}]}, {"configurable": {"thread_id": "1"}})
```

生产环境使用持久化后端：
- `PostgresSaver` / `AsyncPostgresSaver`
- `MongoDBSaver` / `AsyncMongoDBSaver`
- `SqliteSaver` / `AsyncSqliteSaver`

子图自动继承父图的 checkpointer；也可为子图单独配置 `checkpointer=True` 以启用中断支持等。

### 线程状态管理

- `graph.get_state(config)` 获取最新检查点快照（`StateSnapshot`）。
- `list(graph.get_state_history(config))` 查看线程所有检查点，按时间倒序。
- 可删除指定线程的所有检查点：`checkpointer.delete_thread(thread_id)`。

---

## 2. 长期记忆配置

### 基础启用

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
graph = builder.compile(store=store)
```

节点内通过 `Runtime[Context]` 自动注入 store：

```python
async def call_model(state: MessagesState, runtime: Runtime[Context]):
    memories = await runtime.store.asearch(namespace, query=..., limit=3)
    await runtime.store.aput(namespace, str(uuid.uuid4()), {"data": "..."})
```

需要先定义 `context_schema`，并在调用时传入 `context` 提供用户 ID 等用于命名空间。

### 生产环境

使用 `PostgresStore`、`MongoDBStore`、`RedisStore` 等持久化 store。推荐在部署前运行 `store.setup()` 进行迁移。

### 语义搜索

配置嵌入和维度即可启用：

```python
from langchain.embeddings import init_embeddings

store = InMemoryStore(
    index={
        "embed": init_embeddings("openai:text-embedding-3-small"),
        "dims": 1536,
    }
)
```

之后可通过 `store.search(namespace, query=..., limit=...)` 进行语义检索，或通过 `runtime.store.asearch` 在节点内使用。

---

## 3. 管理短期记忆容量

当对话历史超出 LLM 上下文窗口时，需要主动压缩。

| 策略       | 方法                                                         | 持久性     |
| ---------- | ------------------------------------------------------------ | ---------- |
| **修剪**   | 使用 `trim_messages` 按 token 数保留最后 N 条消息，可指定策略和边界角色 | 瞬态       |
| **删除**   | 返回 `RemoveMessage(id=...)` 或 `RemoveMessage(id=REMOVE_ALL_MESSAGES)` 从状态中永久移除消息 | 持久化     |
| **总结**   | 自定义节点生成摘要，存入扩展的 `summary` 字段，并删除旧消息；也可使用 `langmem.short_term.SummarizationNode` 配合 `RunningSummary` | 持久化     |

### 修剪示例

```python
from langchain_core.messages.utils import trim_messages, count_tokens_approximately

messages = trim_messages(
    state["messages"], strategy="last", token_counter=count_tokens_approximately,
    max_tokens=128, start_on="human", end_on=("human", "tool")
)
```

### 删除示例

```python
from langchain.messages import RemoveMessage
# 删除最早两条
return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}
# 删除全部
return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}
```

删除后需保证消息序列有效（如以 `user` 开头，`tool` 紧跟 tool_call）。

### 总结示例

扩展 `MessagesState` 增加 `summary` 字段；编写 `summarize_conversation` 节点，使用现有摘要作为上下文生成新摘要，并删除旧消息。也可使用 `SummarizationNode` 与 `RunningSummary` 实现自动管理。

---

## 4. 数据库管理

所有持久化后端通常提供 `setup()` 方法用于运行迁移。应在部署前执行，或作为服务器启动步骤之一。具体实现参考对应库文档。

---

## 5. 与全局概念的关联

- **持久化 (Persistence)**：记忆的底层基础，checkpointer 和 store 都是持久化的一部分。
- **上下文工程**：短期记忆的消息历史是模型上下文的核心来源；长期记忆中的偏好、知识可动态注入系统提示或消息。
- **工具 (Tools)**：工具通过 `ToolRuntime` 访问 store，实现记忆读写。
- **流式传输**：记忆状态的变化可通过 `updates` 模式或 `values` 模式流式观察。
- **人机协同**：依赖 checkpointer 持久化状态，实现暂停审查。
- **容错**：重试和错误处理基于检查点恢复。
- **检查点操作**：提供了查看状态历史、重放、分支等高级调试能力。

---

## 链接原文

### 语义检索（聚焦查询）

- `短期记忆 checkpointer thread_id InMemorySaver` → 基本启用
- `PostgresSaver MongoDBSaver 生产` → 生产 checkpointer
- `长期记忆 InMemoryStore store compile Runtime` → 长期记忆配置
- `语义搜索 embed dims index` → 启用语义检索
- `trim_messages count_tokens_approximately strategy` → 修剪策略
- `RemoveMessage REMOVE_ALL_MESSAGES 删除` → 删除消息
- `SummarizationNode RunningSummary 总结` → 自动总结
- `get_state get_state_history delete_thread` → 状态查看与清理
- `store.setup 迁移` → 数据库初始化

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 添加短期记忆`、`### 在子图中使用`、`## 添加长期记忆`、`### 修剪消息`），可用 `read_file` 精确定位对应章节。