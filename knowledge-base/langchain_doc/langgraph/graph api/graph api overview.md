# Graphs

LangGraph 的核心是将 agent 工作流建模为图 (graphs)。您使用三个关键组件来定义 agent 的行为：

1. `State`：一个共享的数据结构，代表应用程序的当前快照。它可以是任何数据类型，但通常使用共享的状态模式 (state schema) 来定义。

2. `Nodes`：封装 agent 逻辑的函数。它们接收当前状态作为输入，执行一些计算或副作用，并返回更新后的状态。

3. `Edges`：根据当前状态决定接下来执行哪个 `Node` 的函数。它们可以是条件分支或固定转换。

通过组合 `Nodes` 和 `Edges`，您可以创建复杂的、循环的工作流，使状态随时间演变。然而，真正的力量来自于 LangGraph 如何管理该状态。

需要强调的是：`Nodes` 和 `Edges` 只不过是函数——它们可以包含 LLM，也可以仅仅是普通的代码。

简而言之：*节点负责工作，边决定下一步做什么*。

LangGraph 底层的图算法使用消息传递来定义通用程序。当一个节点完成其操作时，它会沿着一条或多条边向其他节点发送消息。这些接收节点随后执行它们的函数，将结果消息传递给下一组节点，如此继续。受 Google 的 Pregel 系统启发，程序以离散的“超级步骤 (super-steps)”进行。

一个超级步骤可以被视为对图节点的一次迭代。并行运行的节点属于同一个超级步骤，而顺序运行的节点属于不同的超级步骤。在图执行开始时，所有节点都处于 `inactive` 状态。当一个节点在其任何传入边（或“通道”）上收到新消息（状态）时，它会变为 `active` 状态。然后，活动节点运行其函数并响应更新。在每个超级步骤结束时，没有传入消息的节点通过将自己标记为 `inactive` 来投票“停止”。当所有节点都是 `inactive` 且没有消息在传输中时，图执行终止。

### StateGraph

`StateGraph` 类是主要使用的图类。它由用户定义的 `State` 对象参数化。

### 编译您的图

要构建您的图，您首先定义状态，然后添加节点和边，最后编译它。编译您的图究竟是什么？为什么需要它？

编译是一个相当简单的步骤。它对图的结构进行一些基本检查（例如，没有孤立节点等）。它也是您可以指定运行时参数（如 checkpointers 和断点）的地方。您只需调用 `.compile` 方法来编译图：

```python
graph = graph_builder.compile(...)
```

在可以使用图之前，您**必须**编译它。

## State

定义图时，您做的第一件事是定义图的 `State`。`State` 包括图的模式 (schema) 以及指定如何将更新应用于状态的 reducer 函数。`State` 的模式将是图中所有 `Nodes` 和 `Edges` 的输入模式，可以是 `TypedDict` 或 `Pydantic` 模型。所有 `Nodes` 都会发出对 `State` 的更新，然后使用指定的 reducer 函数应用这些更新。

### Schema

指定图模式的主要文档化方法是使用 `TypedDict`。如果您想在状态中提供默认值，请使用 `dataclass`。如果您需要递归数据验证，我们也支持使用 Pydantic `BaseModel` 作为图状态（但请注意，Pydantic 的性能不如 `TypedDict` 或 `dataclass`）。

默认情况下，图具有相同的输入和输出模式。如果您想更改这一点，您也可以直接指定显式的输入和输出模式。当您有很多键，其中一些明确用于输入，另一些用于输出时，这很有用。有关更多信息，请参阅指南。

`langchain` 中更高级的 `create_agent` 工厂不支持 Pydantic 状态模式。

#### 多模式 (Multiple schemas)

通常，所有图节点都使用单一模式进行通信。这意味着它们将读取和写入相同的状态通道。但是，在某些情况下，我们希望对此有更多控制：

* 内部节点可以传递图输入/输出中不需要的信息。
* 我们可能还想为图使用不同的输入/输出模式。例如，输出可能只包含一个相关的输出键。

可以让节点将信息写入图内部的私有状态通道，用于内部节点通信。我们可以简单地定义一个私有模式 `PrivateState`。

也可以为图定义显式的输入和输出模式。在这些情况下，我们定义一个包含图操作*所有*相关键的“内部”模式。但是，我们还定义了 `input` 和 `output` 模式，它们是“内部”模式的子集，以约束图的输入和输出。有关更多详细信息，请参阅定义输入和输出模式。

