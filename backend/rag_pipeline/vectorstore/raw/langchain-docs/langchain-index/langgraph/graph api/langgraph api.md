# Graphs

> 这是 LangGraph 中**图（Graphs）**的胖索引，覆盖状态定义与 Reducer、节点与边的类型、`Command` 与 `Send` 原语、运行时上下文、递归限制及图迁移策略。
> 阅读本文档可一次性掌握图建模的全部概念及其关联，为设计健壮、可扩展的 Agent 工作流提供决策支撑。

---

## 概念全景

LangGraph 将 Agent 工作流建模为由**状态 (State)**、**节点 (Nodes)** 和**边 (Edges)** 构成的有向图。节点负责工作（逻辑与副作用），边决定下一步做什么（路由）。图以离散的超级步骤 (super-steps) 运行，并行节点属于同一超级步骤，所有节点变为 inactive 时图执行终止。

| 组件               | 职责                                                         | 关键子类 / 机制                                      |
| ------------------ | ------------------------------------------------------------ | ---------------------------------------------------- |
| **State**          | 共享数据结构，表示应用当前快照                               | Schema（`TypedDict`、Pydantic、dataclass）、Reducer   |
| **Nodes**          | 封装 Agent 逻辑的 Python 函数，接收 state、config、runtime   | 普通节点、`START`、`END`、节点缓存                   |
| **Edges**          | 根据当前状态决定下一个执行的节点                             | 普通边、条件边、入口点、条件入口点                   |
| **Send**           | 动态并行分发：从条件边返回 `Send` 对象，为每个目标携带不同状态 | map-reduce 模式                                      |
| **Command**        | 多功能控制原语：在单个步骤中结合状态更新与路由、从工具控制流、恢复中断 | `update`、`goto`、`graph`、`resume`                  |

图编译时进行结构校验，并指定运行时参数（checkpointer、断点、缓存等）。编译是使用图的强制步骤。

核心决策点：**选择何种 State 模式及 Reducer、如何设计节点粒度和路由逻辑、何时使用 `Command` 替代条件边、如何管理递归深度和运行时上下文**。

---

## 1. State

### Schema 定义

- 推荐使用 `TypedDict`；需要默认值时用 `dataclass`；需要递归验证时用 Pydantic `BaseModel`（注意性能开销）。
- 图默认具有相同的输入和输出模式；可通过 `input_schema` / `output_schema` 显式指定不同的输入/输出模式。
- 节点可以声明额外的私有状态通道（`PrivateState`），用于内部通信而不暴露给图的输入/输出。

### Reducer

每个状态键有独立的 reducer，决定更新如何合并。无显式 reducer 时默认覆盖。

| Reducer 类型        | 行为示例                                                     |
| ------------------- | ------------------------------------------------------------ |
| 默认覆盖            | `{"bar": ["bye"]}` 直接替换原值                              |
| `operator.add`      | `{"bar": ["bye"]}` 追加到原列表 → `["hi", "bye"]`            |
| `add_messages`      | 专用于消息列表：按 ID 更新已有消息，新消息追加；自动反序列化 |
| `Overwrite`         | 绕过 reducer 强制覆盖                                        |

### 消息状态

- `MessagesState` 是预构建状态，包含 `messages` 键（`AnyMessage` 列表 + `add_messages` reducer），可直接子类化扩展。
- 消息序列化：支持 LangChain 消息对象或字典格式的混合输入，自动反序列化。

---

## 2. Nodes

节点函数签名：`(state: State, config: RunnableConfig, runtime: Runtime) -> dict | Command`。

- 通过 `add_node(name, func)` 注册。
- 特殊节点：`START`（用户输入入口）、`END`（终止节点）。
- **节点缓存**：通过 `cache_policy=CachePolicy(ttl=...)` 启用，`InMemoryCache` 用于开发，生产可用持久化缓存。

---

## 3. Edges

| 边类型         | 方法                        | 说明                                                   |
| -------------- | --------------------------- | ------------------------------------------------------ |
| 普通边         | `add_edge(A, B)`            | 固定路由，A 后总是执行 B                               |
| 条件边         | `add_conditional_edges(A, fn, mapping?)` | fn 返回节点名或列表，可并行执行多个目标；可提供映射字典 |
| 入口点         | `add_edge(START, A)`        | 从 START 出发的普通边即入口点                          |
| 条件入口点     | `add_conditional_edges(START, fn)` | 根据初始状态动态选择首个节点                       |

- 同一节点**不应混合**普通边和动态路由（`Command` 或条件边），避免意外并行执行。

---

## 4. Send

从条件边返回 `[Send("node", state), ...]` 实现 map-reduce 模式：对列表中每个元素动态创建并行任务，每个任务携带独立的状态。目标节点数量可运行时确定。

---

