# Streaming

LangGraph 实现了一个流式传输系统，用于展示实时更新。流式传输对于提升基于 LLM 构建的应用的响应速度至关重要。通过逐步显示输出，甚至在完整响应就绪之前，流式传输显著改善了用户体验 (UX)，尤其是在处理 LLM 的延迟时。

## 开始使用

### 基本用法

LangGraph 图暴露了 `stream`（同步）和 `astream`（异步）方法，以迭代器的形式产出流式输出。传递一个或多个流模式 (stream modes) 来控制您接收的数据。

```python
for chunk in graph.stream(
    {"topic": "ice cream"},
    stream_mode=["updates", "custom"],  
    version="v2",  
):
    if chunk["type"] == "updates":
        for node_name, state in chunk["data"].items():
            print(f"Node {node_name} updated: {state}")
    elif chunk["type"] == "custom":
        print(f"Status: {chunk['data']['status']}")
```
**输出**
```shell
Status: thinking of a joke...
Node generate_joke updated: {'joke': 'Why did the ice cream go to school? To get a sundae education!'}
```
**完整示例**
```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer

class State(TypedDict):
  topic: str
  joke: str

def generate_joke(state: State):
  writer = get_stream_writer()
  writer({"status": "thinking of a joke..."})
  return {"joke": f"Why did the {state['topic']} go to school? To get a sundae education!"}

graph = (
  StateGraph(State)
  .add_node(generate_joke)
  .add_edge(START, "generate_joke")
  .add_edge("generate_joke", END)
  .compile()
)

for chunk in graph.stream(
  {"topic": "ice cream"},
  stream_mode=["updates", "custom"],
  version="v2",
):
  if chunk["type"] == "updates":
	  for node_name, state in chunk["data"].items():
		  print(f"Node {node_name} updated: {state}")
  elif chunk["type"] == "custom":
	  print(f"Status: {chunk['data']['status']}")
```
输出
```shell
Status: thinking of a joke...
Node generate_joke updated: {'joke': 'Why did the ice cream go to school? To get a sundae education!'}
```

### 流输出格式 (v2)

向 `stream()` 或 `astream()` 传递 `version="v2"` 以获得统一的输出格式。每个 chunk 都是一个 `StreamPart` 字典，具有一致的形状 — 无论流模式、模式数量或子图设置如何：

```python
{
    "type": "values" | "updates" | "messages" | "custom" | "checkpoints" | "tasks" | "debug",
    "ns": (),           # 命名空间元组，用于子图事件
    "data": ...,        # 实际负载（类型因流模式而异）
}
```

每种流模式都有对应的 `TypedDict`，包含 `ValuesStreamPart`、`UpdatesStreamPart`、`MessagesStreamPart`、`CustomStreamPart`、`CheckpointStreamPart`、`TasksStreamPart`、`DebugStreamPart`。您可以从 `langgraph.types` 导入这些类型。联合类型 `StreamPart` 是基于 `part["type"]` 的不相交联合，支持编辑器和类型检查器中的完整类型收窄。

使用 v1（默认）时，输出格式会根据您的流式选项而变化（单模式返回原始数据，多模式返回 `(mode, data)` 元组，子图返回 `(namespace, data)` 元组）。使用 v2 时，格式始终相同：

```python
for chunk in graph.stream(inputs, stream_mode="updates", version="v2"):
  print(chunk["type"])  # "updates"
  print(chunk["ns"])    # ()
  print(chunk["data"])  # {"node_name": {"key": "value"}}
```

v2 格式还支持类型收窄，这意味着您可以按 `chunk["type"]` 过滤 chunk 并获得正确的负载类型。每个分支将 `part["data"]` 收窄为该模式的特定类型：

