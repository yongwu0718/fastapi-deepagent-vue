# 如何使用 RemoteGraph 与部署交互

`RemoteGraph` 是一个客户端接口，允许您像使用本地 graph 一样与您的部署进行交互。它与 `CompiledGraph` 具有 API 对等性，这意味着您可以在开发和生产环境中使用相同的方法（`invoke()`、`stream()`、`get_state()` 等）。本页介绍如何初始化 `RemoteGraph` 并与之交互。

`RemoteGraph` 在以下场景中非常有用：

* **开发与部署分离**：在本地使用 `CompiledGraph` 构建和测试 graph，将其部署到 LangSmith，然后在生产环境中使用 `RemoteGraph` 调用它，同时使用相同的 API 接口。
* **线程级持久化**：通过 thread ID 在多次调用之间持久化和获取对话状态。
* **子图嵌入**：通过将 `RemoteGraph` 作为子图嵌入到另一个 graph 中，为多 agent 工作流组合模块化 graph。
* **可复用工作流**：将已部署的 graph 用作节点或工具，从而可以复用和暴露复杂逻辑。

**重要提示：避免调用同一个部署**

`RemoteGraph` 旨在调用其他部署上的 graph。请勿使用 `RemoteGraph` 调用自身或同一部署上的另一个 graph，因为这可能导致死锁和资源耗尽。对于同一部署内的 graph，应使用本地 graph 组合或子图。

## 前提条件

在开始使用 `RemoteGraph` 之前，请确保您具备：

* 可访问 LangSmith，在其中开发和管理您的 graph。
* 一个正在运行的 Agent Server，用于托管已部署的 graph 以进行远程交互。

## 初始化 Graph

初始化 `RemoteGraph` 时，必须始终指定：

* `name`：您要交互的 graph 的名称 **或者** assistant ID。如果指定 graph 名称，将使用默认 assistant。如果指定 assistant ID，将使用该特定 assistant。graph 名称与您在部署的 `langgraph.json` 配置文件中使用的名称相同。
* `api_key`：有效的 LangSmith API key。您可以将其设置为环境变量（`LANGSMITH_API_KEY`）或直接通过 `api_key` 参数传递。如果在初始化 `LangGraphClient` / `SyncLangGraphClient` 时使用了 `api_key` 参数，也可以在 `client` / `sync_client` 参数中提供该 API key。

此外，您必须提供以下之一：

* `url`：您要交互的部署的 URL。如果传递 `url` 参数，将使用提供的 URL、headers（如果提供）和默认配置值（例如超时）创建同步和异步客户端。
* `client`：用于异步与部署交互的 `LangGraphClient` 实例（例如使用 `.astream()`、`.ainvoke()`、`.aget_state()`、`.aupdate_state()`）。
* `sync_client`：用于同步与部署交互的 `SyncLangGraphClient` 实例（例如使用 `.stream()`、`.invoke()`、`.get_state()`、`.update_state()`）。

如果同时传递了 `client` 或 `sync_client` 以及 `url` 参数，则 `client`/`sync_client` 将优先于 `url` 参数。如果未提供 `client` / `sync_client` / `url` 参数中的任何一个，`RemoteGraph` 将在运行时抛出 `ValueError`。

### 使用 URL

```python
from langgraph.pregel.remote import RemoteGraph

url = ""

# 使用 graph 名称（使用默认 assistant）
graph_name = "agent"
remote_graph = RemoteGraph(graph_name, url=url)

# 使用 assistant ID
assistant_id = ""
remote_graph = RemoteGraph(assistant_id, url=url)
```

### 使用 Client

```python
from langgraph_sdk import get_client, get_sync_client
from langgraph.pregel.remote import RemoteGraph

url = ""
client = get_client(url=url)
sync_client = get_sync_client(url=url)

# 使用 graph 名称（使用默认 assistant）
graph_name = "agent"
remote_graph = RemoteGraph(graph_name, client=client, sync_client=sync_client)

# 使用 assistant ID
assistant_id = ""
remote_graph = RemoteGraph(assistant_id, client=client, sync_client=sync_client)
```

## 调用 Graph

`RemoteGraph` 实现了与 `CompiledGraph` 相同的 Runnable 接口，因此您可以像使用已编译 graph 一样使用它。它支持全套标准方法，包括 `.invoke()`、`.stream()`、`.get_state()` 和 `.update_state()`，以及它们的异步变体。

### 异步使用

要异步使用 graph，必须在初始化 `RemoteGraph` 时提供 `url` 或 `client`。

```python
# invoke the graph
result = await remote_graph.ainvoke({
    "messages": [{"role": "user", "content": "what's the weather in sf"}]
})

# stream outputs from the graph
async for chunk in remote_graph.astream({
    "messages": [{"role": "user", "content": "what's the weather in la"}]
}):
    print(chunk)
```

### 同步使用

要同步使用 graph，必须在初始化 `RemoteGraph` 时提供 `url` 或 `sync_client`。

```python
# invoke the graph
result = remote_graph.invoke({
    "messages": [{"role": "user", "content": "what's the weather in sf"}]
})

# stream outputs from the graph
for chunk in remote_graph.stream({
    "messages": [{"role": "user", "content": "what's the weather in la"}]
}):
    print(chunk)
```

## 在线程级别持久化状态

默认情况下，graph 运行（例如使用 `.invoke()` 或 `.stream()` 进行的调用）是无状态的，这意味着中间 checkpoint 和最终状态在运行后不会持久化。

如果您希望保留运行的输出——例如，为了支持人机交互工作流——您可以创建一个 thread 并通过 `config` 参数传递其 ID。其工作方式与常规的已编译 graph 相同：

```python
from langgraph_sdk import get_sync_client

url = ""
graph_name = "agent"
sync_client = get_sync_client(url=url)
remote_graph = RemoteGraph(graph_name, url=url)

# create a thread (or use an existing thread instead)
thread = sync_client.threads.create()

# invoke the graph with the thread config
config = {"configurable": {"thread_id": thread["thread_id"]}}
result = remote_graph.invoke({
    "messages": [{"role": "user", "content": "what's the weather in sf"}]
}, config=config)

# verify that the state was persisted to the thread
thread_state = remote_graph.get_state(config)
print(thread_state)
```

## 用作子图

如果需要在包含 `RemoteGraph` 子图节点的 graph 中使用 `checkpointer`，请确保使用 UUID 作为 thread ID。

一个 graph 也可以调用多个 `RemoteGraph` 实例作为*子图*节点。这允许构建模块化、可扩展的工作流，将不同的职责拆分到不同的 graph 中。

`RemoteGraph` 暴露了与常规 `CompiledGraph` 相同的接口，因此您可以直接将其用作另一个 graph 内部的子图。例如：

```python
from langgraph_sdk import get_sync_client
from langgraph.graph import StateGraph, MessagesState, START
from typing import TypedDict

url = ""
graph_name = "agent"
remote_graph = RemoteGraph(graph_name, url=url)

# define parent graph
builder = StateGraph(MessagesState)
# add remote graph directly as a node
builder.add_node("child", remote_graph)
builder.add_edge(START, "child")
graph = builder.compile()

# invoke the parent graph
result = graph.invoke({
    "messages": [{"role": "user", "content": "what's the weather in sf"}]
})
print(result)

# stream outputs from both the parent graph and subgraph
for chunk in graph.stream({
    "messages": [{"role": "user", "content": "what's the weather in sf"}]
}, subgraphs=True):
    print(chunk)
```