# Subgraphs

本指南解释了使用子图 (subgraphs) 的机制。子图是作为另一个图中的节点 (node) 使用的图。

子图在以下场景中很有用：

* 构建多智能体系统 (multi-agent systems)
* 在多个图中重用一组节点
* 分布式开发：当您希望不同的团队独立处理图的不同部分时，您可以将每个部分定义为一个子图，只要遵守子图接口（输入和输出模式），父图就可以在不了解子图任何细节的情况下构建。

## 设置

```bash
pip install -U langgraph
```

**为 LangGraph 开发设置 LangSmith**

注册 LangSmith 以快速发现问题并提高 LangGraph 项目的性能。LangSmith 允许您使用跟踪数据来调试、测试和监控使用 LangGraph 构建的 LLM 应用程序——阅读更多关于如何开始使用 LangSmith 的信息。

## 定义子图通信

添加子图时，您需要定义父图和子图之间如何通信：

| 模式                                                         | 使用场景                                                                                                        | 状态模式                                                                                                  |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| 在节点内部调用子图 | 父图和子图具有**不同的状态模式**（没有共享的键），或者您需要在它们之间转换状态 | 您编写一个包装函数，将父状态映射到子图输入，并将子图输出映射回父状态 |
| 将子图添加为节点           | 父图和子图**共享状态键**——子图读取和写入与父图相同的通道     | 您直接将编译后的子图传递给 `add_node`——不需要包装函数                               |

### 在节点内部调用子图

当父图和子图具有**不同的状态模式**（没有共享的键）时，在节点函数内部调用子图。这在多智能体系统中很常见，您希望为每个智能体保留一个私有的消息历史。

节点函数在调用子图之前将父状态转换为子图状态，并在返回之前将结果转换回父状态。

```python
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph, START

class SubgraphState(TypedDict):
    bar: str

# 子图

def subgraph_node_1(state: SubgraphState):
    return {"bar": "hi! " + state["bar"]}

subgraph_builder = StateGraph(SubgraphState)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()

# 父图

class State(TypedDict):
    foo: str

def call_subgraph(state: State):
    # 将状态转换为子图状态
    subgraph_output = subgraph.invoke({"bar": state["foo"]})  
    # 将响应转换回父状态
    return {"foo": subgraph_output["bar"]}

builder = StateGraph(State)
builder.add_node("node_1", call_subgraph)
builder.add_edge(START, "node_1")
graph = builder.compile()
```

**不同的状态模式**
```python
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph, START

# 定义子图
class SubgraphState(TypedDict):
  # 请注意，这些键都没有与父图状态共享
  bar: str
  baz: str

def subgraph_node_1(state: SubgraphState):
  return {"baz": "baz"}

def subgraph_node_2(state: SubgraphState):
  return {"bar": state["bar"] + state["baz"]}

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

def node_2(state: ParentState):
  # 将状态转换为子图状态
  response = subgraph.invoke({"bar": state["foo"]})
  # 将响应转换回父状态
  return {"foo": response["bar"]}

builder = StateGraph(ParentState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
graph = builder.compile()

for chunk in graph.stream({"foo": "foo"}, subgraphs=True, version="v2"):
  if chunk["type"] == "updates":
	  print(chunk["ns"], chunk["data"])
```

```
() {'node_1': {'foo': 'hi! foo'}}
('node_2:577b710b-64ae-31fb-9455-6a4d4cc2b0b9',) {'subgraph_node_1': {'baz': 'baz'}}
('node_2:577b710b-64ae-31fb-9455-6a4d4cc2b0b9',) {'subgraph_node_2': {'bar': 'hi! foobaz'}}
() {'node_2': {'foo': 'hi! foobaz'}}
```

### 将子图添加为节点

当父图和子图**共享状态键**时，您可以直接将编译后的子图传递给 `add_node`。不需要包装函数——子图会自动从父级的状态通道读取和写入。例如，在多智能体系统中，智能体通常通过一个共享的 `messages` 键进行通信。

如果您的子图与父图共享状态键，您可以按照以下步骤将其添加到您的图中：

1.  定义子图工作流（下例中的 `subgraph_builder`）并编译它
2.  在定义父图工作流时，将编译后的子图传递给 `add_node` 方法

```python
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph, START

class State(TypedDict):
    foo: str

# 子图

def subgraph_node_1(state: State):
    return {"foo": "hi! " + state["foo"]}

subgraph_builder = StateGraph(State)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()

# 父图

builder = StateGraph(State)
builder.add_node("node_1", subgraph)  
builder.add_edge(START, "node_1")
graph = builder.compile()
```

