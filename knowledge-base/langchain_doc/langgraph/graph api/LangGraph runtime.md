# LangGraph runtime

Pregel实现了 LangGraph 的运行时，负责管理 LangGraph 应用程序的执行。

编译一个 StateGraph或创建一个 @entrypoint 会产生一个 `Pregel`实例，该实例可以通过输入调用。

本指南从高层次上解释运行时，并提供直接使用 Pregel 实现应用程序的说明。

> **注意：** Pregel运行时得名于 Google 的 Pregel 算法，该算法描述了一种使用图进行大规模并行计算的有效方法。

## 概述

在 LangGraph 中，Pregel 将 **actors** 和 **channels** 组合成一个单一的应用程序。**Actors** 从 channels 读取数据并向 channels 写入数据。Pregel 将应用程序的执行组织成多个步骤，遵循 **Pregel 算法** / **批量同步并行** 模型。

每一步包含三个阶段：

* **计划（Plan）**：确定在此步骤中要执行哪些 **actors**。例如，在第一步中，选择订阅特殊 **input** 通道的 **actors**；在后续步骤中，选择订阅上一步中更新的通道的 **actors**。
* **执行（Execution）**：并行执行所有选定的 **actors**，直到全部完成、其中一个失败或达到超时。在此阶段，通道更新对 actors 不可见，直到下一步。
* **更新（Update）**：使用在此步骤中由 **actors** 写入的值更新通道。

重复上述步骤，直到没有 **actors** 被选中执行，或达到最大步骤数。

## Actors

一个 **actor** 是一个 `PregelNode`。它订阅 channels，从中读取数据，并向它们写入数据。它可以被看作是 Pregel 算法中的一个 **actor**。`PregelNodes` 实现了 LangChain 的 `Runnable` 接口。

## Channels

Channels 用于在 actors（PregelNodes）之间进行通信。每个 channel 都有一个值类型、一个更新类型和一个更新函数——该函数接收一系列更新并修改存储的值。Channels 可用于将数据从一个链发送到另一个链，或在一个未来的步骤中将数据从一个链发送到自身。

### LastValue

LastValue 是默认的 channel 类型。它存储写入其中的最后一个值，覆盖任何先前的值。用于输入和输出值，或用于将数据从一个步骤传递到下一步。

```python 
from langgraph.channels import LastValue

channel: LastValue[int] = LastValue(int)
```

### Topic

`Topic` 是一个可配置的 PubSub channel，对于在 actors 之间发送多个值或跨步骤累积输出非常有用。它可以配置为去重值，或累积在一次运行期间写入的所有值。

```python
from langgraph.channels import Topic

# Accumulate all values written across steps
channel: Topic[str] = Topic(str, accumulate=True)
```

### BinaryOperatorAggregate

`BinaryOperatorAggregate` 存储一个持久化的值，通过将二元运算符应用于当前值和每个新更新来更新该值。用于计算跨步骤的运行聚合。

```python 
import operator
from langgraph.channels import BinaryOperatorAggregate

# Running total: each write adds to the current value
total = BinaryOperatorAggregate(int, operator.add)
```

### DeltaChannel (beta)

`DeltaChannel` 需要 `langgraph>=1.2`，目前处于 beta 阶段。API 在未来的版本中可能会发生变化。

`DeltaChannel` 在每个步骤中仅存储增量，而不是完整的累积值。这对于频繁写入并随时间累积大量值的通道最有用——例如，长时间运行的线程中的对话消息列表。如果没有增量存储，完整的列表会在每个检查点中被重新序列化；而使用 `DeltaChannel`，只会存储每一步写入的新消息。

当一个通道既被频繁写入，又随时间变得很大时，考虑使用 `DeltaChannel`。一个很好的信号是：如果您注意到特定通道的检查点大小随线程长度线性增长，那么 `DeltaChannel` 可能是一个很好的选择。

在 `Annotated` 类型注解中使用 `DeltaChannel` 的方式与使用普通 reducer 相同：

```python 
from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langgraph.channels import DeltaChannel

def my_reducer(state: list[str], writes: Sequence[list[str]]) -> list[str]:
    result = list(state)
    for write in writes:
        result.extend(write)
    return result

class State(TypedDict):
    messages: Annotated[list[str], DeltaChannel(my_reducer)]
```

#### 批量 reducer 要求

传递给 `DeltaChannel` 的 `reducer` 是一个 **批量 reducer**：它接收当前状态和当前步骤中所有写入的*序列*（在单次调用中），而不是像标准 reducer 那样成对处理。这与 `StateGraph` 中 `Annotated` 使用的每键 reducer（每次更新调用一次）不同。


  批量 reducer **必须是可结合的**（批处理不变的）：

