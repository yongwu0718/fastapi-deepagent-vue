# LangGraph runtime (Pregel)

> 这是 LangGraph **运行时（Pregel）** 的胖索引，覆盖 Pregel 执行模型、Actor/Channel 体系、通道类型（LastValue、Topic、BinaryOperatorAggregate、DeltaChannel）以及高级 API 的生成关系。
> 阅读本文档可一次性掌握 LangGraph 运行时的全部概念及其关联，为理解图执行底层机制和优化检查点存储提供决策支撑。

---

## 概念全景

LangGraph 的运行时由 **Pregel** 实现，命名源自 Google 的大规模并行图计算模型。Pregel 管理所有图的执行，将 **Actors（节点）** 和 **Channels（通道）** 编织成批量同步并行 (BSP) 的执行流程。

| 维度               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **执行模型**       | 三步循环：**计划 (Plan)** → **执行 (Execution)** → **更新 (Update)**，直到无 Actor 被调度或达到最大步数 |
| **Actor**          | `PregelNode`，订阅 Channels，读取数据、执行逻辑、写入更新。本质是 LangChain `Runnable` |
| **Channel**        | Actors 间的通信管道，每个 Channel 有值类型、更新类型和更新函数，控制数据的存储与合并 |
| **高级 API**       | `StateGraph` (Graph API) 和 `@entrypoint` (Functional API) 编译后均生成 `Pregel` 实例 |
| **关键通道类型**   | `LastValue` (默认覆盖)、`Topic` (发布订阅/累积)、`BinaryOperatorAggregate` (二元聚合)、`DeltaChannel` (增量存储) |

核心决策点：**选择何种 Channel 类型以平衡性能与存储开销（特别是使用 DeltaChannel 优化长对话的检查点大小），以及理解 Pregel 的 BSP 模型对并发和状态一致性的影响**。

---

## 1. Pregel 执行模型

每个超级步骤包含三个阶段：

1. **计划**：确定本步要执行的 Actors。首步选择订阅 `input` 通道的 Actors；后续步骤选择订阅了上一步中发生更新的通道的 Actors。
2. **执行**：并行执行所有选定的 Actors，直到全部完成、某一失败或超时。本步内 Actors 产生的通道更新对彼此不可见。
3. **更新**：将所有 Actors 写入的值更新到对应 Channels，使下一步可见。

循环直到无 Actors 可执行或达到递归限制。

---

## 2. Actors

- 每个 Actor 是一个 `PregelNode`，实现 `Runnable` 接口。
- 订阅特定的 Channels，读取当前值，执行用户定义的函数，将结果写入指定的 Channels。
- 通过 `StateGraph` 定义的节点在编译后成为 `PregelNode`。

---

## 3. Channels

Channels 是 Actor 间通信的唯一机制。每个 Channel 定义了值如何被更新和累积。

### 3.1 LastValue
- 默认 Channel 类型。仅保留最后写入的值，直接覆盖。
- 适用于输入/输出值，或单步传递的数据。

### 3.2 Topic
- 可配置的发布订阅通道。支持累积 (`accumulate=True`) 或去重。
- 适合在多个 Actors 间广播消息或跨步骤累积值。

### 3.3 BinaryOperatorAggregate
- 持久化一个聚合值，每次更新时将当前值与新写入值通过二元运算符结合。
- 用于计算运行总和、集合合并等。

### 3.4 DeltaChannel (beta, 需 `langgraph>=1.2`)
- 仅存储每步的**增量写入**，而非完整累积值。适用于频繁追加且随时间增长巨大的通道（如对话消息列表），可显著减小检查点大小。
- 使用**批量 reducer**：接收当前状态和本步骤所有写入的列表，必须满足**结合律**。reducer 在重建值时调用，而非写入时。
- 可通过 `snapshot_frequency` 参数在每隔 K 步写入完整快照，以限制重建时的读取延迟。

| 通道类型                   | 写入行为                     | 读取内容                     | 适用场景                         |
| -------------------------- | ---------------------------- | ---------------------------- | -------------------------------- |
| `LastValue`                | 覆盖前值                     | 最后写入的值                 | 单值传递，输入输出               |
| `Topic` (accumulate=True)  | 追加到列表                   | 所有写入的累积列表           | 多 Actor 输出聚合                |
| `BinaryOperatorAggregate`  | 通过二元运算与当前值结合     | 聚合后的单一值               | 运行总和、计数器                 |
| `DeltaChannel`             | 仅存储每步写入的增量         | 通过重放增量重建值（可配置快照） | 长对话消息列表等大规模累积场景   |

---

## 4. 高级 API 与 Pregel 的关系

- `StateGraph` (Graph API) 和 `@entrypoint` (Functional API) 均是对 Pregel 的高级封装。
- 编译 `StateGraph` 或 `@entrypoint` 会生成 `Pregel` 实例，其中包含自动创建的 `PregelNode` 和一系列 Channels（包括 `LastValue`、`EphemeralValue` 和用于边路由的 `branch` 通道等）。
- 高级 API 隐藏了 Actor/Channel 的细节，但理解底层有助于性能调优和问题排查。

---

## 5. 关键约束与最佳实践

- **DeltaChannel 的 reducer 必须可结合**，且不应依赖副作用（如生成 UUID 或时间戳），因为 reducer 会在每次重建时重新运行。
- **在写入通道前为数据附加稳定标识**（如 ID），而非在 reducer 内部生成，以保证跨轮次的可追踪性。
- **权衡 `snapshot_frequency`**：值越大存储开销越低但读取越慢；设为 `None` 完全跳过快照，仅适合短线程或极少读取的场景。
- **理解 BSP 模型**：同一超级步骤内 Actors 的更新相互隔离，确保确定性执行，但也意味着步骤内无法实现 Actor 间的实时数据依赖。
- **检查通道类型**：编译后的 `graph.channels` 可检查实际使用的通道类型，用于验证设计是否符合预期。

---

## 6. 与全局概念的关联

- **图 (Graphs)**：`StateGraph` 编译为 `Pregel`，所有节点和边最终映射为 Actors 和 Channels。
- **持久化 (Persistence)**：Channels 的值被序列化到检查点；`DeltaChannel` 通过仅存储增量优化检查点大小。
- **中断 (Interrupts)**：中断依赖检查点保存状态；Pregel 的 BSP 模型确保中断发生在干净的超级步骤边界。
- **流式传输 (Streaming)**：`stream()` 方法基于超级步骤边界产出事件，与 Pregel 的三阶段模型对应。
- **容错 (Fault tolerance)**：重试和错误处理在 Actor 执行阶段生效；失败超级步骤的成功写入会被保留。

---

## 链接原文

### 语义检索（聚焦查询）

- `Pregel 计划 执行 更新 超级步骤` → 执行模型
- `PregelNode Actor channel 订阅` → Actor 机制
- `LastValue Topic BinaryOperatorAggregate` → 基础通道类型
- `DeltaChannel 批量 reducer 结合律 snapshot_frequency` → 增量通道
- `StateGraph 编译 Pregel channels` → 高级 API 关系
- `EphemeralValue branch channel` → 内部通道

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 概述`、`### LastValue`、`### DeltaChannel`、`## 高级 API`），可用 `read_file` 精确定位对应章节。