## 5. Command

| 参数 / 模式       | 用途                                                         |
| ----------------- | ------------------------------------------------------------ |
| `update`          | 应用状态更新                                                 |
| `goto`            | 导航到特定节点（类似条件边，但允许同步更新状态）             |
| `graph`           | 在子图内导航到父图节点 (`Command.PARENT`)                     |
| `resume`          | 输入给 `invoke`/`stream`，恢复中断并提供返回值               |

- **从节点返回**：`Command(update=..., goto=...)` 同时更新状态和路由。必须添加 `Command[Literal["target_node"]]` 返回类型注释。
- **从工具返回**：工具内同样支持 `Command`，可结合状态更新与流程控制。
- **恢复中断**：`Command(resume=value)` 是中断后继续执行的唯一正确方式；不要用 `Command(update=...)` 作为普通输入来继续对话（应使用普通字典）。
- **子图导航**：子图内节点通过 `Command(goto="...", graph=Command.PARENT)` 跳转到父图节点；更新跨层共享键时必须为父图对应键定义 reducer。

---

## 6. 运行时上下文

- 通过 `context_schema` 定义运行时上下文（如 LLM 提供商、数据库连接），通过 `Runtime` 在节点内访问。
- `invoke` 时传入 `context={...}` 提供具体值。

---

## 7. 递归限制

- 默认递归限制 1000 步，可通过 `config={"recursion_limit": N}` 自定义。
- `config["metadata"]["langgraph_step"]` 可在节点内访问当前步数。
- **主动处理**：使用 `RemainingSteps` 托管值在限制前进行优雅降级（推荐）。
- **被动处理**：捕获 `GraphRecursionError`，但图执行会终止。

### 主动 vs 被动

| 方法                  | 检测时机     | 处理方式           | 优点                                 |
| --------------------- | ------------ | ------------------ | ------------------------------------ |
| 主动 (`RemainingSteps`) | 达到限制前   | 条件路由、部分结果 | 优雅完成、可保存中间状态、更好 UX    |
| 被动 (`try/catch`)    | 超过限制后   | 外部捕获           | 实现简单、无需修改图逻辑             |

---

## 8. 图迁移

- 已完成线程可任意更改拓扑（增删改节点/边）。
- 中断线程支持除删除/重命名节点外的拓扑更改。
- 状态键可安全增删；重命名或类型不兼容更改可能丢失已保存状态。

---

## 9. 关键约束与最佳实践

- **编译是必须的**：未编译的图无法使用，编译时进行基本结构检查并指定运行时参数。
- **Reducer 选择**：消息列表必须用 `add_messages`，否则覆盖导致历史丢失。
- **路由单一性**：每个节点只使用一种路由机制（普通边、条件边或 `Command`），避免非确定性。
- **`Command` 类型注解**：从节点返回 `Command` 时必须添加 `Command[Literal[...]]` 返回类型。
- **对话继续用普通字典**：不要用 `Command(update=...)` 作为输入，应使用普通输入字典。
- **子图跨层更新**：父图对应键必须定义 reducer。
- **缓存策略**：对昂贵且幂等的节点启用缓存以提升性能。
- **递归处理**：推荐在图中主动监控 `RemainingSteps` 实现优雅降级。

---

## 10. 与全局概念的关联

- **持久化 (Persistence)**：图编译时指定 checkpointer，使状态可保存、恢复、重放。
- **流式传输 (Streaming)**：`stream()` 方法基于图的超级步骤边界输出事件。
- **中断 (Interrupts)**：`interrupt()` 暂停节点执行，通过 `Command(resume=...)` 恢复。
- **子图 (Subgraphs)**：子图作为节点添加到父图，`Command.PARENT` 实现跨层导航。
- **容错 (Fault tolerance)**：重试、超时和错误处理均在节点级别配置。
- **记忆 (Memory)**：短期记忆通过 `MessagesState` 的 `messages` 键实现；长期记忆通过 `Runtime.store` 访问。
- **运行时上下文**：与 `create_agent` 的 `context_schema` 对应，为图注入依赖。

---

## 链接原文

### 语义检索（聚焦查询）

- `State TypedDict reducer add_messages` → 状态定义与消息 reducer
- `add_node add_edge add_conditional_edges` → 节点与边 API
- `Command update goto graph resume` → Command 四种模式
- `Send map-reduce 动态并行` → 动态分发
- `节点缓存 CachePolicy ttl InMemoryCache` → 缓存机制
- `RemainingSteps 递归限制 GraphRecursionError` → 递归处理
- `context_schema Runtime invoke context` → 运行时上下文
- `图迁移 状态键 节点 删除 重命名` → 版本迁移规则

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## State`、`### Reducers`、`### Command`、`### 递归限制`），可用 `read_file` 精确定位对应章节。