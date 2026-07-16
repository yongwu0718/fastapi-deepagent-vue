# 在运行时重建 graph

> 使用 `ServerRuntime` 为每次运行以不同配置重建您的 graph。

您可能需要为一次新的运行以不同的配置重建 graph。例如，您可能希望根据用户的凭据加载不同的工具。本指南将展示如何使用 `ServerRuntime` 实现这一点。

在大多数情况下，最佳实践是在单个 **node** 内部根据配置进行条件化处理，而不是动态改变整个 graph 结构。这样更容易测试和管理。

## 前提条件

* 请务必先阅读关于如何为部署设置应用的操作指南。
* `ServerRuntime` 需要 `langgraph-api >= 0.7.31` 和 `langgraph-sdk >= 0.3.5`。在此版本之前，graph 工厂函数只接受单个 `config: RunnableConfig` 参数。

## 定义 Graphs

假设您有一个简单的应用，其中包含一个调用 LLM 并将响应返回给用户的 graph。应用文件目录结构如下：

```
my-app/
|-- langgraph.json
|-- my_project/
|   |-- __init__.py
|   |-- agents.py     # graph 代码
|-- pyproject.toml
```

graph 在 `agents.py` 中定义。

### 不重建（No rebuild）

部署 Agent Server 最常见的方式是引用在文件顶层定义的已编译 graph 实例。示例如下：

```python
# my_project/agents.py
from langgraph.graph import StateGraph, MessagesState, START

async def model(state: MessagesState):
    return {"messages": [{"role": "assistant", "content": "Hi, there!"}]}

graph_workflow = StateGraph(MessagesState)
graph_workflow.add_node("model", model)
graph_workflow.add_edge(START, "model")
agent = graph_workflow.compile()
```

为了让服务器知道您的 graph，您需要在 LangGraph API 配置文件（`langgraph.json`）中指定包含 `CompiledStateGraph` 实例的变量的路径，例如：

```json
{
    "$schema": "https://langgra.ph/schema.json",
    "dependencies": ["."],
    "graphs": {
        "chat_agent": "my_project.agents:agent",
    }
}
```

### 重建（Rebuild）

要为每次新运行重建 graph，请提供一个**工厂函数**，该函数返回（或 yield）一个 graph。工厂函数可以选择性地接受一个 `ServerRuntime` 参数或一个 `RunnableConfig`。服务器会检查您的函数的类型注解，以确定注入哪些参数，因此请确保使用正确的类型提示。每当需要处理一次运行时，服务器的队列工作进程就会调用您的工厂函数。该函数还会在某些其他端点（用于更新状态、读取状态或获取 assistant schemas）中被调用。`ServerRuntime` 会告诉您是什么上下文触发了本次调用。

`ServerRuntime` 目前处于测试阶段，在未来的版本中可能会发生变化。

#### 简单工厂函数

最简单的形式是一个 `async def`，它返回一个已编译的 graph：

```python
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langchain_core.runnables import RunnableConfig
from langgraph_sdk.runtime import ServerRuntime

from my_agent.utils.state import AgentState

model = ChatOpenAI(model="gpt-5.4")

def make_graph_for_user(user_id: str):
    """为每个用户定制构建 graph。"""
    graph_workflow = StateGraph(AgentState)

    async def call_model(state):
        return {"messages": [await model.ainvoke(state["messages"])]}

    graph_workflow.add_node("agent", call_model)
    graph_workflow.add_edge(START, "agent")
    return graph_workflow.compile()

async def make_graph(config: RunnableConfig, runtime: ServerRuntime):
    user = runtime.ensure_user()
    return make_graph_for_user(user.identity)
```

#### 上下文管理器工厂

如果您需要设置和清理资源（数据库连接、加载 MCP tools 等），请使用异步上下文管理器。使用 `runtime.execution_runtime` 来判断 graph 是被用于实际执行，还是仅用于内省（schemas、可视化）：

