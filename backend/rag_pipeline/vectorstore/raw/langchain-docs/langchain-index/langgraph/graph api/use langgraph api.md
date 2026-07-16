# Use the graph API

> 这是 LangGraph **图 API 使用**的胖索引，覆盖状态定义与 reducer 机制、输入/输出模式、运行时配置、重试与缓存、节点序列与分支（并行、延迟、条件、Send）、循环与递归控制、Command 组合、异步执行及可视化。
> 阅读本文档可快速定位图 API 的使用模式与关键决策点，为编写健壮的 Agent 工作流提供操作指南。

---

## 概念全景

本文档是 LangGraph 图 API 的实操手册，展示了如何通过 `StateGraph` 构建、编译和运行图，以及如何利用 reducer、重试、缓存、并发控制等机制微调执行行为。

| 主题                   | 关键 API / 机制                                               | 用途                                                         |
| ---------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **状态定义**           | `TypedDict`、`Annotated`、`add_messages`、`MessagesState`、`Overwrite` | 定义图的数据结构，控制更新如何合并（追加、覆盖、消息 ID 感知） |
| **输入 / 输出模式**    | `input_schema`、`output_schema`、`PrivateState`              | 分离内部通信与对外接口，保护私有状态                         |
| **运行时配置**         | `context_schema`、`Runtime`、`context` 参数                   | 在调用时注入 LLM 提供商、系统消息等，避免污染状态            |
| **重试策略**           | `retry_policy=RetryPolicy(...)`、`runtime.execution_info`     | 自动重试失败节点，感知重试次数                               |
| **节点缓存**           | `cache_policy=CachePolicy(ttl=...)`、`InMemoryCache`         | 缓存昂贵节点的结果                                           |
| **序列与简写**         | `add_node` + `add_edge`、`.add_sequence()`                   | 快速构建线性步骤                                             |
| **分支**               | 普通边、`add_conditional_edges`、`defer=True`、`max_concurrency` | 实现并行、延迟汇聚、动态路由                                 |
| **Map-Reduce**         | `Send` API、`add_conditional_edges` 返回 `Send` 列表         | 对动态列表的每一项并行执行节点，结果合并                     |
| **循环**               | 条件边 + `END`、`recursion_limit`、`RemainingSteps`          | 创建循环工作流，通过递归限制或剩余步数优雅终止               |
| **Command**            | `Command(update=..., goto=..., graph=...)`                   | 在同一节点内组合状态更新与控制流，工具内更新状态             |
| **异步**               | `async def` 节点、`ainvoke`/`astream`                        | 提升 I/O 密集型并发性能                                      |
| **可视化**             | `get_graph().draw_mermaid_png()`、`draw_mermaid()`、Graphviz  | 调试与展示图结构                                             |

核心决策点：**如何设计状态模式与 reducer、何时使用私有状态和输入/输出模式、如何组合 Command 以合并更新与路由、如何控制循环终止和递归深度、是否启用节点缓存或重试**。

---

## 1. 状态定义与更新

### 基本模式
- `TypedDict` 定义状态，`Annotated` 指定 reducer。
- 默认覆盖；`operator.add` 追加；`add_messages` 处理消息 ID 与反序列化。
- `MessagesState` 是预构建状态，只包含 `messages` 键。

### `Overwrite`
- 绕过 reducer 强制替换值。同一超级步骤内只能有一个节点对同一键使用 `Overwrite`。

### 输入 / 输出模式
- `StateGraph(OverallState, input_schema=InputState, output_schema=OutputState)` 限制外部接口。
- 内部状态可包含私有数据（`PrivateState`），通过函数签名仅传递给需要它的节点。

### Pydantic 状态
- 支持 Pydantic `BaseModel`，输入时有运行时验证；输出为字典，不会自动转换回模型。
- 注意序列化：使用 `AnyMessage` 而非 `BaseMessage`。

---

## 2. 运行时配置

- 通过 `context_schema` 定义配置结构，节点内通过 `runtime.context` 访问。
- `invoke` 时传入 `context` 字典，可动态切换 LLM 提供商、系统消息等。

---

## 3. 重试与缓存

### 重试
- `add_node(..., retry_policy=RetryPolicy(max_attempts=..., retry_on=...))`。
- 默认重试除 `ValueError`、`TypeError` 等外的异常；HTTP 5xx 可重试。
- 节点内通过 `runtime.execution_info.node_attempt` 感知重试状态。

### 缓存
- `add_node(..., cache_policy=CachePolicy(ttl=...))`，编译时提供 `cache=InMemoryCache()`。

---

## 4. 构建步骤

### 序列
- 手动 `add_node` + `add_edge`，或简写 `.add_sequence([...])`。

### 分支
- **并行**：从同一节点添加多条出边，目标节点在同一超级步骤并发执行；使用 `operator.add` 累加结果。
- **延迟节点**：`add_node(..., defer=True)` 等待所有待处理任务完成后才执行。
- **条件分支**：`add_conditional_edges`，路由函数返回节点名或列表。

### Map-Reduce
- 条件边返回 `[Send("node", {"key": val}), ...]`，每个 `Send` 创建一个带有特定状态的任务，结果通过 reducer 合并。

### 循环
- 条件边控制何时返回 `END`。
- `recursion_limit` 设置最大超级步数，超限引发 `GraphRecursionError`。
- `RemainingSteps` 托管值用于在限制到达前主动降级。

---

## 5. Command 组合

- 从节点返回 `Command(update=..., goto=...)` 同时更新状态和路由。需要 `Command[Literal["target"]]` 类型注解。
- 在子图中导航到父图节点：`Command(..., graph=Command.PARENT)`。跨层更新共享键时必须为父图对应键定义 reducer。
- 从工具返回 `Command` 以更新状态（必须包含 `ToolMessage`）；推荐配合 `ToolNode` 使用。

---

## 6. 异步与可视化

### 异步
- 节点改为 `async def`，内部使用 `await`，调用使用 `ainvoke` / `astream`。

### 可视化
- `draw_mermaid()` 输出 Mermaid 语法；`draw_mermaid_png()` 生成 PNG（可选 Pyppeteer 或 Graphviz）。

---

## 链接原文

### 语义检索（聚焦查询）
- `定义状态 TypedDict reducer add_messages` → 状态核心
- `Overwrite 绕过 reducer` → 强制覆盖
- `输入模式 输出模式 input_schema output_schema` → I/O 分离
- `私有状态 PrivateState node 之间` → 内部通信
- `Pydantic 状态 BaseModel 验证` → 模型验证
- `context_schema Runtime context 参数` → 运行时配置
- `retry_policy RetryPolicy execution_info` → 重试
- `cache_policy CachePolicy InMemoryCache` → 缓存
- `add_sequence 简写` → 快速序列
- `并行 扇出 add_conditional_edges` → 分支与并行
- `defer=True 延迟节点` → 等待汇聚
- `Send map-reduce` → 动态分发
- `循环 recursion_limit RemainingSteps` → 循环控制
- `Command goto graph PARENT` → 组合控制流
- `异步 async def ainvoke` → 异步执行
- `draw_mermaid draw_mermaid_png` → 可视化

### 标题路径兜底
语义检索返回的片段均携带原文标题路径（如 `### 定义状态`、`### 使用 reducers 处理状态更新`、`### 使用 Overwrite 绕过 Reducers`、`## Map-Reduce 和 Send API`），可用 `read_file` 精确定位对应章节。