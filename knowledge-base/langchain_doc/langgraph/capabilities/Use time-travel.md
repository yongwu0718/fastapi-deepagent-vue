# 使用时间旅行 (Use time-travel)

> 在 LangGraph 中重放过去的执行并分叉以探索替代路径

## 概述

LangGraph 通过检查点 (checkpoints) 支持时间旅行：

* **重放 (Replay)**：从先前的检查点重试。
* **分支 (Fork)**：从修改了状态的先前检查点分叉，以探索替代路径。

两者都通过从先前的检查点恢复执行来实现。检查点之前的节点不会重新执行（结果已保存）。检查点之后的节点会重新执行，包括任何 LLM 调用、API 请求和中断（可能会产生不同的结果）。

## 重放 (Replay)

使用先前检查点的配置调用图，以从该点重放。

重放会重新执行节点——不仅仅是读取缓存。LLM 调用、API 请求和中断会再次触发，并可能返回不同的结果。从最终检查点（没有 `next` 节点）重放是无操作的。

使用 `get_state_history` 找到您想要重放的检查点，然后使用该检查点的配置调用 `invoke`：

```python
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import InMemorySaver
from typing_extensions import TypedDict, NotRequired
from langchain_core.utils.uuid import uuid7

class State(TypedDict):
    topic: NotRequired[str]
    joke: NotRequired[str]

def generate_topic(state: State):
    return {"topic": "socks in the dryer"}

def write_joke(state: State):
    return {"joke": f"Why do {state['topic']} disappear? They elope!"}

checkpointer = InMemorySaver()
graph = (
    StateGraph(State)
    .add_node("generate_topic", generate_topic)
    .add_node("write_joke", write_joke)
    .add_edge(START, "generate_topic")
    .add_edge("generate_topic", "write_joke")
    .compile(checkpointer=checkpointer)
)

# 步骤 1：运行图
config = {"configurable": {"thread_id": str(uuid7())}}
result = graph.invoke({}, config)

# 步骤 2：找到要重放的检查点
history = list(graph.get_state_history(config))
# 历史记录按时间倒序排列
for state in history:
    print(f"next={state.next}, checkpoint_id={state.config['configurable']['checkpoint_id']}")

# 步骤 3：从特定检查点重放
# 找到 write_joke 之前的检查点
before_joke = next(s for s in history if s.next == ("write_joke",))
replay_result = graph.invoke(None, before_joke.config)
# write_joke 重新执行（再次运行），generate_topic 不重新执行
```

## 分支 (Fork)

分支从过去的检查点创建一个新的分支，并带有修改后的状态。在先前的检查点上调用 `update_state` 来创建分支，然后使用 `None` 调用 `invoke` 以继续执行。

`update_state` **不会**回滚线程。它会创建一个从指定点分支出来的新检查点。原始执行历史保持不变。

```python
# 找到 write_joke 之前的检查点
history = list(graph.get_state_history(config))
before_joke = next(s for s in history if s.next == ("write_joke",))

# 分支：更新状态以更改主题
fork_config = graph.update_state(
    before_joke.config,
    values={"topic": "chickens"},
)

# 从分支恢复执行 — write_joke 使用新主题重新执行
fork_result = graph.invoke(None, fork_config)
print(fork_result["joke"])  # 关于 chickens 的笑话，而不是 socks
```

### 从特定节点

当您调用 `update_state` 时，值会使用指定节点的写入器（包括 reducer）应用。检查点记录该节点产生了更新，并且执行从该节点的后继节点恢复。

默认情况下，LangGraph 从检查点的版本历史中推断 `as_node`。当从特定检查点分支时，这种推断几乎总是正确的。

在以下情况下显式指定 `as_node`：

* **并行分支**：多个节点在同一步骤中更新了状态，并且 LangGraph 无法确定哪个是最后的（`InvalidUpdateError`）。
* **没有执行历史**：在一个新线程上设置状态（常见于测试）。
* **跳过节点**：将 `as_node` 设置为一个较晚的节点，使图认为该节点已经运行过。

```python
# 图：generate_topic -> write_joke

# 将此更新视为 generate_topic 产生的。
# 执行将在 write_joke（generate_topic 的后继者）处恢复。
fork_config = graph.update_state(
    before_joke.config,
    values={"topic": "chickens"},
    as_node="generate_topic",
)
```

## 中断 (Interrupts)

如果您的图使用 `interrupt` 进行人机交互工作流，则在时间旅行期间，中断总是会重新触发。包含中断的节点会重新执行，并且 `interrupt()` 会暂停，等待新的 `Command(resume=...)`。

