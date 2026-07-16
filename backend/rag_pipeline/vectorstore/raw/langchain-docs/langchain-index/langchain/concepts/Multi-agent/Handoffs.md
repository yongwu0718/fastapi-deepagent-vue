# Handoffs

> 这是 LangChain / LangGraph 多智能体系统中 **Handoffs（交接）** 模式的胖索引，覆盖状态驱动行为、单智能体中间件实现、多智能体子图实现、上下文工程、性能特征与最佳实践。
> 阅读本文档可一次性掌握交接模式的全部概念及其关联，为构建具有动态控制流的多智能体应用提供决策支撑。

---

## 概念全景

交接模式通过工具调用更新一个持久化的状态变量（如 `current_step` 或 `active_agent`），系统读取该变量来动态切换当前智能体的行为或直接路由到另一个智能体。它天然支持顺序约束和多轮对话状态保持。

| 维度               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **核心机制**       | 工具返回 `Command`，更新状态变量并选择下一步执行节点或动态配置 |
| **状态持久化**     | 必须配置 Checkpointer，确保状态跨轮次保留                   |
| **实现方式**       | 单智能体 + 中间件（动态提示/工具切换）或多智能体子图 + `Command.PARENT` |
| **关键组件**       | `ToolMessage`（完成 LLM 工具调用闭环）、`AIMessage`（传递控制权时保留消息配对） |
| **适用场景**       | 多阶段对话流、需顺序解锁能力的客户支持、不同专业智能体间的直接交互 |

核心决策点：**选用单智能体中间件还是多智能体子图、如何控制交接时的消息传递（全量历史/过滤/摘要）、如何设计状态变量来驱动行为变化**。

---

## 1. 单智能体中间件实现

一个智能体通过中间件根据状态动态切换系统提示和可用工具。工具更新状态变量触发转换。

- **状态定义**：在 `AgentState` 中新增 `current_step` 等字段，作为行为切换的依据。
- **工具**：返回 `Command`，其中包含 `ToolMessage`（必须包含 `tool_call_id`）和更新的状态变量。
- **中间件**：使用 `@wrap_model_call` 拦截每次模型调用，根据 `current_step` 从配置映射中选取对应的提示和工具，覆盖到请求中。
- **优点**：结构简单，消息历史自然流动，无需手动管理上下文。

```python
# 状态
class SupportState(AgentState):
    current_step: str = "triage"
    warranty_status: str | None = None

# 中间件
@wrap_model_call
def apply_step_config(request: ModelRequest, handler):
    step = request.state.get("current_step", "triage")
    config = configs[step]
    request = request.override(system_prompt=config["prompt"].format(**request.state), tools=config["tools"])
    return handler(request)
```

---

## 2. 多智能体子图实现

不同的智能体作为独立图节点存在，交接工具通过 `Command(goto=..., graph=Command.PARENT)` 在节点间导航。

- **工具**：获取触发交接的 `AIMessage`，构造对应的 `ToolMessage`，使用 `Command.PARENT` 跳转到目标节点，更新 `active_agent`。
- **节点**：每个节点调用对应智能体的 `invoke`。
- **路由**：通过条件边读取 `active_agent` 或检查最后一条消息是否为无工具调用的 `AIMessage` 来决定继续交接或结束。
- **上下文工程**：交接时只传递关键的 `AIMessage` 和 `ToolMessage` 对，避免传递完整子智能体历史，防止上下文膨胀和混乱。

```python
@tool
def transfer_to_sales(runtime: ToolRuntime) -> Command:
    last_ai_message = next(msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage))
    transfer_message = ToolMessage(content="Transferred to sales agent", tool_call_id=runtime.tool_call_id)
    return Command(
        goto="sales_agent",
        update={"active_agent": "sales_agent", "messages": [last_ai_message, transfer_message]},
        graph=Command.PARENT,
    )
```

**何时使用子图**：仅当需要定制化智能体实现（如图节点内部包含反思、检索步骤的复杂图）时才使用多智能体子图；否则单智能体中间件更简洁。

---

## 3. 上下文工程要点

- **消息配对完整性**：交接时必须包含触发交接的 `AIMessage` 和对应的 `ToolMessage`，否则接收方会看到不完整的对话历史。
- **选择性上下文传递**：通常只传递交接对，而非完整子智能体历史；如需额外上下文，可在 `ToolMessage` 内容中总结子智能体的工作。
- **返回用户控制权**：最终响应必须是 `AIMessage`，以向 UI 发出智能体已完成本轮工作的信号。
- **Token 效率**：随着对话变长，总结和选择性传递比全量历史更经济。

---

## 4. 与全局概念的关联

- **多智能体系统 (Multi-agent)**：交接是五种核心模式之一，适用于需要顺序执行和直接用户交互的场景。
- **子图 (Subgraphs)**：多智能体子图实现直接映射到 LangGraph 子图机制，`Command.PARENT` 实现跨层导航。
- **工具 (Tools)**：交接工具是普通工具，但通过返回 `Command` 来同时更新状态和控制流。
- **中间件 (Middleware)**：单智能体交接利用 `@wrap_model_call` 实现动态提示和工具切换，是上下文工程的核心实现。
- **检查点 (Checkpointer)**：交接依赖状态持久化，必须配置 Checkpointer（如 `InMemorySaver` 或 `PostgresSaver`）。
- **消息 (Messages)**：`ToolMessage` 和 `AIMessage` 的正确配对是交接有效性的基础。
- **性能**：交接在重复请求中比无状态模式节省 40-50% 模型调用次数。

---

## 链接原文

### 语义检索（聚焦查询）

- `交接 handoffs 状态驱动 Command` → 交接机制总览
- `单智能体 中间件 wrap_model_call 动态配置` → 中间件实现
- `多智能体子图 Command.PARENT transfer_to` → 子图实现
- `ToolMessage tool_call_id 消息配对` → 消息完整性
- `上下文工程 选择性传递 总结` → 上下文管理
- `交接性能 重复请求 调用次数` → 性能对比

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 基本实现`、`### 带中间件的单个 agent`、`### 多 agent 子图`、`### 上下文工程`），可用 `read_file` 精确定位对应章节。