```python
import contextlib

from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langchain_core.runnables import RunnableConfig
from langgraph_sdk.runtime import ServerRuntime

from my_agent.utils.state import AgentState

model = ChatOpenAI(model="gpt-5.4")

def make_agent_graph(tools: list):
    """创建一个简单的 LLM agent graph。"""
    graph_workflow = StateGraph(AgentState)
    bound = model.bind_tools(tools)

    async def call_model(state):
        return {"messages": [await bound.ainvoke(state["messages"])]}

    graph_workflow.add_node("agent", call_model)
    graph_workflow.add_edge(START, "agent")
    return graph_workflow.compile()

@contextlib.asynccontextmanager
async def make_graph(runtime: ServerRuntime):
    if ert := runtime.execution_runtime:
        # 仅在真正执行时设置昂贵的资源。
        # 内省调用（get_schema、get_graph 等）会跳过这一步。
        mcp_tools = await connect_mcp(ert.ensure_user())  # 您的设置逻辑
        yield make_agent_graph(tools=mcp_tools)
        await disconnect_mcp()  # 您的清理逻辑
    else:
        # 对于 schema/state 读取，返回具有相同拓扑但无需设置昂贵资源的 graph。
        yield make_agent_graph(tools=[])
```

最后，在 `langgraph.json` 中指定工厂函数的路径：

```json
{
    "$schema": "https://langgra.ph/schema.json",
    "dependencies": ["."],
    "graphs": {
        "chat_agent": "my_project.agents:make_graph",
    }
}
```

## ServerRuntime 参考

您的工厂函数会收到一个 `ServerRuntime` 实例，它具有以下属性：

| 属性               | 类型                       | 描述                                                                                       |
| ------------------ | -------------------------- | ------------------------------------------------------------------------------------------ |
| `access_context`   | `str`                      | 工厂函数被调用的原因：`"threads.create_run"`、`"threads.update"`、`"threads.read"` 或 `"assistants.read"`。 |
| `user`             | `BaseUser \| None`         | 已认证的用户，如果未配置自定义认证则为 `None`。                                            |
| `store`            | `BaseStore`                | 用于持久化和记忆的 store 实例。                                                            |

**方法：**

| 方法                  | 描述                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------ |
| `ensure_user()`       | 返回已认证的用户。如果没有提供用户，则抛出 `PermissionError`。                                   |
| `execution_runtime`   | 当 `access_context` 为 `"threads.create_run"` 时返回执行运行时，否则返回 `None`。使用它来仅在执行期间有条件地设置昂贵资源。 |

### 访问上下文（Access contexts）

除了执行运行之外，服务器还会在多种上下文中调用您的工厂函数。在所有上下文中，返回的 graph 应具有**相同的拓扑**（nodes, edges, state schema）。在写上下文（`threads.create_run`、`threads.update`）中，不匹配的拓扑可能导致错误的状态更新。在读上下文（`threads.read`、`assistants.read`）中，拓扑不匹配会影响报告的待处理任务、schemas 和可视化，但不会损坏数据。使用 `execution_runtime` 可以在不改变 graph 结构的情况下有条件地设置昂贵资源。

| 上下文               | 描述                                                                                   |
| -------------------- | -------------------------------------------------------------------------------------- |
| `threads.create_run` | 完整的 graph 执行。`execution_runtime` 可用。                                          |
| `threads.update`     | 通过 `aupdate_state` 更新状态。不执行 node 函数，但可以改变待处理任务。                |
| `threads.read`       | 通过 `aget_state` / `aget_state_history` 读取状态。                                    |
| `assistants.read`    | 用于可视化、MCP、A2A 等的 schema 和 graph 内省。                                       |

## 按 graph 自定义追踪

您可以使用工厂函数来为特定 graph 自定义或禁用追踪。有关示例，请参见“条件追踪：在已部署 agent 中自定义追踪”。

更多信息请参阅 LangGraph API 配置文件。