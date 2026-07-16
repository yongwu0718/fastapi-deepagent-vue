# Memory

AI 应用程序需要记忆来跨多个交互共享上下文。在 LangGraph 中，您可以添加两种类型的记忆：

* 将短期记忆作为 agent 状态的一部分，以支持多轮对话。
* 添加长期记忆，以存储跨会话的用户特定或应用级数据。

## 添加短期记忆

**短期**记忆（线程级持久化）使 agent 能够跟踪多轮对话。要添加短期记忆：

```python
from langgraph.checkpoint.memory import InMemorySaver  
from langgraph.graph import StateGraph

checkpointer = InMemorySaver()  

builder = StateGraph(...)
graph = builder.compile(checkpointer=checkpointer)  

graph.invoke(
    {"messages": [{"role": "user", "content": "hi! i am Bob"}]},
    {"configurable": {"thread_id": "1"}},  
)
```

### 在生产环境中使用

在生产环境中，使用由数据库支持的 checkpointer：

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:  
    builder = StateGraph(...)
    graph = builder.compile(checkpointer=checkpointer)  
```


```
pip install -U pymongo langgraph langgraph-checkpoint-mongodb
```

**设置**
    要使用 MongoDB checkpointer，您需要一个 MongoDB 集群。如果还没有集群，请按照本指南创建一个。

```python
  from langchain.chat_models import init_chat_model
  from langgraph.graph import StateGraph, MessagesState, START
  from langgraph.checkpoint.mongodb import MongoDBSaver  

  model = init_chat_model(model="claude-haiku-4-5-20251001")

  MONGODB_URI = "localhost:27017"
  with MongoDBSaver.from_conn_string(MONGODB_URI) as checkpointer:  

	  def call_model(state: MessagesState):
		  response = model.invoke(state["messages"])
		  return {"messages": response}

	  builder = StateGraph(MessagesState)
	  builder.add_node(call_model)
	  builder.add_edge(START, "call_model")

	  graph = builder.compile(checkpointer=checkpointer)  

	  config = {
		  "configurable": {
			  "thread_id": "1"  
		  }
	  }

	  for chunk in graph.stream(
		  {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
		  config,  
		  stream_mode="values"
	  ):
		  chunk["messages"][-1].pretty_print()

	  for chunk in graph.stream(
		  {"messages": [{"role": "user", "content": "what's my name?"}]},
		  config,  
		  stream_mode="values"
	  ):
		  chunk["messages"][-1].pretty_print()
  ```

```python
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver  

model = init_chat_model(model="claude-haiku-4-5-20251001")

MONGODB_URI = "localhost:27017"
async with AsyncMongoDBSaver.from_conn_string(MONGODB_URI) as checkpointer:  

  async def call_model(state: MessagesState):
	  response = await model.ainvoke(state["messages"])
	  return {"messages": response}

  builder = StateGraph(MessagesState)
  builder.add_node(call_model)
  builder.add_edge(START, "call_model")

  graph = builder.compile(checkpointer=checkpointer)  

  config = {
	  "configurable": {
		  "thread_id": "1"  
	  }
  }

  async for chunk in graph.astream(
	  {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
	  config,  
	  stream_mode="values"
  ):
	  chunk["messages"][-1].pretty_print()

  async for chunk in graph.astream(
	  {"messages": [{"role": "user", "content": "what's my name?"}]},
	  config,  
	  stream_mode="values"
  ):
	  chunk["messages"][-1].pretty_print()
```

### 在子图中使用

如果您的图包含子图，您只需要在编译父图时提供 checkpointer。LangGraph 会自动将 checkpointer 传播到子子图。

```python
from langgraph.graph import START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict

class State(TypedDict):
    foo: str

# 子图

def subgraph_node_1(state: State):
    return {"foo": state["foo"] + "bar"}

subgraph_builder = StateGraph(State)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()  

# 父图

builder = StateGraph(State)
builder.add_node("node_1", subgraph)  
builder.add_edge(START, "node_1")

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)  
```

您可以配置特定于子图的 checkpointing 行为。有关持久化级别（包括中断支持和有状态延续）的详细信息，请参阅子图持久化。

```python
subgraph_builder = StateGraph(...)
subgraph = subgraph_builder.compile(checkpointer=True)  
```

## 添加长期记忆

使用长期记忆来存储跨对话的用户特定或应用特定数据。

```python
from langgraph.store.memory import InMemoryStore  
from langgraph.graph import StateGraph

store = InMemoryStore()  

builder = StateGraph(...)
graph = builder.compile(store=store)  
```

### 在节点内部访问存储

一旦您使用 store 编译图，LangGraph 会自动将 store 注入到您的节点函数中。推荐通过 `Runtime` 对象访问 store。

```python
from dataclasses import dataclass
from langgraph.runtime import Runtime
from langgraph.graph import StateGraph, MessagesState, START
import uuid

@dataclass
class Context:
    user_id: str

async def call_model(state: MessagesState, runtime: Runtime[Context]):  
    user_id = runtime.context.user_id  
    namespace = (user_id, "memories")

    # 搜索相关记忆
    memories = await runtime.store.asearch(  
        namespace, query=state["messages"][-1].content, limit=3
    )
    info = "\n".join([d.value["data"] for d in memories])

    # ... 在模型调用中使用记忆

    # 存储新记忆
    await runtime.store.aput(  
        namespace, str(uuid.uuid4()), {"data": "User prefers dark mode"}
    )

builder = StateGraph(MessagesState, context_schema=Context)  
builder.add_node(call_model)
builder.add_edge(START, "call_model")
graph = builder.compile(store=store)

# 调用时传递上下文
graph.invoke(
    {"messages": [{"role": "user", "content": "hi"}]},
    {"configurable": {"thread_id": "1"}},
    context=Context(user_id="1"),  
)
```

### 在生产环境中使用

在生产环境中，使用由数据库支持的 store：

```python
from langgraph.store.postgres import PostgresStore

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
with PostgresStore.from_conn_string(DB_URI) as store:  
    builder = StateGraph(...)
    graph = builder.compile(store=store)  
```

```python
from dataclasses import dataclass
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore  
from langgraph.runtime import Runtime  
import uuid

model = init_chat_model(model="claude-haiku-4-5-20251001")

@dataclass
class Context:
    user_id: str

def call_model(
    state: MessagesState,
    runtime: Runtime[Context],
):
    user_id = runtime.context.user_id  
    namespace = ("memories", user_id)
    memories = runtime.store.search(namespace, query=str(state["messages"][-1].content))
    info = "\n".join([d.value["data"] for d in memories])
    system_msg = f"You are a helpful assistant talking to the user. User info: {info}"

    # Store new memories if the user asks the model to remember
    last_message = state["messages"][-1]
    if "remember" in last_message.content.lower():
        memory = "User name is Bob"
        runtime.store.put(namespace, str(uuid.uuid4()), {"data": memory})

    response = model.invoke(
        [{"role": "system", "content": system_msg}] + state["messages"]
    )
    return {"messages": response}

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"

with (
    PostgresStore.from_conn_string(DB_URI) as store,
    PostgresSaver.from_conn_string(DB_URI) as checkpointer,
):
    # store.setup()
    # checkpointer.setup()

    builder = StateGraph(MessagesState, context_schema=Context)
    builder.add_node(call_model)
    builder.add_edge(START, "call_model")

    graph = builder.compile(
        checkpointer=checkpointer,
        store=store,
    )

    config = {"configurable": {"thread_id": "1"}}
    for chunk in graph.stream(
        {"messages": [{"role": "user", "content": "Hi! Remember: my name is Bob"}]},
        config,
        stream_mode="values",
        context=Context(user_id="1"),
    ):
        chunk["messages"][-1].pretty_print()

    config = {"configurable": {"thread_id": "2"}}
    for chunk in graph.stream(
        {"messages": [{"role": "user", "content": "what is my name?"}]},
        config,
        stream_mode="values",
        context=Context(user_id="1"),
    ):
        chunk["messages"][-1].pretty_print()
```
### 使用语义搜索

在图的内存存储中启用语义搜索，让图的 agents 能够通过语义相似性搜索存储中的项目。

```python
from langchain.embeddings import init_embeddings
from langgraph.store.memory import InMemoryStore

# 创建启用语义搜索的存储
embeddings = init_embeddings("openai:text-embedding-3-small")
store = InMemoryStore(
    index={
        "embed": embeddings,
        "dims": 1536,
    }
)

store.put(("user_123", "memories"), "1", {"text": "I love pizza"})
store.put(("user_123", "memories"), "2", {"text": "I am a plumber"})

items = store.search(
    ("user_123", "memories"), query="I'm hungry", limit=1
)
```

带语义搜索的长期记忆

```python

from langchain.embeddings import init_embeddings
from langchain.chat_models import init_chat_model
from langgraph.store.memory import InMemoryStore
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.runtime import Runtime  

model = init_chat_model("gpt-5.4-mini")

# 创建启用语义搜索的存储
embeddings = init_embeddings("openai:text-embedding-3-small")
store = InMemoryStore(
  index={
	  "embed": embeddings,
	  "dims": 1536,
  }
)

store.put(("user_123", "memories"), "1", {"text": "I love pizza"})
store.put(("user_123", "memories"), "2", {"text": "I am a plumber"})

async def chat(state: MessagesState, runtime: Runtime):  
  # 根据用户的最后一条消息进行搜索
  items = await runtime.store.asearch(  
	  ("user_123", "memories"), query=state["messages"][-1].content, limit=2
  )
  memories = "\n".join(item.value["text"] for item in items)
  memories = f"## Memories of user\n{memories}" if memories else ""
  response = await model.ainvoke(
	  [
		  {"role": "system", "content": f"You are a helpful assistant.\n{memories}"},
		  *state["messages"],
	  ]
  )
  return {"messages": [response]}

builder = StateGraph(MessagesState)
builder.add_node(chat)
builder.add_edge(START, "chat")
graph = builder.compile(store=store)

async for message, metadata in graph.astream(
  input={"messages": [{"role": "user", "content": "I'm hungry"}]},
  stream_mode="messages",
):
  print(message.content, end="")
```

## 管理短期记忆

启用短期记忆后，长对话可能会超过 LLM 的上下文窗口。常见的解决方案有：

* 修剪消息：移除前 N 条或后 N 条消息（在调用 LLM 之前）
* 从 LangGraph 状态中永久删除消息
* 总结消息：总结历史中较早的消息并用摘要替换它们
* 管理检查点以存储和检索消息历史
* 自定义策略（例如，消息过滤等）

这使得 agent 能够跟踪对话而不会超出 LLM 的上下文窗口。

### 修剪消息

大多数 LLM 都有一个最大支持的上下文窗口（以 tokens 计）。决定何时截断消息的一种方法是计算消息历史中的 token 数量，并在接近该限制时进行截断。如果您使用 LangChain，可以使用消息修剪工具，并指定要从列表中保留的 token 数量，以及用于处理边界的 `strategy`（例如，保留最后 `max_tokens` 条消息）。

要修剪消息历史，请使用 `trim_messages` 函数：

```python
from langchain_core.messages.utils import (  
    trim_messages,  
    count_tokens_approximately  
)  

def call_model(state: MessagesState):
    messages = trim_messages(  
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=128,
        start_on="human",
        end_on=("human", "tool"),
    )
    response = model.invoke(messages)
    return {"messages": [response]}

builder = StateGraph(MessagesState)
builder.add_node(call_model)
...
```

```python
from langchain_core.messages.utils import (
  trim_messages,  
  count_tokens_approximately  
)
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, MessagesState

model = init_chat_model("claude-sonnet-4-6")
summarization_model = model.bind(max_tokens=128)

def call_model(state: MessagesState):
  messages = trim_messages(  
	  state["messages"],
	  strategy="last",
	  token_counter=count_tokens_approximately,
	  max_tokens=128,
	  start_on="human",
	  end_on=("human", "tool"),
  )
  response = model.invoke(messages)
  return {"messages": [response]}

checkpointer = InMemorySaver()
builder = StateGraph(MessagesState)
builder.add_node(call_model)
builder.add_edge(START, "call_model")
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "1"}}
graph.invoke({"messages": "hi, my name is bob"}, config)
graph.invoke({"messages": "write a short poem about cats"}, config)
graph.invoke({"messages": "now do the same but for dogs"}, config)
final_response = graph.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
```

```
Ai Message 