让我们看一个例子：

```python
class InputState(TypedDict):
    user_input: str

class OutputState(TypedDict):
    graph_output: str

class OverallState(TypedDict):
    foo: str
    user_input: str
    graph_output: str

class PrivateState(TypedDict):
    bar: str

def node_1(state: InputState) -> OverallState:
    # 写入 OverallState
    return {"foo": state["user_input"] + " name"}

def node_2(state: OverallState) -> PrivateState:
    # 从 OverallState 读取，写入 PrivateState
    return {"bar": state["foo"] + " is"}

def node_3(state: PrivateState) -> OutputState:
    # 从 PrivateState 读取，写入 OutputState
    return {"graph_output": state["bar"] + " Lance"}

builder = StateGraph(OverallState, input_schema=InputState, output_schema=OutputState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)

graph = builder.compile()
graph.invoke({"user_input":"My"})
# {'graph_output': 'My name is Lance'}
```

这里有两个微妙而重要的点需要注意：

1.  我们将 `state: InputState` 作为输入模式传递给 `node_1`。但是，我们写入 `foo`，它是 `OverallState` 中的一个通道。我们如何写入一个未包含在输入模式中的状态通道？这是因为一个节点*可以写入图状态中的任何状态通道。* 图状态是在初始化时定义的状态通道的并集，其中包括 `OverallState` 以及过滤器 `InputState` 和 `OutputState`。

2.  我们使用以下方式初始化图：

    ```python
    StateGraph(
        OverallState,
        input_schema=InputState,
        output_schema=OutputState
    )
    ```

    我们如何在 `node_2` 中写入 `PrivateState`？如果该模式未在 `StateGraph` 初始化中传递，图如何获得对该模式的访问权？

    我们可以这样做，因为只要状态模式定义存在，`_nodes` 也可以声明额外的状态 `channels_`。在这种情况下，`PrivateState` 模式已定义，因此我们可以将 `bar` 作为新的状态通道添加到图中并写入它。

### Reducers

Reducers 是理解来自节点的更新如何应用于 `State` 的关键。`State` 中的每个键都有自己独立的 reducer 函数。如果没有明确指定 reducer 函数，则假定对该键的所有更新都应覆盖它。有几种不同类型的 reducer，从默认的 reducer 类型开始：

#### 默认 Reducer

这两个示例展示了如何使用默认 reducer：

```python
from typing_extensions import TypedDict

class State(TypedDict):
    foo: int
    bar: list[str]
```

在此示例中，没有为任何键指定 reducer 函数。假设图的输入是：`{"foo": 1, "bar": ["hi"]}`。然后假设第一个 `Node` 返回 `{"foo": 2}`。这被视为对状态的更新。请注意，`Node` 不需要返回整个 `State` 模式——只需返回一个更新。应用此更新后，`State` 将变为 `{"foo": 2, "bar": ["hi"]}`。如果第二个节点返回 `{"bar": ["bye"]}`，则 `State` 将变为 `{"foo": 2, "bar": ["bye"]}`。

```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add

class State(TypedDict):
    foo: int
    bar: Annotated[list[str], add]
```

在此示例中，我们使用 `Annotated` 类型为第二个键 (`bar`) 指定了一个 reducer 函数 (`operator.add`)。请注意，第一个键保持不变。假设图的输入是 `{"foo": 1, "bar": ["hi"]}`。然后假设第一个 `Node` 返回 `{"foo": 2}`。这被视为对状态的更新。应用此更新后，`State` 将变为 `{"foo": 2, "bar": ["hi"]}`。如果第二个节点返回 `{"bar": ["bye"]}`，则 `State` 将变为 `{"foo": 2, "bar": ["hi", "bye"]}`。请注意，这里 `bar` 键是通过将两个列表相加来更新的。

#### Overwrite

在某些情况下，您可能希望绕过 reducer 并直接覆盖状态值。LangGraph 为此提供了 `Overwrite` 类型。在此了解如何使用 `Overwrite`。

### 在图状态中使用消息

#### 为什么要使用消息？

大多数现代 LLM 提供商都有一个聊天模型接口，该接口接受消息列表作为输入。特别是，LangChain 的聊天模型接口接受消息对象列表作为输入。这些消息有各种形式，例如 `HumanMessage`（用户输入）或 `AIMessage`（LLM 响应）。

