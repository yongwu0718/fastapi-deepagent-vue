# 单元测试 (Unit Testing)

> 这是 LangChain Agent **单元测试** 的胖索引，覆盖使用模拟聊天模型和内存持久化隔离测试 Agent 逻辑的方法。
> 阅读本文档可快速掌握如何在不调用真实 API 的情况下，用确定性的 fake 响应验证 Agent 行为。

---

## 概念全景

单元测试的目标是将 Agent 的各个部分隔离运行，通过用内存中的模拟对象替代真实的 LLM 和存储，实现快速、可重复、无外部依赖的测试。

| 维度               | 描述                                                         | 关键工具                               |
| ------------------ | ------------------------------------------------------------ | -------------------------------------- |
| **模拟 LLM**       | 预先编排精确的文本、工具调用或错误响应，每次调用返回下一项   | `GenericFakeChatModel`                |
| **模拟持久化**     | 在内存中模拟检查点与长期记忆，支持多轮对话测试               | `InMemorySaver`、`InMemoryStore`       |
| **测试范围**       | 单个节点、工具、路由逻辑，或包含多轮交互的 Agent 执行路径     | `agent.invoke(...)`                   |

核心决策点：**如何编排模拟模型的响应序列、如何管理 thread_id 以模拟多轮对话、如何验证状态转换与工具调用**。

---

## 1. 模拟聊天模型

LangChain 提供了 `GenericFakeChatModel` 用于模拟文本响应。它接受一个响应迭代器（可以是 `AIMessage` 对象或字符串），每次调用会返回其中的下一个项。它同时支持常规用法和流式用法。

```python
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

model = GenericFakeChatModel(messages=iter([
    AIMessage(content="", tool_calls=[ToolCall(name="foo", args={"bar": "baz"}, id="call_1")]),
    "bar"
]))

model.invoke("hello")
# AIMessage(content='', ..., tool_calls=[{'name': 'foo', 'args': {'bar': 'baz'}, 'id': 'call_1', 'type': 'tool_call'}])
```

如果再次调用模型，它将返回迭代器中的下一个项：

```python
model.invoke("hello, again!")
# AIMessage(content='bar', ...)
```

---

## 2. 模拟持久化

使用 `InMemorySaver` 作为 checkpointer，在测试中启用线程级状态持久化，从而测试跨回合的记忆行为：

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model,
    tools=[],
    checkpointer=InMemorySaver()
)

# 第一轮：注入用户信息
agent.invoke(
    {"messages": [HumanMessage(content="I live in Sydney, Australia")]},
    config={"configurable": {"thread_id": "session-1"}}
)
# 第二轮：验证 Agent 记住了上一轮的悉尼位置
agent.invoke(
    {"messages": [HumanMessage(content="What's my local time?")]},
    config={"configurable": {"thread_id": "session-1"}}
)
```

- 通过相同的 `thread_id` 维持会话连续性。
- 可同样使用 `InMemoryStore` 来模拟长期记忆的读写。

---

## 3. 关键约束与最佳实践

- **响应序列要精确**：模拟模型的响应必须与预期的交互次数和顺序匹配，否则会抛出 `StopIteration`。
- **隔离副作用**：单元测试中不应有任何网络调用、文件读写或真实的外部依赖。
- **验证关键行为**：断言节点返回的状态更新、工具调用参数、消息内容以及路由路径。
- **管理 thread_id**：不同测试用例应使用不同的 `thread_id`，避免状态污染。

---

## 4. 与全局概念的关联

- **模型 (Models)**：单元测试用 `GenericFakeChatModel` 替代真实聊天模型，使测试确定化。
- **持久化 (Persistence)**：`InMemorySaver` 与 `InMemoryStore` 是测试短期和长期记忆的标准配置。
- **工具 (Tools)**：可结合模拟模型返回的工具调用，验证工具执行逻辑与状态更新。
- **中断 (Interrupts)**：通过编排模型输出中包含中断触发的响应，测试中断与恢复流程。
- **上下文工程**：验证动态提示、消息注入等中间件在模拟对话中的实际效果。

---

## 链接原文

### 语义检索（聚焦查询）

- `GenericFakeChatModel tool_call` → 模拟带工具调用的响应
- `InMemorySaver 多轮对话 thread_id` → 模拟持久化与记忆

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## Mock chat model`、`## InMemorySaver checkpointer`），可用 `read_file` 精确定位对应章节。