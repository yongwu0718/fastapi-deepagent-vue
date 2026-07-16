# Streaming

> 从 agent 运行中流式传输实时更新

LangChain 实现了一个流式传输系统，用于展示实时更新。

流式传输对于提升基于 LLM 构建的应用的响应速度至关重要。通过逐步显示输出，甚至在完整响应就绪之前，流式传输显著改善了用户体验 (UX)，尤其是在处理 LLM 的延迟时。

## Overview

LangChain 的流式传输系统让您可以将 agent 运行的实时反馈提供给应用程序。

LangChain 流式传输可以实现的功能：

*   **流式传输 agent 进度** — 在 agent 的每一步之后获取状态更新。
*   **流式传输 LLM tokens** — 在语言模型 token 生成时实时流式传输。
*   **流式传输思考 / 推理 tokens** — 在模型生成推理时实时展示。
*   **流式传输自定义更新** — 发出用户定义的信号（例如 `"Fetched 10/100 records"`）。
*   **多种流式模式** — 从 `updates`（agent 进度）、`messages`（LLM tokens + 元数据）或 `custom`（任意用户数据）中选择。

有关更多端到端的示例，请参阅下面的常见模式 (common patterns) 部分。

## 支持的流式模式

将一个或多个以下流式模式作为列表传递给 `stream` 或 `astream` 方法：

| 模式        | 描述                                                                                         |
| ----------- | -------------------------------------------------------------------------------------------- |
| `updates`   | 在 agent 的每一步之后流式传输状态更新。如果在同一步中进行了多次更新（例如运行了多个节点），则这些更新会分别流式传输。 |
| `messages`  | 从调用 LLM 的任何 graph 节点流式传输 `(token, metadata)` 元组。                              |
| `custom`    | 使用 stream writer 从 graph 节点内部流式传输自定义数据。                                     |

## Agent progress

要流式传输 agent 进度，请使用 `stream` 或 `astream` 方法并设置 `stream_mode="updates"`。这会在 agent 的每一步之后发出一个事件。

例如，如果您有一个只调用一次 tool 的 agent，您应该会看到以下更新：

*   **LLM node**: 带有 tool call 请求的 `AIMessage`
*   **Tool node**: 带有执行结果的 `ToolMessage`
*   **LLM node**: 最终的 AI 响应

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """获取给定城市的天气。"""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)
for chunk in agent.stream(  
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="updates",
    version="v2",  
):
    if chunk["type"] == "updates":  
        for step, data in chunk["data"].items():  
            print(f"step: {step}")
            print(f"content: {data['messages'][-1].content_blocks}")
```

```shell
step: model
content: [{'type': 'tool_call', 'name': 'get_weather', 'args': {'city': 'San Francisco'}, 'id': 'call_OW2NYNsNSKhRZpjW0wm2Aszd'}]

step: tools
content: [{'type': 'text', 'text': "It's always sunny in San Francisco!"}]