```python
for part in graph.stream(
{"topic": "ice cream"},
stream_mode=["values", "updates", "messages", "custom"],
version="v2",
):
if part["type"] == "values":
	# ValuesStreamPart — 每一步之后完整的状态快照
	print(f"State: topic={part['data']['topic']}")
elif part["type"] == "updates":
	# UpdatesStreamPart — 仅每个节点更改的键
	for node_name, state in part["data"].items():
		print(f"Node `{node_name}` updated: {state}")
elif part["type"] == "messages":
	# MessagesStreamPart — 来自 LLM 调用的 (message_chunk, metadata)
	msg, metadata = part["data"]
	print(msg.content, end="", flush=True)
elif part["type"] == "custom":
	# CustomStreamPart — 来自 get_stream_writer() 的任意数据
	print(f"Progress: {part['data']['progress']}%")
```

## 流模式

将一个或多个以下流模式作为列表传递给 `stream` 或 `astream` 方法：

| 模式                        | 类型                                                                                                  | 描述                                                                                                                          |
| :-------------------------- | :---------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------- |
| values      | `ValuesStreamPart`         | 每一步之后的完整状态。                                                                                                        |
| updates     | `UpdatesStreamPart`       | 每一步之后的状态更新。同一步中的多个更新会分别流式传输。                                                                      |
| messages     | `MessagesStreamPart`     | 来自 LLM 调用的 (LLM token, metadata) 二元组。                                                                                 |
| custom      | `CustomStreamPart`         | 节点通过 `get_stream_writer` 发出的自定义数据。 |
| checkpoints | `CheckpointStreamPart` | 检查点事件（格式与 `get_state()` 相同）。需要 checkpointer。                                                                   |
| tasks             | `TasksStreamPart`           | 任务开始/结束事件，包含结果和错误。需要 checkpointer。                                                                        |
| debug             | `DebugStreamPart`           | 所有可用信息 — 结合 `checkpoints` 和 `tasks` 并附加元数据。                                                                    |

### 图状态

使用流模式 `updates` 和 `values` 来流式传输图执行过程中的状态。

* `updates` 在图的每一步之后流式传输状态的**更新**。
* `values` 在图的每一步之后流式传输状态的**完整值**。

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

使用此方法仅流式传输每一步后节点返回的**状态更新**。流式输出包括节点名称以及更新。

```python
for chunk in graph.stream(
	{"topic": "ice cream"},
	stream_mode="updates",  
	version="v2",  
):
	if chunk["type"] == "updates":
		for node_name, state in chunk["data"].items():
			print(f"Node `{node_name}` updated: {state}")
```

```shell
Node `refine_topic` updated: {'topic': 'ice cream and cats'}
Node `generate_joke` updated: {'joke': 'This is a joke about ice cream and cats'}
```

使用此方法流式传输每一步之后图的**完整状态**。

```python
for chunk in graph.stream(
	{"topic": "ice cream"},
	stream_mode="values",  
	version="v2",  
):
	if chunk["type"] == "values":
		print(f"topic: {chunk['data']['topic']}, joke: {chunk['data']['joke']}")
```

```shell
topic: ice cream, joke:
topic: ice cream and cats, joke:
topic: ice cream and cats, joke: This is a joke about ice cream and cats
```

### LLM tokens

使用 `messages` 流式模式从图的任何部分（包括节点、工具、子图或任务）**逐 token** 流式传输大型语言模型 (LLM) 的输出。

`messages` 模式流式传输的输出是一个元组 `(message_chunk, metadata)`，其中：

* `message_chunk`：来自 LLM 的 token 或消息片段。
* `metadata`：包含图节点和 LLM 调用详细信息的字典。