**完整示例**
```python
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph, START

# 定义子图
class SubgraphState(TypedDict):
  foo: str  # 与父图状态共享
  bar: str  # SubgraphState 私有

def subgraph_node_1(state: SubgraphState):
  return {"bar": "bar"}

def subgraph_node_2(state: SubgraphState):
  # 请注意，此节点正在使用仅在子图中可用的状态键 ('bar')
  # 并在共享状态键 ('foo') 上发送更新
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

for chunk in graph.stream({"foo": "foo"}, version="v2"):
  if chunk["type"] == "updates":
	  print(chunk["data"])
```

```
{'node_1': {'foo': 'hi! foo'}}
{'node_2': {'foo': 'hi! foobar'}}
```

## 子图持久化

当您使用子图时，您需要决定其内部数据在调用之间如何处理。考虑一个委派给专业子代理的客服机器人：“账单专家”子代理应该记住客户之前的问题，还是每次被调用时都重新开始？

`.compile()` 上的 `checkpointer` 参数控制子图持久化：

| 模式                                      | `checkpointer=`  | 行为                                                                                                                                                                                                       |
| ----------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 每次调用 (Per-invocation) | `None` (默认)     | 每次调用都是全新的，并继承父图的 checkpointer，以支持单次调用内的中断和持久执行。 |
| 每个线程 (Per-thread)                 | `True`           | 状态在同一线程的多次调用中累积。每次调用从上一次停止的地方继续。                                                                                                             |
| 无状态 (Stateless)                   | `False`          | 完全没有 checkpointing——像普通函数调用一样运行。没有中断或持久执行。                                                                                                                   |

Per-invocation 是大多数应用程序的正确选择，包括多智能体系统，其中子代理处理独立的请求。当子代理需要多轮对话记忆时（例如，一个研究助手在几次交流中构建上下文），请使用 per-thread。

父图必须使用 checkpointer 编译，子图持久化功能（中断、状态检查、每个线程的记忆）才能工作。请参阅 persistence。

下面的示例使用 LangChain 的 `create_agent`，这是构建 agent 的一种常见方式。`create_agent` 在底层生成一个 LangGraph 图，因此所有子图持久化概念都直接适用。如果您使用原始的 LangGraph `StateGraph` 构建，同样的模式和配置选项也适用——有关详细信息，请参阅 Graph API。

### 有状态 (Stateful)

有状态子图继承父图的 checkpointer，这启用了中断、持久执行和状态检查。这两种有状态模式的区别在于状态保留多长时间。

#### 每次调用 (Per-invocation)（默认）

这是大多数应用程序（包括将子代理作为工具调用的多智能体系统）的推荐模式。它支持中断、持久执行和并行调用，同时保持每次调用的隔离。

当对子图的每次调用都是独立的，并且子代理不需要记住之前调用的任何内容时，请使用 per-invocation 持久化。这是最常见的模式，特别是对于多智能体系统，其中子代理处理一次性请求，如“查找此客户的订单”或“总结此文档”。

省略 `checkpointer` 或将其设置为 `None`。每次调用都是全新的，但在单次调用内，子图继承父图的 checkpointer，并可以使用 `interrupt()` 暂停和恢复。

以下示例使用两个子代理（水果专家、蔬菜专家）包装为外部 agent 的工具：

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

@tool
def fruit_info(fruit_name: str) -> str:
    """查找水果信息。"""
    return f"Info about {fruit_name}"

@tool
def veggie_info(veggie_name: str) -> str:
    """查找蔬菜信息。"""
    return f"Info about {veggie_name}"

# 子代理 - 没有设置 checkpointer（继承父类）
fruit_agent = create_agent(
    model="gpt-5.4-mini",
    tools=[fruit_info],
    prompt="You are a fruit expert. Use the fruit_info tool. Respond in one sentence.",
)

veggie_agent = create_agent(
    model="gpt-5.4-mini",
    tools=[veggie_info],
    prompt="You are a veggie expert. Use the veggie_info tool. Respond in one sentence.",
)

# 将子代理包装为外部 agent 的工具
@tool
def ask_fruit_expert(question: str) -> str:
    """询问水果专家。所有水果问题都使用此工具。"""
    response = fruit_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
    )
    return response["messages"][-1].content

@tool
def ask_veggie_expert(question: str) -> str:
    """询问蔬菜专家。所有蔬菜问题都使用此工具。"""
    response = veggie_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
    )
    return response["messages"][-1].content