要阅读有关消息对象的更多信息，请参阅 Messages 概念指南。

#### 在图中使用消息

在许多情况下，将之前的对话历史作为图中的消息列表存储是很有帮助的。为此，我们可以在图状态中添加一个键（通道），用于存储 `Message` 对象的列表，并使用 reducer 函数对其进行注解（请参见下面示例中的 `messages` 键）。reducer 函数对于告诉图如何在每次状态更新时更新状态中的 `Message` 对象列表至关重要。如果您不指定 reducer，则每次状态更新都会用最新提供的值覆盖消息列表。如果您只是想将消息追加到现有列表中，可以使用 `operator.add` 作为 reducer。

但是，您可能还想手动更新图状态中的消息（例如人机交互）。如果您使用 `operator.add`，您发送给图的手动状态更新将被追加到现有消息列表中，而不是更新现有消息。为了避免这种情况，您需要一个能够跟踪消息 ID 并在更新时覆盖现有消息的 reducer。为此，您可以使用预构建的 `add_messages` 函数。对于新消息，它只会追加到现有列表，但它也会正确处理现有消息的更新。

#### 序列化

除了跟踪消息 ID 之外，每当在 `messages` 通道上收到状态更新时，`add_messages` 函数还会尝试将消息反序列化为 LangChain `Message` 对象。

有关更多信息，请参阅 LangChain 序列化/反序列化。这允许以以下格式发送图输入/状态更新：

```python
# 支持这种格式
{"messages": [HumanMessage(content="message")]}

# 也支持这种格式
{"messages": [{"type": "human", "content": "message"}]}
```

由于使用 `add_messages` 时，状态更新总是被反序列化为 LangChain `Messages`，因此您应该使用点符号来访问消息属性，例如 `state["messages"][-1].content`。

下面是一个使用 `add_messages` 作为其 reducer 函数的图示例。

```python
from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict

class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

#### MessagesState

由于在状态中拥有消息列表非常常见，因此存在一个名为 `MessagesState` 的预构建状态，它使使用消息变得容易。`MessagesState` 定义了一个 `messages` 键，该键是 `AnyMessage` 对象的列表，并使用 `add_messages` reducer。通常，除了消息之外，还有更多状态需要跟踪，因此我们看到人们对这个状态进行子类化并添加更多字段，例如：

```python
from langgraph.graph import MessagesState

class State(MessagesState):
    documents: list[str]
```

## Nodes

在 LangGraph 中，节点是接受以下参数的 Python 函数（同步或异步）：

1. `state` — 图的状态
2. `config` — 一个 `RunnableConfig` 对象，包含配置信息，如 `thread_id` 和跟踪信息，如 `tags`
3. `runtime` — 一个 `Runtime` 对象，包含运行时 `context` 以及其他信息，如 `store`、`stream_writer`、`execution_info` 和 `server_info`

类似于 `NetworkX`，您使用 `add_node` 方法将这些节点添加到图中：

```python
from dataclasses import dataclass
from typing_extensions import TypedDict

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime

class State(TypedDict):
    input: str
    results: str

@dataclass
class Context:
    user_id: str

builder = StateGraph(State)

def plain_node(state: State):
    return state

def node_with_runtime(state: State, runtime: Runtime[Context]):
    print("In node: ", runtime.context.user_id)
    return {"results": f"Hello, {state['input']}!"}

def node_with_execution_info(state: State, runtime: Runtime):
    print("In node with thread_id: ", runtime.execution_info.thread_id)  
    return {"results": f"Hello, {state['input']}!"}

builder.add_node("plain_node", plain_node)
builder.add_node("node_with_runtime", node_with_runtime)
builder.add_node("node_with_execution_info", node_with_execution_info)
...
```

在后台，函数被转换为 `RunnableLambda`，它为您的函数添加了批处理和异步支持，以及本机跟踪和调试功能。

如果您添加一个节点到图中而没有指定名称，它将被赋予一个默认为函数名的名称。

```python
builder.add_node(my_node)
# 然后您可以通过引用 "my_node" 来创建指向/来自该节点的边
```

### `START` 节点

`START` 节点是一个特殊节点，代表将用户输入发送到图的节点。引用此节点的主要目的是确定应首先调用哪些节点。

```python
from langgraph.graph import START

graph.add_edge(START, "node_a")
```

### `END` 节点

`END` 节点是一个特殊节点，代表一个终端节点。当您想要表示哪些边完成后没有后续操作时，会引用此节点。

```python
from langgraph.graph import END

