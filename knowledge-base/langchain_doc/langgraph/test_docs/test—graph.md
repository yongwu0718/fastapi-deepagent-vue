# 测试

在您完成 LangGraph agent 的原型构建之后，接下来很自然的一步就是添加测试。本指南涵盖了您在编写单元测试时可以采用的一些有用模式。

请注意，本指南专门针对 LangGraph，并聚焦于具有自定义结构的 graph 场景——如果您才刚刚开始，请转而查阅使用 LangChain 内置 `create_agent` 的测试。

## 先决条件

首先，确保您已安装 `pytest`：

```bash
$ pip install -U pytest
```

## 入门

由于许多 LangGraph agent 依赖 state，一个有用的模式是在每次使用 graph 的测试之前先创建该 graph，然后在测试中用一个全新的 checkpointer 实例来编译它。

下面的示例展示了一个依次经过 `node1` 和 `node2` 的简单线性 graph 如何工作。每个 node 都会更新唯一的 state 键 `my_key`：

```python
import pytest

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

def create_graph() -> StateGraph:
    class MyState(TypedDict):
        my_key: str

    graph = StateGraph(MyState)
    graph.add_node("node1", lambda state: {"my_key": "hello from node1"})
    graph.add_node("node2", lambda state: {"my_key": "hello from node2"})
    graph.add_edge(START, "node1")
    graph.add_edge("node1", "node2")
    graph.add_edge("node2", END)
    return graph

def test_basic_agent_execution() -> None:
    checkpointer = MemorySaver()
    graph = create_graph()
    compiled_graph = graph.compile(checkpointer=checkpointer)
    result = compiled_graph.invoke(
        {"my_key": "initial_value"},
        config={"configurable": {"thread_id": "1"}}
    )
    assert result["my_key"] == "hello from node2"
```

## 测试单个 node 和边

编译后的 LangGraph agent 会通过 `graph.nodes` 暴露对每个单独 node 的引用。您可以利用这一点来测试 agent 中的单个 node。请注意，这会绕过在编译 graph 时传入的任何 checkpointer：

```python
import pytest

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

def create_graph() -> StateGraph:
    class MyState(TypedDict):
        my_key: str

    graph = StateGraph(MyState)
    graph.add_node("node1", lambda state: {"my_key": "hello from node1"})
    graph.add_node("node2", lambda state: {"my_key": "hello from node2"})
    graph.add_edge(START, "node1")
    graph.add_edge("node1", "node2")
    graph.add_edge("node2", END)
    return graph

def test_individual_node_execution() -> None:
    # 在此示例中将被忽略
    checkpointer = MemorySaver()
    graph = create_graph()
    compiled_graph = graph.compile(checkpointer=checkpointer)
    # 仅调用 node 1
    result = compiled_graph.nodes["node1"].invoke(
        {"my_key": "initial_value"},
    )
    assert result["my_key"] == "hello from node1"
```

## 局部执行

对于由较大 graph 构成的 agent，您可能希望测试 agent 中的局部执行路径，而不是端到端的整个流程。在某些情况下，将这些部分重构为 subgraph 在语义上更合理，这样您就可以像往常一样独立调用它们。

不过，如果您不想更改 agent graph 的整体结构，可以利用 LangGraph 的持久化机制来模拟这样一种 state：agent 恰好在您想要执行的部分开始之前暂停，并在该部分结束时再次暂停。具体步骤如下：

1. 用一个 checkpointer 来编译您的 agent（用于测试时，内存 checkpointer `InMemorySaver` 就足够了）。
2. 调用 agent 的 `update_state` 方法，并将 `as_node` 参数设置为在您想开始测试的 node 之前那个 node 的名称。
3. 使用与更新 state 时相同的 `thread_id` 来调用您的 agent，并设置 `interrupt_after` 参数为您希望停止的 node 的名称。

以下是一个仅执行线性 graph 中第二个和第三个 node 的示例：

```python
import pytest

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

def create_graph() -> StateGraph:
    class MyState(TypedDict):
        my_key: str

    graph = StateGraph(MyState)
    graph.add_node("node1", lambda state: {"my_key": "hello from node1"})
    graph.add_node("node2", lambda state: {"my_key": "hello from node2"})
    graph.add_node("node3", lambda state: {"my_key": "hello from node3"})
    graph.add_node("node4", lambda state: {"my_key": "hello from node4"})
    graph.add_edge(START, "node1")
    graph.add_edge("node1", "node2")
    graph.add_edge("node2", "node3")
    graph.add_edge("node3", "node4")
    graph.add_edge("node4", END)
    return graph

def test_partial_execution_from_node2_to_node3() -> None:
    checkpointer = MemorySaver()
    graph = create_graph()
    compiled_graph = graph.compile(checkpointer=checkpointer)
    compiled_graph.update_state(
        config={
          "configurable": {
            "thread_id": "1"
          }
        },
        # 传入 node 2 的 state —— 模拟 node 1 结束后的 state
        values={"my_key": "initial_value"},
        # 将保存的 state 更新为好像来自 node 1
        # 执行将从 node 2 继续
        as_node="node1",
    )
    result = compiled_graph.invoke(
        # 通过传入 None 继续执行
        None,
        config={"configurable": {"thread_id": "1"}},
        # 在 node 3 之后停止，这样 node 4 不会运行
        interrupt_after="node3",
    )
    assert result["my_key"] == "hello from node3"
```