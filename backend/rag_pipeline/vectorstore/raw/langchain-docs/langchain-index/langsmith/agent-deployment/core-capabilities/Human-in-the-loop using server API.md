# 使用服务器 API 实现人机交互

要在 agent 或工作流中审查、编辑和批准工具调用，请使用 LangGraph 的人机交互功能。

## 动态中断

```python
from langgraph_sdk import get_client
from langgraph_sdk.schema import Command
client = get_client(url=<your_url>)

# 使用名为 "agent" 部署的 graph
assistant_id = "agent"

# 创建一个 thread
thread = await client.threads.create()
thread_id = thread["thread_id"]

# 运行 graph 直到触发中断
result = await client.runs.wait(
    thread_id,
    assistant_id,
    input={"some_text": "original text"}   # (1)!
)

print(result['__interrupt__']) # (2)!
# > [
# >     {
# >         'value': {'text_to_revise': 'original text'},
# >         'resumable': True,
# >         'ns': ['human_node:fc722478-2f21-0578-c572-d9fc4dd07c3b'],
# >         'when': 'during'
# >     }
# > ]

# 恢复 graph
print(await client.runs.wait(
    thread_id,
    assistant_id,
    command=Command(resume="Edited text")   # (3)!
))
# > {'some_text': 'Edited text'}
```

1. 使用一些初始状态调用 graph。
2. 当 graph 触发中断时，它会返回一个包含 payload 和元数据的中断对象。
3. 使用 `Command(resume=...)` 恢复 graph，注入人类的输入并继续执行。

以下是一个可以在 Agent Server 中运行的示例 graph。
更多详情请参见 LangSmith 快速入门。

```python
from typing import TypedDict
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command

class State(TypedDict):
    some_text: str

def human_node(state: State):
    value = interrupt( # (1)!
        {
            "text_to_revise": state["some_text"] # (2)!
        }
    )
    return {
        "some_text": value # (3)!
    }

# 构建 graph
graph_builder = StateGraph(State)
graph_builder.add_node("human_node", human_node)
graph_builder.add_edge(START, "human_node")

graph = graph_builder.compile()
```

1. `interrupt(...)` 在 `human_node` 处暂停执行，将给定的 payload 展示给人类。
2. 任何可 JSON 序列化的值都可以传递给 `interrupt` 函数。此处是一个包含待修订文本的 dict。
3. 恢复后，`interrupt(...)` 的返回值是人类提供的输入，用于更新状态。

一旦您有一个正在运行的 Agent Server，就可以使用 LangGraph SDK 与之交互

```python
from langgraph_sdk import get_client
from langgraph_sdk.schema import Command
client = get_client(url=<your_url>)

# 使用名为 "agent" 部署的 graph
assistant_id = "agent"

# 创建一个 thread
thread = await client.threads.create()
thread_id = thread["thread_id"]

# 运行 graph 直到触发中断
result = await client.runs.wait(
    thread_id,
    assistant_id,
    input={"some_text": "original text"}   # (1)!
)

print(result['__interrupt__']) # (2)!
# > [
# >     {
# >         'value': {'text_to_revise': 'original text'},
# >         'resumable': True,
# >         'ns': ['human_node:fc722478-2f21-0578-c572-d9fc4dd07c3b'],
# >         'when': 'during'
# >     }
# > ]

# 恢复 graph
print(await client.runs.wait(
    thread_id,
    assistant_id,
    command=Command(resume="Edited text")   # (3)!
))
# > {'some_text': 'Edited text'}
```

1. 使用一些初始状态调用 graph。
2. 当 graph 触发中断时，它会返回一个包含 payload 和元数据的中断对象。
3. 使用 `Command(resume=...)` 恢复 graph，注入人类的输入并继续执行。

## 静态中断

静态中断（也称为静态断点）在节点执行之前或之后触发。

**不建议**将静态中断用于人机交互工作流。它们最适合用于调试和测试。

您可以在编译时通过指定 `interrupt_before` 和 `interrupt_after` 来设置静态中断：

```python
graph = graph_builder.compile( # (1)!
    interrupt_before=["node_a"], # (2)!
    interrupt_after=["node_b", "node_c"], # (3)!
)
```

1. 断点在 `compile` 时设置。
2. `interrupt_before` 指定节点，在这些节点执行之前应暂停执行。
3. `interrupt_after` 指定节点，在这些节点执行之后应暂停执行。

或者，您也可以在运行时设置静态中断：

```python
await client.runs.wait( # (1)!
    thread_id,
    assistant_id,
    inputs=inputs,
    interrupt_before=["node_a"], # (2)!
    interrupt_after=["node_b", "node_c"] # (3)!
)
```

1. 使用 `interrupt_before` 和 `interrupt_after` 参数调用 `client.runs.wait`。这是一个运行时配置，每次调用都可以更改。
2. `interrupt_before` 指定节点，在这些节点执行之前应暂停执行。
3. `interrupt_after` 指定节点，在这些节点执行之后应暂停执行。

以下示例展示了如何添加静态中断：

```python
from langgraph_sdk import get_client
client = get_client(url=<your_url>)

# 使用名为 "agent" 部署的 graph
assistant_id = "agent"

# 创建一个 thread
thread = await client.threads.create()
thread_id = thread["thread_id"]

# 运行 graph 直到断点
result = await client.runs.wait(
    thread_id,
    assistant_id,
    input=inputs   # (1)!
)

# 恢复 graph
await client.runs.wait(
    thread_id,
    assistant_id,
    input=None   # (2)!
)
```

1. 运行 graph 直到遇到第一个断点。
2. 通过为 `input` 传递 `None` 来恢复 graph。这将运行 graph 直到遇到下一个断点。

## 了解更多

* 人机交互概念指南：了解更多关于 LangGraph 人机交互功能的信息。
* 常见模式：学习如何实现批准/拒绝操作、请求用户输入、工具调用审查和验证人类输入等模式。