> 如果您的 LLM 不能作为 LangChain 集成使用，您可以改用 `custom` 模式流式传输其输出。有关详细信息，请参见与任意 LLM 一起使用。

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
    """调用 LLM 生成关于主题的笑话"""
    # 注意：即使 LLM 使用 .invoke 而不是 .stream 运行，也会发出消息事件
    model_response = model.invoke(  
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

# "messages" 流模式流式传输带元数据的 LLM tokens
# 使用 version="v2" 获得统一的 StreamPart 格式
for chunk in graph.stream(
    {"topic": "ice cream"},
    stream_mode="messages",  
    version="v2",  
):
    if chunk["type"] == "messages":
        message_chunk, metadata = chunk["data"]
        if message_chunk.content:
            print(message_chunk.content, end="|", flush=True)
```

#### 按 LLM 调用过滤

您可以将 `tags` 与 LLM 调用关联，以按 LLM 调用过滤流式传输的 token。

```python
from langchain.chat_models import init_chat_model

# model_1 标记为 "joke"
model_1 = init_chat_model(model="gpt-5.4-mini", tags=['joke'])
# model_2 标记为 "poem"
model_2 = init_chat_model(model="gpt-5.4-mini", tags=['poem'])

graph = ... # 定义使用这些 LLM 的图

# stream_mode 设置为 "messages" 以流式传输 LLM tokens
# metadata 包含有关 LLM 调用的信息，包括 tags
async for chunk in graph.astream(
    {"topic": "cats"},
    stream_mode="messages",  
    version="v2",  
):
    if chunk["type"] == "messages":
        msg, metadata = chunk["data"]
        # 通过 metadata 中的 tags 字段过滤流式传输的 token，只包含标记为 "joke" 的 LLM 调用的 token
        if metadata["tags"] == ["joke"]:
            print(msg.content, end="|", flush=True)
```
按标签筛选
```python
from typing import TypedDict

from langchain.chat_models import init_chat_model
from langgraph.graph import START, StateGraph

# joke_model 标记为 "joke"
joke_model = init_chat_model(model="gpt-5.4-mini", tags=["joke"])
# poem_model 标记为 "poem"
poem_model = init_chat_model(model="gpt-5.4-mini", tags=["poem"])

class State(TypedDict):
	topic: str
	joke: str
	poem: str

async def call_model(state, config):
	topic = state["topic"]
	print("Writing joke...")
	# 注意：显式传递 config 对于 python < 3.11 是必需的
	# 因为在此之前没有添加上下文变量支持：https://docs.python.org/3/library/asyncio-task.html#creating-tasks
	# 显式传递 config 以确保上下文变量正确传播
	# 这在 Python < 3.11 使用异步代码时是必需的。有关更多详细信息，请参阅异步部分
	joke_response = await joke_model.ainvoke(
		  [{"role": "user", "content": f"Write a joke about {topic}"}],
		  config,
	)
	print("\n\nWriting poem...")
	poem_response = await poem_model.ainvoke(
		  [{"role": "user", "content": f"Write a short poem about {topic}"}],
		  config,
	)
	return {"joke": joke_response.content, "poem": poem_response.content}

graph = (
	StateGraph(State)
	.add_node(call_model)
	.add_edge(START, "call_model")
	.compile()
)

# stream_mode 设置为 "messages" 以流式传输 LLM tokens
# metadata 包含有关 LLM 调用的信息，包括 tags
async for chunk in graph.astream(
	{"topic": "cats"},
	stream_mode="messages",
	version="v2",
):
  if chunk["type"] == "messages":
	  msg, metadata = chunk["data"]
	  if metadata["tags"] == ["joke"]:
		  print(msg.content, end="|", flush=True)
```

#### 从流中省略消息

使用 `nostream` 标签将 LLM 输出完全排除在流之外。标记为 `nostream` 的调用仍然运行并产生输出；它们的 token 只是不会在 `messages` 模式下发出。

这在以下情况下很有用：

* 您需要 LLM 输出用于内部处理（例如结构化输出），但不想将其流式传输到客户端
* 您通过不同通道（例如自定义 UI 消息）流式传输相同内容，并希望避免在 `messages` 流中出现重复输出

```python
from typing import Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langgraph.graph import START, StateGraph

stream_model = ChatAnthropic(model_name="claude-haiku-4-5-20251001")
internal_model = ChatAnthropic(model_name="claude-haiku-4-5-20251001").with_config(
    {"tags": ["nostream"]}
)

class State(TypedDict):
    topic: str
    answer: str
    notes: str

def answer(state: State) -> dict[str, Any]:
    r = stream_model.invoke(
        [{"role": "user", "content": f"Reply briefly about {state['topic']}"}]
    )
    return {"answer": r.content}

def internal_notes(state: State) -> dict[str, Any]:
    # 由于 nostream，此模型的 token 从 stream_mode="messages" 中省略
    r = internal_model.invoke(
        [{"role": "user", "content": f"Private notes on {state['topic']}"}]
    )
    return {"notes": r.content}

graph = (
    StateGraph(State)
    .add_node("write_answer", answer)
    .add_node("internal_notes", internal_notes)
    .add_edge(START, "write_answer")
    .add_edge("write_answer", "internal_notes")
    .compile()
)

initial_state: State = {"topic": "AI", "answer": "", "notes": ""}
stream = graph.stream(initial_state, stream_mode="messages")
```

#### 按节点过滤

要仅流式传输来自特定节点的 token，请使用 `stream_mode="messages"` 并通过流式传输元数据中的 `langgraph_node` 字段过滤输出：

```python
# "messages" 流模式流式传输带元数据的 LLM tokens
# 使用 version="v2" 获得统一的 StreamPart 格式
for chunk in graph.stream(
    inputs,
    stream_mode="messages",  
    version="v2",  
):
    if chunk["type"] == "messages":
        msg, metadata = chunk["data"]
        # 通过 metadata 中的 langgraph_node 字段过滤流式传输的 token
        # 仅包含来自指定节点的 token
        if msg.content and metadata["langgraph_node"] == "some_node_name":
            ...
```
扩展示例
```python
from typing import TypedDict
from langgraph.graph import START, StateGraph
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-5.4-mini")

class State(TypedDict):
	topic: str
	joke: str
	poem: str

def write_joke(state: State):
	topic = state["topic"]
	joke_response = model.invoke(
		  [{"role": "user", "content": f"Write a joke about {topic}"}]
	)
	return {"joke": joke_response.content}

def write_poem(state: State):
	topic = state["topic"]
	poem_response = model.invoke(
		  [{"role": "user", "content": f"Write a short poem about {topic}"}]
	)
	return {"poem": poem_response.content}

graph = (
	StateGraph(State)
	.add_node(write_joke)
	.add_node(write_poem)
	# 同时编写笑话和诗歌
	.add_edge(START, "write_joke")
	.add_edge(START, "write_poem")
	.compile()
)

# "messages" 流模式流式传输带元数据的 LLM tokens
# 使用 version="v2" 获得统一的 StreamPart 格式
for chunk in graph.stream(
  {"topic": "cats"},
  stream_mode="messages",  
  version="v2",  
):
  if chunk["type"] == "messages":
	  msg, metadata = chunk["data"]
	  # 通过 metadata 中的 langgraph_node 字段过滤流式传输的 token
	  # 仅包含来自 write_poem 节点的 token
	  if msg.content and metadata["langgraph_node"] == "write_poem":
		  print(msg.content, end="|", flush=True)
```

### 自定义数据

要从 LangGraph 节点或工具内部发送**自定义用户定义数据**，请按照以下步骤操作：

1.  使用 `get_stream_writer` 访问流写入器并发出自定义数据。
2.  调用 `.stream()` 或 `.astream()` 时设置 `stream_mode="custom"`，以便在流中获取自定义数据。您可以组合多种模式（例如 `["updates", "custom"]`），但至少必须有一个是 `"custom"`。
**节点**
```python
from typing import TypedDict
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph, START

class State(TypedDict):
	query: str
	answer: str

def node(state: State):
	# 获取流写入器以发送自定义数据
	writer = get_stream_writer()
	# 发出自定义键值对（例如进度更新）
	writer({"custom_key": "Generating custom data inside node"})
	return {"answer": "some data"}

graph = (
	StateGraph(State)
	.add_node(node)
	.add_edge(START, "node")
	.compile()
)

inputs = {"query": "example"}

# 设置 stream_mode="custom" 以在流中接收自定义数据
for chunk in graph.stream(inputs, stream_mode="custom", version="v2"):
	if chunk["type"] == "custom":
		print(f"Custom event: {chunk['data']['custom_key']}")
```
**tool**
```python
from langchain.tools import tool
from langgraph.config import get_stream_writer

@tool
def query_database(query: str) -> str:
	"""Query the database."""
	# 访问流写入器以发送自定义数据
	writer = get_stream_writer()  
	# 发出自定义键值对（例如进度更新）
	writer({"data": "Retrieved 0/100 records", "type": "progress"})  
	# 执行查询
	# 发出另一个自定义键值对
	writer({"data": "Retrieved 100/100 records", "type": "progress"})
	return "some-answer"

graph = ... # 定义使用此工具的图

# 设置 stream_mode="custom" 以在流中接收自定义数据
for chunk in graph.stream(inputs, stream_mode="custom", version="v2"):
	if chunk["type"] == "custom":
		print(f"{chunk['data']['type']}: {chunk['data']['data']}")
```

### 子图输出

要在流式传输的输出中包含子图的输出，您可以在父图的 `.stream()` 方法中设置 `subgraphs=True`。这将流式传输父图和任何子图的输出。

输出将作为元组 `(namespace, data)` 流式传输，其中 `namespace` 是包含调用子图的节点路径的元组，例如 `("parent_node:", "child_node:")`。

使用 `version="v2"` 时，子图事件使用相同的 `StreamPart` 格式。`ns` 字段标识源图：

```python
for chunk in graph.stream(
	{"foo": "foo"},
	subgraphs=True,  
	stream_mode="updates",
	version="v2", 
):
	print(chunk["type"])  # "updates"
	print(chunk["ns"])    # () 表示根图，("node_name:",) 表示子图
	print(chunk["data"])  # {"node_name": {"key": "value"}}
```
示例
```python
from langgraph.graph import START, StateGraph
from typing import TypedDict

# 定义子图
class SubgraphState(TypedDict):
  foo: str  # 请注意，此键与父图状态共享
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

for chunk in graph.stream(
  {"foo": "foo"},
  stream_mode="updates",
  # 设置 subgraphs=True 以流式传输子图的输出
  subgraphs=True,  
  version="v2",  
):
  if chunk["type"] == "updates":
	  if chunk["ns"]:
		  print(f"Subgraph {chunk['ns']}: {chunk['data']}")
	  else:
		  print(f"Root: {chunk['data']}")
```

```
Root: {'node_1': {'foo': 'hi! foo'}}
Subgraph ('node_2:dfddc4ba-c3c5-6887-5012-a243b5b377c2',): {'subgraph_node_1': {'bar': 'bar'}}
Subgraph ('node_2:dfddc4ba-c3c5-6887-5012-a243b5b377c2',): {'subgraph_node_2': {'foo': 'hi! foobar'}}
Root: {'node_2': {'foo': 'hi! foobar'}}
```

  **注意**我们不仅收到了节点更新，还收到了命名空间，它告诉我们正在从哪个图（或子图）流式传输。

### 检查点

使用 `checkpoints` 流模式在图形执行时接收检查点事件。每个检查点事件的格式与 `get_state()` 的输出相同。需要 checkpointer。

```python
from langgraph.checkpoint.memory import MemorySaver

graph = (
    StateGraph(State)
    .add_node(refine_topic)
    .add_node(generate_joke)
    .add_edge(START, "refine_topic")
    .add_edge("refine_topic", "generate_joke")
    .add_edge("generate_joke", END)
    .compile(checkpointer=MemorySaver())
)

config = {"configurable": {"thread_id": "1"}}

for chunk in graph.stream(
    {"topic": "ice cream"},
    config=config,
    stream_mode="checkpoints",  
    version="v2",  
):
    if chunk["type"] == "checkpoints":
        print(chunk["data"])
```

### 任务

使用 `tasks` 流模式在图形执行时接收任务开始和结束事件。任务事件包括有关正在运行的节点、其结果以及任何错误的信息。需要 checkpointer。

```python
from langgraph.checkpoint.memory import MemorySaver

graph = (
    StateGraph(State)
    .add_node(refine_topic)
    .add_node(generate_joke)
    .add_edge(START, "refine_topic")
    .add_edge("refine_topic", "generate_joke")
    .add_edge("generate_joke", END)
    .compile(checkpointer=MemorySaver())
)

config = {"configurable": {"thread_id": "1"}}

for chunk in graph.stream(
    {"topic": "ice cream"},
    config=config,
    stream_mode="tasks",  
    version="v2",  
):
    if chunk["type"] == "tasks":
        print(chunk["data"])
```

### 调试

使用 `debug` 流模式在图形执行过程中流式传输尽可能多的信息。流式输出包括节点名称以及完整状态。

```python
for chunk in graph.stream(
    {"topic": "ice cream"},
    stream_mode="debug",  
    version="v2",  
):
    if chunk["type"] == "debug":
        print(chunk["data"])
```

`debug` 模式结合了 `checkpoints` 和 `tasks` 事件以及附加元数据。如果您只需要调试信息的子集，请直接使用 `checkpoints` 或 `tasks`。

### 同时使用多种模式

您可以传递一个列表作为 `stream_mode` 参数，以同时流式传输多种模式。

使用 `version="v2"` 时，每个 chunk 都是一个 `StreamPart` 字典。使用 `chunk["type"]` 区分模式：

```python
for chunk in graph.stream(inputs, stream_mode=["updates", "custom"], version="v2"):
	if chunk["type"] == "updates":
	  for node_name, state in chunk["data"].items():
		  print(f"Node `{node_name}` updated: {state}")
	elif chunk["type"] == "custom":
	  print(f"Custom event: {chunk['data']}")
```

## 高级

### 与任意 LLM 一起使用

您可以使用 `stream_mode="custom"` 从**任何 LLM API** 流式传输数据——即使该 API **未**实现 LangChain 聊天模型接口。

这允许您集成原始的 LLM 客户端或提供自己流式接口的外部服务，使 LangGraph 对自定义设置高度灵活。

```python
from langgraph.config import get_stream_writer

def call_arbitrary_model(state):
    """调用任意模型并流式传输输出的示例节点"""
    # 获取流写入器以发送自定义数据
    writer = get_stream_writer()  
    # 假设您有一个生成 chunk 的流式客户端
    # 使用您的自定义流式客户端生成 LLM tokens
    for chunk in your_custom_streaming_client(state["topic"]):
        # 使用 writer 向流发送自定义数据
        writer({"custom_llm_chunk": chunk})  
    return {"result": "completed"}

graph = (
    StateGraph(State)
    .add_node(call_arbitrary_model)
    # 根据需要添加其他节点和边
    .compile()
)
# 设置 stream_mode="custom" 以在流中接收自定义数据
for chunk in graph.stream(
    {"topic": "cats"},
    stream_mode="custom",  
    version="v2",  
):
    if chunk["type"] == "custom":
        # chunk 数据将包含从 LLM 流式传输的自定义数据
        print(chunk["data"])
```
示例
```python
import operator
import json

from typing import TypedDict
from typing_extensions import Annotated
from langgraph.graph import StateGraph, START

from openai import AsyncOpenAI

openai_client = AsyncOpenAI()
model_name = "gpt-5.4-mini"

async def stream_tokens(model_name: str, messages: list[dict]):
  response = await openai_client.chat.completions.create(
	  messages=messages, model=model_name, stream=True
  )
  role = None
  async for chunk in response:
	  delta = chunk.choices[0].delta

	  if delta.role is not None:
		  role = delta.role

	  if delta.content:
		  yield {"role": role, "content": delta.content}

# 这是我们的工具
async def get_items(place: str) -> str:
  """使用此工具列出在您被问及的地方可能找到的物品。"""
  writer = get_stream_writer()
  response = ""
  async for msg_chunk in stream_tokens(
	  model_name,
	  [
		  {
			  "role": "user",
			  "content": (
				  "Can you tell me what kind of items "
				  f"i might find in the following place: '{place}'. "
				  "List at least 3 such items separating them by a comma. "
				  "And include a brief description of each item."
			  ),
		  }
	  ],
  ):
	  response += msg_chunk["content"]
	  writer(msg_chunk)

  return response

class State(TypedDict):
  messages: Annotated[list[dict], operator.add]

# 这是工具调用图节点
async def call_tool(state: State):
  ai_message = state["messages"][-1]
  tool_call = ai_message["tool_calls"][-1]

  function_name = tool_call["function"]["name"]
  if function_name != "get_items":
	  raise ValueError(f"Tool {function_name} not supported")

  function_arguments = tool_call["function"]["arguments"]
  arguments = json.loads(function_arguments)

  function_response = await get_items(**arguments)
  tool_message = {
	  "tool_call_id": tool_call["id"],
	  "role": "tool",
	  "name": function_name,
	  "content": function_response,
  }
  return {"messages": [tool_message]}

graph = (
  StateGraph(State)
  .add_node(call_tool)
  .add_edge(START, "call_tool")
  .compile()
)
```

  让我们使用包含工具调用的 `AIMessage` 调用图：

  ```python
  inputs = {
      "messages": [
          {
              "content": None,
              "role": "assistant",
              "tool_calls": [
                  {
                      "id": "1",
                      "function": {
                          "arguments": '{"place":"bedroom"}',
                          "name": "get_items",
                      },
                      "type": "function",
                  }
              ],
          }
      ]
  }

  async for chunk in graph.astream(
      inputs,
      stream_mode="custom",
      version="v2",
  ):
      if chunk["type"] == "custom":
          print(chunk["data"]["content"], end="|", flush=True)
  ```

### 禁用特定聊天模型的流式传输

如果您的应用程序混合了支持流式传输和不支持流式传输的模型，您可能需要为不支持流式传输的模型显式禁用流式传输。

初始化模型时设置 `streaming=False`。

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
	"claude-sonnet-4-6",
	# 设置 streaming=False 以禁用聊天模型的流式传输
	streaming=False  
)
```

```python
from langchain_openai import ChatOpenAI

# 设置 streaming=False 以禁用聊天模型的流式传输
model = ChatOpenAI(model="o1-preview", streaming=False)
```

并非所有聊天模型集成都支持 `streaming` 参数。如果您的模型不支持，请改用 `disable_streaming=True`。该参数可通过基类在所有聊天模型上使用。

### 迁移到 v2

v2 流式传输格式（本页贯穿使用）提供了统一的输出格式。以下是关键差异以及如何迁移的摘要：

| 场景                    | v1（默认）                       | v2（`version="v2"`）                               |
| --------------------------- | ---------------------------------- | ------------------------------------------------- |
| 单流模式          | 原始数据 (dict)                    | 带有 `type`, `ns`, `data` 的 `StreamPart` 字典       |
| 多流模式       | `(mode, data)` 元组              | 相同的 `StreamPart` 字典，按 `chunk["type"]` 过滤 |
| 子图流式传输          | `(namespace, data)` 元组         | 相同的 `StreamPart` 字典，检查 `chunk["ns"]`       |
| 多模式 + 子图  | `(namespace, mode, data)` 三元组  | 相同的 `StreamPart` 字典                            |
| `invoke()` 返回类型      | 普通字典 (state)                 | 带有 `.value` 和 `.interrupts` 的 `GraphOutput`     |
| 中断位置 (stream) | 状态字典中的 `__interrupt__` 键  | `values` 流部分上的 `interrupts` 字段       |
| 中断位置 (invoke) | 结果字典中的 `__interrupt__` 键 | `GraphOutput` 上的 `.interrupts` 属性          |
| Pydantic/dataclass 输出   | 返回普通字典                 | 强制转换为模型/dataclass 实例               |

#### v2 invoke 格式

当您向 `invoke()` 或 `ainvoke()` 传递 `version="v2"` 时，它会返回一个带有 `.value` 和 `.interrupts` 属性的 `GraphOutput` 对象：

```python
from langgraph.types import GraphOutput

result = graph.invoke(inputs, version="v2")

assert isinstance(result, GraphOutput)
result.value       # 您的输出 — dict, Pydantic model, 或 dataclass
result.interrupts  # tuple[Interrupt, ...], 如果没有中断则为空
```

对于除默认 `"values"` 之外的任何流模式，`invoke(..., stream_mode="updates", version="v2")` 返回 `list[StreamPart]` 而不是 `list[tuple]`。

在 `GraphOutput` 上进行字典风格的访问（`result["key"]`, `"key" in result`, `result["__interrupt__"]`）仍然可以向后兼容，但**已弃用**，并将在未来版本中删除。迁移到 `result.value` 和 `result.interrupts`。

这将状态与中断元数据分开。使用 v1，中断嵌入在返回的字典中的 `__interrupt__` 下：

```python
config = {"configurable": {"thread_id": "thread-1"}}
result = graph.invoke(inputs, config=config, version="v2")

if result.interrupts:
  print(result.interrupts[0].value)
  graph.invoke(Command(resume=True), config=config, version="v2")
```

#### Pydantic 和 dataclass 状态强制转换

当您的图状态是 Pydantic model 或 dataclass 时，v2 `values` 模式会自动将输出强制转换为正确的类型：

```python
from pydantic import BaseModel
from typing import Annotated
import operator

class MyState(BaseModel):
    value: str
    items: Annotated[list[str], operator.add]

# 使用 version="v2" 时，chunk["data"] 是一个 MyState 实例
for chunk in graph.stream(
    {"value": "x", "items": []}, stream_mode="values", version="v2"
):
    print(type(chunk["data"]))  # <class '__main__.MyState'>
```

### Python < 3.11 的异步

在 Python 版本 < 3.11 中，asyncio 任务不支持 `context` 参数。这限制了 LangGraph 自动传播上下文的能力，并以两种关键方式影响 LangGraph 的流式传输机制：

1.  您**必须**显式地将 `RunnableConfig` 传递给异步 LLM 调用（例如 `ainvoke()`），因为回调不会自动传播。
2.  您**不能**在异步节点或工具中使用 `get_stream_writer`——您必须直接传递 `writer` 参数。

```python
from typing import TypedDict
from langgraph.graph import START, StateGraph
from langchain.chat_models import init_chat_model

model = init_chat_model(model="gpt-5.4-mini")

class State(TypedDict):
    topic: str
    joke: str

# 在异步节点函数中将 config 作为参数接受
async def call_model(state, config):
    topic = state["topic"]
    print("Generating joke...")
    # 将 config 传递给 model.ainvoke() 以确保正确的上下文传播
    joke_response = await model.ainvoke(  
        [{"role": "user", "content": f"Write a joke about {topic}"}],
        config,
    )
    return {"joke": joke_response.content}

graph = (
    StateGraph(State)
    .add_node(call_model)
    .add_edge(START, "call_model")
    .compile()
)

# 设置 stream_mode="messages" 以流式传输 LLM tokens
async for chunk in graph.astream(
    {"topic": "ice cream"},
    stream_mode="messages",  
    version="v2",  
):
    if chunk["type"] == "messages":
        message_chunk, metadata = chunk["data"]
        if message_chunk.content:
            print(message_chunk.content, end="|", flush=True)
```

```python
from typing import TypedDict
from langgraph.types import StreamWriter

class State(TypedDict):
    topic: str
    joke: str

# 在异步节点或工具的函数签名中添加 writer 作为参数
# LangGraph 将自动将流写入器传递给函数
async def generate_joke(state: State, writer: StreamWriter):  
    writer({"custom_key": "Streaming custom data while generating a joke"})
    return {"joke": f"This is a joke about {state['topic']}"}

graph = (
    StateGraph(State)
    .add_node(generate_joke)
    .add_edge(START, "generate_joke")
    .compile()
)

# 设置 stream_mode="custom" 以在流中接收自定义数据  
async for chunk in graph.astream(
    {"topic": "ice cream"},
    stream_mode="custom",
    version="v2",
):
    if chunk["type"] == "custom":
        print(chunk["data"])
```