# 带有 checkpointer 的外部 agent
agent = create_agent(
    model="gpt-5.4-mini",
    tools=[ask_fruit_expert, ask_veggie_expert],
    prompt=(
        "You have two experts: ask_fruit_expert and ask_veggie_expert. "
        "ALWAYS delegate questions to the appropriate expert."
    ),
    checkpointer=MemorySaver(),
)
```

每次调用都可以使用 `interrupt()` 来暂停和恢复。将 `interrupt()` 添加到工具函数中以要求在继续之前获得用户批准：

```python
@tool
def fruit_info(fruit_name: str) -> str:
	"""查找水果信息。"""
	interrupt("continue?")  
	return f"Info about {fruit_name}"
```

```python
config = {"configurable": {"thread_id": "1"}}

# 调用 - 子代理的工具调用 interrupt()
response = agent.invoke(
	{"messages": [{"role": "user", "content": "Tell me about apples"}]},
	config=config,
)
# response 包含 __interrupt__

# 恢复 - 批准中断
response = agent.invoke(Command(resume=True), config=config)  
# 子代理消息计数：4
```

每次调用都以全新的子代理状态开始。子代理不记得之前的调用：

```python
config = {"configurable": {"thread_id": "1"}}

# 第一次调用
response = agent.invoke(
	{"messages": [{"role": "user", "content": "Tell me about apples"}]},
	config=config,
)
# 子代理消息计数：4

# 第二次调用 - 子代理全新开始，不记得苹果
response = agent.invoke(
	{"messages": [{"role": "user", "content": "Now tell me about bananas"}]},
	config=config,
)
# 子代理消息计数：4（仍然是全新的！）
```

对同一子图的多次调用可以无冲突地进行，因为每次调用都有自己的检查点命名空间：

```python
config = {"configurable": {"thread_id": "1"}}

# LLM 同时调用 ask_fruit_expert 询问苹果和香蕉
response = agent.invoke(
	{"messages": [{"role": "user", "content": "Tell me about apples and bananas"}]},
	config=config,
)
# 子代理消息计数：4（苹果 - 全新）
# 子代理消息计数：4（香蕉 - 全新）
```

#### 每个线程 (Per-thread)

当子代理需要记住之前的交互时，请使用 per-thread 持久化。例如，一个研究助理在几次交流中构建上下文，或者一个编码助理跟踪它已经编辑了哪些文件。子代理的对话历史和数据在同一线程的多次调用中累积。每次调用从上一次停止的地方继续。

使用 `checkpointer=True` 编译以启用此行为。

Per-thread 子图不支持并行工具调用。当 LLM 可以访问作为工具的 per-thread 子代理时，它可能会尝试并行调用该工具多次（例如，同时询问水果专家关于苹果和香蕉的信息）。这会导致检查点冲突，因为两次调用都写入同一个命名空间。

  以下示例使用 LangChain 的 `ToolCallLimitMiddleware` 来防止这种情况。如果您使用纯 LangGraph `StateGraph` 构建，您需要自己防止并行工具调用——例如，通过配置您的模型禁用并行工具调用，或通过添加逻辑确保同一子图不会并行多次调用。

以下示例使用一个使用 `checkpointer=True` 编译的水果专家子代理：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

@tool
def fruit_info(fruit_name: str) -> str:
    """查找水果信息。"""
    return f"Info about {fruit_name}"

# 使用 checkpointer=True 实现持久状态的子代理
fruit_agent = create_agent(
    model="gpt-5.4-mini",
    tools=[fruit_info],
    prompt="You are a fruit expert. Use the fruit_info tool. Respond in one sentence.",
    checkpointer=True,  
)

# 将子代理包装为外部 agent 的工具
@tool
def ask_fruit_expert(question: str) -> str:
    """询问水果专家。所有水果问题都使用此工具。"""
    response = fruit_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
    )
    return response["messages"][-1].content

# 带有 checkpointer 的外部 agent
# 使用 ToolCallLimitMiddleware 防止对 per-thread 子代理的并行调用，
# 否则会导致检查点冲突。
agent = create_agent(
    model="gpt-5.4-mini",
    tools=[ask_fruit_expert],
    prompt="You have a fruit expert. ALWAYS delegate fruit questions to ask_fruit_expert.",
    middleware=[  
        ToolCallLimitMiddleware(tool_name="ask_fruit_expert", run_limit=1),  
    ],  
    checkpointer=MemorySaver(),
)
```

Per-thread 子代理与 per-invocation 一样支持 `interrupt()`。将 `interrupt()` 添加到工具函数中以要求在继续之前获得用户批准：

```python
@tool
def fruit_info(fruit_name: str) -> str:
	"""查找水果信息。"""
	interrupt("continue?")  
	return f"Info about {fruit_name}"
```