```
reducer(reducer(state, [xs]), [ys]) == reducer(state, [xs, ys])
```

  如果您的 reducer 不可结合，则重构的状态可能因 LangGraph 在步骤之间对写入的批处理方式不同而产生不一致的行为。

  **reducer 在重建时运行，而不是在写入时。** 与 `BinaryOperatorAggregate`不同（后者的 reducer 在写入时调用，因此组合值被序列化到检查点中），`DeltaChannel` 的 reducer 是在从持久化的写入*重建*通道值时被调用的。被序列化的是原始的每步写入；reducer 仅在值被物化时调用——即在下次读取时、下一步的 actors 运行时，或在重放历史时。

  设计 reducer 时的实际影响：

  * **使其成为 `(state, writes)` 的纯函数。** 任何副作用、随机性或读取挂钟时间（例如 `uuid.uuid4()`、`datetime.now()`）都会在每次值被重建时执行，并在每次重放时产生不同的结果。它们*不会*被固化到持久化的写入中。
  * **不要依赖对传入写入的突变被持久化。** 如果您的 reducer 突变了一个写入对象（例如，为一个到达时没有 ID 的项目分配一个稳定的 ID），该突变仅存在于重建的值中。存储的写入仍然具有原始形状，因此下一次重建将再次看到未突变的输入。
  * **在上游附加标识和其他稳定的元数据。** 如果下游代码需要跨轮次通过 ID 引用一个项目（例如，以便稍后更新或删除它），请在值被写入通道之前分配该 ID——不要在 reducer 内部执行。

以下是两个最常见情况的批量 reducer：

```python 
from typing import Any, Sequence

# List: append all writes in order
def list_reducer(state: list[Any], writes: Sequence[list[Any]]) -> list[Any]:
    result = list(state)
    for write in writes:
        result.extend(write)
    return result

# Dict: merge all writes, last write wins on key conflicts
def dict_reducer(
    state: dict[str, Any], writes: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    result = dict(state)
    for write in writes:
        result.update(write)
    return result
```

两者都是可结合的：一次应用一个批次与一起应用它们产生相同的结果。

#### 使用 `snapshot_frequency` 限制读取延迟

如果没有快照，读取一个 `DeltaChannel` 值需要重放完整的写入历史——对于具有 N 个步骤的线程，复杂度为 O(N)。设置 `snapshot_frequency=K` 会在每 K 个 pregel 步骤写入一个完整的快照，从而将读取深度限制在最多 K 步：

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
class State(TypedDict):
    messages: Annotated[
        list[str],
        DeltaChannel(my_reducer, snapshot_frequency=5),
    ]
```

较高的 `snapshot_frequency` 值会降低存储开销，但会增加读取延迟。较低的值会以更大的检查点为代价更严格地限制延迟。`None`（默认值）完全跳过快照——适用于读取很少或线程很短的情况。

## 示例

虽然大多数用户将通过 StateGraphAPI 或 `@entrypoint` 装饰器与 Pregel 交互，但也可以直接与 Pregel 交互。

以下是一些不同的示例，让您了解 Pregel API。

```python 
from langgraph.channels import EphemeralValue
from langgraph.pregel import Pregel, NodeBuilder

node1 = (
	NodeBuilder().subscribe_only("a")
	.do(lambda x: x + x)
	.write_to("b")
)

app = Pregel(
	nodes={"node1": node1},
	channels={
		"a": EphemeralValue(str),
		"b": EphemeralValue(str),
	},
	input_channels=["a"],
	output_channels=["b"],
)

app.invoke({"a": "foo"})
```

```con 
{'b': 'foofoo'}
```

## 高级 API

LangGraph 提供了两个用于创建 Pregel 应用程序的高级 API：StateGraph (Graph API)和 Functional API。

    [StateGraph (Graph API)](https://reference.langchain.com/python/langgraph/graph/state/StateGraph) 是一个更高层次的抽象，它简化了 Pregel 应用程序的创建。它允许您定义节点和边的图。当您编译该图时，StateGraph API 会自动为您创建 Pregel 应用程序。

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from typing import TypedDict

from langgraph.constants import START
from langgraph.graph import StateGraph

class Essay(TypedDict):
	topic: str
	content: str | None
	score: float | None

def write_essay(essay: Essay):
	return {
		"content": f"Essay about {essay['topic']}",
	}

def score_essay(essay: Essay):
	return {
		"score": 10
	}

builder = StateGraph(Essay)
builder.add_node(write_essay)
builder.add_node(score_essay)
builder.add_edge(START, "write_essay")
builder.add_edge("write_essay", "score_essay")

# Compile the graph.
# This will return a Pregel instance.
graph = builder.compile()
```

编译后的 Pregel 实例将与一系列节点和通道关联。您可以通过打印它们来检查节点和通道。

```python 
print(graph.nodes)
```

您将看到类似这样的内容：

```python
{'__start__': <langgraph.pregel.read.PregelNode at 0x7d05e3ba1810>,
 'write_essay': <langgraph.pregel.read.PregelNode at 0x7d05e3ba14d0>,
 'score_essay': <langgraph.pregel.read.PregelNode at 0x7d05e3ba1710>}
```

```python
print(graph.channels)
```

你应该看到这些
```python
{'topic': <langgraph.channels.last_value.LastValue at 0x7d05e3294d80>,
 'content': <langgraph.channels.last_value.LastValue at 0x7d05e3295040>,
 'score': <langgraph.channels.last_value.LastValue at 0x7d05e3295980>,
 '__start__': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e3297e00>,
 'write_essay': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e32960c0>,
 'score_essay': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e2d8ab80>,
 'branch:__start__:__self__:write_essay': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e32941c0>,
 'branch:__start__:__self__:score_essay': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e2d88800>,
 'branch:write_essay:__self__:write_essay': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e3295ec0>,
 'branch:write_essay:__self__:score_essay': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e2d8ac00>,
 'branch:score_essay:__self__:write_essay': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e2d89700>,
 'branch:score_essay:__self__:score_essay': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e2d8b400>,
 'start:write_essay': <langgraph.channels.ephemeral_value.EphemeralValue at 0x7d05e2d8b280>}
```