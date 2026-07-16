# 使用时间旅行 (Time Travel)

> 这是 LangGraph 中**时间旅行**的胖索引，覆盖重放（Replay）与分支（Fork）两大核心操作、与中断（Interrupts）的交互、子图场景下的行为差异以及最佳实践。
> 阅读本文档可一次性掌握时间旅行领域的全部概念及其关联，为调试、探索替代执行路径和构建灵活的人机协同工作流提供决策支撑。

---

## 概念全景

时间旅行基于 LangGraph 的检查点机制，允许从历史检查点**重放**（重新执行后续节点）或**分支**（修改状态后从该点创建新路径）。检查点之前的节点不会重新执行（结果已保存），检查点之后的节点会重新执行，包括 LLM 调用、API 请求和中断，可能产生不同结果。

| 操作               | 描述                                                         | 关键方法                                          |
| ------------------ | ------------------------------------------------------------ | ------------------------------------------------- |
| **重放 (Replay)**   | 从历史检查点配置直接调用图，重新执行后续节点                 | `graph.invoke(None, checkpoint_config)`            |
| **分支 (Fork)**     | 在历史检查点上调用 `update_state` 修改状态后创建新分支       | `graph.update_state(config, values, as_node=...)`  |
| **与中断的交互**   | 包含中断的节点在重放/分支时总会重新触发 `interrupt()`，需再次 `Command(resume)` | 正常使用 `Command` 恢复                            |
| **子图时间旅行**   | 默认子图作为单一超级步骤，仅可从父级时间旅行；子图启用自身 checkpointer 后可从子图内部节点级别时间旅行 | `checkpointer=True` + `get_state(subgraphs=True)` |

核心决策点：**从哪个检查点开始重放或分支、是否修改状态、何时显式指定 `as_node`、子图是否需要独立的检查点粒度**。

---

## 1. 重放 (Replay)

从历史检查点恢复执行，该点之后的节点会被重新执行（包括 LLM 调用、API 请求、中断），可能产生不同结果。

操作步骤：
1. 通过 `graph.get_state_history(config)` 获取历史检查点列表（按时间倒序）。
2. 筛选目标检查点（例如通过 `s.next` 判断后续节点）。
3. 使用该检查点的 `config` 调用 `graph.invoke(None, config)`。

```python
history = list(graph.get_state_history(config))
before_joke = next(s for s in history if s.next == ("write_joke",))
replay_result = graph.invoke(None, before_joke.config)
```

注意：从最终检查点（`next` 为空元组）重放是无操作的。

---

## 2. 分支 (Fork)

在历史检查点上修改状态，创建新分支并继续执行。`update_state` 不会回滚原有线程，原始历史保持不变。

基本流程：
1. 找到目标历史检查点。
2. 调用 `graph.update_state(checkpoint_config, values=..., as_node=...)` 获得新分支配置。
3. 使用该分支配置调用 `graph.invoke(None, fork_config)`。

```python
fork_config = graph.update_state(before_joke.config, values={"topic": "chickens"})
fork_result = graph.invoke(None, fork_config)
```

### `as_node` 参数

默认情况下 LangGraph 从检查点版本历史推断 `as_node`（通常正确）。在以下情况需显式指定：

- **并行分支**：同一步骤多个节点更新状态，无法自动推断（抛出 `InvalidUpdateError`）。
- **无执行历史**：在新线程上设置初始状态（常见于测试）。
- **跳过节点**：将 `as_node` 设为较晚的节点，使图认为该节点已执行过。

更新后执行从指定节点的后继节点恢复。

---

## 3. 与中断的交互

包含 `interrupt()` 的节点在重放或分支时**总是会重新触发中断**，需要再次使用 `Command(resume=...)` 恢复。这同样适用于多中断流程。

- 从中断之前的检查点重放/分支：节点重新执行，在 `interrupt()` 处再次暂停。
- 分支后可传入不同的恢复值，探索不同路径。
- 多个中断之间可进行分支：修改中间状态，保留已完成的回答，仅重新询问后续问题。

---

## 4. 子图时间旅行

子图的时间旅行行为取决于其是否拥有独立的 checkpointer。

### 默认（无独立 checkpointer）

子图继承父图 checkpointer，整个子图被视为**单一超级步骤**。仅可从父级检查点进行时间旅行，无法访问子图内部节点之间的检查点。从子图之前重放/分支会重新执行整个子图。

### 启用独立 checkpointer

为子图设置 `checkpointer=True` 后，子图每个步骤都会创建检查点。可通过 `graph.get_state(config, subgraphs=True)` 获取子图的内部检查点配置，然后从子图特定节点之间进行分支或重放。

```python
parent_state = graph.get_state(config, subgraphs=True)
sub_config = parent_state.tasks[0].state.config
fork_config = graph.update_state(sub_config, {"value": ["forked"]})
result = graph.invoke(None, fork_config)
```

这允许在子图内的中断之间进行精细化的时间旅行。

---

## 5. 关键约束与最佳实践

- **重放会重新触发副作用**：LLM 调用、API 请求、中断都会再次执行，可能产生不同结果和成本。
- **`update_state` 使用 reducer**：状态值通过该节点的 reducer（如 `add`）应用，可能累加而非覆盖。
- **并行分支时显式 `as_node`**：避免 `InvalidUpdateError`，确保执行从正确的后继节点恢复。
- **子图时间旅行粒度**：默认子图不可内部时间旅行；如需细粒度控制，为子图启用独立 checkpointer。
- **多中断分支**：可利用分支更改中间状态，只重新询问后续问题，避免重复填写整个表单。
- **历史不可变**：`update_state` 创建新分支，不修改原始检查点，原始执行历史完整保留。

---

## 6. 与全局概念的关联

- **持久化 (Persistence)**：时间旅行完全依赖检查点机制，所有重放和分支操作都基于持久化的状态快照。
- **中断 (Interrupts)**：中断节点在时间旅行中会重新触发，使人机协同工作流可被重放或分支，支持灵活的回溯审查。
- **记忆 (Memory)**：短期记忆（消息历史）作为状态的一部分被检查点保存，时间旅行时也会被重放或分支修改。
- **子图 (Subgraphs)**：子图的检查点配置直接影响时间旅行的粒度；独立 checkpointer 提供更细粒度的控制。
- **容错 (Fault tolerance)**：重放机制本身就是一种从失败点恢复执行的方式，与重试策略互补。

---

## 链接原文

### 语义检索（聚焦查询）

- `重放 replay get_state_history invoke None` → 基本重放
- `分支 fork update_state as_node` → 分支操作与参数
- `中断 interrupt 时间旅行 Command resume` → 中断交互
- `多个中断 之间 分支 ask_name ask_age` → 多中断场景
- `子图 subgraphs checkpointer=True get_state subgraphs=True` → 子图时间旅行

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 重放`、`## 分支`、`### 从特定节点`、`## 中断`、`## 子图`），可用 `read_file` 精确展开对应章节。