Your name is Bob, as you mentioned when you first introduced yourself.
```

### 删除消息

您可以从图状态中删除消息以管理消息历史。当您想要删除特定消息或清除整个消息历史时，这非常有用。

要从图状态中删除消息，您可以使用 `RemoveMessage`。要使 `RemoveMessage` 生效，您需要使用带有 `add_messages` reducer 的状态键，比如 `MessagesState`。

要删除特定消息：

```python
from langchain.messages import RemoveMessage  

def delete_messages(state):
    messages = state["messages"]
    if len(messages) > 2:
        # 移除最早的两条消息
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}  
```

要删除**所有**消息：

```python
from langgraph.graph.message import REMOVE_ALL_MESSAGES  

def delete_messages(state):
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}  
```

删除消息时，**请确保**生成的消息历史是有效的。请检查您正在使用的 LLM provider 的限制。例如：

  * 某些 providers 期望消息历史以 `user` 消息开头
  * 大多数 providers 要求带有 tool calls 的 `assistant` 消息后必须跟随相应的 `tool` 结果消息。

```python
from langchain.messages import RemoveMessage  

def delete_messages(state):
  messages = state["messages"]
  if len(messages) > 2:
	  # 移除最早的两条消息
	  return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}  

def call_model(state: MessagesState):
  response = model.invoke(state["messages"])
  return {"messages": response}

