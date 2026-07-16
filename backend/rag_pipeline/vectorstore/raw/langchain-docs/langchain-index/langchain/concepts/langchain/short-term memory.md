# 短期记忆 (Short-term memory)

> 这是 LangChain / Deep Agents 中**短期记忆**的胖索引，覆盖检查点持久化、状态管理、消息修剪/删除/总结策略，以及在工具、提示和中间件中访问与修改记忆的方法。
> 阅读本文档可一次性掌握短期记忆领域的全部概念及其关联，为构建多轮对话和上下文管理提供决策支撑。

---

## 概念全景

短期记忆让 Agent 在单线程（对话）内记住之前的交互。核心机制是通过**检查点器（Checkpointer）**将 Agent 状态持久化，使线程随时可恢复。

| 维度               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **存储位置**       | `AgentState`（默认包含 `messages` 列表，可扩展自定义字段）    |
| **持久化机制**     | Checkpointer（`InMemorySaver` 用于开发，`PostgresSaver` 等用于生产） |
| **生命周期**       | 同一 `thread_id` 内的所有回合，通过检查点跨回合持久化         |
| **管理策略**       | 修剪（保留最近 N 条）、删除（移除特定消息）、总结（用摘要替换历史） |
| **访问入口**       | 工具内通过 `ToolRuntime`，提示内通过 `dynamic_prompt`，中间件内通过 `@before_model` / `@after_model` |

核心决策点：**选择何种 Checkpointer、何时触发消息压缩策略、如何扩展 `AgentState` 来承载自定义记忆字段**，直接决定 Agent 的记忆能力和长对话的稳定性。

---

## 1. 基础配置

### 开发环境

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent("gpt-5.4", tools=[...], checkpointer=InMemorySaver())
agent.invoke({"messages": [{"role": "user", "content": "..."}]}, {"configurable": {"thread_id": "1"}})
```

### 生产环境

```python
from langgraph.checkpoint.postgres import PostgresSaver

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()
    agent = create_agent("gpt-5.4", tools=[...], checkpointer=checkpointer)
```

支持的持久化后端还包括 SQLite、Azure Cosmos DB 等。

---

## 2. 自定义状态（扩展记忆字段）

通过继承 `AgentState` 添加自定义字段，并存放在状态中随检查点持久化：

```python
class CustomAgentState(AgentState):
    user_id: str
    preferences: dict

agent = create_agent("gpt-5.4", tools=[...], state_schema=CustomAgentState, checkpointer=...)
agent.invoke({
    "messages": [{"role": "user", "content": "Hello"}],
    "user_id": "user_123",
    "preferences": {"theme": "dark"}
}, {"configurable": {"thread_id": "1"}})
```

---

## 3. 消息管理策略

当对话历史超出 LLM 上下文窗口时，需应用以下策略之一：

### 修剪（Trim）

使用 `@before_model` 中间件，保留系统消息和最近 N 条消息，丢弃中间部分：

```python
@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict | None:
    if len(state["messages"]) <= 3:
        return None
    # 保留首条 + 最后 3-4 条
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *new_messages]}
```

### 删除（Delete）

使用 `RemoveMessage` 删除特定消息或全部消息，必须在 `messages` 键使用 `add_messages` reducer 的状态中生效（默认 `AgentState` 已具备）：

```python
# 删除最早两条
{"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}

# 删除全部
{"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}
```

> 注意：删除后需保证消息历史符合 LLM provider 的要求（例如以 `user` 开头，`tool` 紧跟在包含 `tool_call` 的 `assistant` 之后）。

### 总结（Summarize）

使用内置 `SummarizationMiddleware`，根据 token 数量或消息数量触发，用模型生成的摘要替换旧消息：

```python
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-5.4",
    middleware=[SummarizationMiddleware(model="gpt-5.4-mini", trigger=("tokens", 4000), keep=("messages", 20))],
    ...
)
```

---

## 4. 访问与修改记忆

### 在工具中访问

```python
@tool
def get_user_info(runtime: ToolRuntime) -> str:
    return runtime.state["user_id"]  # 读取状态
```

### 从工具写入（更新状态）

通过返回 `Command` 来修改状态，同时可附带 `ToolMessage` 向模型反馈：

```python
@tool
def update_user_info(runtime: ToolRuntime[CustomContext, CustomState]) -> Command:
    return Command(update={"user_name": name, "messages": [ToolMessage("...", tool_call_id=runtime.tool_call_id)]})
```

### 在提示中访问

使用 `@dynamic_prompt` 中间件根据状态或上下文生成动态系统提示：

```python
@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context["user_name"]
    return f"You are a helpful assistant. Address the user as {user_name}."
```

### 在模型之前（`@before_model`）

在调用模型前检查/修改状态，典型用途是修剪消息（见上文示例）。执行顺序：`before_model` → `model`，且 tools 之后会再次经过 `before_model`。

### 在模型之后（`@after_model`）

在模型返回后检查/修改状态，典型用途是过滤敏感内容：

```python
@after_model
def validate_response(state: AgentState, runtime: Runtime) -> dict | None:
    if "password" in state["messages"][-1].content:
        return {"messages": [RemoveMessage(id=last_message.id)]}
    return None
```

执行顺序：`model` → `after_model` → tools / END。

---

## 5. 关键约束与最佳实践

- **始终为生产配置持久化 Checkpointer**（Postgres、SQLite 等），`InMemorySaver` 仅用于开发和测试。
- **消息删除/修剪后必须维持消息历史的有效性**，特别是 `tool_call` 与 `ToolMessage` 的配对关系和首条消息角色。
- **当多个工具可能并发更新同一状态字段时，为该字段定义 reducer**，避免冲突。
- **使用 `SummarizationMiddleware` 而非简单截断**，以在压缩上下文的同时保留关键信息，但需留意摘要模型调用会引入额外延迟和成本。
- **扩展 `AgentState` 时，自定义字段应与对话逻辑紧密相关**，避免将大量静态配置放入状态中（静态配置更适合通过 `Context` 传递）。

---

## 6. 与全局概念的关联

- **长期记忆（StoreBackend）**：短期记忆线程隔离、同线程持久；长期记忆跨线程/跨会话持久。两者通过 `ToolRuntime` 在工具中分别以 `runtime.state` 和 `runtime.store` 访问。
- **消息（Messages）**：短期记忆的内容载体。所有修剪、删除、总结操作均直接作用于消息列表。
- **工具（Tools）**：工具通过 `ToolRuntime` 读写短期记忆，并可通过返回 `Command` 更新状态，实现工具与记忆的双向交互。
- **上下文压缩**：总结中间件（`SummarizationMiddleware`）即是一种上下文压缩的具体实现，修剪和删除也是轻量级的压缩手段。
- **检查点器（Checkpointer）**：是短期记忆的底层基础设施，也用于 graph 执行的中断和恢复。

---

## 链接原文

### 语义检索（聚焦查询）

使用以下关键词组合可精准命中原始文档中的对应章节：

- `checkpointer InMemorySaver PostgresSaver` → 基础配置
- `AgentState 自定义状态 state_schema` → 扩展记忆字段
- `RemoveMessage REMOVE_ALL_MESSAGES` → 删除消息
- `trim_messages before_model` → 修剪消息模式
- `SummarizationMiddleware trigger keep` → 总结消息配置
- `ToolRuntime state 工具访问` → 工具中访问记忆
- `dynamic_prompt ModelRequest` → 提示中访问状态
- `after_model validate_response` → 模型后处理

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 使用方法`、`### 修剪消息`、`### 在 tool 中读取短期记忆`），可用 `read_file` 精确展开对应章节。