step: model
content: [{'type': 'text', 'text': 'It's always sunny in San Francisco!'}]
```

## LLM tokens

要流式传输 LLM 生成的 token，请使用 `stream_mode="messages"`。下面您可以看到 agent 流式传输 tool calls 和最终响应的输出。

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """获取给定城市的天气。"""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)
for chunk in agent.stream(  
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="messages",
    version="v2",  
):
    if chunk["type"] == "messages":  
        token, metadata = chunk["data"]  
        print(f"node: {metadata['langgraph_node']}")
        print(f"content: {token.content_blocks}")
        print("\n")
```

## Custom updates

要从正在执行的 tools 中流式传输更新，您可以使用 `get_stream_writer`。

```python
from langchain.agents import create_agent
from langgraph.config import get_stream_writer  

def get_weather(city: str) -> str:
    """获取给定城市的天气。"""
    writer = get_stream_writer()  
    # 流式传输任意数据
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="claude-sonnet-4-6",
    tools=[get_weather],
)

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="custom",  
    version="v2",  
):
    if chunk["type"] == "custom":  
        print(chunk["data"])  
```

```shell
Looking up data for city: San Francisco
Acquired data for city: San Francisco
```

如果您在 tool 内部添加了 `get_stream_writer`，则无法在 LangGraph 执行上下文之外调用该 tool。

## 流式传输多种模式

您可以通过将 stream mode 作为列表传递来指定多种流式模式：`stream_mode=["updates", "custom"]`。

每个流式传输的 chunk 都是一个 `StreamPart` 字典，包含 `type`、`ns` 和 `data` 键。使用 `chunk["type"]` 确定流式模式，使用 `chunk["data"]` 访问负载。

```python
from langchain.agents import create_agent
from langgraph.config import get_stream_writer

def get_weather(city: str) -> str:
    """获取给定城市的天气。"""
    writer = get_stream_writer()
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)

for chunk in agent.stream(  
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode=["updates", "custom"],
    version="v2",  
):
    print(f"stream_mode: {chunk['type']}")  
    print(f"content: {chunk['data']}")  
    print("\n")
```

```shell
stream_mode: updates
content: {'model': {'messages': [AIMessage(content='', response_metadata={'token_usage': {'completion_tokens': 280, 'prompt_tokens': 132, 'total_tokens': 412, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 256, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_provider': 'openai', 'model_name': 'gpt-5-nano-2025-08-07', 'system_fingerprint': None, 'id': 'chatcmpl-C9tlgBzGEbedGYxZ0rTCz5F7OXpL7', 'service_tier': 'default', 'finish_reason': 'tool_calls', 'logprobs': None}, id='lc_run--480c07cb-e405-4411-aa7f-0520fddeed66-0', tool_calls=[{'name': 'get_weather', 'args': {'city': 'San Francisco'}, 'id': 'call_KTNQIftMrl9vgNwEfAJMVu7r', 'type': 'tool_call'}], usage_metadata={'input_tokens': 132, 'output_tokens': 280, 'total_tokens': 412, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 256}})]}}

stream_mode: custom
content: Looking up data for city: San Francisco

stream_mode: custom
content: Acquired data for city: San Francisco

stream_mode: updates
content: {'tools': {'messages': [ToolMessage(content="It's always sunny in San Francisco!", name='get_weather', tool_call_id='call_KTNQIftMrl9vgNwEfAJMVu7r')]}}

stream_mode: updates
content: {'model': {'messages': [AIMessage(content='San Francisco weather: It's always sunny in San Francisco!\n\n', response_metadata={'token_usage': {'completion_tokens': 764, 'prompt_tokens': 168, 'total_tokens': 932, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 704, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_provider': 'openai', 'model_name': 'gpt-5-nano-2025-08-07', 'system_fingerprint': None, 'id': 'chatcmpl-C9tljDFVki1e1haCyikBptAuXuHYG', 'service_tier': 'default', 'finish_reason': 'stop', 'logprobs': None}, id='lc_run--acbc740a-18fe-4a14-8619-da92a0d0ee90-0', usage_metadata={'input_tokens': 168, 'output_tokens': 764, 'total_tokens': 932, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 704}})]}}
```

## Common patterns

以下是展示流式传输常见用例的示例。

### 流式传输思考 / 推理 tokens

一些模型在产生最终答案之前会执行内部推理。您可以通过筛选标准 content blocks 中 `type` 为 `"reasoning"` 的块来流式传输这些思考 / 推理 tokens。

必须在模型上启用推理输出。

  有关配置详细信息，请参阅 reasoning 部分和您的 provider 集成页面。

  要快速检查模型的推理支持，请参阅 models.dev。

要从 agent 流式传输思考 tokens，请使用 `stream_mode="messages"` 并筛选出 reasoning content blocks：

```python
from langchain.agents import create_agent
from langchain.messages import AIMessageChunk
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import Runnable

def get_weather(city: str) -> str:
    """获取给定城市的天气。"""
    return f"It's always sunny in {city}!"

model = ChatAnthropic(
    model_name="claude-sonnet-4-6",
    timeout=None,
    stop=None,
    thinking={"type": "enabled", "budget_tokens": 5000},
)
agent: Runnable = create_agent(
    model=model,
    tools=[get_weather],
)

for token, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="messages",  
):
    if not isinstance(token, AIMessageChunk):
        continue
    reasoning = [b for b in token.content_blocks if b["type"] == "reasoning"]
    text = [b for b in token.content_blocks if b["type"] == "text"]
    if reasoning:
        print(f"[thinking] {reasoning[0]['reasoning']}", end="")
    if text:
        print(text[0]["text"], end="")
```

```shell
[thinking] The user is asking about the weather in San Francisco. I have a tool
[thinking]  available to get this information. Let me call the get_weather tool
[thinking]  with "San Francisco" as the city parameter.
The weather in San Francisco is: It's always sunny in San Francisco!
```

无论使用哪个模型 provider，这种方法都同样有效——LangChain 通过 `content_blocks` 属性将 provider 特定格式（Anthropic 的 `thinking` 块，OpenAI 的 `reasoning` 摘要等）规范化为标准的 `"reasoning"` content block 类型。

要直接从聊天模型流式传输推理 tokens（不使用 agent），请参阅 streaming with chat models。

### 流式传输 tool calls

您可能希望同时流式传输：

1.  生成 tool calls 时的部分 JSON
2.  已完成的、解析后的将被执行的 tool calls

指定 `stream_mode="messages"` 将流式传输 agent 中所有 LLM 调用生成的增量消息块。要访问带有解析后 tool calls 的完整消息：

1.  如果这些消息在状态中被跟踪（如在 `create_agent` 的 model node 中），请使用 `stream_mode=["messages", "updates"]` 通过状态更新访问完整的消息（如下所示）。
2.  如果这些消息未在状态中跟踪，请使用自定义更新或在流式循环中聚合这些 chunks（下一节）。

如果您的 agent 包含多个 LLM，请参阅下面关于从子 agent 流式传输的部分。

```python
from typing import Any

from langchain.agents import create_agent
from langchain.messages import AIMessage, AIMessageChunk, AnyMessage, ToolMessage

def get_weather(city: str) -> str:
    """获取给定城市的天气。"""
    return f"It's always sunny in {city}!"

agent = create_agent("openai:gpt-5.4", tools=[get_weather])

def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)
    # N.B. 所有内容都可以通过 token.content_blocks 获取

def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")

input_message = {"role": "user", "content": "What is the weather in Boston?"}
for chunk in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates"],  
    version="v2",  
):
    if chunk["type"] == "messages":  
        token, metadata = chunk["data"]  
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)  
    elif chunk["type"] == "updates":  
        for source, update in chunk["data"].items():  
            if source in ("model", "tools"):  # `source` 捕获节点名称
                _render_completed_message(update["messages"][-1])  
```

```shell
[{'name': 'get_weather', 'args': '', 'id': 'call_D3Orjr89KgsLTZ9hTzYv7Hpf', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'city', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'Boston', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'get_weather', 'args': {'city': 'Boston'}, 'id': 'call_D3Orjr89KgsLTZ9hTzYv7Hpf', 'type': 'tool_call'}]
Tool response: [{'type': 'text', 'text': "It's always sunny in Boston!"}]
The| weather| in| Boston| is| **|sun|ny|**|.|
```

#### 访问已完成的 messages

如果完整的消息在 agent 的状态中被跟踪，您可以像“流式传输 tool calls”部分中演示的那样使用 `stream_mode=["messages", "updates"]` 在流式传输期间访问完整的消息。

在某些情况下，完整的消息不会反映在状态更新中。如果您可以访问 agent 的内部结构，您可以使用自定义更新在流式传输期间访问这些消息。否则，您可以在流式循环中聚合消息 chunks（见下文）。

考虑下面的例子，我们在一个简化的护栏 (guardrail) 中间件中合并了一个 stream writer。这个中间件演示了 tool calling 来生成结构化的“安全 / 不安全”评估（也可以使用结构化输出来实现）：

```python
from typing import Any, Literal

from langchain.agents.middleware import after_agent, AgentState
from langgraph.runtime import Runtime
from langchain.messages import AIMessage
from langchain.chat_models import init_chat_model
from langgraph.config import get_stream_writer  
from pydantic import BaseModel

class ResponseSafety(BaseModel):
    """评估响应是安全还是不安全的。"""
    evaluation: Literal["safe", "unsafe"]

safety_model = init_chat_model("openai:gpt-5.4")

@after_agent(can_jump_to=["end"])
def safety_guardrail(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """基于模型的护栏：使用 LLM 评估响应安全性。"""
    stream_writer = get_stream_writer()  
    # 获取模型响应
    if not state["messages"]:
        return None

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return None

    # 使用另一个模型评估安全性
    model_with_tools = safety_model.bind_tools([ResponseSafety], tool_choice="any")
    result = model_with_tools.invoke(
        [
            {
                "role": "system",
                "content": "Evaluate this AI response as generally safe or unsafe."
            },
            {
                "role": "user",
                "content": f"AI response: {last_message.text}"
            }
        ]
    )
    stream_writer(result)  

    tool_call = result.tool_calls[0]
    if tool_call["args"]["evaluation"] == "unsafe":
        last_message.content = "I cannot provide that response. Please rephrase your request."

    return None
```

然后，我们可以将此中间件合并到我们的 agent 中，并包含其自定义流事件：

```python
from typing import Any

from langchain.agents import create_agent
from langchain.messages import AIMessageChunk, AIMessage, AnyMessage

def get_weather(city: str) -> str:
    """获取给定城市的天气。"""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="openai:gpt-5.4",
    tools=[get_weather],
    middleware=[safety_guardrail],  
)

def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)

def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")

input_message = {"role": "user", "content": "What is the weather in Boston?"}
for chunk in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates", "custom"],  
    version="v2",  
):
    if chunk["type"] == "messages":  
        token, metadata = chunk["data"]  
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    elif chunk["type"] == "updates":  
        for source, update in chunk["data"].items():  
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
    elif chunk["type"] == "custom":  
        # 在流中访问已完成的消息
        print(f"Tool calls: {chunk['data'].tool_calls}")  
```

```shell
[{'name': 'get_weather', 'args': '', 'id': 'call_je6LWgxYzuZ84mmoDalTYMJC', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'city', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'Boston', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'get_weather', 'args': {'city': 'Boston'}, 'id': 'call_je6LWgxYzuZ84mmoDalTYMJC', 'type': 'tool_call'}]
Tool response: [{'type': 'text', 'text': "It's always sunny in Boston!"}]
The| weather| in| **|Boston|**| is| **|sun|ny|**|.|[{'name': 'ResponseSafety', 'args': '', 'id': 'call_O8VJIbOG4Q9nQF0T8ltVi58O', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'evaluation', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'safe', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'ResponseSafety', 'args': {'evaluation': 'safe'}, 'id': 'call_O8VJIbOG4Q9nQF0T8ltVi58O', 'type': 'tool_call'}]
```

或者，如果您无法向流中添加自定义事件，您可以在流式循环中聚合消息 chunks：

```python
input_message = {"role": "user", "content": "What is the weather in Boston?"}
full_message = None  
for chunk in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates"],
    version="v2",  
):
    if chunk["type"] == "messages":  
        token, metadata = chunk["data"]  
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
            full_message = token if full_message is None else full_message + token  
            if token.chunk_position == "last":  
                if full_message.tool_calls:  
                    print(f"Tool calls: {full_message.tool_calls}")  
                full_message = None  
    elif chunk["type"] == "updates":  
        for source, update in chunk["data"].items():  
            if source == "tools":
                _render_completed_message(update["messages"][-1])
```

### 使用 Human-in-the-loop 进行流式传输

为了处理人机交互 (human-in-the-loop) 的中断，我们在上述示例的基础上进行构建：

1.  我们使用人机交互中间件和一个 checkpointer 来配置 agent
2.  我们在 `"updates"` 流式模式期间收集生成的中断
3.  我们使用一个 command 来响应这些中断

```python
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.messages import AIMessage, AIMessageChunk, AnyMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, Interrupt

def get_weather(city: str) -> str:
    """获取给定城市的天气。"""
    return f"It's always sunny in {city}!"

checkpointer = InMemorySaver()

agent = create_agent(
    "openai:gpt-5.4",
    tools=[get_weather],
    middleware=[  
        HumanInTheLoopMiddleware(interrupt_on={"get_weather": True}),  
    ],  
    checkpointer=checkpointer,  
)

def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)

def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")

def _render_interrupt(interrupt: Interrupt) -> None:  
    interrupts = interrupt.value  
    for request in interrupts["action_requests"]:  
        print(request["description"])  

input_message = {
    "role": "user",
    "content": (
        "Can you look up the weather in Boston and San Francisco?"
    ),
}
config = {"configurable": {"thread_id": "some_id"}}  
interrupts = []  
for chunk in agent.stream(
    {"messages": [input_message]},
    config=config,  
    stream_mode=["messages", "updates"],
    version="v2",  
):
    if chunk["type"] == "messages":  
        token, metadata = chunk["data"]  
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    elif chunk["type"] == "updates":  
        for source, update in chunk["data"].items():  
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
            if source == "__interrupt__":  
                interrupts.extend(update)  
                _render_interrupt(update[0])  
```

```shell
[{'name': 'get_weather', 'args': '', 'id': 'call_GOwNaQHeqMixay2qy80padfE', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"ci', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'ty": ', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"Bosto', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'n"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': 'get_weather', 'args': '', 'id': 'call_Ndb4jvWm2uMA0JDQXu37wDH6', 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"ci', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'ty": ', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"San F', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'ranc', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'isco"', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '}', 'id': None, 'index': 1, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'get_weather', 'args': {'city': 'Boston'}, 'id': 'call_GOwNaQHeqMixay2qy80padfE', 'type': 'tool_call'}, {'name': 'get_weather', 'args': {'city': 'San Francisco'}, 'id': 'call_Ndb4jvWm2uMA0JDQXu37wDH6', 'type': 'tool_call'}]
Tool execution requires approval

Tool: get_weather
Args: {'city': 'Boston'}
Tool execution requires approval

Tool: get_weather
Args: {'city': 'San Francisco'}
```

接下来，我们为每个中断收集一个决策。重要的是，决策的顺序必须与我们收集到的 actions 的顺序匹配。

为了说明，我们将编辑一个 tool call 并接受另一个：

```python
def _get_interrupt_decisions(interrupt: Interrupt) -> list[dict]:
    return [
        {
            "type": "edit",
            "edited_action": {
                "name": "get_weather",
                "args": {"city": "Boston, U.K."},
            },
        }
        if "boston" in request["description"].lower()
        else {"type": "approve"}
        for request in interrupt.value["action_requests"]
    ]

decisions = {}
for interrupt in interrupts:
    decisions[interrupt.id] = {
        "decisions": _get_interrupt_decisions(interrupt)
    }

decisions
```

```shell
{
    'a96c40474e429d661b5b32a8d86f0f3e': {
        'decisions': [
            {
                'type': 'edit',
                 'edited_action': {
                     'name': 'get_weather',
                     'args': {'city': 'Boston, U.K.'}
                 }
            },
            {'type': 'approve'},
        ]
    }
}
```

然后，我们可以通过将 command 传递到同一个流式循环中来恢复执行：

```python
interrupts = []
for chunk in agent.stream(
    Command(resume=decisions),  
    config=config,
    stream_mode=["messages", "updates"],
    version="v2",  
):
    # 流式循环保持不变
    if chunk["type"] == "messages":  
        token, metadata = chunk["data"]  
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    elif chunk["type"] == "updates":  
        for source, update in chunk["data"].items():  
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
            if source == "__interrupt__":
                interrupts.extend(update)
                _render_interrupt(update[0])
```

```shell
Tool response: [{'type': 'text', 'text': "It's always sunny in Boston, U.K.!"}]
Tool response: [{'type': 'text', 'text': "It's always sunny in San Francisco!"}]
-| **|Boston|**|:| It|'s| always| sunny| in| Boston|,| U|.K|.|
|-| **|San| Francisco|**|:| It|'s| always| sunny| in| San| Francisco|!|
```

### 从子 agents 流式传输

当 agent 中任何位置存在多个 LLM 时，通常需要消除生成消息的来源的歧义。

为此，请在创建每个 agent 时传递一个 `name`。然后，在以 `"messages"` 模式流式传输时，该名称可以通过 `lc_agent_name` 键在 metadata 中获得。

下面，我们更新了流式传输 tool calls 的示例：

1.  我们将 tool 替换为内部调用 agent 的 `call_weather_agent` tool
2.  我们为每个 agent 添加一个 `name`
3.  我们在创建流时指定 `subgraphs=True`
4.  我们的流处理与之前相同，但我们添加了逻辑，使用 `create_agent` 的 `name` 参数来跟踪哪个 agent 处于活动状态

当您在 agent 上设置 `name` 时，该名称也会附加到该 agent 生成的任何 `AIMessage` 上。

首先，我们构建 agent：

```python
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, AnyMessage

def get_weather(city: str) -> str:
    """获取给定城市的天气。"""
    return f"It's always sunny in {city}!"

weather_model = init_chat_model("openai:gpt-5.4")
weather_agent = create_agent(
    model=weather_model,
    tools=[get_weather],
    name="weather_agent",  
)

def call_weather_agent(query: str) -> str:
    """查询天气 agent。"""
    result = weather_agent.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    return result["messages"][-1].text

supervisor_model = init_chat_model("openai:gpt-5.4")
agent = create_agent(
    model=supervisor_model,
    tools=[call_weather_agent],
    name="supervisor",  
)
```

接下来，我们在流式循环中添加逻辑来报告哪个 agent 正在发出 tokens：

```python
def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)

def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")

input_message = {"role": "user", "content": "What is the weather in Boston?"}
current_agent = None  
for chunk in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates"],
    subgraphs=True,  
    version="v2",  
):
    if chunk["type"] == "messages":  
        token, metadata = chunk["data"]  
        if agent_name := metadata.get("lc_agent_name"):  
            if agent_name != current_agent:  
                print(f"🤖 {agent_name}: ")  
                current_agent = agent_name  
        if isinstance(token, AIMessage):
            _render_message_chunk(token)
    elif chunk["type"] == "updates":  
        for source, update in chunk["data"].items():  
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
```

```shell
🤖 supervisor:
[{'name': 'call_weather_agent', 'args': '', 'id': 'call_asorzUf0mB6sb7MiKfgojp7I', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'query', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'Boston', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' weather', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' right', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' now', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' and', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': " today's", 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': ' forecast', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'call_weather_agent', 'args': {'query': "Boston weather right now and today's forecast"}, 'id': 'call_asorzUf0mB6sb7MiKfgojp7I', 'type': 'tool_call'}]
🤖 weather_agent:
[{'name': 'get_weather', 'args': '', 'id': 'call_LZ89lT8fW6w8vqck5pZeaDIx', 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '{"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'city', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '":"', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': 'Boston', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
[{'name': None, 'args': '"}', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
Tool calls: [{'name': 'get_weather', 'args': {'city': 'Boston'}, 'id': 'call_LZ89lT8fW6w8vqck5pZeaDIx', 'type': 'tool_call'}]
Tool response: [{'type': 'text', 'text': "It's always sunny in Boston!"}]
Boston| weather| right| now|:| **|Sunny|**|.

|Today|'s| forecast| for| Boston|:| **|Sunny| all| day|**|.|Tool response: [{'type': 'text', 'text': 'Boston weather right now: **Sunny**.\n\nToday's forecast for Boston: **Sunny all day**.'}]
🤖 supervisor:
Boston| weather| right| now|:| **|Sunny|**|.

|Today|'s| forecast| for| Boston|:| **|Sunny| all| day|**|.|
```

## 禁用 Streaming

在某些应用程序中，您可能需要禁用特定模型的单个 token 流式传输。这在以下情况下很有用：

*   在多 agent 系统中控制哪些 agent 流式传输它们的输出
*   混合使用支持流式传输和不支持流式传输的模型
*   部署到 LangSmith 并希望防止某些模型输出被流式传输到客户端

在初始化模型时设置 `streaming=False`。

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-5.4",
    streaming=False  
)
```

当部署到 LangSmith 时，在任何您不希望将其输出流式传输到客户端的模型上设置 `streaming=False`。这是在部署之前在图代码中配置的。

并非所有聊天模型集成都支持 `streaming` 参数。如果您的模型不支持，请改用 `disable_streaming=True`。该参数可通过基类在所有聊天模型上使用。

有关更多详细信息，请参阅 LangGraph streaming guide。

## v2 streaming format

需要 LangGraph >= 1.1。

向 `stream()` 或 `astream()` 传递 `version="v2"` 以获得统一的输出格式。每个 chunk 都是一个 `StreamPart` 字典，包含 `type`、`ns` 和 `data` 键——无论流式模式或模式数量如何，其形状都相同：

```python
  # 统一格式 — 不再需要解包元组
  for chunk in agent.stream(
      {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
      stream_mode=["updates", "custom"],
      version="v2",
  ):
      print(chunk["type"])  # "updates" or "custom"
      print(chunk["data"])  # payload
  ```

  ```python
  # 必须解包 (mode, data) 元组
  for mode, chunk in agent.stream(
      {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
      stream_mode=["updates", "custom"],
  ):
      print(mode)   # "updates" or "custom"
      print(chunk)  # payload
  ```

v2 格式还改进了 `invoke()`——它返回一个 `GraphOutput` 对象，具有 `.value` 和 `.interrupts` 属性，将状态与中断元数据清晰地分开：

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Hello"}]},
    version="v2",
)
print(result.value)       # state (dict, Pydantic model, or dataclass)
print(result.interrupts)  # tuple of Interrupt objects (empty if none)
```

有关 v2 格式的更多详细信息，包括类型收窄、Pydantic/dataclass 强制转换和子图流式传输，请参阅 LangGraph streaming docs。

## Related

*   Frontend streaming — 使用 `useStream` 构建 React UI 以实现实时 agent 交互
*   Streaming with chat models — 直接从聊天模型流式传输 tokens，无需使用 agent 或 graph
*   Reasoning with chat models — 配置和访问聊天模型的推理输出
*   Standard content blocks — 了解用于推理、文本和其他内容类型的标准化 content block 格式
*   Streaming with human-in-the-loop — 在处理人机审查中断的同时流式传输 agent 进度
*   LangGraph streaming — 高级流式传输选项，包括 `values`、`debug` 模式和子图流式传输