builder = StateGraph(MessagesState)
builder.add_sequence([call_model, delete_messages])
builder.add_edge(START, "call_model")

checkpointer = InMemorySaver()
app = builder.compile(checkpointer=checkpointer)

for event in app.stream(
  {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
  config,
  stream_mode="values"
):
  print([(message.type, message.content) for message in event["messages"]])

for event in app.stream(
  {"messages": [{"role": "user", "content": "what's my name?"}]},
  config,
  stream_mode="values"
):
  print([(message.type, message.content) for message in event["messages"]])
```

```
[('human', "hi! I'm bob")]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! How are you doing today? Is there anything I can help you with?')]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! How are you doing today? Is there anything I can help you with?'), ('human', "what's my name?")]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! How are you doing today? Is there anything I can help you with?'), ('human', "what's my name?"), ('ai', 'Your name is Bob.')]
[('human', "what's my name?"), ('ai', 'Your name is Bob.')]
```

### 总结消息

如上所示，修剪或删除消息的问题在于，您可能会因为删除消息队列而丢失信息。因此，一些应用程序受益于使用聊天模型对消息历史进行总结的更复杂方法。

可以使用提示和编排逻辑来总结消息历史。例如，在 LangGraph 中，您可以扩展 `MessagesState` 以包含一个 `summary` 键：

```python
from langgraph.graph import MessagesState
class State(MessagesState):
    summary: str
