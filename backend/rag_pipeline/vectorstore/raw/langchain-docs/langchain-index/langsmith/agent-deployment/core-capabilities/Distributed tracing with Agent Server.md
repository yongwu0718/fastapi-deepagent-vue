# 使用 Agent Server 进行分布式追踪

> 当您从另一个服务通过 `RemoteGraph` 或 SDK 调用已部署的 Agent Server 时，统一追踪。

当您从另一个服务调用已部署的 Agent Server 时，可以传播 trace 上下文，以便整个请求在 LangSmith 中显示为单个统一的 trace。这利用了 LangSmith 的分布式追踪能力，它通过 HTTP headers 传播上下文。

## 工作原理

分布式追踪通过上下文传播 headers 来链接跨服务的 runs：

1. **客户端**从当前 run 推断 trace 上下文，并将其作为 HTTP headers 发送。
2. **服务器**读取这些 headers，并将它们作为 `langsmith-trace` 和 `langsmith-project` 可配置值添加到 run 的 config 和 metadata 中。您可以选择使用它们来为您的 agent 被使用时的某个 run 设置追踪上下文。

使用的 headers 包括：

* `langsmith-trace`：包含 trace 的点分顺序。
* `baggage`：指定 LangSmith 项目以及其他可选的 tags 和 metadata。

要选择加入分布式追踪，客户端和服务器都需要选择加入。

## 配置服务器

要接受分布式 trace 上下文，您的 graph 必须从 config 中读取 trace headers 并设置追踪上下文。这些 headers 通过 `configurable` 字段作为 `langsmith-trace` 和 `langsmith-project` 传递。

```python
import contextlib
import langsmith as ls
from langgraph.graph import StateGraph, MessagesState

# Define your graph
builder = StateGraph(MessagesState)
# ... add nodes and edges ...
my_graph = builder.compile()

@contextlib.contextmanager
async def graph(config):
    configurable = config.get("configurable", {})
    parent_trace = configurable.get("langsmith-trace")
    parent_project = configurable.get("langsmith-project")
    # If you want to also include metadata and tags from the client
    metadata = configurable.get("langsmith-metadata")
    tags = configurable.get("langsmith-tags")
    with ls.tracing_context(parent=parent_trace, project_name=parent_project, metadata=metadata, tags=tags):
        yield my_graph
```

在您的 `langgraph.json` 中导出此 `graph` 函数：

```json
{
  "graphs": {
    "agent": "./src/agent.py:graph"
  }
}
```

## 从客户端连接
**remote_graph 示例**
在初始化 `RemoteGraph` 时设置 `distributed_tracing=True`。这将自动在所有请求上传播 trace headers。

```python
from langgraph.graph import StateGraph
from langgraph.pregel.remote import RemoteGraph

remote_graph = RemoteGraph(
    "agent",
    url="<your_url>",
    distributed_tracing=True,  # Enable trace propagation
)

def subgraph_node(query: str):
    # Trace context is automatically propagated
    return remote_graph.invoke({
        "messages": [{"role": "user", "content": query}]
    })['messages'][-1]['content']

# The RemoteGraph is called in the context of some on going work.
# This could be a parent LangGraph agent, code traced with `@ls.traceable`,
# or any other instrumented code.
graph = (
        StateGraph(str)
            .add_node(subgraph_node)
            .add_edge("__start__", "subgraph_node")
            .compile()
)
# The remote graph's execution will appear as a child of this trace
result = graph.invoke("What's the weather in SF?")
```

**SDK 示例**
如果您直接使用 LangGraph SDK，请使用 `run_tree.to_headers()` 手动传播 trace headers：

```python
from langgraph_sdk import get_client
import langsmith as ls

client = get_client(url="<your_url>")

with ls.trace("call_remote_agent", inputs={"query": query}) as rt:
    headers = rt.to_headers()
    async for chunk in client.runs.stream(
        thread_id=None,
        assistant_id="agent",
        input={"messages": [{"role": "user", "content": query}]},
        stream_mode="values",
        headers=headers,  # Pass trace headers
    ):
        pass
    return chunk

result = await call_remote_agent("What's the weather in SF?")
```

## 相关内容

* 分布式追踪：通用的分布式追踪概念和模式
* RemoteGraph：关于使用 `RemoteGraph` 与部署交互的完整指南