graph.add_edge("node_a", END)
```

### 节点缓存

LangGraph 支持基于节点输入缓存任务/节点。要使用缓存：

* 在编译图（或指定入口点）时指定一个缓存
* 为节点指定一个缓存策略 (cache policy)。每个缓存策略支持：
  * `key_func` 用于根据节点输入生成缓存键，默认为使用 pickle 对输入进行 `hash`。
  * `ttl`，缓存的生存时间（秒）。如果未指定，缓存将永不过期。

例如：

```python
import time
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langgraph.cache.memory import InMemoryCache
from langgraph.types import CachePolicy

class State(TypedDict):
    x: int
    result: int

builder = StateGraph(State)

def expensive_node(state: State) -> dict[str, int]:
    # 昂贵计算
    time.sleep(2)
    return {"result": state["x"] * 2}

builder.add_node("expensive_node", expensive_node, cache_policy=CachePolicy(ttl=3))
builder.set_entry_point("expensive_node")
builder.set_finish_point("expensive_node")

graph = builder.compile(cache=InMemoryCache())

print(graph.invoke({"x": 5}, stream_mode='updates'))    
# [{'expensive_node': {'result': 10}}]
print(graph.invoke({"x": 5}, stream_mode='updates'))    
# [{'expensive_node': {'result': 10}, '__metadata__': {'cached': True}}]
```

1. 第一次运行需要两秒钟（由于模拟的昂贵计算）。
2. 第二次运行利用缓存并快速返回。

## Edges

边定义了逻辑的路由方式以及图决定停止的方式。这是您的 agents 工作方式以及不同节点之间相互通信的重要组成部分。有几种关键的边类型：

* 普通边 (Normal Edges)：直接从当前节点指向下一个节点。
* 条件边 (Conditional Edges)：调用一个函数来决定接下来要转到哪个节点。
* 入口点 (Entry Point)：当用户输入到达时，首先调用哪个节点。
* 条件入口点 (Conditional Entry Point)：调用一个函数来决定当用户输入到达时，首先调用哪个节点。

一个节点可以有多个出边。如果一个节点有多个出边，那么所有这些目标节点都将在下一个超级步骤中并行执行。

对于每个节点，选择一种路由机制：使用普通边进行静态路由，或使用条件边 / `Command` 进行动态路由。不要混合使用来自同一节点的普通边和动态路由，因为两条路径都可能执行，使图行为更难推理。

### 普通边

如果您**总是**想从节点 A 转到节点 B，您可以直接使用 `add_edge` 方法。

```python
graph.add_edge("node_a", "node_b")
```

### 条件边

如果您想**有条件地**路由到一个或多个边（或选择性地终止），您可以使用 `add_conditional_edges` 方法。此方法接受一个节点的名称和一个在该节点执行后调用的“路由函数”：

```python
graph.add_conditional_edges("node_a", routing_function)
```

与节点类似，`routing_function` 接受图的当前 `state` 并返回一个值。

默认情况下，`routing_function` 的返回值用作下一个要发送状态的节点（或节点列表）的名称。所有这些节点都将在下一个超级步骤中并行运行。

您可以选择提供一个字典，将 `routing_function` 的输出映射到下一个节点的名称。

```python
graph.add_conditional_edges("node_a", routing_function, {True: "node_b", False: "node_c"})
```

如果您希望在单个函数中结合状态更新和路由，请使用 `Command` 而不是条件边。

### 入口点

入口点是图启动时首先运行的节点。您可以使用从虚拟 `START` 节点到第一个要执行的节点的 `add_edge` 方法来指定图的入口点。

```python
from langgraph.graph import START

graph.add_edge(START, "node_a")
```

### 条件入口点

条件入口点允许您根据自定义逻辑在不同的节点处开始。您可以使用从虚拟 `START` 节点的 `add_conditional_edges` 来实现这一点。

```python
from langgraph.graph import START