```

然后，您可以使用任何现有的摘要作为下一个摘要的上下文，生成聊天历史的摘要。当 `messages` 状态键中累积了一定数量的消息后，可以调用这个 `summarize_conversation` 节点。

```python
def summarize_conversation(state: State):

    # 首先，获取任何现有的摘要
    summary = state.get("summary", "")

    # 创建我们的摘要提示
    if summary:

        # 摘要已存在
        summary_message = (
            f"This is a summary of the conversation to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )

    else:
        summary_message = "Create a summary of the conversation above:"

    # 将提示添加到我们的历史中
    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = model.invoke(messages)

    # 删除除最近 2 条消息之外的所有消息
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    return {"summary": response.content, "messages": delete_messages}
```

完整示例
```python
from typing import Any, TypedDict

from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langmem.short_term import SummarizationNode, RunningSummary  

model = init_chat_model("claude-sonnet-4-6")
summarization_model = model.bind(max_tokens=128)

class State(MessagesState):
  context: dict[str, RunningSummary]  

class LLMInputState(TypedDict):  
  summarized_messages: list[AnyMessage]
  context: dict[str, RunningSummary]

summarization_node = SummarizationNode(  
  token_counter=count_tokens_approximately,
  model=summarization_model,
  max_tokens=256,
  max_tokens_before_summary=256,
  max_summary_tokens=128,
)

def call_model(state: LLMInputState):  
  response = model.invoke(state["summarized_messages"])
  return {"messages": [response]}

checkpointer = InMemorySaver()
builder = StateGraph(State)
builder.add_node(call_model)
builder.add_node("summarize", summarization_node)  
builder.add_edge(START, "summarize")
builder.add_edge("summarize", "call_model")
graph = builder.compile(checkpointer=checkpointer)

# 调用图
config = {"configurable": {"thread_id": "1"}}
graph.invoke({"messages": "hi, my name is bob"}, config)
graph.invoke({"messages": "write a short poem about cats"}, config)
graph.invoke({"messages": "now do the same but for dogs"}, config)
final_response = graph.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
print("\nSummary:", final_response["context"]["running_summary"].summary)
```

  1. 我们将在 `context` 字段中跟踪正在运行的摘要

  （`SummarizationNode` 所期望的）。

  2. 定义私有状态，该状态将仅用于过滤

  `call_model` 节点的输入。

  3. 我们在这里传递一个私有输入状态，以隔离由总结节点返回的消息

  ```
  ================================== Ai Message ==================================

  From our conversation, I can see that you introduced yourself as Bob. That's the name you shared with me when we began talking.

  Summary: In this conversation, I was introduced to Bob, who then asked me to write a poem about cats. I composed a poem titled "The Mystery of Cats" that captured cats' graceful movements, independent nature, and their special relationship with humans. Bob then requested a similar poem about dogs, so I wrote "The Joy of Dogs," which highlighted dogs' loyalty, enthusiasm, and loving companionship. Both poems were written in a similar style but emphasized the distinct characteristics that make each pet special.
  ```

### 管理检查点

您可以查看和删除 checkpointer 存储的信息。

#### 查看线程状态

```python
config = {
	"configurable": {
		"thread_id": "1",  
		# 可选地提供特定检查点的 ID，
		# 否则将显示最新的检查点
		# "checkpoint_id": "1f029ca3-1f5b-6704-8004-820c16b69a5a"  

	}
}
graph.get_state(config)  
```

```
StateSnapshot(
	values={'messages': [HumanMessage(content="hi! I'm bob"), AIMessage(content='Hi Bob! How are you doing today?), HumanMessage(content="what's my name?"), AIMessage(content='Your name is Bob.')]}, next=(),
	config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1f029ca3-1f5b-6704-8004-820c16b69a5a'}},
	metadata={
		'source': 'loop',
		'writes': {'call_model': {'messages': AIMessage(content='Your name is Bob.')}},
		'step': 4,
		'parents': {},
		'thread_id': '1'
	},
	created_at='2025-05-05T16:01:24.680462+00:00',
	parent_config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1f029ca3-1790-6b0a-8003-baf965b6a38f'}},
	tasks=(),
	interrupts=()
)
```

```python
config = {
	"configurable": {
		"thread_id": "1",  
		# 可选地提供特定检查点的 ID，
		# 否则将显示最新的检查点
		# "checkpoint_id": "1f029ca3-1f5b-6704-8004-820c16b69a5a"  

	}
}
checkpointer.get_tuple(config)  
```

#### 查看线程的历史记录

```python
config = {
	"configurable": {
		"thread_id": "1"  
	}
}
list(graph.get_state_history(config))  
```

```python
config = {
	"configurable": {
		"thread_id": "1"  
	}
}
list(checkpointer.list(config))  
```

#### 删除一个线程的所有检查点

```python
thread_id = "1"
checkpointer.delete_thread(thread_id)
```

## 数据库管理

如果您正在使用任何基于数据库的持久化实现（例如 Postgres 或 Redis）来存储短期和/或长期记忆，您需要在将其与数据库一起使用之前运行迁移以设置所需的模式。

按照惯例，大多数特定于数据库的库在 checkpointer 或 store 实例上定义了一个 `setup()` 方法来运行所需的迁移。但是，您应该检查您使用的 `BaseCheckpointSaver` 或 `BaseStore` 的具体实现，以确认确切的方法名称和用法。

我们建议将迁移作为专门的部署步骤运行，或者您可以确保它们在服务器启动时作为一部分运行。