```python
from langgraph.types import interrupt, Command

class State(TypedDict):
    value: list[str]

def ask_human(state: State):
    answer = interrupt("What is your name?")
    return {"value": [f"Hello, {answer}!"]}

def final_step(state: State):
    return {"value": ["Done"]}

graph = (
    StateGraph(State)
    .add_node("ask_human", ask_human)
    .add_node("final_step", final_step)
    .add_edge(START, "ask_human")
    .add_edge("ask_human", "final_step")
    .compile(checkpointer=InMemorySaver())
)

config = {"configurable": {"thread_id": "1"}}

# 第一次运行：遇到中断
graph.invoke({"value": []}, config)
# 使用答案恢复
graph.invoke(Command(resume="Alice"), config)

# 从 ask_human 之前重放
history = list(graph.get_state_history(config))
before_ask = [s for s in history if s.next == ("ask_human",)][-1]

replay_result = graph.invoke(None, before_ask.config)
# 在中断处暂停 — 等待新的 Command(resume=...)

# 从 ask_human 之前分支
fork_config = graph.update_state(before_ask.config, {"value": ["forked"]})
fork_result = graph.invoke(None, fork_config)
# 在中断处暂停 — 等待新的 Command(resume=...)

# 使用不同的答案恢复分支的中断
graph.invoke(Command(resume="Bob"), fork_config)
# 结果：{"value": ["forked", "Hello, Bob!", "Done"]}
```

### 多个中断

如果您的图在多个点收集输入（例如，多步骤表单），您可以在中断之间进行分支，以更改后面的答案而无需重新询问前面的问题。

```python
def ask_name(state):
    name = interrupt("What is your name?")
    return {"value": [f"name:{name}"]}

def ask_age(state):
    age = interrupt("How old are you?")
    return {"value": [f"age:{age}"]}

# 图：ask_name -> ask_age -> final
# 完成两个中断后：

# 在两个中断之间进行分支（在 ask_name 之后，ask_age 之前）
history = list(graph.get_state_history(config))
between = [s for s in history if s.next == ("ask_age",)][-1]

fork_config = graph.update_state(between.config, {"value": ["modified"]})
result = graph.invoke(None, fork_config)
# ask_name 的结果保留（"name:Alice"）
# ask_age 在中断处暂停 — 等待新的答案
```

## 子图 (Subgraphs)

使用子图进行时间旅行取决于子图是否拥有自己的 checkpointer。这决定了您可以从中进行时间旅行的检查点的粒度。

默认情况下，子图继承父图的 checkpointer。父图将整个子图视为一个**单一的超级步骤**——整个子图执行只有一个父级检查点。从子图之前进行时间旅行会从头重新执行子图。

您无法在默认子图的*节点之间*进行时间旅行——您只能从父级进行时间旅行。

```python
# 没有自己 checkpoint 的子图（默认）
subgraph = (
	StateGraph(State)
	.add_node("step_a", step_a)       # 有 interrupt()
	.add_node("step_b", step_b)       # 有 interrupt()
	.add_edge(START, "step_a")
	.add_edge("step_a", "step_b")
	.compile()  # 没有 checkpointer — 从父类继承
)

graph = (
	StateGraph(State)
	.add_node("subgraph_node", subgraph)
	.add_edge(START, "subgraph_node")
	.compile(checkpointer=InMemorySaver())
)

config = {"configurable": {"thread_id": "1"}}

# 完成两个中断
graph.invoke({"value": []}, config)            # 遇到 step_a 中断
graph.invoke(Command(resume="Alice"), config)  # 遇到 step_b 中断
graph.invoke(Command(resume="30"), config)     # 完成

# 从子图之前进行时间旅行
history = list(graph.get_state_history(config))
before_sub = [s for s in history if s.next == ("subgraph_node",)][-1]

fork_config = graph.update_state(before_sub.config, {"value": ["forked"]})
result = graph.invoke(None, fork_config)
# 整个子图从头重新执行
# 您无法在 step_a 和 step_b 之间进行时间旅行
```

在子图上设置 `checkpointer=True` 以赋予其自己的检查点历史。这会在子图的**每个步骤**创建检查点，允许您从子图内部的特定点进行时间旅行——例如，在两个中断之间。

使用 `subgraphs=True` 的 `get_state` 来访问子图自己的检查点配置，然后从中分支：

```python
# 具有自己 checkpoint 的子图
subgraph = (
	StateGraph(State)
	.add_node("step_a", step_a)       # 有 interrupt()
	.add_node("step_b", step_b)       # 有 interrupt()
	.add_edge(START, "step_a")
	.add_edge("step_a", "step_b")
	.compile(checkpointer=True)  # 自己的检查点历史
)

graph = (
	StateGraph(State)
	.add_node("subgraph_node", subgraph)
	.add_edge(START, "subgraph_node")
	.compile(checkpointer=InMemorySaver())
)

config = {"configurable": {"thread_id": "1"}}

# 运行直到 step_a 中断
graph.invoke({"value": []}, config)

# 恢复 step_a -> 遇到 step_b 中断
graph.invoke(Command(resume="Alice"), config)

# 获取子图自己的检查点（在 step_a 和 step_b 之间）
parent_state = graph.get_state(config, subgraphs=True)
sub_config = parent_state.tasks[0].state.config

# 从子图检查点分支
fork_config = graph.update_state(sub_config, {"value": ["forked"]})
result = graph.invoke(None, fork_config)
# step_b 重新执行，step_a 的结果被保留
```

有关配置子图检查点器的更多信息，请参阅子图持久化。