graph.add_conditional_edges(START, routing_function)
```

您可以选择提供一个字典，将 `routing_function` 的输出映射到下一个节点的名称。

```python
graph.add_conditional_edges(START, routing_function, {True: "node_b", False: "node_c"})
```

## `Send`

默认情况下，`Nodes` 和 `Edges` 是提前定义的，并在相同的共享状态上操作。但是，在某些情况下，确切的边可能无法提前知道，并且/或者您可能希望不同版本的 `State` 同时存在。一个常见的例子是 map-reduce 设计模式。在这种设计模式中，第一个节点可能会生成一个对象列表，并且您可能希望将某个其他节点应用于所有这些对象。对象的数量可能无法提前知道（这意味着边的数量可能未知），并且下游 `Node` 的输入 `State` 应该不同（每个生成的对象对应一个）。

为了支持这种设计模式，LangGraph 支持从条件边返回 `Send` 对象。`Send` 接受两个参数：第一个是节点的名称，第二个是要传递给该节点的状态。

```python
from langgraph.types import Send

def continue_to_jokes(state: OverallState):
    return [Send("generate_joke", {"subject": s}) for s in state['subjects']]

graph.add_conditional_edges("node_a", continue_to_jokes)
```

## `Command`

`Command` 是一个用于控制图执行的多功能原语。它接受四个参数：

* `update`：应用状态更新（类似于从节点返回更新）。
* `goto`：导航到特定节点（类似于条件边）。
* `graph`：在从子图导航时，定位父图。
* `resume`：提供一个值以在中断后恢复执行。

`Command` 在三种上下文中使用：

* **从节点返回**：使用 `update`、`goto` 和 `graph` 将状态更新与流程控制相结合。
* **输入到 `invoke` 或 `stream`**：使用 `resume` 在中断后继续执行。
* **从工具返回**：类似于从节点返回，在工具内部结合状态更新和流程控制。

### 从节点返回

#### `update` 和 `goto`

从节点函数返回 `Command` 以在单个步骤中更新状态并路由到下一个节点：

```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    return Command(
        # 状态更新
        update={"foo": "bar"},
        # 流程控制
        goto="my_other_node"
    )
```

使用 `Command`，您还可以实现动态流程控制行为（与条件边相同）：

```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    if state["foo"] == "bar":
        return Command(update={"foo": "baz"}, goto="my_other_node")
```

当您**既**需要更新状态**又**需要路由到不同节点时，请使用 `Command`。如果您只需要路由而不需要更新状态，请改用条件边。

在节点函数中返回 `Command` 时，您必须添加带有节点列表的返回类型注释，该节点列表是节点要路由到的，例如 `Command[Literal["my_other_node"]]`。这对于图渲染是必要的，并告诉 LangGraph `my_node` 可以导航到 `my_other_node`。

`Command` 仅添加动态边——使用 `add_edge` / `addEdge` 定义的静态边仍然会执行。例如，如果 `node_a` 返回 `Command(goto="my_other_node")` 并且您还使用了 `graph.add_edge("node_a", "node_b")`，那么 `node_b` 和 `my_other_node` 都将运行。对于每个节点，使用 `Command` 或静态边来路由到下一个节点，不要同时使用两者。

查看此操作指南，了解如何使用 `Command` 的端到端示例。

#### `graph`

如果您使用子图，您可以通过在 `Command` 中指定 `graph=Command.PARENT` 从子图内的节点导航到父图中的不同节点：

```python
def my_node(state: State) -> Command[Literal["other_subgraph"]]:
    return Command(
        update={"foo": "bar"},
        goto="other_subgraph",  # 其中 `other_subgraph` 是父图中的一个节点
        graph=Command.PARENT
    )
```

将 `graph` 设置为 `Command.PARENT` 将导航到最近的父图。

  当您从子图节点向父图节点发送更新，且该键在父图和子图状态模式中都存在时，您**必须**为父图状态中正在更新的键定义一个 reducer。请参阅此示例。

这在实现多智能体交接时特别有用。有关详细信息，请参阅导航到父图中的节点。

### 输入到 `invoke` 或 `stream`

`Command(resume=...)` 是**唯一**预期作为 `invoke()`/`stream()` 输入的 `Command` 模式。不要使用 `Command(update=...)` 作为输入来继续多轮对话——因为传递任何 `Command` 作为输入都会从最新的检查点（即运行的最后一个步骤，而不是 `__start__`）恢复，如果图已经完成，它就会看起来卡住了。要继续现有线程上的对话，请传递一个普通的输入字典：

  ```python
  # 错误 - 图从最新的检查点（运行的最后一个步骤）恢复，看起来卡住了
  graph.invoke(Command(update={  
      "messages": [{"role": "user", "content": "follow up"}]  
  }), config)  

  # 正确 - 普通字典从 __start__ 重新开始
  graph.invoke( {  
      "messages": [{"role": "user", "content": "follow up"}]  
  }, config)  
  ```

#### `resume`

使用 `Command(resume=...)` 来提供一个值并在中断后恢复图执行。传递给 `resume` 的值成为暂停节点内 `interrupt()` 调用的返回值：

```python
from langgraph.types import Command, interrupt

