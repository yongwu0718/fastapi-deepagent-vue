# Streaming API

LangGraph SDK 允许您以多种模式从 LangSmith Deployment API 流式传输输出，从每个步骤后的完整状态快照到逐 token 的 LLM 输出。Thread 流式传输还支持可恢复性：如果连接断开，可以使用最后一个事件 ID 重新连接，从中断处继续接收。

LangGraph SDK 和 Agent Server 是 LangSmith 的一部分。

## 基本用法

基本用法示例：

```python
from langgraph_sdk import get_client
client = get_client(url=<your_url>, api_key=<your_key>)

# 使用名为 "agent" 部署的 graph
assistant_id = "agent"

# 创建一个 thread
thread = await client.threads.create()
thread_id = thread["thread_id"]

# 创建一个流式运行
async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input=inputs,
    stream_mode="updates"
):
    print(chunk.data)
```

以下是一个可以在 Agent Server 中运行的示例 graph。
更多详情请参见 LangSmith 快速入门。

```python
# graph.py
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    topic: str
    joke: str

def refine_topic(state: State):
    return {"topic": state["topic"] + " and cats"}

def generate_joke(state: State):
    return {"joke": f"This is a joke about {state['topic']}"}

graph = (
    StateGraph(State)
    .add_node(refine_topic)
    .add_node(generate_joke)
    .add_edge(START, "refine_topic")
    .add_edge("refine_topic", "generate_joke")
    .add_edge("generate_joke", END)
    .compile()
)
```

一旦您有一个正在运行的 Agent Server，就可以使用 LangGraph SDK 与之交互

```python
from langgraph_sdk import get_client
client = get_client(url=<your_url>)

# 使用名为 "agent" 部署的 graph
assistant_id = "agent"

# 创建一个 thread
thread = await client.threads.create()
thread_id = thread["thread_id"]

# 创建一个流式运行
async for chunk in client.runs.stream(  # (1)!
    thread_id,
    assistant_id,
    input={"topic": "ice cream"},
    stream_mode="updates"  # (2)!
):
    print(chunk.data)
```

1. `client.runs.stream()` 方法返回一个迭代器，产生流式输出。
2. 设置 `stream_mode="updates"` 以仅流式传输每个节点之后的 graph 状态更新。也支持其他流模式。详情请参见支持的流模式。

```python
{'run_id': '1f02c2b3-3cef-68de-b720-eec2a4a8e920', 'attempt': 1}
{'refine_topic': {'topic': 'ice cream and cats'}}
{'generate_joke': {'joke': 'This is a joke about ice cream and cats'}}
```

### 支持的流模式 (stream modes)

| Mode             | 描述                                                              | LangGraph 库方法                                          |
| ---------------- | --------------------------------------------------------------- | ------------------------------------------------------ |
| `values`         | 在每个超级步骤之后流式传输完整的 graph 状态。                                      | `.stream()` / `.astream()` 配合 `stream_mode="values"`   |
| `updates`        | 在 graph 的每个步骤之后流式传输状态的更新。如果在同一步骤中有多个更新（例如多个节点被运行），这些更新会被分别流式传输。 | `.stream()` / `.astream()` 配合 `stream_mode="updates"`  |
| `messages-tuple` | 流式传输调用 LLM 的 graph 节点中的 LLM token 和元数据（对聊天应用很有用）。               | `.stream()` / `.astream()` 配合 `stream_mode="messages"` |
| `debug`          | 在 graph 执行过程中流式传输尽可能多的信息。                                       | `.stream()` / `.astream()` 配合 `stream_mode="debug"`    |
| `custom`         | 从您的 graph 内部流式传输自定义数据                                           | `.stream()` / `.astream()` 配合 `stream_mode="custom"`   |
| `events`         | 流式传输所有事件（包括 graph 的状态）；在迁移大型 LCEL 应用时主要用。                       | `.astream_events()`                                    |

### 同时流式传输多种模式

您可以将一个列表作为 `stream_mode` 参数传递，以同时流式传输多种模式。

流式输出的结果将是 `(mode, chunk)` 元组，其中 `mode` 是流模式的名称，`chunk` 是该模式流式传输的数据。

```python
async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input=inputs,
    stream_mode=["updates", "custom"]
):
    print(chunk)
```

## 流式传输 graph 状态

使用流模式 `updates` 和 `values` 在 graph 执行时流式传输其状态。

* `updates` 流式传输 graph 每个步骤之后的**状态更新**。
* `values` 流式传输 graph 每个步骤之后的**完整状态值**。

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
  topic: str
  joke: str

def refine_topic(state: State):
    return {"topic": state["topic"] + " and cats"}

def generate_joke(state: State):
    return {"joke": f"This is a joke about {state['topic']}"}

