# 单元测试

> 使用 fake chat models 和 in-memory persistence，在不进行 API 调用的情况下测试 agent 逻辑。

Unit tests 以隔离的方式运行 agent 中规模较小、可确定的部分。用内存中的 fake（又名 fixture）替代真实的 LLM，您可以预先编排精确的响应（文本、tool calls 和错误），从而使测试快速、免费且无需 API 密钥即可重复进行。

## Mock chat model

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

## InMemorySaver checkpointer

为了在测试期间启用持久化，您可以使用 `InMemorySaver` checkpointer。这允许您模拟多轮对话，以测试依赖 state 的行为：

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model,
    tools=[],
    checkpointer=InMemorySaver()
)

# 第一次调用
agent.invoke(
    {"messages": [HumanMessage(content="I live in Sydney, Australia")]},
    config={"configurable": {"thread_id": "session-1"}}
)

# 第二次调用：第一条消息已被持久化（悉尼的位置信息），因此模型会返回 GMT+10 时间
agent.invoke(
    {"messages": [HumanMessage(content="What's my local time?")]},
    config={"configurable": {"thread_id": "session-1"}}
)
```

## 下一步

了解如何在 Integration testing 中使用真实的模型提供程序 API 来测试您的 agent。