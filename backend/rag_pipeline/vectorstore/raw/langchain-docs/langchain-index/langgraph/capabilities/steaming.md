# Streaming

> 这是 LangGraph 中**流式传输（Streaming）**的胖索引，覆盖 v2 统一格式、七种流模式、子图输出、高级用法（任意 LLM 集成、标签过滤、禁用流式）及迁移指南。
> 阅读本文档可一次性掌握 LangGraph 流式体系的全部概念及其关联，为构建响应迅速的实时交互应用提供决策支撑。

---

## 概念全景

LangGraph 通过 `stream()` / `astream()` 方法提供实时更新，逐步展示输出以改善 LLM 延迟下的用户体验。v2 版本提供了统一的 `StreamPart` 字典格式，无论使用何种流模式组合、是否包含子图，输出结构始终一致。

| 流模式            | 类型                       | 提供的能力                                         |
| ----------------- | -------------------------- | -------------------------------------------------- |
| `values`          | `ValuesStreamPart`         | 每一步之后的完整状态快照                           |
| `updates`         | `UpdatesStreamPart`        | 每一步之后的状态更新（仅变更部分）                 |
| `messages`        | `MessagesStreamPart`       | LLM 调用的 token 级输出（含元数据，可按标签/节点过滤） |
| `custom`          | `CustomStreamPart`         | 节点或工具通过 `get_stream_writer` 发出的自定义数据 |
| `checkpoints`     | `CheckpointStreamPart`     | 检查点事件（需 checkpointer）                      |
| `tasks`           | `TasksStreamPart`          | 任务开始/结束事件（含结果和错误，需 checkpointer）  |
| `debug`           | `DebugStreamPart`          | 组合 `checkpoints` + `tasks` + 附加元数据          |

v2 格式的 `StreamPart` 结构：`{"type": ..., "ns": (), "data": ...}`，支持按 `type` 进行类型收窄，`ns` 标识子图来源（根图为空元组）。

核心决策点：**选择哪些流模式组合、是否启用子图输出、如何通过标签或节点过滤消息流、何时使用 v2 格式**。

---

## 1. v2 流格式

使用 `version="v2"` 获得统一输出，每个 chunk 都是 `StreamPart` 字典。无论单模式、多模式、是否子图，格式一致，支持编辑器和类型检查器的完整类型收窄。

```python
for chunk in graph.stream(inputs, stream_mode=["updates", "custom"], version="v2"):
    if chunk["type"] == "updates":
        ...
    elif chunk["type"] == "custom":
        ...
```

`invoke()` 在 v2 下返回 `GraphOutput` 对象，包含 `.value`（最终状态）和 `.interrupts`（中断列表），将状态与中断元数据清晰分离。当状态是 Pydantic 或 dataclass 时，v2 自动强制转换为对应类型。

---

## 2. 流模式详解

### 状态流：`updates` 与 `values`

- `updates`：仅返回每个节点变更的键，同一步骤多个更新分别流式传输。
- `values`：返回每一步后的完整状态快照。

### LLM tokens：`messages`

从任何图组件（节点、工具、子图、任务）逐 token 流式传输 LLM 输出。即使节点内部使用 `invoke` 而非 `stream`，消息事件仍会发出。

- **按节点过滤**：通过 `metadata["langgraph_node"]` 字段筛选特定节点的 token。
- **按标签过滤**：初始化模型时设置 `tags=["joke"]`，在流中通过 `metadata["tags"]` 筛选。
- **省略特定流**：使用 `tags=["nostream"]` 标记模型，其 token 不会在 `messages` 模式中发出（适用于内部处理但不需要展示给客户端的调用）。

### 自定义数据：`custom`

节点或工具内通过 `get_stream_writer()` 发送任意键值对，流式传输时设置 `stream_mode="custom"` 捕获。支持进度更新、中间结果等。

### 检查点与任务：`checkpoints`、`tasks`、`debug`

- `checkpoints`：需要 checkpointer，每个事件与 `get_state()` 输出格式相同。
- `tasks`：需要 checkpointer，提供任务开始/结束事件，包含结果和错误。
- `debug`：组合 `checkpoints` + `tasks` + 附加元数据，提供最详尽的信息。

