# 事件流式传输

> 从 LangChain agent 运行中流式传输实时更新

LangChain agents 构建于 LangGraph 之上，因此它们支持相同的流式传输栈，并提供了面向 agent 的 projections，用于 messages、tool calls、state 和自定义更新。

对于大多数应用和前端场景，请使用 **Event Streaming**，通过 `stream_events(..., version="v3")` 来实现。Event Streaming 返回一个带有类型化 projections 的 run 对象，因此每个 projection 都可以独立消费，而无需解析 stream-mode 元组。

```python 
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"It's always sunny in {city}!"


agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)

stream = agent.stream_events({
    "messages": [{"role": "user", "content": "What is the weather in SF?"}],
}, version="v3")

for message in stream.messages:
    for delta in message.text:
        print(delta, end="", flush=True)

final_state = stream.output
```

## 你可以流式传输的内容

| Projection            | 用途                                                      |
| --------------------- | ------------------------------------------------------- |
| `for event in stream` | 原始协议事件，包含完整 envelope，并可访问每个 channel。                    |
| `stream.messages`     | 模型 message 流，每个 LLM 调用对应一个。                             |
| `message.text`        | 一条 message 的文本 deltas 和最终文本。                            |
| `message.reasoning`   | 针对暴露推理内容的模型所提供的推理 deltas。                               |
| `message.tool_calls`  | Tool-call 参数 chunks 和已完成的 tool calls。                   |
| `message.output`      | 模型调用完成后的最终 message 对象。                                  |
| `stream.values`       | Agent state 快照。                                         |
| `stream.output`       | 最终 agent state。                                         |
| `stream.subgraphs`    | 嵌套图运行（sub-agents 和普通 subgraphs）。                        |
| `stream.extensions`   | 自定义 transformer projections。                            |
| `stream.tool_calls`   | Tool 执行生命周期，包括 inputs、output deltas、最终 output 和 errors。 |

`stream.messages` 生成 `ChatModelStream` 对象。每个 message 流暴露 `.text`、`.reasoning`、`.tool_calls` 和 `.output`。同步 projections 可迭代以获取实时 deltas，也可 drain 以获取最终值：使用 `str(message.text)` 获取最终文本，使用 `message.tool_calls.get()` 获取已完成的 tool calls。

## Agent messages

当你希望从每个 LLM 调用中获取模型输出时，请使用 `stream.messages`。

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
stream = agent.stream_events(input, version="v3")

for message in stream.messages:
    print(f"[{message.node}] ", end="")
    for delta in message.text:
        print(delta, end="", flush=True)

    full_message = message.output
    usage = full_message.usage_metadata
    if usage:
        print(usage)
```

`message.output` 为你提供最终完成的 AI message，包括特定于提供商的 content blocks。在 TypeScript 中，当你只需要 token 计数或其他 usage metadata 时，可以使用 `message.usage`；在 pythonthon 中，从 `message.output.usage_metadata` 读取 usage 信息。

## 推理内容

Reasoning 内容使用与 text 内容相同的形态，但仅当所选模型发出 reasoning blocks 时才可用。

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
stream = agent.stream_events(input, version="v3")

for message in stream.messages:
    for delta in message.reasoning:
        print(f"[thinking] {delta}", end="", flush=True)

    for delta in message.text:
        print(delta, end="", flush=True)
```

有关模型配置的详细信息，请参阅 reasoning 指南 和你的模型提供商的集成页面。

## Tool calls

有两种有用的 tool-call projections：

* `message.tool_calls` 在模型生成 tool call 时流式传输 tool-call 参数 chunks。
* `stream.tool_calls` 在 tool call 开始后，流式传输 tool 执行的生命周期。

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
stream = agent.stream_events(input, version="v3")

for message in stream.messages:
    for chunk in message.tool_calls:
        print(f"tool call chunk: {chunk}")

    finalized = message.tool_calls.get()
    if finalized:
        print(f"finalized tool calls: {finalized}")