graph = (
  StateGraph(State)
  .add_node(refine_topic)
  .add_node(generate_joke)
  .add_edge(START, "refine_topic")
  .add_edge("refine_topic", "generate_joke")
  .add_edge("generate_joke", END)
  .compile()
)
```

**有状态运行**
下面的示例假设您希望**持久化**流式运行的输出到 checkpoint 数据库，并且已经创建了一个 thread。要创建一个 thread：

```python
from langgraph_sdk import get_client
client = get_client(url=<your_url>)

# 使用名为 "agent" 部署的 graph
assistant_id = "agent"
# 创建一个 thread
thread = await client.threads.create()
thread_id = thread["thread_id"]
```

如果您不需要持久化运行的输出，可以在流式传输时传递 `None` 而不是 `thread_id`。

### 流模式：`updates`

使用此模式仅流式传输每个步骤之后节点返回的**状态更新**。流式输出包括节点名称以及更新内容。

```python
async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input={"topic": "ice cream"},
    stream_mode="updates"
):
    print(chunk.data)
```

### 流模式：`values`

使用此模式在每个步骤之后流式传输 graph 的**完整状态**。

```python
async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input={"topic": "ice cream"},
    stream_mode="values"
):
    print(chunk.data)
```

## 子图 (Subgraphs)

要在流式输出中包含子图的输出，可以在父图的 `.stream()` 方法中设置 `subgraphs=True`。这将流式传输父图和任何子图的输出。

```python
async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input={"foo": "foo"},
    stream_subgraphs=True, # (1)!
    stream_mode="updates",
):
    print(chunk)
```

1. 设置 `stream_subgraphs=True` 以流式传输子图的输出。

以下是一个可以在 Agent Server 中运行的示例 graph。
更多详情请参见 LangSmith 快速入门。

```python
# graph.py
from langgraph.graph import START, StateGraph
from typing import TypedDict

# 定义子图
class SubgraphState(TypedDict):
    foo: str  # 注意这个 key 与父图状态共享
    bar: str

def subgraph_node_1(state: SubgraphState):
    return {"bar": "bar"}

def subgraph_node_2(state: SubgraphState):
    return {"foo": state["foo"] + state["bar"]}

subgraph_builder = StateGraph(SubgraphState)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_node(subgraph_node_2)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph_builder.add_edge("subgraph_node_1", "subgraph_node_2")
subgraph = subgraph_builder.compile()

# 定义父图
class ParentState(TypedDict):
    foo: str

def node_1(state: ParentState):
    return {"foo": "hi! " + state["foo"]}

builder = StateGraph(ParentState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", subgraph)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
graph = builder.compile()
```

一旦您有一个正在运行的 Agent Server，就可以使用 LangGraph SDK 与之交互

```python
from langgraph_sdk import get_client
client = get_client(url=<your_url>)

# 使用名为 "agent" 部署的 graph
assistant_id = "agent"

# 创建一个 thread
thread = await client.threads.create()
thread_id = thread["thread_id"]

async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input={"foo": "foo"},
    stream_subgraphs=True, # (1)!
    stream_mode="updates",
):
    print(chunk)
```

1. 设置 `stream_subgraphs=True` 以流式传输子图的输出。

**注意** 我们不仅收到节点更新，还收到命名空间 (namespaces)，这告诉我们正在从哪个 graph（或子图）流式传输。

## 调试 (Debugging)

使用 `debug` 流模式在 graph 执行过程中流式传输尽可能多的信息。流式输出包括节点名称以及完整状态。

```python
async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input={"topic": "ice cream"},
    stream_mode="debug"
):
    print(chunk.data)
```

## LLM tokens

使用 `messages-tuple` 流模式，从 graph 的任何部分（包括节点、tools、子图或任务）**逐个 token** 流式传输大语言模型 (LLM) 的输出。

`messages-tuple` 模式的流式输出是一个元组 `(message_chunk, metadata)`，其中：

* `message_chunk`：来自 LLM 的 token 或消息片段。
* `metadata`：包含有关 graph 节点和 LLM 调用的详细信息的字典。

```python
from dataclasses import dataclass

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START

@dataclass
class MyState:
    topic: str
    joke: str = ""

model = init_chat_model(model="gpt-5.4-mini")

def call_model(state: MyState):
    """调用 LLM 生成关于某个主题的笑话"""
    model_response = model.invoke( # (1)!
        [
            {"role": "user", "content": f"Generate a joke about {state.topic}"}
        ]
    )
    return {"joke": model_response.content}

graph = (
    StateGraph(MyState)
    .add_node(call_model)
    .add_edge(START, "call_model")
    .compile()
)
```

1. 注意，即使 LLM 是使用 `invoke` 而不是 `stream` 运行的，消息事件仍然会被发出。

```python
async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input={"topic": "ice cream"},
    stream_mode="messages-tuple",
):
    if chunk.event != "messages":
        continue

    message_chunk, metadata = chunk.data  # (1)!
    if message_chunk["content"]:
        print(message_chunk["content"], end="|", flush=True)