def human_review(state: State):
    # 暂停图并等待一个值
    answer = interrupt("Do you approve?")
    return {"messages": [{"role": "user", "content": answer}]}

# 第一次调用 - 遇到中断并暂停
result = graph.invoke({"messages": [...]}, config)

# 用一个值恢复 - interrupt() 调用返回 "yes"
result = graph.invoke(Command(resume="yes"), config)
```

请查看中断概念指南，了解中断模式的完整细节，包括多个中断和验证循环。

### 从工具返回

您可以从工具返回 `Command` 来更新图状态和流程控制。使用 `update` 修改状态（例如，保存对话期间查找的客户信息），并使用 `goto` 在工具完成后路由到特定节点。

在工具内部使用时，`goto` 会添加一条动态边——调用该工具的节点上已经定义的任何静态边仍将执行。对于每个节点，请使用工具驱动的动态路由或静态边来路由到下一个节点，不要同时使用两者。

有关详细信息，请参阅在工具内部使用。

## 图迁移

LangGraph 可以轻松处理图定义（节点、边和状态）的迁移，即使使用 checkpointer 来跟踪状态也是如此。

* 对于处于图末尾（即未中断）的线程，您可以更改图的整个拓扑结构（即所有节点和边，删除、添加、重命名等）。
* 对于当前中断的线程，我们支持除重命名/删除节点之外的所有拓扑更改（因为该线程现在可能即将进入一个不再存在的节点）——如果这是一个障碍，请联系我们，我们可以优先考虑解决方案。
* 对于修改状态，我们对于添加和删除键具有完全的向后和向前兼容性。
* 重命名的状态键会丢失其在现有线程中保存的状态。
* 类型以不兼容方式更改的状态键目前可能会在更改前存在状态的线程中引起问题——如果这是一个障碍，请联系我们，我们可以优先考虑解决方案。

## 运行时上下文

在创建图时，您可以指定一个 `context_schema` 用于传递给节点的运行时上下文。这对于传递不属于图状态的信息给节点很有用。例如，您可能想要传递依赖项，如模型名称或数据库连接。

```python
@dataclass
class ContextSchema:
    llm_provider: str = "openai"

graph = StateGraph(State, context_schema=ContextSchema)
```

然后，您可以使用 `invoke` 方法的 `context` 参数将此上下文传递给图。

```python
graph.invoke(inputs, context={"llm_provider": "anthropic"})
```

然后，您可以在节点或条件边内部访问和使用此上下文：

```python
from langgraph.runtime import Runtime

def node_a(state: State, runtime: Runtime[ContextSchema]):
    llm = get_llm(runtime.context.llm_provider)
    # ...
```

有关配置的完整说明，请参阅添加运行时配置。

### 递归限制

递归限制设置了图在单次执行期间可以执行的最大超级步骤数。一旦达到限制，LangGraph 将引发 `GraphRecursionError`。从 1.0.6 版本开始，默认递归限制设置为 1000 步。递归限制可以在运行时在任何图上设置，并通过配置字典传递给 `invoke`/`stream`。重要的是，`recursion_limit` 是一个独立的 `config` 键，不应像其他用户定义的配置一样传递到 `configurable` 键内部。请参见下面的示例：

```python
graph.invoke(inputs, config={"recursion_limit": 5}, context={"llm": "anthropic"})
```

阅读递归限制以了解有关递归限制如何工作的更多信息。

### 访问和处理递归计数器

当前步数计数器可在任何节点内的 `config["metadata"]["langgraph_step"]` 中访问，从而允许在达到递归限制之前主动处理递归。这使您能够在图逻辑中实现优雅降级策略。

#### 工作原理

步数计数器存储在 `config["metadata"]["langgraph_step"]` 中。递归限制检查遵循逻辑：`step > stop`，其中 `stop = step + recursion_limit + 1`。当超过限制时，LangGraph 会引发 `GraphRecursionError`。

#### 访问当前步数计数器

您可以在任何节点内访问当前步数计数器以监控执行进度。

```python
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