for call in stream.tool_calls:
    print(f"{call.tool_name}({call.input})")
    for delta in call.output_deltas:
        print(delta, end="", flush=True)
    print(call.output, call.error)
```

## 流式传输 sub-agents

当一个 `create_agent` 调用通过包装 tool 调用另一个 `create_agent` 时，内部 agent 的事件会在嵌套的 namespace 中流动，并作为 `stream.subgraphs` 上的一个 handle 呈现。每个 handle 都暴露内部 agent 自己的 `.messages`、`.values`、`.tool_calls` 和 `.output` projections。你传递给 `create_agent` 的 `name=` 会变成 `subagent.graph_name` (pythonthon) / `subagent.name` (JS)，这使你能够按 agent 进行过滤和标记。

每个嵌套的 `CompiledStateGraph` 都会出现在 `stream.subgraphs` 上——`create_agent` 实例是其中一种特定类型。通过名称过滤，只对你关心的那些执行操作。

```python 
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

weather_agent = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    tools=[get_weather],
    name="weather_agent",
)

def call_weather(query: str) -> str:
    """Query the weather agent."""
    result = weather_agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].text

supervisor = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    tools=[call_weather],
    name="supervisor",
)

stream = supervisor.stream_events(
    {"messages": [{"role": "user", "content": "What's the weather in Boston?"}]},
    version="v3",
)

for subagent in stream.subgraphs:
    if subagent.graph_name != "weather_agent":
        continue
    print(f"{subagent.graph_name}: ", end="")
    for message in subagent.messages:
        for token in message.text:
            print(token, end="", flush=True)
    print()
```

同样的 projection 也适用于从 tool 调用的普通 `StateGraph` subgraphs——在 `.compile(name=...)` 上设置 `name=` 即可在 `subagent.graph_name` 中获得一个标签。没有单独的仅 sub-agent 的 projection；过滤逻辑由你在循环中编写。

## State 和最终输出

使用 `stream.values` 获取 state 快照，使用 `stream.output` 获取最终 agent state。

```python
stream = agent.stream_events(input, version="v3")

for snapshot in stream.values:
    print(snapshot)

final_state = stream.output
```

## 多个 projections

在异步代码中进行并发消费，可使用 `astream_events` 结合 `asyncio.gather`：

```python
import asyncio

stream = await agent.astream_events(input, version="v3")

async def consume_messages():
    async for message in stream.messages:
        print(await message.text)

async def consume_tool_calls():
    async for call in stream.tool_calls:
        print(call.tool_name, call.input)

await asyncio.gather(consume_messages(), consume_tool_calls())
```

对于同步代码，改用 `stream.interleave(...)`：

```python
stream = agent.stream_events(input, version="v3")

for name, item in stream.interleave("messages", "tool_calls", "values"):
    if name == "messages":
        print(item.text)
    elif name == "tool_calls":
        print(item.tool_name, item.input)
    elif name == "values":
        print(item)
```

要访问未作为类型化 projections 暴露的 channels，或检查完整的事件 envelope，可迭代原始协议事件：

```python
for event in stream:
    print(event["method"], event["params"]["namespace"], event["params"]["data"])
```

## 自定义更新

当你的应用程序需要一个内置 projections 未提供的 projection 时（例如检索进度、工件或领域特定事件），可使用自定义 stream transformers。

```python
stream = agent.stream_events(
    input,
    version="v3",
    transformers=[ToolActivityTransformer],
)

for activity in stream.extensions["tool_activity"]:
    print(activity)
```

有关 transformer 合约，请参阅 构建你自己的 projection。

## 相关链接

* Streaming 涵盖了底层的 Pregel stream 模式。
* 构建你自己的 projection 涵盖了编写特定于应用程序的 projections。
* 前端流式传输模式展示了基于流式 state 构建的 UI 用例。