### 多模式组合

传入列表可同时流式传输多种模式，在循环中根据 `chunk["type"]` 分发处理。

---

## 3. 子图流式

在父图的 `stream()` 中设置 `subgraphs=True`，子图事件将以相同的 `StreamPart` 格式输出，通过 `chunk["ns"]` 字段标识来源。根图 `ns` 为空元组，子图为 `("node_name:uuid",)`。这使得前端可以按图层次渲染输出。

---

## 4. 高级用法

### 任意 LLM 集成

即使 LLM 未实现 LangChain 聊天模型接口，也可通过 `get_stream_writer()` + `stream_mode="custom"` 将自定义流式客户端的输出逐 chunk 推送到流中。

### 禁用特定模型的流式

初始化模型时设置 `streaming=False`（或 `disable_streaming=True`），该模型的 token 不会出现在 `messages` 流中。适用于混合使用支持/不支持流式的模型，或需要控制前端流量的场景。

### Python < 3.11 异步

- 必须显式将 `RunnableConfig` 传递给异步 LLM 调用（`model.ainvoke(..., config)`）。
- 不能在异步节点/工具中使用 `get_stream_writer`，需在函数签名中直接接收 `writer: StreamWriter` 参数。

---

## 5. v1 → v2 迁移

| 场景                     | v1                                  | v2                                                 |
| ------------------------ | ----------------------------------- | -------------------------------------------------- |
| 单模式                   | 原始数据                            | `StreamPart` 字典                                  |
| 多模式                   | `(mode, data)` 元组                 | 统一 `StreamPart`，按 `type` 过滤                  |
| 子图                     | `(namespace, data)` 元组            | 统一 `StreamPart`，通过 `ns` 字段标识              |
| 多模式+子图              | `(namespace, mode, data)` 三元组    | 统一 `StreamPart` 字典                             |
| `invoke()` 返回          | 普通字典（含 `__interrupt__` 键）   | `GraphOutput`（`.value` + `.interrupts`）          |
| Pydantic/dataclass 状态   | 返回普通字典                        | 自动强制转换为模型实例                             |

v1 的字典式访问（`result["key"]`、`result["__interrupt__"]`）在 `GraphOutput` 上仍可用但已弃用，建议迁移到 `.value` 和 `.interrupts`。

---

## 6. 与全局概念的关联

- **事件流式传输 (Event Streaming v3)**：`stream_events(version="v3")` 是更高层的封装，提供更友好的投影（如 `stream.messages`、`stream.tool_calls`）；`stream()` 是其底层基础。
- **子图 (Subgraphs)**：`subgraphs=True` 使子图内部事件可见，是实现可观察多智能体系统的关键。
- **中断 (Interrupts)**：v2 格式下中断通过 `GraphOutput.interrupts` 或 `values` 流的 `interrupts` 字段获取，与状态清晰分离。
- **持久化 (Persistence)**：`checkpoints`、`tasks`、`debug` 模式依赖 checkpointer 提供检查点事件流。
- **工具 (Tools)**：工具内通过 `get_stream_writer` 推送自定义进度，通过 `custom` 模式流式输出。
- **模型 (Models)**：`messages` 模式直接消费模型 token；标签和 `nostream` 机制控制流式输出的粒度。

---

## 链接原文

### 语义检索（聚焦查询）

- `version="v2" StreamPart type ns data` → v2 格式
- `stream_mode updates values` → 状态流
- `stream_mode messages metadata langgraph_node tags nostream` → LLM token 流
- `stream_mode custom get_stream_writer` → 自定义数据流
- `subgraphs=True ns 字段` → 子图流式
- `stream_mode checkpoints tasks debug` → 检查点/任务/调试流
- `GraphOutput interrupts value` → v2 invoke 返回
- `任意 LLM custom stream_writer` → 非 LangChain 模型集成
- `Python 3.11 异步 config StreamWriter` → 异步兼容性

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 流模式`、`### LLM tokens`、`### 自定义数据`、`### 子图输出`、`## 迁移到 v2`），可用 `read_file` 精确定位对应章节。