```

1. "messages-tuple" 流模式返回一个 `(message_chunk, metadata)` 元组的迭代器，其中 `message_chunk` 是由 LLM 流式传输的 token，`metadata` 是一个包含有关调用 LLM 的 graph 节点和其他信息的字典。

### 过滤 LLM tokens

* 要按 LLM 调用过滤流式传输的 token，可以将 `tags` 与 LLM 调用关联起来。
* 要仅从特定节点流式传输 token，请使用 `stream_mode="messages"` 并通过流式元数据中的 `langgraph_node` 字段过滤输出。

## 流式传输自定义数据 (Custom Data)

要发送**自定义用户定义数据**：

```python
async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input={"query": "example"},
    stream_mode="custom"
):
    print(chunk.data)
```

## 流式传输事件 (Events)

要流式传输所有事件，包括 graph 的状态：

```python
async for chunk in client.runs.stream(
    thread_id,
    assistant_id,
    input={"topic": "ice cream"},
    stream_mode="events"
):
    print(chunk.data)
```

## 无状态运行 (Stateless Runs)

如果您不想将流式运行的输出**持久化**到 checkpoint 数据库中，可以创建一个无状态运行而不创建 thread：

```python
from langgraph_sdk import get_client
client = get_client(url=<your_url>, api_key=<your_key>)

async for chunk in client.runs.stream(
    None,  # (1)!
    assistant_id,
    input=inputs,
    stream_mode="updates"
):
    print(chunk.data)
```

## Join 和流式传输

LangSmith 允许您加入一个活跃的后台运行并从中流式传输输出。为此，您可以使用 LangGraph SDK 的 `client.runs.join_stream` 方法：

```python
from langgraph_sdk import get_client
client = get_client(url=<your_url>, api_key=<your_key>)

async for chunk in client.runs.join_stream(
    thread_id,
    run_id,  # (1)!
):
    print(chunk)
```

1. 这是您要加入的现有运行的 `run_id`。

**输出不缓冲**
  当您使用 `.join_stream` 时，输出不会被缓冲，因此在加入之前产生的任何输出都不会被接收到。

## 流式传输一个 Thread

Thread 流式传输为 thread 打开一个长连接，并流式传输在该 thread 上执行的**每次运行**的输出。这允许您从一个单一连接监控 thread 上的所有活动，例如，在聊天 UI 中，随着时间的推移，通过后续消息、人机交互恢复或后台运行可能会触发多次运行。要通过 ID 加入特定的现有运行，请参阅 Join 和流式传输。

### 比较 Thread 流式传输和 Run 流式传输

|                         | Thread 流式传输                  | Run 流式传输                           |
| ----------------------- | --------------------------------- | --------------------------------------- |
| **SDK 方法**          | `client.threads.join_stream()`    | `client.runs.stream()`                  |
| **REST 端点**       | `GET /threads/{thread_id}/stream` | `POST /threads/{thread_id}/runs/stream` |
| **范围**               | 一个 thread 上的所有 runs              | 单个 run                            |
| **连接生命周期** | 无限期打开                 | 当运行完成时关闭           |
| **创建 run**       | 否                                | 是                                     |
| **用例**            | 监控持续的 thread 活动   | 执行并流式传输一次交互 |

### 基本用法

```python
from langgraph_sdk import get_client
client = get_client(url=<your_url>, api_key=<your_key>)

thread = await client.threads.create()
thread_id = thread["thread_id"]

async for chunk in client.threads.join_stream(thread_id):
    print(chunk)
```

### Thread 流模式 (Stream Modes)

Thread 流式传输支持三种流模式，用于控制返回哪些事件。通过 `stream_mode` 参数传递一个或多个模式。

| Mode                  | 描述                   |
| --------------------- | ----------------------------------------------------- |
| `run_modes` (默认) | 流式传输所有 run 事件，等同于 `client.runs.stream()` 的输出。               |
| `lifecycle`           | 仅流式传输 run 开始和结束事件。使用此模式进行轻量级监控运行状态，无需完整输出。 |
| `state_update`        | 仅流式传输状态更新事件，在每个 run 完成后提供 thread 状态。         |

```python
async for chunk in client.threads.join_stream(
    thread_id,
    stream_mode=["lifecycle", "state_update"],
):
    print(chunk.event, chunk.data)
```

### 从最后一个事件恢复

Thread 流式传输支持通过 `Last-Event-ID` header 进行可恢复性。如果连接断开，请传递您收到的最后一个事件的 ID 以恢复而不丢失事件。传递 `"-"` 以从头开始重放。

```python
async for chunk in client.threads.join_stream(
    thread_id,
    last_event_id="<event_id>",
):
    print(chunk)
```

## API 参考

有关 API 的使用和实现，请参阅 API 参考。