```python
config = {"configurable": {"thread_id": "1"}}

# 调用 - 子代理的工具调用 interrupt()
response = agent.invoke(
	{"messages": [{"role": "user", "content": "Tell me about apples"}]},
	config=config,
)
# response 包含 __interrupt__

# 恢复 - 批准中断
response = agent.invoke(Command(resume=True), config=config)  
# 子代理消息计数：4
```

状态在多次调用中累积——子代理记住过去的对话：

```python
config = {"configurable": {"thread_id": "1"}}

# 第一次调用
response = agent.invoke(
	{"messages": [{"role": "user", "content": "Tell me about apples"}]},
	config=config,
)
# 子代理消息计数：4

# 第二次调用 - 子代理记住了苹果对话
response = agent.invoke(
	{"messages": [{"role": "user", "content": "Now tell me about bananas"}]},
	config=config,
)
# 子代理消息计数：8（累积了！）
```

当您有多个**不同**的 per-thread 子图时（例如，一个水果专家和一个蔬菜专家），每个都需要自己的存储空间，以便它们的检查点不会相互覆盖。这称为**命名空间隔离**。

如果您在节点内部调用子图，LangGraph 会根据调用顺序分配命名空间（第一次调用、第二次调用等）。这意味着重新排序您的调用可能会混淆哪个子图加载哪个状态。为了避免这种情况，将每个子代理包装在具有唯一节点名称的自己的 `StateGraph` 中——这为每个子图提供了一个稳定的、唯一的命名空间：

```python
from langgraph.graph import MessagesState, StateGraph

def create_sub_agent(model, *, name, **kwargs):
	"""用唯一节点名称包装 agent 以实现命名空间隔离。"""
	agent = create_agent(model=model, name=name, **kwargs)
	return (
		StateGraph(MessagesState)
		.add_node(name, agent)  # 唯一的名称 → 稳定的命名空间  
		.add_edge("__start__", name)
		.compile()
	)

fruit_agent = create_sub_agent(
	"gpt-5.4-mini", name="fruit_agent",
	tools=[fruit_info], prompt="...", checkpointer=True,
)
veggie_agent = create_sub_agent(
	"gpt-5.4-mini", name="veggie_agent",
	tools=[veggie_info], prompt="...", checkpointer=True,
)

config = {"configurable": {"thread_id": "1"}}

# 第一次调用 - LLM 同时调用水果和蔬菜专家
response = agent.invoke(
	{"messages": [{"role": "user", "content": "Tell me about cherries and broccoli"}]},
	config=config,
)
# 水果子代理消息计数：4
# 蔬菜子代理消息计数：4

# 第二次调用 - 两个代理独立累积
response = agent.invoke(
	{"messages": [{"role": "user", "content": "Now tell me about oranges and carrots"}]},
	config=config,
)
# 水果子代理消息计数：8（记住了樱桃！）
# 蔬菜子代理消息计数：8（记住了西兰花！）
```

作为节点添加的子图已经自动获得了基于名称的命名空间，因此它们不需要这个包装器。

### 无状态 (Stateless)

当您希望像普通函数调用一样运行子代理而没有 checkpointing 开销时，请使用此模式。子图无法暂停/恢复，并且不能从持久执行中受益。使用 `checkpointer=False` 编译。

没有 checkpointing，子图就没有持久执行。如果进程在运行中途崩溃，子图无法恢复，必须从头开始重新运行。

```python
subgraph_builder = StateGraph(...)
subgraph = subgraph_builder.compile(checkpointer=False)  
```

### Checkpointer 参考

使用 `.compile()` 上的 `checkpointer` 参数控制子图持久化：

```python
subgraph = builder.compile(checkpointer=False)  # 或 True / None
```

| 特性                              | 每次调用 (默认)                                                                                                                                                                                                                                 | 每个线程                                                                                                                                    | 无状态 |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| `checkpointer=`                      | `None`                                                                                                                                                                                                                                                   | `True`                                                                                                                                        | `False`   |
| 中断 (HITL)                    | ✅                                                                                                                                                                                                                                                        | ✅                                                                                                                                             | ❌         |
| 多轮记忆                    | ❌                                                                                                                                                                                                                                                        | ✅                                                                                                                                             | ❌         |
| 多次调用（不同的子图） | ✅                                                                                                                                                                                                                                                        | ⚠️ | ✅         |
| 多次调用（相同的子图）       | ✅                                                                                                                                                                                                                                                        | ❌                                                                                                                                             | ✅         |
| 状态检查                     | ⚠️ | ✅                                                                                                                                             | ❌         |