def my_node(state: dict, config: RunnableConfig) -> dict:
    current_step = config["metadata"]["langgraph_step"]
    print(f"Currently on step: {current_step}")
    return state
```

#### 主动递归处理

LangGraph 提供了一个 `RemainingSteps` 托管值，用于跟踪在达到递归限制之前还剩多少步。这允许在图内进行优雅降级。

```python
from typing import Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.managed import RemainingSteps

class State(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]
    remaining_steps: RemainingSteps  # 托管值 - 跟踪直到限制的步数

def reasoning_node(state: State) -> dict:
    # RemainingSteps 由 LangGraph 自动填充
    remaining = state["remaining_steps"]

    # 检查是否步数不足
    if remaining <= 2:
        return {"messages": ["Approaching limit, wrapping up..."]}

    # 正常处理
    return {"messages": ["thinking..."]}

def route_decision(state: State) -> Literal["reasoning_node", "fallback_node"]:
    """根据剩余步数进行路由"""
    if state["remaining_steps"] <= 2:
        return "fallback_node"
    return "reasoning_node"

def fallback_node(state: State) -> dict:
    """处理接近递归限制的情况"""
    return {"messages": ["Reached complexity limit, providing best effort answer"]}

# 构建图
builder = StateGraph(State)
builder.add_node("reasoning_node", reasoning_node)
builder.add_node("fallback_node", fallback_node)
builder.add_edge(START, "reasoning_node")
builder.add_conditional_edges("reasoning_node", route_decision)
builder.add_edge("fallback_node", END)

graph = builder.compile()

# RemainingSteps 适用于任何 recursion_limit
result = graph.invoke({"messages": []}, {"recursion_limit": 10})
```

#### 主动方法与被动方法

处理递归限制有两种主要方法：主动方法（在图内监控）和被动方法（在外部捕获错误）。

```python
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.managed import RemainingSteps
from langgraph.errors import GraphRecursionError

class State(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]
    remaining_steps: RemainingSteps

# 主动方法（推荐） - 使用 RemainingSteps
def agent_with_monitoring(state: State) -> dict:
    """在图内主动监控和处理递归"""
    remaining = state["remaining_steps"]

    # 早期检测 - 路由到内部处理
    if remaining <= 2:
        return {
            "messages": ["Approaching limit, returning partial result"]
        }

    # 正常处理
    return {"messages": [f"Processing... ({remaining} steps remaining)"]}

def route_decision(state: State) -> Literal["agent", END]:
    if state["remaining_steps"] <= 2:
        return END
    return "agent"

# 构建图
builder = StateGraph(State)
builder.add_node("agent", agent_with_monitoring)
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_decision)
graph = builder.compile()

# 主动：图优雅地完成
result = graph.invoke({"messages": []}, {"recursion_limit": 10})

# 被动方法（回退） - 在外部捕获错误
try:
    result = graph.invoke({"messages": []}, {"recursion_limit": 10})
except GraphRecursionError as e:
    # 在图执行失败后在外部处理
    result = {"messages": ["Fallback: recursion limit exceeded"]}
```

这些方法之间的主要区别在于：

| 方法                                  | 检测时机            | 处理方式                             | 控制流                       |
| ----------------------------------------- | -------------------- | ------------------------------------ | ---------------------------------- |
| 主动（使用 `RemainingSteps`）        | 达到限制之前 | 图内部通过条件路由 | 图继续到完成节点 |
| 被动（捕获 `GraphRecursionError`） | 超过限制之后 | 图外部的 try/catch           | 图执行终止         |

**主动方法的优点：**

* 在图内优雅降级
* 可以在检查点中保存中间状态
* 更好的用户体验，提供部分结果
* 图正常完成（无异常）

**被动方法的优点：**

* 实现更简单
* 无需修改图逻辑
* 集中的错误处理

#### 其他可用的元数据

除了 `langgraph_step`，以下元数据也在 `config["metadata"]` 中可用：

```python
def inspect_metadata(state: dict, config: RunnableConfig) -> dict:
    metadata = config["metadata"]

    print(f"Step: {metadata['langgraph_step']}")
    print(f"Node: {metadata['langgraph_node']}")
    print(f"Triggers: {metadata['langgraph_triggers']}")
    print(f"Path: {metadata['langgraph_path']}")
    print(f"Checkpoint NS: {metadata['langgraph_checkpoint_ns']}")

    return state
```