*   **中断 (HITL)**：子图可以使用 `interrupt()` 暂停执行等待用户输入，然后从中断处恢复。
*   **多轮记忆**：子图在同一线程的多次调用中保留其状态。每次调用从上一次停止的地方继续，而不是重新开始。
*   **多次调用（不同的子图）**：可以在单个节点内调用多个不同的子图实例，而不会产生检查点命名空间冲突。
*   **多次调用（相同的子图）**：可以在单个节点内多次调用相同的子图实例。使用有状态持久化时，这些调用会写入同一个检查点命名空间并发生冲突——请改用 per-invocation 持久化。
*   **状态检查**：子图的状态可通过 `get_state(config, subgraphs=True)` 获得，用于调试和监控。

## 查看子图状态

当您启用持久化时，您可以使用 `subgraphs` 选项检查子图状态。对于无状态 checkpointing（`checkpointer=False`），不会保存子图检查点，因此子图状态不可用。

查看子图状态要求 LangGraph 能够**静态发现**子图——即，它被添加为节点或在节点内部被调用。当子图在工具函数或其他间接调用中（例如，子代理模式）被调用时，它无法工作。无论嵌套如何，中断仍然会传播到顶层图。

返回**仅当前调用**的子图状态。每次调用都是全新的。

```python
from langgraph.graph import START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from typing_extensions import TypedDict

class State(TypedDict):
	foo: str

# 子图
def subgraph_node_1(state: State):
	value = interrupt("Provide value:")
	return {"foo": state["foo"] + value}

subgraph_builder = StateGraph(State)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()  # 继承父类的 checkpointer

# 父图
builder = StateGraph(State)
builder.add_node("node_1", subgraph)
builder.add_edge(START, "node_1")

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "1"}}

graph.invoke({"foo": ""}, config)

# 查看当前调用的子图状态
subgraph_state = graph.get_state(config, subgraphs=True).tasks[0].state  

# 恢复子图
graph.invoke(Command(resume="bar"), config)
```

返回此线程上所有调用的**累积**子图状态。

```python
from langgraph.graph import START, StateGraph, MessagesState
from langgraph.checkpoint.memory import MemorySaver

# 具有自己的持久状态的子图
subgraph_builder = StateGraph(MessagesState)
# ... 添加节点和边
subgraph = subgraph_builder.compile(checkpointer=True)  

# 父图
builder = StateGraph(MessagesState)
builder.add_node("agent", subgraph)
builder.add_edge(START, "agent")

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "1"}}

graph.invoke({"messages": [{"role": "user", "content": "hi"}]}, config)
graph.invoke({"messages": [{"role": "user", "content": "what did I say?"}]}, config)

# 查看累积的子图状态（包括两次调用的消息）
subgraph_state = graph.get_state(config, subgraphs=True).tasks[0].state  
```

## 流式传输子图输出

要在流式传输的输出中包含子图的输出，您可以在父图的 `stream` 方法中设置 `subgraphs` 选项。这将同时流式传输父图和任何子图的输出。

使用 `version="v2"` 时，子图事件使用相同的 `StreamPart` 格式。`ns` 字段标识源图：

```python
for chunk in graph.stream(
	{"foo": "foo"},
	subgraphs=True, 
	stream_mode="updates",
	version="v2", 
):
	print(chunk["type"])  # "updates"
	print(chunk["ns"])    # () 表示根图，('node_2:',) 表示子图
	print(chunk["data"])  # {"node_name": {"key": "value"}}
```

```python
for chunk in graph.stream(
	{"foo": "foo"},
	subgraphs=True, 
	stream_mode="updates",
):
	print(chunk)
```

```python
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph, START

# 定义子图
class SubgraphState(TypedDict):
  foo: str
  bar: str

def subgraph_node_1(state: SubgraphState):
  return {"bar": "bar"}

def subgraph_node_2(state: SubgraphState):
  # 请注意，此节点正在使用仅在子图中可用的状态键 ('bar')
  # 并在共享状态键 ('foo') 上发送更新
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
  subgraphs=True, 
  version="v2", 
):
  if chunk["type"] == "updates":
	  print(chunk["ns"], chunk["data"])
```

```
() {'node_1': {'foo': 'hi! foo'}}
('node_2:e58e5673-a661-ebb0-70d4-e298a7fc28b7',) {'subgraph_node_1': {'bar': 'bar'}}
('node_2:e58e5673-a661-ebb0-70d4-e298a7fc28b7',) {'subgraph_node_2': {'foo': 'hi! foobar'}}
() {'node_2': {'foo': 'hi! foobar'}}
```