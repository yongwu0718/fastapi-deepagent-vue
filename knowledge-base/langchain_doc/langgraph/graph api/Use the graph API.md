# Use the graph API
## 定义和更新状态

这里我们展示如何在 LangGraph 中定义和更新状态。我们将演示：

1.  如何使用状态来定义图的模式
2.  如何使用 reducers 来控制状态更新的处理方式。

### 定义状态

LangGraph 中的状态可以是 `TypedDict`、`Pydantic` 模型或 dataclass。下面我们将使用 `TypedDict`。有关使用 Pydantic 的详细信息，请参见将 Pydantic 模型用于图状态。

默认情况下，图将具有相同的输入和输出模式，状态决定了该模式。有关如何定义不同的输入和输出模式，请参见定义输入和输出模式。

让我们考虑一个使用消息的简单示例。这代表了许多 LLM 应用程序中状态的通用表述。有关更多详细信息，请参阅我们的概念页面。

```python
from langchain.messages import AnyMessage
from typing_extensions import TypedDict

class State(TypedDict):
    messages: list[AnyMessage]
    extra_field: int
```

此状态跟踪一个消息对象列表以及一个额外的整数字段。

### 更新状态

让我们构建一个包含单个节点的示例图。我们的节点只是一个 Python 函数，它读取图的状态并对其进行更新。此函数的第一个参数始终是状态：

```python
from langchain.messages import AIMessage

def node(state: State):
    messages = state["messages"]
    new_message = AIMessage("Hello!")
    return {"messages": messages + [new_message], "extra_field": 10}
```

这个节点只是将一条消息附加到我们的消息列表中，并填充一个额外的字段。

节点应直接返回对状态的更新，而不是改变状态。

接下来，我们定义一个包含此节点的简单图。我们使用 `StateGraph` 来定义在此状态上操作的图。然后使用 `add_node` 填充我们的图。

```python
from langgraph.graph import StateGraph

builder = StateGraph(State)
builder.add_node(node)
builder.set_entry_point("node")
graph = builder.compile()
```

LangGraph 提供了用于可视化您的图的内置实用程序。让我们检查一下我们的图。有关可视化的详细信息，请参阅可视化您的图。

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

在本例中，我们的图只执行一个节点。让我们进行一个简单的调用：

```python
from langchain.messages import HumanMessage

result = graph.invoke({"messages": [HumanMessage("Hi")]})
result
```

```
{'messages': [HumanMessage(content='Hi'), AIMessage(content='Hello!')], 'extra_field': 10}
```

请注意：

*   我们通过更新状态的单个键来启动调用。
*   我们在调用结果中收到整个状态。

为了方便，我们经常通过 pretty-print 来检查消息对象的内容：

```python
for message in result["messages"]:
    message.pretty_print()
```

```
================================ Human Message ================================

Hi
================================== Ai Message ==================================

Hello!
```

### 使用 reducers 处理状态更新

状态中的每个键都可以有自己的独立 reducer 函数，该函数控制如何应用来自节点的更新。如果没有明确指定 reducer 函数，则假定对该键的所有更新都应覆盖它。

对于 `TypedDict` 状态模式，我们可以通过使用 reducer 函数注释状态的相应字段来定义 reducers。

在前面的示例中，我们的节点通过将消息附加到状态来更新状态中的 `"messages"` 键。下面，我们为此键添加一个 reducer，以便更新自动追加：

```python
from typing_extensions import Annotated

def add(left, right):
    """也可以从 `operator` 内置模块导入 `add`。"""
    return left + right

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add]  
    extra_field: int
```

现在我们的节点可以简化：

```python
def node(state: State):
    new_message = AIMessage("Hello!")
    return {"messages": [new_message], "extra_field": 10}  
```

```python
from langgraph.graph import START

graph = StateGraph(State).add_node(node).add_edge(START, "node").compile()

result = graph.invoke({"messages": [HumanMessage("Hi")]})

for message in result["messages"]:
    message.pretty_print()
```

```
================================ Human Message ================================

Hi
================================== Ai Message ==================================

Hello!
```

#### MessagesState

在实践中，更新消息列表还有其他考虑因素：

*   我们可能希望更新状态中的现有消息。
*   我们可能希望接受消息格式的简写形式，例如 OpenAI 格式。

LangGraph 包含一个内置的 reducer `add_messages` 来处理这些考虑：

```python
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  
    extra_field: int

def node(state: State):
    new_message = AIMessage("Hello!")
    return {"messages": [new_message], "extra_field": 10}

graph = StateGraph(State).add_node(node).set_entry_point("node").compile()
```

```python
input_message = {"role": "user", "content": "Hi"}  

result = graph.invoke({"messages": [input_message]})

for message in result["messages"]:
    message.pretty_print()
```

```
================================ Human Message ================================

Hi
================================== Ai Message ==================================

Hello!
```

对于涉及聊天模型的应用程序来说，这是一种通用的状态表示。LangGraph 为了方便起见包含了一个预构建的 `MessagesState`，因此我们可以：

```python
from langgraph.graph import MessagesState

class State(MessagesState):
    extra_field: int
```

### 使用 `Overwrite` 绕过 Reducers

在某些情况下，您可能希望绕过 reducer 并直接覆盖状态值。LangGraph 为此提供了 `Overwrite` 类型。当一个节点返回用 `Overwrite` 包装的值时，reducer 被绕过，通道直接设置为该值。

当您想要重置或替换累积状态而不是将其与现有值合并时，这很有用。

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Overwrite
from typing_extensions import Annotated, TypedDict
import operator

class State(TypedDict):
    messages: Annotated[list, operator.add]

def add_message(state: State):
    return {"messages": ["first message"]}

def replace_messages(state: State):
    # 绕过 reducer 并替换整个 messages 列表
    return {"messages": Overwrite(["replacement message"])}

builder = StateGraph(State)
builder.add_node("add_message", add_message)
builder.add_node("replace_messages", replace_messages)
builder.add_edge(START, "add_message")
builder.add_edge("add_message", "replace_messages")
builder.add_edge("replace_messages", END)

graph = builder.compile()

result = graph.invoke({"messages": ["initial"]})
print(result["messages"])
```

```
['replacement message']
```

您也可以使用带有特殊键 `"__overwrite__"` 的 JSON 格式：

```python
def replace_messages(state: State):
    return {"messages": {"__overwrite__": ["replacement message"]}}
```

当节点并行执行时，在给定的超级步骤中，只能有一个节点对同一状态键使用 `Overwrite`。如果多个节点尝试在同一超级步骤中覆盖同一个键，将引发 `InvalidUpdateError`。

### 定义输入和输出模式

默认情况下，`StateGraph` 使用单一模式操作，并且期望所有节点使用该模式进行通信。但是，也可以为图定义不同的输入和输出模式。

当指定了不同的模式时，内部仍将使用一个内部模式用于节点之间的通信。输入模式确保提供的输入符合预期的结构，而输出模式则过滤内部数据，只根据定义的输出模式返回相关信息。

下面，我们将看到如何定义不同的输入和输出模式。

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

# 定义输入的模式
class InputState(TypedDict):
    question: str

# 定义输出的模式
class OutputState(TypedDict):
    answer: str

# 定义整体模式，结合了输入和输出
class OverallState(InputState, OutputState):
    pass

# 定义处理输入并生成答案的节点
def answer_node(state: InputState):
    # 示例答案和一个额外的键
    return {"answer": "bye", "question": state["question"]}

# 构建图，指定输入和输出模式
builder = StateGraph(OverallState, input_schema=InputState, output_schema=OutputState)
builder.add_node(answer_node)  # 添加答案节点
builder.add_edge(START, "answer_node")  # 定义起始边
builder.add_edge("answer_node", END)  # 定义结束边
graph = builder.compile()  # 编译图

# 用输入调用图并打印结果
print(graph.invoke({"question": "hi"}))
```

```
{'answer': 'bye'}
```

请注意，`invoke` 的输出只包含输出模式。

### 在节点之间传递私有状态

在某些情况下，您可能希望节点交换对于中间逻辑至关重要但不需要成为图主要模式一部分的信息。这些私有数据与图的整体输入/输出无关，并且只应在某些节点之间共享。

下面，我们将创建一个由三个节点（node\_1、node\_2 和 node\_3）组成的顺序图示例，其中私有数据在前两个步骤（node\_1 和 node\_2）之间传递，而第三个步骤（node\_3）只能访问公共的整体状态。

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

# 图的整体状态（这是节点间共享的公共状态）
class OverallState(TypedDict):
    a: str

# node_1 的输出包含不属于整体状态的私有数据
class Node1Output(TypedDict):
    private_data: str

# 私有数据仅在 node_1 和 node_2 之间共享
def node_1(state: OverallState) -> Node1Output:
    output = {"private_data": "set by node_1"}
    print(f"Entered node `node_1`:\n\tInput: {state}.\n\tReturned: {output}")
    return output

# Node 2 的输入仅请求 node_1 之后可用的私有数据
class Node2Input(TypedDict):
    private_data: str

def node_2(state: Node2Input) -> OverallState:
    output = {"a": "set by node_2"}
    print(f"Entered node `node_2`:\n\tInput: {state}.\n\tReturned: {output}")
    return output

# Node 3 只能访问整体状态（无法访问来自 node_1 的私有数据）
def node_3(state: OverallState) -> OverallState:
    output = {"a": "set by node_3"}
    print(f"Entered node `node_3`:\n\tInput: {state}.\n\tReturned: {output}")
    return output

# 按顺序连接节点
# node_2 接受来自 node_1 的私有数据，而
# node_3 看不到私有数据。
builder = StateGraph(OverallState).add_sequence([node_1, node_2, node_3])
builder.add_edge(START, "node_1")
graph = builder.compile()

# 使用初始状态调用图
response = graph.invoke(
    {
        "a": "set at start",
    }
)

print()
print(f"Output of graph invocation: {response}")
```

```
Entered node `node_1`:
    Input: {'a': 'set at start'}.
    Returned: {'private_data': 'set by node_1'}
Entered node `node_2`:
    Input: {'private_data': 'set by node_1'}.
    Returned: {'a': 'set by node_2'}
Entered node `node_3`:
    Input: {'a': 'set by node_2'}.
    Returned: {'a': 'set by node_3'}

Output of graph invocation: {'a': 'set by node_3'}
```

### 使用 pydantic 模型作为图状态

`StateGraph` 在初始化时接受一个 `state_schema` 参数，该参数指定了图中节点可以访问和更新的状态的“形状”。

在我们的示例中，我们通常使用 Python 原生 `TypedDict` 或 `dataclass` 作为 `state_schema`，但 `state_schema` 可以是任何类型。

在这里，我们将看到如何使用 Pydantic `BaseModel` 作为 `state_schema`，为**输入**添加运行时验证。

**已知限制**

  * 目前，图的输出**将不**会是 pydantic 模型的实例。
  * 运行时验证仅发生在图中第一个节点的输入上，而不是后续节点或输出上。
  * 来自 pydantic 的验证错误跟踪不会显示错误发生在哪个节点。
  * Pydantic 的递归验证可能较慢。对于性能敏感的应用程序，您可能需要考虑使用 `dataclass` 代替。

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from pydantic import BaseModel

# 图的整体状态（这是节点间共享的公共状态）
class OverallState(BaseModel):
    a: str

def node(state: OverallState):
    return {"a": "goodbye"}

# 构建状态图
builder = StateGraph(OverallState)
builder.add_node(node)  # node_1 是第一个节点
builder.add_edge(START, "node")  # 以 node_1 开始图
builder.add_edge("node", END)  # 在 node_1 之后结束图
graph = builder.compile()

# 使用有效输入测试图
graph.invoke({"a": "hello"})
```

使用**无效**输入调用图

```python
try:
    graph.invoke({"a": 123})  # 应该是字符串
except Exception as e:
    print("An exception was raised because `a` is an integer rather than a string.")
    print(e)
```

```
An exception was raised because `a` is an integer rather than a string.
1 validation error for OverallState
a
  Input should be a valid string [type=string_type, input_value=123, input_type=int]
    For further information visit https://errors.pydantic.dev/2.9/v/string_type
```

有关 Pydantic 模型状态的更多特性，请参见下文：

当使用 Pydantic 模型作为状态模式时，了解序列化的工作原理非常重要，尤其是在以下情况下：

  * 将 Pydantic 对象作为输入传递
  * 从图接收输出
  * 使用嵌套的 Pydantic 模型

  让我们看看这些行为。

  ```python
  from langgraph.graph import StateGraph, START, END
  from pydantic import BaseModel

  class NestedModel(BaseModel):
      value: str

  class ComplexState(BaseModel):
      text: str
      count: int
      nested: NestedModel

  def process_node(state: ComplexState):
      # 节点接收一个经过验证的 Pydantic 对象
      print(f"Input state type: {type(state)}")
      print(f"Nested type: {type(state.nested)}")
      # 返回字典更新
      return {"text": state.text + " processed", "count": state.count + 1}

  # 构建图
  builder = StateGraph(ComplexState)
  builder.add_node("process", process_node)
  builder.add_edge(START, "process")
  builder.add_edge("process", END)
  graph = builder.compile()

  # 为输入创建一个 Pydantic 实例
  input_state = ComplexState(text="hello", count=0, nested=NestedModel(value="test"))
  print(f"Input object type: {type(input_state)}")

  # 使用 Pydantic 实例调用图
  result = graph.invoke(input_state)
  print(f"Output type: {type(result)}")
  print(f"Output content: {result}")

  # 如果需要，转换回 Pydantic 模型
  output_model = ComplexState(**result)
  print(f"Converted back to Pydantic: {type(output_model)}")
  ```

Pydantic 对某些数据类型执行运行时类型强制转换。这可能很有用，但如果您不了解，也可能导致意外行为。

  ```python
  from langgraph.graph import StateGraph, START, END
  from pydantic import BaseModel

  class CoercionExample(BaseModel):
      # Pydantic 会将字符串数字强制转换为整数
      number: int
      # Pydantic 会将字符串布尔值解析为 bool
      flag: bool

  def inspect_node(state: CoercionExample):
      print(f"number: {state.number} (type: {type(state.number)})")
      print(f"flag: {state.flag} (type: {type(state.flag)})")
      return {}

  builder = StateGraph(CoercionExample)
  builder.add_node("inspect", inspect_node)
  builder.add_edge(START, "inspect")
  builder.add_edge("inspect", END)
  graph = builder.compile()

  # 演示使用将被转换的字符串输入进行强制转换
  result = graph.invoke({"number": "42", "flag": "true"})

  # 这将因验证错误而失败
  try:
      graph.invoke({"number": "not-a-number", "flag": "true"})
  except Exception as e:
      print(f"\nExpected validation error: {e}")
  ```

当您在状态模式中使用 LangChain 消息类型时，对于序列化有重要的考虑。您应该使用 `AnyMessage`（而不是 `BaseMessage`）以便在通过网络使用消息对象时进行正确的序列化/反序列化。

  ```python
  from langgraph.graph import StateGraph, START, END
  from pydantic import BaseModel
  from langchain.messages import HumanMessage, AIMessage, AnyMessage
  from typing import List

  class ChatState(BaseModel):
      messages: List[AnyMessage]
      context: str

  def add_message(state: ChatState):
      return {"messages": state.messages + [AIMessage(content="Hello there!")]}

  builder = StateGraph(ChatState)
  builder.add_node("add_message", add_message)
  builder.add_edge(START, "add_message")
  builder.add_edge("add_message", END)
  graph = builder.compile()

  # 使用消息创建输入
  initial_state = ChatState(
      messages=[HumanMessage(content="Hi")], context="Customer support chat"
  )

  result = graph.invoke(initial_state)
  print(f"Output: {result}")

  # 转换回 Pydantic 模型以查看消息类型
  output_model = ChatState(**result)
  for i, msg in enumerate(output_model.messages):
      print(f"Message {i}: {type(msg).__name__} - {msg.content}")
  ```

## 添加运行时配置

有时，您希望在调用图时能够对其进行配置。例如，您可能希望能够在运行时指定使用哪个 LLM 或系统提示，*而不用用这些参数污染图状态*。

要添加运行时配置：

1.  为您的配置指定一个模式
2.  将配置添加到节点或条件边的函数签名中
3.  将配置传递给图。

参见下面的简单示例：

```python
from langgraph.graph import END, StateGraph, START
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

# 1. 指定配置模式
class ContextSchema(TypedDict):
    my_runtime_value: str

# 2. 定义一个在节点中访问配置的图
class State(TypedDict):
    my_state_value: str

def node(state: State, runtime: Runtime[ContextSchema]):  
    if runtime.context["my_runtime_value"] == "a":  
        return {"my_state_value": 1}
    elif runtime.context["my_runtime_value"] == "b":  
        return {"my_state_value": 2}
    else:
        raise ValueError("Unknown values.")

builder = StateGraph(State, context_schema=ContextSchema)  
builder.add_node(node)
builder.add_edge(START, "node")
builder.add_edge("node", END)

graph = builder.compile()

# 3. 在运行时传入配置：
print(graph.invoke({}, context={"my_runtime_value": "a"}))  
print(graph.invoke({}, context={"my_runtime_value": "b"}))  
```

```
{'my_state_value': 1}
{'my_state_value': 2}
```

下面我们演示一个实际示例，其中我们配置在运行时使用哪个 LLM。我们将同时使用 OpenAI 和 Anthropic 模型。

  ```python
  from dataclasses import dataclass

  from langchain.chat_models import init_chat_model
  from langgraph.graph import MessagesState, END, StateGraph, START
  from langgraph.runtime import Runtime
  from typing_extensions import TypedDict

  @dataclass
  class ContextSchema:
      model_provider: str = "anthropic"

  MODELS = {
      "anthropic": init_chat_model("claude-haiku-4-5-20251001"),
      "openai": init_chat_model("gpt-5.4-mini"),
  }

  def call_model(state: MessagesState, runtime: Runtime[ContextSchema]):
      model = MODELS[runtime.context.model_provider]
      response = model.invoke(state["messages"])
      return {"messages": [response]}

  builder = StateGraph(MessagesState, context_schema=ContextSchema)
  builder.add_node("model", call_model)
  builder.add_edge(START, "model")
  builder.add_edge("model", END)

  graph = builder.compile()

  # 用法
  input_message = {"role": "user", "content": "hi"}
  # 没有配置，使用默认值（Anthropic）
  response_1 = graph.invoke({"messages": [input_message]}, context=ContextSchema())["messages"][-1]
  # 或者，可以设置 OpenAI
  response_2 = graph.invoke({"messages": [input_message]}, context={"model_provider": "openai"})["messages"][-1]

  print(response_1.response_metadata["model_name"])
  print(response_2.response_metadata["model_name"])
  ```

  ```
  claude-haiku-4-5-20251001
  gpt-5.4-mini
  ```

下面我们演示一个实际示例，其中我们配置两个参数：要在运行时使用的 LLM 和系统消息。

  ```python
  from dataclasses import dataclass
  from langchain.chat_models import init_chat_model
  from langchain.messages import SystemMessage
  from langgraph.graph import END, MessagesState, StateGraph, START
  from langgraph.runtime import Runtime
  from typing_extensions import TypedDict

  @dataclass
  class ContextSchema:
      model_provider: str = "anthropic"
      system_message: str | None = None

  MODELS = {
      "anthropic": init_chat_model("claude-haiku-4-5-20251001"),
      "openai": init_chat_model("gpt-5.4-mini"),
  }

  def call_model(state: MessagesState, runtime: Runtime[ContextSchema]):
      model = MODELS[runtime.context.model_provider]
      messages = state["messages"]
      if (system_message := runtime.context.system_message):
          messages = [SystemMessage(system_message)] + messages
      response = model.invoke(messages)
      return {"messages": [response]}

  builder = StateGraph(MessagesState, context_schema=ContextSchema)
  builder.add_node("model", call_model)
  builder.add_edge(START, "model")
  builder.add_edge("model", END)

  graph = builder.compile()

  # 用法
  input_message = {"role": "user", "content": "hi"}
  response = graph.invoke({"messages": [input_message]}, context={"model_provider": "openai", "system_message": "Respond in Italian."})
  for message in response["messages"]:
      message.pretty_print()
  ```

  ```
  ================================ Human Message ================================

  hi
  ================================== Ai Message ==================================

  Ciao! Come posso aiutarti oggi?
  ```

## 添加重试策略

在许多用例中，您可能希望您的节点具有自定义的重试策略，例如，如果您正在调用 API、查询数据库或调用 LLM 等。LangGraph 允许您向节点添加重试策略。

要配置重试策略，请将 `retry_policy` 参数传递给 `add_node`。`retry_policy` 参数接受一个 `RetryPolicy` 命名元组对象。下面我们使用默认参数实例化一个 `RetryPolicy` 对象，并将其与一个节点关联：

```python
from langgraph.types import RetryPolicy

builder.add_node(
    "node_name",
    node_function,
    retry_policy=RetryPolicy(),
)
```

默认情况下，`retry_on` 参数使用 `default_retry_on` 函数，该函数会重试任何异常，除了以下异常：

* `ValueError`
* `TypeError`
* `ArithmeticError`
* `ImportError`
* `LookupError`
* `NameError`
* `SyntaxError`
* `RuntimeError`
* `ReferenceError`
* `StopIteration`
* `StopAsyncIteration`
* `OSError`

此外，对于来自流行 http 请求库（如 `requests` 和 `httpx`）的异常，它仅重试 5xx 状态码。

考虑一个我们从 SQL 数据库读取数据的示例。下面我们将两种不同的重试策略传递给节点：

  ```python
  import sqlite3
  from typing_extensions import TypedDict
  from langchain.chat_models import init_chat_model
  from langgraph.graph import END, MessagesState, StateGraph, START
  from langgraph.types import RetryPolicy
  from langchain_community.utilities import SQLDatabase
  from langchain.messages import AIMessage

  db = SQLDatabase.from_uri("sqlite:///:memory:")
  model = init_chat_model("claude-haiku-4-5-20251001")

  def query_database(state: MessagesState):
      query_result = db.run("SELECT * FROM Artist LIMIT 10;")
      return {"messages": [AIMessage(content=query_result)]}

  def call_model(state: MessagesState):
      response = model.invoke(state["messages"])
      return {"messages": [response]}

  # 定义一个新图
  builder = StateGraph(MessagesState)
  builder.add_node(
      "query_database",
      query_database,
      retry_policy=RetryPolicy(retry_on=sqlite3.OperationalError),
  )
  builder.add_node("model", call_model, retry_policy=RetryPolicy(max_attempts=5))
  builder.add_edge(START, "model")
  builder.add_edge("model", "query_database")
  builder.add_edge("query_database", END)
  graph = builder.compile()
  ```

### 在节点内部访问执行信息

您可以通过 `runtime.execution_info` 访问执行标识和重试信息。这提供了线程、运行和检查点标识符以及重试状态，而无需直接从 `config` 读取。

| 属性                          | 类型              | 描述                                                                                       |
| ----------------------------- | ----------------- | ------------------------------------------------------------------------------------------ |
| `thread_id`                   | `str \| None`     | 当前执行的线程 ID。如果没有 checkpointer，则为 `None`。                                   |
| `run_id`                      | `str \| None`     | 当前执行的运行 ID。如果配置中未提供，则为 `None`。                                         |
| `checkpoint_id`               | `str`             | 当前执行的检查点 ID。                                                                       |
| `checkpoint_ns`               | `str`             | 当前执行的检查点命名空间。                                                                   |
| `task_id`                     | `str`             | 当前执行的任务 ID。                                                                         |
| `node_attempt`                | `int`             | 当前执行尝试次数（从1开始）。第一次尝试为 `1`，第一次重试为 `2`，依此类推。               |
| `node_first_attempt_time`     | `float \| None`   | 第一次尝试开始的 Unix 时间戳（秒）。在重试期间保持不变。                                   |

#### 访问线程 ID 和运行 ID

使用 `execution_info` 在节点内部访问线程 ID、运行 ID 和其他标识字段：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

class State(TypedDict):
    result: str

def my_node(state: State, runtime: Runtime):
    info = runtime.execution_info
    print(f"Thread: {info.thread_id}, Run: {info.run_id}")  
    return {"result": "done"}

builder = StateGraph(State)
builder.add_node("my_node", my_node)
builder.add_edge(START, "my_node")
builder.add_edge("my_node", END)
graph = builder.compile()
```

#### 根据重试状态调整行为

当一个节点具有重试策略时，使用 `execution_info` 检查当前尝试次数，并在第一次尝试失败后切换到后备方案：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.types import RetryPolicy
from typing_extensions import TypedDict

class State(TypedDict):
    result: str

def my_node(state: State, runtime: Runtime):
    info = runtime.execution_info
    if info.node_attempt > 1:  
        # 重试时使用后备方案
        return {"result": call_fallback_api()}
    return {"result": call_primary_api()}

builder = StateGraph(State)
builder.add_node("my_node", my_node, retry_policy=RetryPolicy(max_attempts=3))
builder.add_edge(START, "my_node")
builder.add_edge("my_node", END)
graph = builder.compile()
```

即使没有重试策略，`execution_info` 在 `Runtime` 对象上也始终可用——`node_attempt` 默认为 `1`，并且 `node_first_attempt_time` 设置为节点开始执行的时间。

### 在节点内部访问服务端信息

当您的图在 LangGraph Server 上运行时，您可以通过 `runtime.server_info` 访问服务器特定的元数据。这提供了 assistant ID、graph ID 和已认证用户，而无需直接从 config 元数据或可配置键中读取。

| 属性            | 类型                   | 描述                                                   |
| --------------- | ---------------------- | ------------------------------------------------------ |
| `assistant_id`  | `str`                  | 当前部署的 assistant ID。                              |
| `graph_id`      | `str`                  | 当前部署的 graph ID。                                  |
| `user`          | `BaseUser \| None`     | 已认证的用户（如果配置了自定义身份验证）。             |

```python
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

class State(TypedDict):
    result: str

def my_node(state: State, runtime: Runtime):
    server = runtime.server_info
    if server is not None:
        print(f"Assistant: {server.assistant_id}, Graph: {server.graph_id}")  
        if server.user is not None:
            print(f"User: {server.user.identity}")
    return {"result": "done"}

builder = StateGraph(State)
builder.add_node("my_node", my_node)
builder.add_edge(START, "my_node")
builder.add_edge("my_node", END)
graph = builder.compile()
```

当图不在 LangGraph Server 上运行时（例如在本地开发或测试期间），`server_info` 为 `None`。

`runtime.execution_info` 和 `runtime.server_info` 需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）。

## 添加节点缓存

节点缓存在您希望避免重复操作（例如在时间或成本方面昂贵的操作）的情况下很有用。LangGraph 允许您向图中的节点添加个性化的缓存策略。

要配置缓存策略，请将 `cache_policy` 参数传递给 `add_node` 函数。在以下示例中，实例化了一个 `CachePolicy` 对象，其生存时间为 120 秒，并使用默认的 `key_func` 生成器。然后将其与一个节点关联：

```python
from langgraph.types import CachePolicy

builder.add_node(
    "node_name",
    node_function,
    cache_policy=CachePolicy(ttl=120),
)
```

然后，要为图启用节点级缓存，请在编译图时设置 `cache` 参数。下面的示例使用 `InMemoryCache` 设置具有内存缓存的图，但 `SqliteCache` 也可用。

```python
from langgraph.cache.memory import InMemoryCache

graph = builder.compile(cache=InMemoryCache())
```

## 创建步骤序列

**先决条件**
  本指南假定您熟悉上面关于状态的部分。

这里我们演示如何构建一个简单的步骤序列。我们将展示：

1.  如何构建一个顺序图
2.  用于构建类似图的内置简写。

要添加节点序列，我们使用图的 `add_node` 和 `add_edge` 方法：

```python
from langgraph.graph import START, StateGraph

builder = StateGraph(State)

# 添加节点
builder.add_node(step_1)
builder.add_node(step_2)
builder.add_node(step_3)

# 添加边
builder.add_edge(START, "step_1")
builder.add_edge("step_1", "step_2")
builder.add_edge("step_2", "step_3")
```

我们也可以使用内置的简写 `.add_sequence`：

```python
builder = StateGraph(State).add_sequence([step_1, step_2, step_3])
builder.add_edge(START, "step_1")
```

LangGraph 可以轻松地向您的应用程序添加底层的持久化层。
  这允许在节点执行之间对状态进行检查点，因此您的 LangGraph 节点可以控制：

  * 状态更新如何被检查点记录
  * 如何在人机交互工作流中恢复中断
  * 如何使用 LangGraph 的时间旅行功能“回退”和分支执行

  它们还确定执行步骤如何流式传输，以及如何使用 Studio 可视化和调试您的应用程序。

  让我们演示一个端到端的示例。我们将创建一个三个步骤的序列：

  1.  在状态的一个键中填充一个值
  2.  更新相同的值
  3.  填充一个不同的值

  让我们首先定义我们的状态。这控制着图的模式，并且还可以指定如何应用更新。有关更多详细信息，请参阅使用 reducers 处理状态更新。

  在我们的例子中，我们将只跟踪两个值：

  ```python
  from typing_extensions import TypedDict

  class State(TypedDict):
      value_1: str
      value_2: int
  ```

  我们的节点只是读取图状态并对其进行更新的 Python 函数。此函数的第一个参数将始终是状态：

  ```python
  def step_1(state: State):
      return {"value_1": "a"}

  def step_2(state: State):
      current_value_1 = state["value_1"]
      return {"value_1": f"{current_value_1} b"}

  def step_3(state: State):
      return {"value_2": 10}
  ```

请注意，当向状态发出更新时，每个节点可以只指定它希望更新的键的值。

    默认情况下，这将**覆盖**相应键的值。您也可以使用 reducers 来控制更新如何处理——例如，您可以将连续的更新追加到一个键上，而不是覆盖。有关更多详细信息，请参阅使用 reducers 处理状态更新。

最后，我们定义图。我们使用 `StateGraph` 来定义在此状态上操作的图。

  然后，我们将使用 `add_node` 和 `add_edge` 来填充我们的图并定义其控制流。

  ```python
  from langgraph.graph import START, StateGraph

  builder = StateGraph(State)

  # 添加节点
  builder.add_node(step_1)
  builder.add_node(step_2)
  builder.add_node(step_3)

  # 添加边
  builder.add_edge(START, "step_1")
  builder.add_edge("step_1", "step_2")
  builder.add_edge("step_2", "step_3")
  ```

**指定自定义名称**
    您可以使用 `add_node` 为节点指定自定义名称：

```python
builder.add_node("my_node", step_1)
```

请注意：

  * `add_edge` 接受节点的名称，对于函数，默认为 `node.__name__`。
  * 我们必须指定图的入口点。为此，我们添加一条带有 `START` 节点的边。
  * 当没有更多节点要执行时，图停止。

  接下来，我们编译我们的图。这会对图的结构进行一些基本检查（例如，识别孤立节点）。如果我们通过 checkpointer 向应用程序添加持久化，它也将在这里传递。

  ```python
  graph = builder.compile()
  ```

  LangGraph 提供了用于可视化您的图的内置实用程序。让我们检查一下我们的序列。有关可视化的详细信息，请参阅可视化您的图。

  ```python
  from IPython.display import Image, display

  display(Image(graph.get_graph().draw_mermaid_png()))
  ```

让我们进行一个简单的调用：

  ```python
  graph.invoke({"value_1": "c"})
  ```

  ```
  {'value_1': 'a b', 'value_2': 10}
  ```

请注意：

  * 我们通过为单个状态键提供一个值来启动调用。我们必须始终为至少一个键提供一个值。
  * 我们传入的值被第一个节点覆盖了。
  * 第二个节点更新了该值。
  * 第三个节点填充了一个不同的值。

**内置简写**
    `langgraph>=0.2.46` 包含一个用于添加节点序列的内置简写 `add_sequence`。您可以按如下方式编译相同的图：

```python
builder = StateGraph(State).add_sequence([step_1, step_2, step_3])  
builder.add_edge(START, "step_1")

graph = builder.compile()

graph.invoke({"value_1": "c"})
```

## 创建分支

节点的并行执行对于加速整体图操作至关重要。LangGraph 原生支持节点的并行执行，这可以显著提高基于图的工作流的性能。这种并行化是通过扇出 (fan-out) 和扇入 (fan-in) 机制实现的，利用普通边和条件边。以下是一些示例，展示了如何添加为您工作的分支数据流。

### 并行运行图节点

在本例中，我们从 `Node A` 扇出到 `B and C`，然后扇入到 `D`。使用我们的状态，我们指定 reducer 的 add 操作。这将组合或累积状态中特定键的值，而不是简单地覆盖现有值。对于列表，这意味着将新列表与现有列表连接起来。有关使用 reducers 更新状态的更多详细信息，请参见上面关于状态 reducer 的部分。

```python
import operator
from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    # operator.add reducer fn 使其变为仅追加
    aggregate: Annotated[list, operator.add]

def a(state: State):
    print(f'Adding "A" to {state["aggregate"]}')
    return {"aggregate": ["A"]}

def b(state: State):
    print(f'Adding "B" to {state["aggregate"]}')
    return {"aggregate": ["B"]}

def c(state: State):
    print(f'Adding "C" to {state["aggregate"]}')
    return {"aggregate": ["C"]}

def d(state: State):
    print(f'Adding "D" to {state["aggregate"]}')
    return {"aggregate": ["D"]}

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(c)
builder.add_node(d)
builder.add_edge(START, "a")
builder.add_edge("a", "b")
builder.add_edge("a", "c")
builder.add_edge("b", "d")
builder.add_edge("c", "d")
builder.add_edge("d", END)
graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

使用 reducer，您可以看到在每个节点中添加的值被累积起来。

```python
graph.invoke({"aggregate": []}, {"configurable": {"thread_id": "foo"}})
```

```
Adding "A" to []
Adding "B" to ['A']
Adding "C" to ['A']
Adding "D" to ['A', 'B', 'C']
```

在上面的例子中，节点 `"b"` 和 `"c"` 在同一超级步骤中并发执行。因为它们在同一步骤中，节点 `"d"` 在 `"b"` 和 `"c"` 都完成后才执行。

  重要的是，来自并行超级步骤的更新可能不会一致地排序。如果您需要来自并行超级步骤的一致、预定的更新顺序，您应该将输出写入状态中的一个单独字段，并附带一个用于排序的值。

LangGraph 在超级步骤内执行节点，这意味着虽然并行分支并行执行，但整个超级步骤是**事务性**的。如果其中任何一个分支引发异常，则**没有**更新被应用到状态（整个超级步骤出错）。

  重要的是，当使用 checkpointer 时，超级步骤中成功节点的结果会被保存，并且在恢复时不会重复。

  如果您的节点容易出错（可能想要处理脆弱的 API 调用），LangGraph 提供了两种方法来解决这个问题：

  1.  您可以在节点内编写常规的 Python 代码来捕获和处理异常。
  2.  您可以设置一个 **retry_policy** 来指示图重试引发特定类型异常的节点。只有失败的分支会被重试，因此您不必担心执行重复的工作。

  总之，这些让您能够执行并行执行并完全控制异常处理。

**设置最大并发数**
  您可以通过在调用图时在配置中设置 `max_concurrency` 来控制并发任务的最大数量。

  ```python
  graph.invoke({"value_1": "c"}, {"configurable": {"max_concurrency": 10}})
  ```

### 延迟节点执行

当您想要延迟节点的执行直到所有其他待处理任务完成时，延迟节点执行很有用。当分支具有不同长度时，这尤其相关，这在 map-reduce 流等工作流中很常见。

上面的示例展示了当每条路径只有一步时如何扇出和扇入。但如果一个分支有多个步骤呢？让我们在 `"b"` 分支中添加一个节点 `"b_2"`：

```python
import operator
from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    # operator.add reducer fn 使其变为仅追加
    aggregate: Annotated[list, operator.add]

def a(state: State):
    print(f'Adding "A" to {state["aggregate"]}')
    return {"aggregate": ["A"]}

def b(state: State):
    print(f'Adding "B" to {state["aggregate"]}')
    return {"aggregate": ["B"]}

def b_2(state: State):
    print(f'Adding "B_2" to {state["aggregate"]}')
    return {"aggregate": ["B_2"]}

def c(state: State):
    print(f'Adding "C" to {state["aggregate"]}')
    return {"aggregate": ["C"]}

def d(state: State):
    print(f'Adding "D" to {state["aggregate"]}')
    return {"aggregate": ["D"]}

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(b_2)
builder.add_node(c)
builder.add_node(d, defer=True)  
builder.add_edge(START, "a")
builder.add_edge("a", "b")
builder.add_edge("a", "c")
builder.add_edge("b", "b_2")
builder.add_edge("b_2", "d")
builder.add_edge("c", "d")
builder.add_edge("d", END)
graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

```python
graph.invoke({"aggregate": []})
```

```
Adding "A" to []
Adding "B" to ['A']
Adding "C" to ['A']
Adding "B_2" to ['A', 'B', 'C']
Adding "D" to ['A', 'B', 'C', 'B_2']
```

在上面的例子中，节点 `"b"` 和 `"c"` 在同一超级步骤中并发执行。我们在节点 `d` 上设置了 `defer=True`，因此它将在所有待处理任务完成之前不会执行。在这种情况下，这意味着 `"d"` 将等待整个 `"b"` 分支完成才执行。

### 条件分支

如果您的扇出应根据状态在运行时发生变化，您可以使用 `add_conditional_edges` 使用图状态选择一个或多个路径。请参见下面的示例，其中节点 `a` 生成一个确定下一个节点的状态更新。

```python
import operator
from typing import Annotated, Literal, Sequence
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    aggregate: Annotated[list, operator.add]
    # 向状态添加一个键。我们将设置此键以确定
    # 如何分支。
    which: str

def a(state: State):
    print(f'Adding "A" to {state["aggregate"]}')
    return {"aggregate": ["A"], "which": "c"}  

def b(state: State):
    print(f'Adding "B" to {state["aggregate"]}')
    return {"aggregate": ["B"]}

def c(state: State):
    print(f'Adding "C" to {state["aggregate"]}')
    return {"aggregate": ["C"]}

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(c)
builder.add_edge(START, "a")
builder.add_edge("b", END)
builder.add_edge("c", END)

def conditional_edge(state: State) -> Literal["b", "c"]:
    # 在此处填充任意逻辑，使用状态
    # 来确定下一个节点
    return state["which"]

builder.add_conditional_edges("a", conditional_edge)  

graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

```python
result = graph.invoke({"aggregate": []})
print(result)
```

```
Adding "A" to []
Adding "C" to ['A']
{'aggregate': ['A', 'C'], 'which': 'c'}
```

您的条件边可以路由到多个目标节点。例如：

  ```python
  def route_bc_or_cd(state: State) -> Sequence[str]:
      if state["which"] == "cd":
          return ["c", "d"]
      return ["b", "c"]
  ```

## Map-Reduce 和 Send API

LangGraph 使用 Send API 支持 map-reduce 和其他高级分支模式。以下是如何使用它的示例：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing_extensions import TypedDict, Annotated
import operator

class OverallState(TypedDict):
    topic: str
    subjects: list[str]
    jokes: Annotated[list[str], operator.add]
    best_selected_joke: str

def generate_topics(state: OverallState):
    return {"subjects": ["lions", "elephants", "penguins"]}

def generate_joke(state: OverallState):
    joke_map = {
        "lions": "Why don't lions like fast food? Because they can't catch it!",
        "elephants": "Why don't elephants use computers? They're afraid of the mouse!",
        "penguins": "Why don't penguins like talking to strangers at parties? Because they find it hard to break the ice."
    }
    return {"jokes": [joke_map[state["subject"]]]}

def continue_to_jokes(state: OverallState):
    return [Send("generate_joke", {"subject": s}) for s in state["subjects"]]

def best_joke(state: OverallState):
    return {"best_selected_joke": "penguins"}

builder = StateGraph(OverallState)
builder.add_node("generate_topics", generate_topics)
builder.add_node("generate_joke", generate_joke)
builder.add_node("best_joke", best_joke)
builder.add_edge(START, "generate_topics")
builder.add_conditional_edges("generate_topics", continue_to_jokes, ["generate_joke"])
builder.add_edge("generate_joke", "best_joke")
builder.add_edge("best_joke", END)
graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

```python
# 调用图：这里我们调用它来生成一个笑话列表
for step in graph.stream({"topic": "animals"}):
    print(step)
```

```
{'generate_topics': {'subjects': ['lions', 'elephants', 'penguins']}}
{'generate_joke': {'jokes': ["Why don't lions like fast food? Because they can't catch it!"]}}
{'generate_joke': {'jokes': ["Why don't elephants use computers? They're afraid of the mouse!"]}}
{'generate_joke': {'jokes': ['Why don't penguins like talking to strangers at parties? Because they find it hard to break the ice.']}}
{'best_joke': {'best_selected_joke': 'penguins'}}
```

## 创建和控制循环

在创建带有循环的图时，我们需要一种终止执行的机制。这最常见的是通过添加一条条件边来实现，该条件边一旦达到某个终止条件就会路由到 `END` 节点。

您还可以在调用或流式传输图时设置图的递归限制。递归限制设置了图在引发错误之前允许执行的超级步骤数。阅读更多关于递归限制概念的信息。

让我们考虑一个带有循环的简单图，以更好地了解这些机制如何工作。

要返回状态的最后一个值而不是收到递归限制错误，请参阅下一节。

在创建循环时，您可以包含一个指定终止条件的条件边：

```python
builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)

def route(state: State) -> Literal["b", END]:
    if termination_condition(state):
        return END
    else:
        return "b"

builder.add_edge(START, "a")
builder.add_conditional_edges("a", route)
builder.add_edge("b", "a")
graph = builder.compile()
```

要控制递归限制，请在配置中指定 `"recursion_limit"`。这将引发一个 `GraphRecursionError`，您可以捕获并处理它：

```python
from langgraph.errors import GraphRecursionError

try:
    graph.invoke(inputs, {"recursion_limit": 3})
except GraphRecursionError:
    print("Recursion Error")
```

让我们定义一个带有简单循环的图。注意我们使用条件边来实现终止条件。

```python
import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    # operator.add reducer fn 使其变为仅追加
    aggregate: Annotated[list, operator.add]

def a(state: State):
    print(f'Node A sees {state["aggregate"]}')
    return {"aggregate": ["A"]}

def b(state: State):
    print(f'Node B sees {state["aggregate"]}')
    return {"aggregate": ["B"]}

# 定义节点
builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)

# 定义边
def route(state: State) -> Literal["b", END]:
    if len(state["aggregate"]) < 7:
        return "b"
    else:
        return END

builder.add_edge(START, "a")
builder.add_conditional_edges("a", route)
builder.add_edge("b", "a")
graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

这种架构类似于一个 ReAct agent，其中节点 `"a"` 是一个工具调用模型，节点 `"b"` 代表工具。

在我们的 `route` 条件边中，我们指定一旦状态中的 `"aggregate"` 列表超过阈值长度，就应该结束。

调用图，我们看到在达到终止条件之前，我们在节点 `"a"` 和 `"b"` 之间交替。

```python
graph.invoke({"aggregate": []})
```

```
Node A sees []
Node B sees ['A']
Node A sees ['A', 'B']
Node B sees ['A', 'B', 'A']
Node A sees ['A', 'B', 'A', 'B']
Node B sees ['A', 'B', 'A', 'B', 'A']
Node A sees ['A', 'B', 'A', 'B', 'A', 'B']
```

### 施加递归限制

在某些应用程序中，我们可能无法保证达到给定的终止条件。在这些情况下，我们可以设置图的递归限制。这将在给定数量的超级步骤后引发 `GraphRecursionError`。然后我们可以捕获并处理这个异常：

```python
from langgraph.errors import GraphRecursionError

try:
    graph.invoke({"aggregate": []}, {"recursion_limit": 4})
except GraphRecursionError:
    print("Recursion Error")
```

```
Node A sees []
Node B sees ['A']
Node C sees ['A', 'B']
Node D sees ['A', 'B']
Node A sees ['A', 'B', 'C', 'D']
Recursion Error
```

我们可以不引发 `GraphRecursionError`，而是在状态中引入一个新的键，用于跟踪直到达到递归限制还剩多少步。然后我们可以使用这个键来确定是否应该结束运行。

  LangGraph 实现了一个特殊的 `RemainingSteps` 注解。在底层，它创建了一个 `ManagedValue` 通道——一个在我们的图运行期间存在且不会更长的状态通道。

  ```python
  import operator
  from typing import Annotated, Literal
  from typing_extensions import TypedDict
  from langgraph.graph import StateGraph, START, END
  from langgraph.managed.is_last_step import RemainingSteps

  class State(TypedDict):
      aggregate: Annotated[list, operator.add]
      remaining_steps: RemainingSteps

  def a(state: State):
      print(f'Node A sees {state["aggregate"]}')
      return {"aggregate": ["A"]}

  def b(state: State):
      print(f'Node B sees {state["aggregate"]}')
      return {"aggregate": ["B"]}

  # 定义节点
  builder = StateGraph(State)
  builder.add_node(a)
  builder.add_node(b)

  # 定义边
  def route(state: State) -> Literal["b", END]:
      if state["remaining_steps"] <= 2:
          return END
      else:
          return "b"

  builder.add_edge(START, "a")
  builder.add_conditional_edges("a", route)
  builder.add_edge("b", "a")
  graph = builder.compile()

  # 测试一下
  result = graph.invoke({"aggregate": []}, {"recursion_limit": 4})
  print(result)
  ```

  ```
  Node A sees []
  Node B sees ['A']
  Node A sees ['A', 'B']
  {'aggregate': ['A', 'B', 'A']}
  ```

为了更好地理解递归限制是如何工作的，让我们考虑一个更复杂的例子。下面我们实现了一个循环，但其中一个步骤扇出到两个节点：

  ```python
  import operator
  from typing import Annotated, Literal
  from typing_extensions import TypedDict
  from langgraph.graph import StateGraph, START, END

  class State(TypedDict):
      aggregate: Annotated[list, operator.add]

  def a(state: State):
      print(f'Node A sees {state["aggregate"]}')
      return {"aggregate": ["A"]}

  def b(state: State):
      print(f'Node B sees {state["aggregate"]}')
      return {"aggregate": ["B"]}

  def c(state: State):
      print(f'Node C sees {state["aggregate"]}')
      return {"aggregate": ["C"]}

  def d(state: State):
      print(f'Node D sees {state["aggregate"]}')
      return {"aggregate": ["D"]}

  # 定义节点
  builder = StateGraph(State)
  builder.add_node(a)
  builder.add_node(b)
  builder.add_node(c)
  builder.add_node(d)

  # 定义边
  def route(state: State) -> Literal["b", END]:
      if len(state["aggregate"]) < 7:
          return "b"
      else:
          return END

  builder.add_edge(START, "a")
  builder.add_conditional_edges("a", route)
  builder.add_edge("b", "c")
  builder.add_edge("b", "d")
  builder.add_edge(["c", "d"], "a")
  graph = builder.compile()
  ```

  ```python
  from IPython.display import Image, display

  display(Image(graph.get_graph().draw_mermaid_png()))
  ```

这个图看起来很复杂，但可以概念化为超级步骤的循环：

  1.  节点 A
  2.  节点 B
  3.  节点 C 和 D
  4.  节点 A
  5.  ...

  我们有一个由四个超级步骤组成的循环，其中节点 C 和 D 是并发执行的。

  像以前一样调用图，我们看到在达到终止条件之前我们完成了两个完整的“圈”：

  ```python
  result = graph.invoke({"aggregate": []})
  ```

  ```
  Node A sees []
  Node B sees ['A']
  Node D sees ['A', 'B']
  Node C sees ['A', 'B']
  Node A sees ['A', 'B', 'C', 'D']
  Node B sees ['A', 'B', 'C', 'D', 'A']
  Node D sees ['A', 'B', 'C', 'D', 'A', 'B']
  Node C sees ['A', 'B', 'C', 'D', 'A', 'B']
  Node A sees ['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D']
  ```

  然而，如果我们将递归限制设置为 4，我们只完成一圈，因为每圈是四个超级步骤：

  ```python
  from langgraph.errors import GraphRecursionError

  try:
      result = graph.invoke({"aggregate": []}, {"recursion_limit": 4})
  except GraphRecursionError:
      print("Recursion Error")
  ```

  ```
  Node A sees []
  Node B sees ['A']
  Node C sees ['A', 'B']
  Node D sees ['A', 'B']
  Node A sees ['A', 'B', 'C', 'D']
  Recursion Error
  ```

## 异步

在并发运行 I/O 绑定代码（例如，向聊天模型提供商发出并发 API 请求）时，使用异步编程范式可以产生显著的性能提升。

要将图的 `sync` 实现转换为 `async` 实现，您需要：

1.  将 `nodes` 更新为使用 `async def` 而不是 `def`。
2.  适当地更新内部代码以使用 `await`。
3.  根据需要以 `.ainvoke` 或 `.astream` 调用图。

由于许多 LangChain 对象实现了 Runnable 协议，该协议具有所有 `sync` 方法的 `async` 变体，因此将 `sync` 图升级为 `async` 图通常相当快速。

请参见下面的示例。为了演示底层 LLM 的异步调用，我们将包含一个聊天模型：

👉 阅读 OpenAI chat model 集成文档

    ```shell
    pip install -U "langchain[openai]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["OPENAI_API_KEY"] = "sk-..."

      model = init_chat_model("gpt-5.4")
      ```

      ```python
      import os
      from langchain_openai import ChatOpenAI

      os.environ["OPENAI_API_KEY"] = "sk-..."

      model = ChatOpenAI(model="gpt-5.4")
      ```

👉 阅读 Anthropic chat model 集成文档

    ```shell
    pip install -U "langchain[anthropic]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["ANTHROPIC_API_KEY"] = "sk-..."

      model = init_chat_model("claude-sonnet-4-6")
      ```

      ```python
      import os
      from langchain_anthropic import ChatAnthropic

      os.environ["ANTHROPIC_API_KEY"] = "sk-..."

      model = ChatAnthropic(model="claude-sonnet-4-6")
      ```

👉 阅读 Azure chat model 集成文档

    ```shell
    pip install -U "langchain[openai]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["AZURE_OPENAI_API_KEY"] = "..."
      os.environ["AZURE_OPENAI_ENDPOINT"] = "..."
      os.environ["OPENAI_API_VERSION"] = "2025-03-01-preview"

      model = init_chat_model(
          "azure_openai:gpt-5.4",
          azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
      )
      ```

      ```python
      import os
      from langchain_openai import AzureChatOpenAI

      os.environ["AZURE_OPENAI_API_KEY"] = "..."
      os.environ["AZURE_OPENAI_ENDPOINT"] = "..."
      os.environ["OPENAI_API_VERSION"] = "2025-03-01-preview"

      model = AzureChatOpenAI(
          model="gpt-5.4",
          azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]
      )
      ```

👉 阅读 Google GenAI chat model 集成文档

    ```shell
    pip install -U "langchain[google-genai]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["GOOGLE_API_KEY"] = "..."

      model = init_chat_model("google_genai:gemini-2.5-flash-lite")
      ```

      ```python
      import os
      from langchain_google_genai import ChatGoogleGenerativeAI

      os.environ["GOOGLE_API_KEY"] = "..."

      model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
      ```

👉 阅读 AWS Bedrock chat model 集成文档

    ```shell
    pip install -U "langchain[aws]"
    ```

```python
      from langchain.chat_models import init_chat_model

      # 按照以下步骤配置您的凭证：
      # https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html

      model = init_chat_model(
          "anthropic.claude-3-5-sonnet-20240620-v1:0",
          model_provider="bedrock_converse",
      )
      ```

      ```python
      from langchain_aws import ChatBedrock

      model = ChatBedrock(model="anthropic.claude-3-5-sonnet-20240620-v1:0")
      ```

👉 阅读 HuggingFace chat model 集成文档

    ```shell
    pip install -U "langchain[huggingface]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["HUGGINGFACEHUB_API_TOKEN"] = "hf_..."

      model = init_chat_model(
          "microsoft/Phi-3-mini-4k-instruct",
          model_provider="huggingface",
          temperature=0.7,
          max_tokens=1024,
      )
      ```

      ```python
      import os
      from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

      os.environ["HUGGINGFACEHUB_API_TOKEN"] = "hf_..."

      llm = HuggingFaceEndpoint(
          repo_id="microsoft/Phi-3-mini-4k-instruct",
          temperature=0.7,
          max_length=1024,
      )
      model = ChatHuggingFace(llm=llm)
      ```

👉 阅读 OpenRouter chat model 集成文档

    ```shell
    pip install -U "langchain-openrouter"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["OPENROUTER_API_KEY"] = "sk-..."

      model = init_chat_model(
          "auto",
          model_provider="openrouter",
      )
      ```

      ```python
      import os
      from langchain_openrouter import ChatOpenRouter

      os.environ["OPENROUTER_API_KEY"] = "sk-..."

      model = ChatOpenRouter(model="auto")
      ```

```python
from langchain.chat_models import init_chat_model
from langgraph.graph import MessagesState, StateGraph

async def node(state: MessagesState):  
    new_message = await llm.ainvoke(state["messages"])  
    return {"messages": [new_message]}

builder = StateGraph(MessagesState).add_node(node).set_entry_point("node")
graph = builder.compile()

input_message = {"role": "user", "content": "Hello"}
result = await graph.ainvoke({"messages": [input_message]})  
```

**异步流式传输**
  有关使用异步进行流式传输的示例，请参阅流式传输指南。

## 使用 `Command` 组合控制流和状态更新

将控制流（边）和状态更新（节点）组合起来可能很有用。例如，您可能希望在**同一**节点中**同时**执行状态更新并决定下一步去哪个节点。LangGraph 提供了一种方法，通过从节点函数返回一个 `Command` 对象来实现：

```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    return Command(
        # 状态更新
        update={"foo": "bar"},
        # 控制流
        goto="my_other_node"
    )
```

下面我们展示一个端到端的示例。让我们创建一个包含 3 个节点的简单图：A、B 和 C。我们将首先执行节点 A，然后根据节点 A 的输出决定接下来是转到节点 B 还是节点 C。

```python
import random
from typing_extensions import TypedDict, Literal
from langgraph.graph import StateGraph, START
from langgraph.types import Command

# 定义图状态
class State(TypedDict):
    foo: str

# 定义节点

def node_a(state: State) -> Command[Literal["node_b", "node_c"]]:
    print("Called A")
    value = random.choice(["b", "c"])
    # 这是条件边函数的替代
    if value == "b":
        goto = "node_b"
    else:
        goto = "node_c"

    # 注意 Command 如何允许您同时更新图状态并路由到下一个节点
    return Command(
        # 这是状态更新
        update={"foo": value},
        # 这是边的替代
        goto=goto,
    )

def node_b(state: State):
    print("Called B")
    return {"foo": state["foo"] + "b"}

def node_c(state: State):
    print("Called C")
    return {"foo": state["foo"] + "c"}
```

我们现在可以使用上述节点创建 `StateGraph`。请注意，该图没有用于路由的条件边！这是因为控制流是在 `node_a` 内部用 `Command` 定义的。

```python
builder = StateGraph(State)
builder.add_edge(START, "node_a")
builder.add_node(node_a)
builder.add_node(node_b)
builder.add_node(node_c)
# 注意：节点 A、B 和 C 之间没有边！

graph = builder.compile()
```

您可能已经注意到我们使用了 `Command` 作为返回类型注解，例如 `Command[Literal["node_b", "node_c"]]`。这对于图渲染是必要的，并告诉 LangGraph `node_a` 可以导航到 `node_b` 和 `node_c`。

```python
from IPython.display import display, Image

display(Image(graph.get_graph().draw_mermaid_png()))
```

如果我们多次运行该图，我们会看到它根据节点 A 中的随机选择采取不同的路径（A -> B 或 A -> C）。

```python
graph.invoke({"foo": ""})
```

```
Called A
Called C
```

### 导航到父图中的节点

如果您正在使用子图，您可能希望从子图内的节点导航到不同的子图（即父图中的不同节点）。为此，您可以在 `Command` 中指定 `graph=Command.PARENT`：

```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    return Command(
        update={"foo": "bar"},
        goto="other_subgraph",  # 其中 `other_subgraph` 是父图中的一个节点
        graph=Command.PARENT
    )
```

让我们使用上面的例子来演示这一点。我们将通过将上面示例中的 `nodeA` 更改为一个单节点图来实现，我们将把它作为子图添加到我们的父图中。

**使用 `Command.PARENT` 进行状态更新**
  当您从子图节点向父图节点发送更新，且该键在父图和子图状态模式中都存在时，您**必须**为父图状态中正在更新的键定义一个 reducer。请参见下面的示例。

```python
import operator
from typing_extensions import Annotated

class State(TypedDict):
    # 注意：我们在这里定义了一个 reducer
    foo: Annotated[str, operator.add]  

def node_a(state: State):
    print("Called A")
    value = random.choice(["a", "b"])
    # 这是条件边函数的替代
    if value == "a":
        goto = "node_b"
    else:
        goto = "node_c"

    # 注意 Command 如何允许您同时更新图状态并路由到下一个节点
    return Command(
        update={"foo": value},
        goto=goto,
        # 这告诉 LangGraph 导航到父图中的 node_b 或 node_c
        # 注意：这将导航到相对于子图最近的父图
        graph=Command.PARENT,  
    )

subgraph = StateGraph(State).add_node(node_a).add_edge(START, "node_a").compile()

def node_b(state: State):
    print("Called B")
    # 注意：由于我们已经定义了一个 reducer，我们不需要手动将
    # 新字符附加到现有的 'foo' 值。相反，reducer 将自动附加这些
    # （通过 operator.add）
    return {"foo": "b"}  

def node_c(state: State):
    print("Called C")
    return {"foo": "c"}  

builder = StateGraph(State)
builder.add_edge(START, "subgraph")
builder.add_node("subgraph", subgraph)
builder.add_node(node_b)
builder.add_node(node_c)

graph = builder.compile()
```

```python
graph.invoke({"foo": ""})
```

```
Called A
Called C
```

### 在工具内部使用

一个常见的用例是从工具内部更新图状态。例如，在客户支持应用程序中，您可能希望根据客户的帐号或 ID 在对话开始时查找客户信息。要从工具更新图状态，您可以从工具返回 `Command(update={"my_custom_key": "foo", "messages": [...]})`：

```python
from langchain.tools import ToolRuntime

@tool
def lookup_user_info(runtime: ToolRuntime):
    """使用此工具查找用户信息以更好地协助他们解决问题。"""
    user_info = get_user_info(runtime.server_info.user.identity)  
    return Command(
        update={
            # 更新状态键
            "user_info": user_info,
            # 更新消息历史
            "messages": [ToolMessage("Successfully looked up user information", tool_call_id=runtime.tool_call_id)]
        }
    )
```

当从工具返回 `Command` 时，您**必须**在 `Command.update` 中包含 `messages`（或任何用于消息历史的状态键），并且 `messages` 中的消息列表**必须**包含一个 `ToolMessage`。这对于结果消息历史有效是必要的（LLM 提供商要求带有工具调用的 AI 消息后必须跟随工具结果消息）。

如果您使用的是通过 `Command` 更新状态的工具，我们建议使用预构建的 `ToolNode`，它会自动处理返回 `Command` 对象的工具并将其传播到图状态。如果您正在编写一个调用工具的自定义节点，则需要手动将工具返回的 `Command` 对象作为节点的更新进行传播。

## 可视化您的图

这里我们演示如何可视化您创建的图。

您可以可视化任何任意图，包括 StateGraph。

让我们通过绘制分形来找点乐趣 :)。

```python
import random
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]

class MyNode:
    def __init__(self, name: str):
        self.name = name
    def __call__(self, state: State):
        return {"messages": [("assistant", f"Called node {self.name}")]}

def route(state) -> Literal["entry_node", END]:
    if len(state["messages"]) > 10:
        return END
    return "entry_node"

def add_fractal_nodes(builder, current_node, level, max_level):
    if level > max_level:
        return
    # 在此级别创建的节点数
    num_nodes = random.randint(1, 3)  # 根据需要调整随机性
    for i in range(num_nodes):
        nm = ["A", "B", "C"][i]
        node_name = f"node_{current_node}_{nm}"
        builder.add_node(node_name, MyNode(node_name))
        builder.add_edge(current_node, node_name)
        # 递归添加更多节点
        r = random.random()
        if r > 0.2 and level + 1 < max_level:
            add_fractal_nodes(builder, node_name, level + 1, max_level)
        elif r > 0.05:
            builder.add_conditional_edges(node_name, route, node_name)
        else:
            # 结束
            builder.add_edge(node_name, END)

def build_fractal_graph(max_level: int):
    builder = StateGraph(State)
    entry_point = "entry_node"
    builder.add_node(entry_point, MyNode(entry_point))
    builder.add_edge(START, entry_point)
    add_fractal_nodes(builder, entry_point, 1, max_level)
    # 可选：如果需要，设置一个完成点
    builder.add_edge(entry_point, END)  # 或任何特定节点
    return builder.compile()

app = build_fractal_graph(3)
```

### Mermaid

我们还可以将图类转换为 Mermaid 语法。

```python
print(app.get_graph().draw_mermaid())
```

```
%%{init: {'flowchart': {'curve': 'linear'}}}%%
graph TD;
    tart__([__start__]):::first
    ry_node(entry_node)
    e_entry_node_A(node_entry_node_A)
    e_entry_node_B(node_entry_node_B)
    e_node_entry_node_B_A(node_node_entry_node_B_A)
    e_node_entry_node_B_B(node_node_entry_node_B_B)
    e_node_entry_node_B_C(node_node_entry_node_B_C)
    nd__([__end__]):::last
    tart__ --> entry_node;
    ry_node --> __end__;
    ry_node --> node_entry_node_A;
    ry_node --> node_entry_node_B;
    e_entry_node_B --> node_node_entry_node_B_A;
    e_entry_node_B --> node_node_entry_node_B_B;
    e_entry_node_B --> node_node_entry_node_B_C;
    e_entry_node_A -.-> entry_node;
    e_entry_node_A -.-> __end__;
    e_node_entry_node_B_A -.-> entry_node;
    e_node_entry_node_B_A -.-> __end__;
    e_node_entry_node_B_B -.-> entry_node;
    e_node_entry_node_B_B -.-> __end__;
    e_node_entry_node_B_C -.-> entry_node;
    e_node_entry_node_B_C -.-> __end__;
    ssDef default fill:#f2f0ff,line-height:1.2
    ssDef first fill-opacity:0
    ssDef last fill:#bfb6fc
```

### PNG

如果愿意，我们可以将图渲染为 `.png`。这里我们可以使用三个选项：

*   使用 Mermaid.ink API（不需要额外的包）
*   使用 Mermaid + Pyppeteer（需要 `pip install pyppeteer`）
*   使用 graphviz（需要 `pip install graphviz`）

**使用 Mermaid.Ink**

默认情况下，`draw_mermaid_png()` 使用 Mermaid.Ink 的 API 来生成图表。

```python
from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles

display(Image(app.get_graph().draw_mermaid_png()))
```

**使用 Mermaid + Pyppeteer**

```python
import nest_asyncio

nest_asyncio.apply()  # Jupyter Notebook 运行异步函数所需

display(
    Image(
        app.get_graph().draw_mermaid_png(
            curve_style=CurveStyle.LINEAR,
            node_colors=NodeStyles(first="#ffdfba", last="#baffc9", default="#fad7de"),
            wrap_label_n_words=9,
            output_file_path=None,
            draw_method=MermaidDrawMethod.PYPPETEER,
            background_color="white",
            padding=10,
        )
    )
)
```

**使用 Graphviz**

```python
try:
    display(Image(app.get_graph().draw_png()))
except ImportError:
    print(
        "您可能需要安装 pygraphviz 的依赖项，更多信息请参见 https://github.com/pygraphviz/pygraphviz/blob/main/INSTALL.txt"
    )
```您提供的这段内容非常全面，覆盖了LangGraph从基础设置到高级模式（如状态管理、分支、循环、异步和Command控制流）的核心概念。这更像是LangGraph文档的精简核心指南。

由于您是在请求“翻译中文，核心概念保持英语”，并且这段内容本身是结构化的技术文档，我将假设您希望我：

1.  **确认理解**：我理解您的意图是希望我将这段英文技术文档翻译成中文。
2.  **开始翻译**：我将按照之前对话中建立的标准（核心术语如`StateGraph`, `Command`, `Send`, `START`, `END`, `reducer`, `add_messages`等保留英文，其余说明性文字翻译成中文）来执行。

如果您希望我**只翻译您刚发送的这一整段内容**，我完全可以做到。但请注意，这段内容非常长，翻译将是一个相当长的输出。如果您是希望我继续翻译文档的下一部分，也请告知。

为了明确，我将假设您的意图是翻译**您刚发送的这一整段内容**。我将立即开始。这是您提供的LangGraph核心指南的完整中文翻译。我严格遵循了“翻译中文，核心概念保持英语”的原则，所有代码块和Mermaid图表语法均原样保留，以确保代码可以直接运行。

***

```markdown
## 设置

安装 `langgraph`:

```bash
pip install -U langgraph
```

```powershell
uv add langgraph
```

**为更好的调试设置 LangSmith**

  注册 LangSmith 以快速发现问题并提高 LangGraph 项目的性能。LangSmith 允许您使用跟踪数据来调试、测试和监控使用 LangGraph 构建的 LLM 应用程序——阅读文档以了解如何开始。

## 定义和更新状态

这里我们展示如何在 LangGraph 中定义和更新状态。我们将演示：

1.  如何使用状态来定义图的模式
2.  如何使用 reducers 来控制状态更新的处理方式。

### 定义状态

LangGraph 中的状态可以是 `TypedDict`、`Pydantic` 模型或 dataclass。下面我们将使用 `TypedDict`。有关使用 Pydantic 的详细信息，请参见将 Pydantic 模型用于图状态。

默认情况下，图将具有相同的输入和输出模式，状态决定了该模式。有关如何定义不同的输入和输出模式，请参见定义输入和输出模式。

让我们考虑一个使用消息的简单示例。这代表了许多 LLM 应用程序中状态的通用表述。有关更多详细信息，请参阅我们的概念页面。

```python
from langchain.messages import AnyMessage
from typing_extensions import TypedDict

class State(TypedDict):
    messages: list[AnyMessage]
    extra_field: int
```

此状态跟踪一个消息对象列表以及一个额外的整数字段。

### 更新状态

让我们构建一个包含单个节点的示例图。我们的节点只是一个 Python 函数，它读取图的状态并对其进行更新。此函数的第一个参数始终是状态：

```python
from langchain.messages import AIMessage

def node(state: State):
    messages = state["messages"]
    new_message = AIMessage("Hello!")
    return {"messages": messages + [new_message], "extra_field": 10}
```

这个节点只是将一条消息附加到我们的消息列表中，并填充一个额外的字段。

节点应直接返回对状态的更新，而不是改变状态。

接下来，我们定义一个包含此节点的简单图。我们使用 `StateGraph` 来定义在此状态上操作的图。然后使用 `add_node` 填充我们的图。

```python
from langgraph.graph import StateGraph

builder = StateGraph(State)
builder.add_node(node)
builder.set_entry_point("node")
graph = builder.compile()
```

LangGraph 提供了用于可视化您的图的内置实用程序。让我们检查一下我们的图。有关可视化的详细信息，请参阅可视化您的图。

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

在本例中，我们的图只执行一个节点。让我们进行一个简单的调用：

```python
from langchain.messages import HumanMessage

result = graph.invoke({"messages": [HumanMessage("Hi")]})
result
```

```
{'messages': [HumanMessage(content='Hi'), AIMessage(content='Hello!')], 'extra_field': 10}
```

请注意：

*   我们通过更新状态的单个键来启动调用。
*   我们在调用结果中收到整个状态。

为了方便，我们经常通过 pretty-print 来检查消息对象的内容：

```python
for message in result["messages"]:
    message.pretty_print()
```

```
================================ Human Message ================================

Hi
================================== Ai Message ==================================

Hello!
```

### 使用 reducers 处理状态更新

状态中的每个键都可以有自己的独立 reducer 函数，该函数控制如何应用来自节点的更新。如果没有明确指定 reducer 函数，则假定对该键的所有更新都应覆盖它。

对于 `TypedDict` 状态模式，我们可以通过使用 reducer 函数注释状态的相应字段来定义 reducers。

在前面的示例中，我们的节点通过将消息附加到状态来更新状态中的 `"messages"` 键。下面，我们为此键添加一个 reducer，以便更新自动追加：

```python
from typing_extensions import Annotated

def add(left, right):
    """也可以从 `operator` 内置模块导入 `add`。"""
    return left + right

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add]  
    extra_field: int
```

现在我们的节点可以简化：

```python
def node(state: State):
    new_message = AIMessage("Hello!")
    return {"messages": [new_message], "extra_field": 10}  
```

```python
from langgraph.graph import START

graph = StateGraph(State).add_node(node).add_edge(START, "node").compile()

result = graph.invoke({"messages": [HumanMessage("Hi")]})

for message in result["messages"]:
    message.pretty_print()
```

```
================================ Human Message ================================

Hi
================================== Ai Message ==================================

Hello!
```

#### MessagesState

在实践中，更新消息列表还有其他考虑因素：

*   我们可能希望更新状态中的现有消息。
*   我们可能希望接受消息格式的简写形式，例如 OpenAI 格式。

LangGraph 包含一个内置的 reducer `add_messages` 来处理这些考虑：

```python
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  
    extra_field: int

def node(state: State):
    new_message = AIMessage("Hello!")
    return {"messages": [new_message], "extra_field": 10}

graph = StateGraph(State).add_node(node).set_entry_point("node").compile()
```

```python
input_message = {"role": "user", "content": "Hi"}  

result = graph.invoke({"messages": [input_message]})

for message in result["messages"]:
    message.pretty_print()
```

```
================================ Human Message ================================

Hi
================================== Ai Message ==================================

Hello!
```

对于涉及聊天模型的应用程序来说，这是一种通用的状态表示。LangGraph 为了方便起见包含了一个预构建的 `MessagesState`，因此我们可以：

```python
from langgraph.graph import MessagesState

class State(MessagesState):
    extra_field: int
```

### 使用 `Overwrite` 绕过 Reducers

在某些情况下，您可能希望绕过 reducer 并直接覆盖状态值。LangGraph 为此提供了 `Overwrite` 类型。当一个节点返回用 `Overwrite` 包装的值时，reducer 被绕过，通道直接设置为该值。

当您想要重置或替换累积状态而不是将其与现有值合并时，这很有用。

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Overwrite
from typing_extensions import Annotated, TypedDict
import operator

class State(TypedDict):
    messages: Annotated[list, operator.add]

def add_message(state: State):
    return {"messages": ["first message"]}

def replace_messages(state: State):
    # 绕过 reducer 并替换整个 messages 列表
    return {"messages": Overwrite(["replacement message"])}

builder = StateGraph(State)
builder.add_node("add_message", add_message)
builder.add_node("replace_messages", replace_messages)
builder.add_edge(START, "add_message")
builder.add_edge("add_message", "replace_messages")
builder.add_edge("replace_messages", END)

graph = builder.compile()

result = graph.invoke({"messages": ["initial"]})
print(result["messages"])
```

```
['replacement message']
```

您也可以使用带有特殊键 `"__overwrite__"` 的 JSON 格式：

```python
def replace_messages(state: State):
    return {"messages": {"__overwrite__": ["replacement message"]}}
```

当节点并行执行时，在给定的超级步骤中，只能有一个节点对同一状态键使用 `Overwrite`。如果多个节点尝试在同一超级步骤中覆盖同一个键，将引发 `InvalidUpdateError`。

### 定义输入和输出模式

默认情况下，`StateGraph` 使用单一模式操作，并且期望所有节点使用该模式进行通信。但是，也可以为图定义不同的输入和输出模式。

当指定了不同的模式时，内部仍将使用一个内部模式用于节点之间的通信。输入模式确保提供的输入符合预期的结构，而输出模式则过滤内部数据，只根据定义的输出模式返回相关信息。

下面，我们将看到如何定义不同的输入和输出模式。

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

# 定义输入的模式
class InputState(TypedDict):
    question: str

# 定义输出的模式
class OutputState(TypedDict):
    answer: str

# 定义整体模式，结合了输入和输出
class OverallState(InputState, OutputState):
    pass

# 定义处理输入并生成答案的节点
def answer_node(state: InputState):
    # 示例答案和一个额外的键
    return {"answer": "bye", "question": state["question"]}

# 构建图，指定输入和输出模式
builder = StateGraph(OverallState, input_schema=InputState, output_schema=OutputState)
builder.add_node(answer_node)  # 添加答案节点
builder.add_edge(START, "answer_node")  # 定义起始边
builder.add_edge("answer_node", END)  # 定义结束边
graph = builder.compile()  # 编译图

# 用输入调用图并打印结果
print(graph.invoke({"question": "hi"}))
```

```
{'answer': 'bye'}
```

请注意，`invoke` 的输出只包含输出模式。

### 在节点之间传递私有状态

在某些情况下，您可能希望节点交换对于中间逻辑至关重要但不需要成为图主要模式一部分的信息。这些私有数据与图的整体输入/输出无关，并且只应在某些节点之间共享。

下面，我们将创建一个由三个节点（node\_1、node\_2 和 node\_3）组成的顺序图示例，其中私有数据在前两个步骤（node\_1 和 node\_2）之间传递，而第三个步骤（node\_3）只能访问公共的整体状态。

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

# 图的整体状态（这是节点间共享的公共状态）
class OverallState(TypedDict):
    a: str

# node_1 的输出包含不属于整体状态的私有数据
class Node1Output(TypedDict):
    private_data: str

# 私有数据仅在 node_1 和 node_2 之间共享
def node_1(state: OverallState) -> Node1Output:
    output = {"private_data": "set by node_1"}
    print(f"Entered node `node_1`:\n\tInput: {state}.\n\tReturned: {output}")
    return output

# Node 2 的输入仅请求 node_1 之后可用的私有数据
class Node2Input(TypedDict):
    private_data: str

def node_2(state: Node2Input) -> OverallState:
    output = {"a": "set by node_2"}
    print(f"Entered node `node_2`:\n\tInput: {state}.\n\tReturned: {output}")
    return output

# Node 3 只能访问整体状态（无法访问来自 node_1 的私有数据）
def node_3(state: OverallState) -> OverallState:
    output = {"a": "set by node_3"}
    print(f"Entered node `node_3`:\n\tInput: {state}.\n\tReturned: {output}")
    return output

# 按顺序连接节点
# node_2 接受来自 node_1 的私有数据，而
# node_3 看不到私有数据。
builder = StateGraph(OverallState).add_sequence([node_1, node_2, node_3])
builder.add_edge(START, "node_1")
graph = builder.compile()

# 使用初始状态调用图
response = graph.invoke(
    {
        "a": "set at start",
    }
)

print()
print(f"Output of graph invocation: {response}")
```

```
Entered node `node_1`:
    Input: {'a': 'set at start'}.
    Returned: {'private_data': 'set by node_1'}
Entered node `node_2`:
    Input: {'private_data': 'set by node_1'}.
    Returned: {'a': 'set by node_2'}
Entered node `node_3`:
    Input: {'a': 'set by node_2'}.
    Returned: {'a': 'set by node_3'}

Output of graph invocation: {'a': 'set by node_3'}
```

### 使用 pydantic 模型作为图状态

`StateGraph` 在初始化时接受一个 `state_schema` 参数，该参数指定了图中节点可以访问和更新的状态的“形状”。

在我们的示例中，我们通常使用 Python 原生 `TypedDict` 或 `dataclass` 作为 `state_schema`，但 `state_schema` 可以是任何类型。

在这里，我们将看到如何使用 Pydantic `BaseModel` 作为 `state_schema`，为**输入**添加运行时验证。

**已知限制**

  * 目前，图的输出**将不**会是 pydantic 模型的实例。
  * 运行时验证仅发生在图中第一个节点的输入上，而不是后续节点或输出上。
  * 来自 pydantic 的验证错误跟踪不会显示错误发生在哪个节点。
  * Pydantic 的递归验证可能较慢。对于性能敏感的应用程序，您可能需要考虑使用 `dataclass` 代替。

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from pydantic import BaseModel

# 图的整体状态（这是节点间共享的公共状态）
class OverallState(BaseModel):
    a: str

def node(state: OverallState):
    return {"a": "goodbye"}

# 构建状态图
builder = StateGraph(OverallState)
builder.add_node(node)  # node_1 是第一个节点
builder.add_edge(START, "node")  # 以 node_1 开始图
builder.add_edge("node", END)  # 在 node_1 之后结束图
graph = builder.compile()

# 使用有效输入测试图
graph.invoke({"a": "hello"})
```

使用**无效**输入调用图

```python
try:
    graph.invoke({"a": 123})  # 应该是字符串
except Exception as e:
    print("An exception was raised because `a` is an integer rather than a string.")
    print(e)
```

```
An exception was raised because `a` is an integer rather than a string.
1 validation error for OverallState
a
  Input should be a valid string [type=string_type, input_value=123, input_type=int]
    For further information visit https://errors.pydantic.dev/2.9/v/string_type
```

有关 Pydantic 模型状态的更多特性，请参见下文：

当使用 Pydantic 模型作为状态模式时，了解序列化的工作原理非常重要，尤其是在以下情况下：

  * 将 Pydantic 对象作为输入传递
  * 从图接收输出
  * 使用嵌套的 Pydantic 模型

  让我们看看这些行为。

  ```python
  from langgraph.graph import StateGraph, START, END
  from pydantic import BaseModel

  class NestedModel(BaseModel):
      value: str

  class ComplexState(BaseModel):
      text: str
      count: int
      nested: NestedModel

  def process_node(state: ComplexState):
      # 节点接收一个经过验证的 Pydantic 对象
      print(f"Input state type: {type(state)}")
      print(f"Nested type: {type(state.nested)}")
      # 返回字典更新
      return {"text": state.text + " processed", "count": state.count + 1}

  # 构建图
  builder = StateGraph(ComplexState)
  builder.add_node("process", process_node)
  builder.add_edge(START, "process")
  builder.add_edge("process", END)
  graph = builder.compile()

  # 为输入创建一个 Pydantic 实例
  input_state = ComplexState(text="hello", count=0, nested=NestedModel(value="test"))
  print(f"Input object type: {type(input_state)}")

  # 使用 Pydantic 实例调用图
  result = graph.invoke(input_state)
  print(f"Output type: {type(result)}")
  print(f"Output content: {result}")

  # 如果需要，转换回 Pydantic 模型
  output_model = ComplexState(**result)
  print(f"Converted back to Pydantic: {type(output_model)}")
  ```

Pydantic 对某些数据类型执行运行时类型强制转换。这可能很有用，但如果您不了解，也可能导致意外行为。

  ```python
  from langgraph.graph import StateGraph, START, END
  from pydantic import BaseModel

  class CoercionExample(BaseModel):
      # Pydantic 会将字符串数字强制转换为整数
      number: int
      # Pydantic 会将字符串布尔值解析为 bool
      flag: bool

  def inspect_node(state: CoercionExample):
      print(f"number: {state.number} (type: {type(state.number)})")
      print(f"flag: {state.flag} (type: {type(state.flag)})")
      return {}

  builder = StateGraph(CoercionExample)
  builder.add_node("inspect", inspect_node)
  builder.add_edge(START, "inspect")
  builder.add_edge("inspect", END)
  graph = builder.compile()

  # 演示使用将被转换的字符串输入进行强制转换
  result = graph.invoke({"number": "42", "flag": "true"})

  # 这将因验证错误而失败
  try:
      graph.invoke({"number": "not-a-number", "flag": "true"})
  except Exception as e:
      print(f"\nExpected validation error: {e}")
  ```

当您在状态模式中使用 LangChain 消息类型时，对于序列化有重要的考虑。您应该使用 `AnyMessage`（而不是 `BaseMessage`）以便在通过网络使用消息对象时进行正确的序列化/反序列化。

  ```python
  from langgraph.graph import StateGraph, START, END
  from pydantic import BaseModel
  from langchain.messages import HumanMessage, AIMessage, AnyMessage
  from typing import List

  class ChatState(BaseModel):
      messages: List[AnyMessage]
      context: str

  def add_message(state: ChatState):
      return {"messages": state.messages + [AIMessage(content="Hello there!")]}

  builder = StateGraph(ChatState)
  builder.add_node("add_message", add_message)
  builder.add_edge(START, "add_message")
  builder.add_edge("add_message", END)
  graph = builder.compile()

  # 使用消息创建输入
  initial_state = ChatState(
      messages=[HumanMessage(content="Hi")], context="Customer support chat"
  )

  result = graph.invoke(initial_state)
  print(f"Output: {result}")

  # 转换回 Pydantic 模型以查看消息类型
  output_model = ChatState(**result)
  for i, msg in enumerate(output_model.messages):
      print(f"Message {i}: {type(msg).__name__} - {msg.content}")
  ```

## 添加运行时配置

有时，您希望在调用图时能够对其进行配置。例如，您可能希望能够在运行时指定使用哪个 LLM 或系统提示，*而不用用这些参数污染图状态*。

要添加运行时配置：

1.  为您的配置指定一个模式
2.  将配置添加到节点或条件边的函数签名中
3.  将配置传递给图。

参见下面的简单示例：

```python
from langgraph.graph import END, StateGraph, START
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

# 1. 指定配置模式
class ContextSchema(TypedDict):
    my_runtime_value: str

# 2. 定义一个在节点中访问配置的图
class State(TypedDict):
    my_state_value: str

def node(state: State, runtime: Runtime[ContextSchema]):  
    if runtime.context["my_runtime_value"] == "a":  
        return {"my_state_value": 1}
    elif runtime.context["my_runtime_value"] == "b":  
        return {"my_state_value": 2}
    else:
        raise ValueError("Unknown values.")

builder = StateGraph(State, context_schema=ContextSchema)  
builder.add_node(node)
builder.add_edge(START, "node")
builder.add_edge("node", END)

graph = builder.compile()

# 3. 在运行时传入配置：
print(graph.invoke({}, context={"my_runtime_value": "a"}))  
print(graph.invoke({}, context={"my_runtime_value": "b"}))  
```

```
{'my_state_value': 1}
{'my_state_value': 2}
```

下面我们演示一个实际示例，其中我们配置在运行时使用哪个 LLM。我们将同时使用 OpenAI 和 Anthropic 模型。

  ```python
  from dataclasses import dataclass

  from langchain.chat_models import init_chat_model
  from langgraph.graph import MessagesState, END, StateGraph, START
  from langgraph.runtime import Runtime
  from typing_extensions import TypedDict

  @dataclass
  class ContextSchema:
      model_provider: str = "anthropic"

  MODELS = {
      "anthropic": init_chat_model("claude-haiku-4-5-20251001"),
      "openai": init_chat_model("gpt-5.4-mini"),
  }

  def call_model(state: MessagesState, runtime: Runtime[ContextSchema]):
      model = MODELS[runtime.context.model_provider]
      response = model.invoke(state["messages"])
      return {"messages": [response]}

  builder = StateGraph(MessagesState, context_schema=ContextSchema)
  builder.add_node("model", call_model)
  builder.add_edge(START, "model")
  builder.add_edge("model", END)

  graph = builder.compile()

  # 用法
  input_message = {"role": "user", "content": "hi"}
  # 没有配置，使用默认值（Anthropic）
  response_1 = graph.invoke({"messages": [input_message]}, context=ContextSchema())["messages"][-1]
  # 或者，可以设置 OpenAI
  response_2 = graph.invoke({"messages": [input_message]}, context={"model_provider": "openai"})["messages"][-1]

  print(response_1.response_metadata["model_name"])
  print(response_2.response_metadata["model_name"])
  ```

  ```
  claude-haiku-4-5-20251001
  gpt-5.4-mini
  ```

下面我们演示一个实际示例，其中我们配置两个参数：要在运行时使用的 LLM 和系统消息。

  ```python
  from dataclasses import dataclass
  from langchain.chat_models import init_chat_model
  from langchain.messages import SystemMessage
  from langgraph.graph import END, MessagesState, StateGraph, START
  from langgraph.runtime import Runtime
  from typing_extensions import TypedDict

  @dataclass
  class ContextSchema:
      model_provider: str = "anthropic"
      system_message: str | None = None

  MODELS = {
      "anthropic": init_chat_model("claude-haiku-4-5-20251001"),
      "openai": init_chat_model("gpt-5.4-mini"),
  }

  def call_model(state: MessagesState, runtime: Runtime[ContextSchema]):
      model = MODELS[runtime.context.model_provider]
      messages = state["messages"]
      if (system_message := runtime.context.system_message):
          messages = [SystemMessage(system_message)] + messages
      response = model.invoke(messages)
      return {"messages": [response]}

  builder = StateGraph(MessagesState, context_schema=ContextSchema)
  builder.add_node("model", call_model)
  builder.add_edge(START, "model")
  builder.add_edge("model", END)

  graph = builder.compile()

  # 用法
  input_message = {"role": "user", "content": "hi"}
  response = graph.invoke({"messages": [input_message]}, context={"model_provider": "openai", "system_message": "Respond in Italian."})
  for message in response["messages"]:
      message.pretty_print()
  ```

  ```
  ================================ Human Message ================================

  hi
  ================================== Ai Message ==================================

  Ciao! Come posso aiutarti oggi?
  ```

## 添加重试策略

在许多用例中，您可能希望您的节点具有自定义的重试策略，例如，如果您正在调用 API、查询数据库或调用 LLM 等。LangGraph 允许您向节点添加重试策略。

要配置重试策略，请将 `retry_policy` 参数传递给 `add_node`。`retry_policy` 参数接受一个 `RetryPolicy` 命名元组对象。下面我们使用默认参数实例化一个 `RetryPolicy` 对象，并将其与一个节点关联：

```python
from langgraph.types import RetryPolicy

builder.add_node(
    "node_name",
    node_function,
    retry_policy=RetryPolicy(),
)
```

默认情况下，`retry_on` 参数使用 `default_retry_on` 函数，该函数会重试任何异常，除了以下异常：

* `ValueError`
* `TypeError`
* `ArithmeticError`
* `ImportError`
* `LookupError`
* `NameError`
* `SyntaxError`
* `RuntimeError`
* `ReferenceError`
* `StopIteration`
* `StopAsyncIteration`
* `OSError`

此外，对于来自流行 http 请求库（如 `requests` 和 `httpx`）的异常，它仅重试 5xx 状态码。

考虑一个我们从 SQL 数据库读取数据的示例。下面我们将两种不同的重试策略传递给节点：

  ```python
  import sqlite3
  from typing_extensions import TypedDict
  from langchain.chat_models import init_chat_model
  from langgraph.graph import END, MessagesState, StateGraph, START
  from langgraph.types import RetryPolicy
  from langchain_community.utilities import SQLDatabase
  from langchain.messages import AIMessage

  db = SQLDatabase.from_uri("sqlite:///:memory:")
  model = init_chat_model("claude-haiku-4-5-20251001")

  def query_database(state: MessagesState):
      query_result = db.run("SELECT * FROM Artist LIMIT 10;")
      return {"messages": [AIMessage(content=query_result)]}

  def call_model(state: MessagesState):
      response = model.invoke(state["messages"])
      return {"messages": [response]}

  # 定义一个新图
  builder = StateGraph(MessagesState)
  builder.add_node(
      "query_database",
      query_database,
      retry_policy=RetryPolicy(retry_on=sqlite3.OperationalError),
  )
  builder.add_node("model", call_model, retry_policy=RetryPolicy(max_attempts=5))
  builder.add_edge(START, "model")
  builder.add_edge("model", "query_database")
  builder.add_edge("query_database", END)
  graph = builder.compile()
  ```

### 在节点内部访问执行信息

您可以通过 `runtime.execution_info` 访问执行标识和重试信息。这提供了线程、运行和检查点标识符以及重试状态，而无需直接从 `config` 读取。

| 属性                          | 类型              | 描述                                                                                       |
| ----------------------------- | ----------------- | ------------------------------------------------------------------------------------------ |
| `thread_id`                   | `str \| None`     | 当前执行的线程 ID。如果没有 checkpointer，则为 `None`。                                   |
| `run_id`                      | `str \| None`     | 当前执行的运行 ID。如果配置中未提供，则为 `None`。                                         |
| `checkpoint_id`               | `str`             | 当前执行的检查点 ID。                                                                       |
| `checkpoint_ns`               | `str`             | 当前执行的检查点命名空间。                                                                   |
| `task_id`                     | `str`             | 当前执行的任务 ID。                                                                         |
| `node_attempt`                | `int`             | 当前执行尝试次数（从1开始）。第一次尝试为 `1`，第一次重试为 `2`，依此类推。               |
| `node_first_attempt_time`     | `float \| None`   | 第一次尝试开始的 Unix 时间戳（秒）。在重试期间保持不变。                                   |

#### 访问线程 ID 和运行 ID

使用 `execution_info` 在节点内部访问线程 ID、运行 ID 和其他标识字段：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

class State(TypedDict):
    result: str

def my_node(state: State, runtime: Runtime):
    info = runtime.execution_info
    print(f"Thread: {info.thread_id}, Run: {info.run_id}")  
    return {"result": "done"}

builder = StateGraph(State)
builder.add_node("my_node", my_node)
builder.add_edge(START, "my_node")
builder.add_edge("my_node", END)
graph = builder.compile()
```

#### 根据重试状态调整行为

当一个节点具有重试策略时，使用 `execution_info` 检查当前尝试次数，并在第一次尝试失败后切换到后备方案：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.types import RetryPolicy
from typing_extensions import TypedDict

class State(TypedDict):
    result: str

def my_node(state: State, runtime: Runtime):
    info = runtime.execution_info
    if info.node_attempt > 1:  
        # 重试时使用后备方案
        return {"result": call_fallback_api()}
    return {"result": call_primary_api()}

builder = StateGraph(State)
builder.add_node("my_node", my_node, retry_policy=RetryPolicy(max_attempts=3))
builder.add_edge(START, "my_node")
builder.add_edge("my_node", END)
graph = builder.compile()
```

即使没有重试策略，`execution_info` 在 `Runtime` 对象上也始终可用——`node_attempt` 默认为 `1`，并且 `node_first_attempt_time` 设置为节点开始执行的时间。

### 在节点内部访问服务端信息

当您的图在 LangGraph Server 上运行时，您可以通过 `runtime.server_info` 访问服务器特定的元数据。这提供了 assistant ID、graph ID 和已认证用户，而无需直接从 config 元数据或可配置键中读取。

| 属性            | 类型                   | 描述                                                   |
| --------------- | ---------------------- | ------------------------------------------------------ |
| `assistant_id`  | `str`                  | 当前部署的 assistant ID。                              |
| `graph_id`      | `str`                  | 当前部署的 graph ID。                                  |
| `user`          | `BaseUser \| None`     | 已认证的用户（如果配置了自定义身份验证）。             |

```python
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

class State(TypedDict):
    result: str

def my_node(state: State, runtime: Runtime):
    server = runtime.server_info
    if server is not None:
        print(f"Assistant: {server.assistant_id}, Graph: {server.graph_id}")  
        if server.user is not None:
            print(f"User: {server.user.identity}")
    return {"result": "done"}

builder = StateGraph(State)
builder.add_node("my_node", my_node)
builder.add_edge(START, "my_node")
builder.add_edge("my_node", END)
graph = builder.compile()
```

当图不在 LangGraph Server 上运行时（例如在本地开发或测试期间），`server_info` 为 `None`。

`runtime.execution_info` 和 `runtime.server_info` 需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）。

## 添加节点缓存

节点缓存在您希望避免重复操作（例如在时间或成本方面昂贵的操作）的情况下很有用。LangGraph 允许您向图中的节点添加个性化的缓存策略。

要配置缓存策略，请将 `cache_policy` 参数传递给 `add_node` 函数。在以下示例中，实例化了一个 `CachePolicy` 对象，其生存时间为 120 秒，并使用默认的 `key_func` 生成器。然后将其与一个节点关联：

```python
from langgraph.types import CachePolicy

builder.add_node(
    "node_name",
    node_function,
    cache_policy=CachePolicy(ttl=120),
)
```

然后，要为图启用节点级缓存，请在编译图时设置 `cache` 参数。下面的示例使用 `InMemoryCache` 设置具有内存缓存的图，但 `SqliteCache` 也可用。

```python
from langgraph.cache.memory import InMemoryCache

graph = builder.compile(cache=InMemoryCache())
```

## 创建步骤序列

**先决条件**
  本指南假定您熟悉上面关于状态的部分。

这里我们演示如何构建一个简单的步骤序列。我们将展示：

1.  如何构建一个顺序图
2.  用于构建类似图的内置简写。

要添加节点序列，我们使用图的 `add_node` 和 `add_edge` 方法：

```python
from langgraph.graph import START, StateGraph

builder = StateGraph(State)

# 添加节点
builder.add_node(step_1)
builder.add_node(step_2)
builder.add_node(step_3)

# 添加边
builder.add_edge(START, "step_1")
builder.add_edge("step_1", "step_2")
builder.add_edge("step_2", "step_3")
```

我们也可以使用内置的简写 `.add_sequence`：

```python
builder = StateGraph(State).add_sequence([step_1, step_2, step_3])
builder.add_edge(START, "step_1")
```

LangGraph 可以轻松地向您的应用程序添加底层的持久化层。
  这允许在节点执行之间对状态进行检查点，因此您的 LangGraph 节点可以控制：

  * 状态更新如何被检查点记录
  * 如何在人机交互工作流中恢复中断
  * 如何使用 LangGraph 的时间旅行功能“回退”和分支执行

  它们还确定执行步骤如何流式传输，以及如何使用 Studio 可视化和调试您的应用程序。

  让我们演示一个端到端的示例。我们将创建一个三个步骤的序列：

  1.  在状态的一个键中填充一个值
  2.  更新相同的值
  3.  填充一个不同的值

  让我们首先定义我们的状态。这控制着图的模式，并且还可以指定如何应用更新。有关更多详细信息，请参阅使用 reducers 处理状态更新。

  在我们的例子中，我们将只跟踪两个值：

  ```python
  from typing_extensions import TypedDict

  class State(TypedDict):
      value_1: str
      value_2: int
  ```

  我们的节点只是读取图状态并对其进行更新的 Python 函数。此函数的第一个参数将始终是状态：

  ```python
  def step_1(state: State):
      return {"value_1": "a"}

  def step_2(state: State):
      current_value_1 = state["value_1"]
      return {"value_1": f"{current_value_1} b"}

  def step_3(state: State):
      return {"value_2": 10}
  ```

请注意，当向状态发出更新时，每个节点可以只指定它希望更新的键的值。

    默认情况下，这将**覆盖**相应键的值。您也可以使用 reducers 来控制更新如何处理——例如，您可以将连续的更新追加到一个键上，而不是覆盖。有关更多详细信息，请参阅使用 reducers 处理状态更新。

最后，我们定义图。我们使用 `StateGraph` 来定义在此状态上操作的图。

  然后，我们将使用 `add_node` 和 `add_edge` 来填充我们的图并定义其控制流。

  ```python
  from langgraph.graph import START, StateGraph

  builder = StateGraph(State)

  # 添加节点
  builder.add_node(step_1)
  builder.add_node(step_2)
  builder.add_node(step_3)

  # 添加边
  builder.add_edge(START, "step_1")
  builder.add_edge("step_1", "step_2")
  builder.add_edge("step_2", "step_3")
  ```

**指定自定义名称**
    您可以使用 `add_node` 为节点指定自定义名称：

    ```python
    builder.add_node("my_node", step_1)
    ```

请注意：

  * `add_edge` 接受节点的名称，对于函数，默认为 `node.__name__`。
  * 我们必须指定图的入口点。为此，我们添加一条带有 `START` 节点的边。
  * 当没有更多节点要执行时，图停止。

  接下来，我们编译我们的图。这会对图的结构进行一些基本检查（例如，识别孤立节点）。如果我们通过 checkpointer 向应用程序添加持久化，它也将在这里传递。

  ```python
  graph = builder.compile()
  ```

  LangGraph 提供了用于可视化您的图的内置实用程序。让我们检查一下我们的序列。有关可视化的详细信息，请参阅可视化您的图。

  ```python
  from IPython.display import Image, display

  display(Image(graph.get_graph().draw_mermaid_png()))
  ```

让我们进行一个简单的调用：

  ```python
  graph.invoke({"value_1": "c"})
  ```

  ```
  {'value_1': 'a b', 'value_2': 10}
  ```

请注意：

  * 我们通过为单个状态键提供一个值来启动调用。我们必须始终为至少一个键提供一个值。
  * 我们传入的值被第一个节点覆盖了。
  * 第二个节点更新了该值。
  * 第三个节点填充了一个不同的值。

**内置简写**
    `langgraph>=0.2.46` 包含一个用于添加节点序列的内置简写 `add_sequence`。您可以按如下方式编译相同的图：

    ```python
    builder = StateGraph(State).add_sequence([step_1, step_2, step_3])  
    builder.add_edge(START, "step_1")

    graph = builder.compile()

    graph.invoke({"value_1": "c"})
    ```

## 创建分支

节点的并行执行对于加速整体图操作至关重要。LangGraph 原生支持节点的并行执行，这可以显著提高基于图的工作流的性能。这种并行化是通过扇出 (fan-out) 和扇入 (fan-in) 机制实现的，利用普通边和条件边。以下是一些示例，展示了如何添加为您工作的分支数据流。

### 并行运行图节点

在本例中，我们从 `Node A` 扇出到 `B and C`，然后扇入到 `D`。使用我们的状态，我们指定 reducer 的 add 操作。这将组合或累积状态中特定键的值，而不是简单地覆盖现有值。对于列表，这意味着将新列表与现有列表连接起来。有关使用 reducers 更新状态的更多详细信息，请参见上面关于状态 reducer 的部分。

```python
import operator
from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    # operator.add reducer fn 使其变为仅追加
    aggregate: Annotated[list, operator.add]

def a(state: State):
    print(f'Adding "A" to {state["aggregate"]}')
    return {"aggregate": ["A"]}

def b(state: State):
    print(f'Adding "B" to {state["aggregate"]}')
    return {"aggregate": ["B"]}

def c(state: State):
    print(f'Adding "C" to {state["aggregate"]}')
    return {"aggregate": ["C"]}

def d(state: State):
    print(f'Adding "D" to {state["aggregate"]}')
    return {"aggregate": ["D"]}

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(c)
builder.add_node(d)
builder.add_edge(START, "a")
builder.add_edge("a", "b")
builder.add_edge("a", "c")
builder.add_edge("b", "d")
builder.add_edge("c", "d")
builder.add_edge("d", END)
graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

使用 reducer，您可以看到在每个节点中添加的值被累积起来。

```python
graph.invoke({"aggregate": []}, {"configurable": {"thread_id": "foo"}})
```

```
Adding "A" to []
Adding "B" to ['A']
Adding "C" to ['A']
Adding "D" to ['A', 'B', 'C']
```

在上面的例子中，节点 `"b"` 和 `"c"` 在同一超级步骤中并发执行。因为它们在同一步骤中，节点 `"d"` 在 `"b"` 和 `"c"` 都完成后才执行。

  重要的是，来自并行超级步骤的更新可能不会一致地排序。如果您需要来自并行超级步骤的一致、预定的更新顺序，您应该将输出写入状态中的一个单独字段，并附带一个用于排序的值。

LangGraph 在超级步骤内执行节点，这意味着虽然并行分支并行执行，但整个超级步骤是**事务性**的。如果其中任何一个分支引发异常，则**没有**更新被应用到状态（整个超级步骤出错）。

  重要的是，当使用 checkpointer 时，超级步骤中成功节点的结果会被保存，并且在恢复时不会重复。

  如果您的节点容易出错（可能想要处理脆弱的 API 调用），LangGraph 提供了两种方法来解决这个问题：

  1.  您可以在节点内编写常规的 Python 代码来捕获和处理异常。
  2.  您可以设置一个 **retry_policy** 来指示图重试引发特定类型异常的节点。只有失败的分支会被重试，因此您不必担心执行重复的工作。

  总之，这些让您能够执行并行执行并完全控制异常处理。

**设置最大并发数**
  您可以通过在调用图时在配置中设置 `max_concurrency` 来控制并发任务的最大数量。

  ```python
  graph.invoke({"value_1": "c"}, {"configurable": {"max_concurrency": 10}})
  ```

### 延迟节点执行

当您想要延迟节点的执行直到所有其他待处理任务完成时，延迟节点执行很有用。当分支具有不同长度时，这尤其相关，这在 map-reduce 流等工作流中很常见。

上面的示例展示了当每条路径只有一步时如何扇出和扇入。但如果一个分支有多个步骤呢？让我们在 `"b"` 分支中添加一个节点 `"b_2"`：

```python
import operator
from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    # operator.add reducer fn 使其变为仅追加
    aggregate: Annotated[list, operator.add]

def a(state: State):
    print(f'Adding "A" to {state["aggregate"]}')
    return {"aggregate": ["A"]}

def b(state: State):
    print(f'Adding "B" to {state["aggregate"]}')
    return {"aggregate": ["B"]}

def b_2(state: State):
    print(f'Adding "B_2" to {state["aggregate"]}')
    return {"aggregate": ["B_2"]}

def c(state: State):
    print(f'Adding "C" to {state["aggregate"]}')
    return {"aggregate": ["C"]}

def d(state: State):
    print(f'Adding "D" to {state["aggregate"]}')
    return {"aggregate": ["D"]}

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(b_2)
builder.add_node(c)
builder.add_node(d, defer=True)  
builder.add_edge(START, "a")
builder.add_edge("a", "b")
builder.add_edge("a", "c")
builder.add_edge("b", "b_2")
builder.add_edge("b_2", "d")
builder.add_edge("c", "d")
builder.add_edge("d", END)
graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

```python
graph.invoke({"aggregate": []})
```

```
Adding "A" to []
Adding "B" to ['A']
Adding "C" to ['A']
Adding "B_2" to ['A', 'B', 'C']
Adding "D" to ['A', 'B', 'C', 'B_2']
```

在上面的例子中，节点 `"b"` 和 `"c"` 在同一超级步骤中并发执行。我们在节点 `d` 上设置了 `defer=True`，因此它将在所有待处理任务完成之前不会执行。在这种情况下，这意味着 `"d"` 将等待整个 `"b"` 分支完成才执行。

### 条件分支

如果您的扇出应根据状态在运行时发生变化，您可以使用 `add_conditional_edges` 使用图状态选择一个或多个路径。请参见下面的示例，其中节点 `a` 生成一个确定下一个节点的状态更新。

```python
import operator
from typing import Annotated, Literal, Sequence
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    aggregate: Annotated[list, operator.add]
    # 向状态添加一个键。我们将设置此键以确定
    # 如何分支。
    which: str

def a(state: State):
    print(f'Adding "A" to {state["aggregate"]}')
    return {"aggregate": ["A"], "which": "c"}  

def b(state: State):
    print(f'Adding "B" to {state["aggregate"]}')
    return {"aggregate": ["B"]}

def c(state: State):
    print(f'Adding "C" to {state["aggregate"]}')
    return {"aggregate": ["C"]}

builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)
builder.add_node(c)
builder.add_edge(START, "a")
builder.add_edge("b", END)
builder.add_edge("c", END)

def conditional_edge(state: State) -> Literal["b", "c"]:
    # 在此处填充任意逻辑，使用状态
    # 来确定下一个节点
    return state["which"]

builder.add_conditional_edges("a", conditional_edge)  

graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

```python
result = graph.invoke({"aggregate": []})
print(result)
```

```
Adding "A" to []
Adding "C" to ['A']
{'aggregate': ['A', 'C'], 'which': 'c'}
```

您的条件边可以路由到多个目标节点。例如：

  ```python
  def route_bc_or_cd(state: State) -> Sequence[str]:
      if state["which"] == "cd":
          return ["c", "d"]
      return ["b", "c"]
  ```

## Map-Reduce 和 Send API

LangGraph 使用 Send API 支持 map-reduce 和其他高级分支模式。以下是如何使用它的示例：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing_extensions import TypedDict, Annotated
import operator

class OverallState(TypedDict):
    topic: str
    subjects: list[str]
    jokes: Annotated[list[str], operator.add]
    best_selected_joke: str

def generate_topics(state: OverallState):
    return {"subjects": ["lions", "elephants", "penguins"]}

def generate_joke(state: OverallState):
    joke_map = {
        "lions": "Why don't lions like fast food? Because they can't catch it!",
        "elephants": "Why don't elephants use computers? They're afraid of the mouse!",
        "penguins": "Why don't penguins like talking to strangers at parties? Because they find it hard to break the ice."
    }
    return {"jokes": [joke_map[state["subject"]]]}

def continue_to_jokes(state: OverallState):
    return [Send("generate_joke", {"subject": s}) for s in state["subjects"]]

def best_joke(state: OverallState):
    return {"best_selected_joke": "penguins"}

builder = StateGraph(OverallState)
builder.add_node("generate_topics", generate_topics)
builder.add_node("generate_joke", generate_joke)
builder.add_node("best_joke", best_joke)
builder.add_edge(START, "generate_topics")
builder.add_conditional_edges("generate_topics", continue_to_jokes, ["generate_joke"])
builder.add_edge("generate_joke", "best_joke")
builder.add_edge("best_joke", END)
graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

```python
# 调用图：这里我们调用它来生成一个笑话列表
for step in graph.stream({"topic": "animals"}):
    print(step)
```

```
{'generate_topics': {'subjects': ['lions', 'elephants', 'penguins']}}
{'generate_joke': {'jokes': ["Why don't lions like fast food? Because they can't catch it!"]}}
{'generate_joke': {'jokes': ["Why don't elephants use computers? They're afraid of the mouse!"]}}
{'generate_joke': {'jokes': ['Why don't penguins like talking to strangers at parties? Because they find it hard to break the ice.']}}
{'best_joke': {'best_selected_joke': 'penguins'}}
```

## 创建和控制循环

在创建带有循环的图时，我们需要一种终止执行的机制。这最常见的是通过添加一条条件边来实现，该条件边一旦达到某个终止条件就会路由到 `END` 节点。

您还可以在调用或流式传输图时设置图的递归限制。递归限制设置了图在引发错误之前允许执行的超级步骤数。阅读更多关于递归限制概念的信息。

让我们考虑一个带有循环的简单图，以更好地了解这些机制如何工作。

要返回状态的最后一个值而不是收到递归限制错误，请参阅下一节。

在创建循环时，您可以包含一个指定终止条件的条件边：

```python
builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)

def route(state: State) -> Literal["b", END]:
    if termination_condition(state):
        return END
    else:
        return "b"

builder.add_edge(START, "a")
builder.add_conditional_edges("a", route)
builder.add_edge("b", "a")
graph = builder.compile()
```

要控制递归限制，请在配置中指定 `"recursion_limit"`。这将引发一个 `GraphRecursionError`，您可以捕获并处理它：

```python
from langgraph.errors import GraphRecursionError

try:
    graph.invoke(inputs, {"recursion_limit": 3})
except GraphRecursionError:
    print("Recursion Error")
```

让我们定义一个带有简单循环的图。注意我们使用条件边来实现终止条件。

```python
import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    # operator.add reducer fn 使其变为仅追加
    aggregate: Annotated[list, operator.add]

def a(state: State):
    print(f'Node A sees {state["aggregate"]}')
    return {"aggregate": ["A"]}

def b(state: State):
    print(f'Node B sees {state["aggregate"]}')
    return {"aggregate": ["B"]}

# 定义节点
builder = StateGraph(State)
builder.add_node(a)
builder.add_node(b)

# 定义边
def route(state: State) -> Literal["b", END]:
    if len(state["aggregate"]) < 7:
        return "b"
    else:
        return END

builder.add_edge(START, "a")
builder.add_conditional_edges("a", route)
builder.add_edge("b", "a")
graph = builder.compile()
```

```python
from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))
```

这种架构类似于一个 ReAct agent，其中节点 `"a"` 是一个工具调用模型，节点 `"b"` 代表工具。

在我们的 `route` 条件边中，我们指定一旦状态中的 `"aggregate"` 列表超过阈值长度，就应该结束。

调用图，我们看到在达到终止条件之前，我们在节点 `"a"` 和 `"b"` 之间交替。

```python
graph.invoke({"aggregate": []})
```

```
Node A sees []
Node B sees ['A']
Node A sees ['A', 'B']
Node B sees ['A', 'B', 'A']
Node A sees ['A', 'B', 'A', 'B']
Node B sees ['A', 'B', 'A', 'B', 'A']
Node A sees ['A', 'B', 'A', 'B', 'A', 'B']
```

### 施加递归限制

在某些应用程序中，我们可能无法保证达到给定的终止条件。在这些情况下，我们可以设置图的递归限制。这将在给定数量的超级步骤后引发 `GraphRecursionError`。然后我们可以捕获并处理这个异常：

```python
from langgraph.errors import GraphRecursionError

try:
    graph.invoke({"aggregate": []}, {"recursion_limit": 4})
except GraphRecursionError:
    print("Recursion Error")
```

```
Node A sees []
Node B sees ['A']
Node C sees ['A', 'B']
Node D sees ['A', 'B']
Node A sees ['A', 'B', 'C', 'D']
Recursion Error
```

我们可以不引发 `GraphRecursionError`，而是在状态中引入一个新的键，用于跟踪直到达到递归限制还剩多少步。然后我们可以使用这个键来确定是否应该结束运行。

  LangGraph 实现了一个特殊的 `RemainingSteps` 注解。在底层，它创建了一个 `ManagedValue` 通道——一个在我们的图运行期间存在且不会更长的状态通道。

  ```python
  import operator
  from typing import Annotated, Literal
  from typing_extensions import TypedDict
  from langgraph.graph import StateGraph, START, END
  from langgraph.managed.is_last_step import RemainingSteps

  class State(TypedDict):
      aggregate: Annotated[list, operator.add]
      remaining_steps: RemainingSteps

  def a(state: State):
      print(f'Node A sees {state["aggregate"]}')
      return {"aggregate": ["A"]}

  def b(state: State):
      print(f'Node B sees {state["aggregate"]}')
      return {"aggregate": ["B"]}

  # 定义节点
  builder = StateGraph(State)
  builder.add_node(a)
  builder.add_node(b)

  # 定义边
  def route(state: State) -> Literal["b", END]:
      if state["remaining_steps"] <= 2:
          return END
      else:
          return "b"

  builder.add_edge(START, "a")
  builder.add_conditional_edges("a", route)
  builder.add_edge("b", "a")
  graph = builder.compile()

  # 测试一下
  result = graph.invoke({"aggregate": []}, {"recursion_limit": 4})
  print(result)
  ```

  ```
  Node A sees []
  Node B sees ['A']
  Node A sees ['A', 'B']
  {'aggregate': ['A', 'B', 'A']}
  ```

为了更好地理解递归限制是如何工作的，让我们考虑一个更复杂的例子。下面我们实现了一个循环，但其中一个步骤扇出到两个节点：

  ```python
  import operator
  from typing import Annotated, Literal
  from typing_extensions import TypedDict
  from langgraph.graph import StateGraph, START, END

  class State(TypedDict):
      aggregate: Annotated[list, operator.add]

  def a(state: State):
      print(f'Node A sees {state["aggregate"]}')
      return {"aggregate": ["A"]}

  def b(state: State):
      print(f'Node B sees {state["aggregate"]}')
      return {"aggregate": ["B"]}

  def c(state: State):
      print(f'Node C sees {state["aggregate"]}')
      return {"aggregate": ["C"]}

  def d(state: State):
      print(f'Node D sees {state["aggregate"]}')
      return {"aggregate": ["D"]}

  # 定义节点
  builder = StateGraph(State)
  builder.add_node(a)
  builder.add_node(b)
  builder.add_node(c)
  builder.add_node(d)

  # 定义边
  def route(state: State) -> Literal["b", END]:
      if len(state["aggregate"]) < 7:
          return "b"
      else:
          return END

  builder.add_edge(START, "a")
  builder.add_conditional_edges("a", route)
  builder.add_edge("b", "c")
  builder.add_edge("b", "d")
  builder.add_edge(["c", "d"], "a")
  graph = builder.compile()
  ```

  ```python
  from IPython.display import Image, display

  display(Image(graph.get_graph().draw_mermaid_png()))
  ```

这个图看起来很复杂，但可以概念化为超级步骤的循环：

  1.  节点 A
  2.  节点 B
  3.  节点 C 和 D
  4.  节点 A
  5.  ...

  我们有一个由四个超级步骤组成的循环，其中节点 C 和 D 是并发执行的。

  像以前一样调用图，我们看到在达到终止条件之前我们完成了两个完整的“圈”：

  ```python
  result = graph.invoke({"aggregate": []})
  ```

  ```
  Node A sees []
  Node B sees ['A']
  Node D sees ['A', 'B']
  Node C sees ['A', 'B']
  Node A sees ['A', 'B', 'C', 'D']
  Node B sees ['A', 'B', 'C', 'D', 'A']
  Node D sees ['A', 'B', 'C', 'D', 'A', 'B']
  Node C sees ['A', 'B', 'C', 'D', 'A', 'B']
  Node A sees ['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D']
  ```

  然而，如果我们将递归限制设置为 4，我们只完成一圈，因为每圈是四个超级步骤：

  ```python
  from langgraph.errors import GraphRecursionError

  try:
      result = graph.invoke({"aggregate": []}, {"recursion_limit": 4})
  except GraphRecursionError:
      print("Recursion Error")
  ```

  ```
  Node A sees []
  Node B sees ['A']
  Node C sees ['A', 'B']
  Node D sees ['A', 'B']
  Node A sees ['A', 'B', 'C', 'D']
  Recursion Error
  ```

## 异步

在并发运行 I/O 绑定代码（例如，向聊天模型提供商发出并发 API 请求）时，使用异步编程范式可以产生显著的性能提升。

要将图的 `sync` 实现转换为 `async` 实现，您需要：

1.  将 `nodes` 更新为使用 `async def` 而不是 `def`。
2.  适当地更新内部代码以使用 `await`。
3.  根据需要以 `.ainvoke` 或 `.astream` 调用图。

由于许多 LangChain 对象实现了 Runnable 协议，该协议具有所有 `sync` 方法的 `async` 变体，因此将 `sync` 图升级为 `async` 图通常相当快速。

请参见下面的示例。为了演示底层 LLM 的异步调用，我们将包含一个聊天模型：

👉 阅读 OpenAI chat model 集成文档

    ```shell
    pip install -U "langchain[openai]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["OPENAI_API_KEY"] = "sk-..."

      model = init_chat_model("gpt-5.4")
      ```

      ```python
      import os
      from langchain_openai import ChatOpenAI

      os.environ["OPENAI_API_KEY"] = "sk-..."

      model = ChatOpenAI(model="gpt-5.4")
      ```

👉 阅读 Anthropic chat model 集成文档

    ```shell
    pip install -U "langchain[anthropic]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["ANTHROPIC_API_KEY"] = "sk-..."

      model = init_chat_model("claude-sonnet-4-6")
      ```

      ```python
      import os
      from langchain_anthropic import ChatAnthropic

      os.environ["ANTHROPIC_API_KEY"] = "sk-..."

      model = ChatAnthropic(model="claude-sonnet-4-6")
      ```

👉 阅读 Azure chat model 集成文档

    ```shell
    pip install -U "langchain[openai]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["AZURE_OPENAI_API_KEY"] = "..."
      os.environ["AZURE_OPENAI_ENDPOINT"] = "..."
      os.environ["OPENAI_API_VERSION"] = "2025-03-01-preview"

      model = init_chat_model(
          "azure_openai:gpt-5.4",
          azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
      )
      ```

      ```python
      import os
      from langchain_openai import AzureChatOpenAI

      os.environ["AZURE_OPENAI_API_KEY"] = "..."
      os.environ["AZURE_OPENAI_ENDPOINT"] = "..."
      os.environ["OPENAI_API_VERSION"] = "2025-03-01-preview"

      model = AzureChatOpenAI(
          model="gpt-5.4",
          azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]
      )
      ```

👉 阅读 Google GenAI chat model 集成文档

    ```shell
    pip install -U "langchain[google-genai]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["GOOGLE_API_KEY"] = "..."

      model = init_chat_model("google_genai:gemini-2.5-flash-lite")
      ```

      ```python
      import os
      from langchain_google_genai import ChatGoogleGenerativeAI

      os.environ["GOOGLE_API_KEY"] = "..."

      model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
      ```

👉 阅读 AWS Bedrock chat model 集成文档

    ```shell
    pip install -U "langchain[aws]"
    ```

```python
      from langchain.chat_models import init_chat_model

      # 按照以下步骤配置您的凭证：
      # https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html

      model = init_chat_model(
          "anthropic.claude-3-5-sonnet-20240620-v1:0",
          model_provider="bedrock_converse",
      )
      ```

      ```python
      from langchain_aws import ChatBedrock

      model = ChatBedrock(model="anthropic.claude-3-5-sonnet-20240620-v1:0")
      ```

👉 阅读 HuggingFace chat model 集成文档

    ```shell
    pip install -U "langchain[huggingface]"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["HUGGINGFACEHUB_API_TOKEN"] = "hf_..."

      model = init_chat_model(
          "microsoft/Phi-3-mini-4k-instruct",
          model_provider="huggingface",
          temperature=0.7,
          max_tokens=1024,
      )
      ```

      ```python
      import os
      from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

      os.environ["HUGGINGFACEHUB_API_TOKEN"] = "hf_..."

      llm = HuggingFaceEndpoint(
          repo_id="microsoft/Phi-3-mini-4k-instruct",
          temperature=0.7,
          max_length=1024,
      )
      model = ChatHuggingFace(llm=llm)
      ```

👉 阅读 OpenRouter chat model 集成文档

    ```shell
    pip install -U "langchain-openrouter"
    ```

```python
      import os
      from langchain.chat_models import init_chat_model

      os.environ["OPENROUTER_API_KEY"] = "sk-..."

      model = init_chat_model(
          "auto",
          model_provider="openrouter",
      )
      ```

      ```python
      import os
      from langchain_openrouter import ChatOpenRouter

      os.environ["OPENROUTER_API_KEY"] = "sk-..."

      model = ChatOpenRouter(model="auto")
      ```

```python
from langchain.chat_models import init_chat_model
from langgraph.graph import MessagesState, StateGraph

async def node(state: MessagesState):  
    new_message = await llm.ainvoke(state["messages"])  
    return {"messages": [new_message]}

builder = StateGraph(MessagesState).add_node(node).set_entry_point("node")
graph = builder.compile()

input_message = {"role": "user", "content": "Hello"}
result = await graph.ainvoke({"messages": [input_message]})  
```

**异步流式传输**
  有关使用异步进行流式传输的示例，请参阅流式传输指南。

## 使用 `Command` 组合控制流和状态更新

将控制流（边）和状态更新（节点）组合起来可能很有用。例如，您可能希望在**同一**节点中**同时**执行状态更新并决定下一步去哪个节点。LangGraph 提供了一种方法，通过从节点函数返回一个 `Command` 对象来实现：

```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    return Command(
        # 状态更新
        update={"foo": "bar"},
        # 控制流
        goto="my_other_node"
    )
```

下面我们展示一个端到端的示例。让我们创建一个包含 3 个节点的简单图：A、B 和 C。我们将首先执行节点 A，然后根据节点 A 的输出决定接下来是转到节点 B 还是节点 C。

```python
import random
from typing_extensions import TypedDict, Literal
from langgraph.graph import StateGraph, START
from langgraph.types import Command

# 定义图状态
class State(TypedDict):
    foo: str

# 定义节点

def node_a(state: State) -> Command[Literal["node_b", "node_c"]]:
    print("Called A")
    value = random.choice(["b", "c"])
    # 这是条件边函数的替代
    if value == "b":
        goto = "node_b"
    else:
        goto = "node_c"

    # 注意 Command 如何允许您同时更新图状态并路由到下一个节点
    return Command(
        # 这是状态更新
        update={"foo": value},
        # 这是边的替代
        goto=goto,
    )

def node_b(state: State):
    print("Called B")
    return {"foo": state["foo"] + "b"}

def node_c(state: State):
    print("Called C")
    return {"foo": state["foo"] + "c"}
```

我们现在可以使用上述节点创建 `StateGraph`。请注意，该图没有用于路由的条件边！这是因为控制流是在 `node_a` 内部用 `Command` 定义的。

```python
builder = StateGraph(State)
builder.add_edge(START, "node_a")
builder.add_node(node_a)
builder.add_node(node_b)
builder.add_node(node_c)
# 注意：节点 A、B 和 C 之间没有边！

graph = builder.compile()
```

您可能已经注意到我们使用了 `Command` 作为返回类型注解，例如 `Command[Literal["node_b", "node_c"]]`。这对于图渲染是必要的，并告诉 LangGraph `node_a` 可以导航到 `node_b` 和 `node_c`。

```python
from IPython.display import display, Image

display(Image(graph.get_graph().draw_mermaid_png()))
```

如果我们多次运行该图，我们会看到它根据节点 A 中的随机选择采取不同的路径（A -> B 或 A -> C）。

```python
graph.invoke({"foo": ""})
```

```
Called A
Called C
```

### 导航到父图中的节点

如果您正在使用子图，您可能希望从子图内的节点导航到不同的子图（即父图中的不同节点）。为此，您可以在 `Command` 中指定 `graph=Command.PARENT`：

```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    return Command(
        update={"foo": "bar"},
        goto="other_subgraph",  # 其中 `other_subgraph` 是父图中的一个节点
        graph=Command.PARENT
    )
```

让我们使用上面的例子来演示这一点。我们将通过将上面示例中的 `nodeA` 更改为一个单节点图来实现，我们将把它作为子图添加到我们的父图中。

**使用 `Command.PARENT` 进行状态更新**
  当您从子图节点向父图节点发送更新，且该键在父图和子图状态模式中都存在时，您**必须**为父图状态中正在更新的键定义一个 reducer。请参见下面的示例。

```python
import operator
from typing_extensions import Annotated

class State(TypedDict):
    # 注意：我们在这里定义了一个 reducer
    foo: Annotated[str, operator.add]  

def node_a(state: State):
    print("Called A")
    value = random.choice(["a", "b"])
    # 这是条件边函数的替代
    if value == "a":
        goto = "node_b"
    else:
        goto = "node_c"

    # 注意 Command 如何允许您同时更新图状态并路由到下一个节点
    return Command(
        update={"foo": value},
        goto=goto,
        # 这告诉 LangGraph 导航到父图中的 node_b 或 node_c
        # 注意：这将导航到相对于子图最近的父图
        graph=Command.PARENT,  
    )

subgraph = StateGraph(State).add_node(node_a).add_edge(START, "node_a").compile()

def node_b(state: State):
    print("Called B")
    # 注意：由于我们已经定义了一个 reducer，我们不需要手动将
    # 新字符附加到现有的 'foo' 值。相反，reducer 将自动附加这些
    # （通过 operator.add）
    return {"foo": "b"}  

def node_c(state: State):
    print("Called C")
    return {"foo": "c"}  

builder = StateGraph(State)
builder.add_edge(START, "subgraph")
builder.add_node("subgraph", subgraph)
builder.add_node(node_b)
builder.add_node(node_c)

graph = builder.compile()
```

```python
graph.invoke({"foo": ""})
```

```
Called A
Called C
```

### 在工具内部使用

一个常见的用例是从工具内部更新图状态。例如，在客户支持应用程序中，您可能希望根据客户的帐号或 ID 在对话开始时查找客户信息。要从工具更新图状态，您可以从工具返回 `Command(update={"my_custom_key": "foo", "messages": [...]})`：

```python
from langchain.tools import ToolRuntime

@tool
def lookup_user_info(runtime: ToolRuntime):
    """使用此工具查找用户信息以更好地协助他们解决问题。"""
    user_info = get_user_info(runtime.server_info.user.identity)  
    return Command(
        update={
            # 更新状态键
            "user_info": user_info,
            # 更新消息历史
            "messages": [ToolMessage("Successfully looked up user information", tool_call_id=runtime.tool_call_id)]
        }
    )
```

当从工具返回 `Command` 时，您**必须**在 `Command.update` 中包含 `messages`（或任何用于消息历史的状态键），并且 `messages` 中的消息列表**必须**包含一个 `ToolMessage`。这对于结果消息历史有效是必要的（LLM 提供商要求带有工具调用的 AI 消息后必须跟随工具结果消息）。

如果您使用的是通过 `Command` 更新状态的工具，我们建议使用预构建的 `ToolNode`，它会自动处理返回 `Command` 对象的工具并将其传播到图状态。如果您正在编写一个调用工具的自定义节点，则需要手动将工具返回的 `Command` 对象作为节点的更新进行传播。

## 可视化您的图

这里我们演示如何可视化您创建的图。

您可以可视化任何任意图，包括 StateGraph。

让我们通过绘制分形来找点乐趣 :)。

```python
import random
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]

class MyNode:
    def __init__(self, name: str):
        self.name = name
    def __call__(self, state: State):
        return {"messages": [("assistant", f"Called node {self.name}")]}

def route(state) -> Literal["entry_node", END]:
    if len(state["messages"]) > 10:
        return END
    return "entry_node"

def add_fractal_nodes(builder, current_node, level, max_level):
    if level > max_level:
        return
    # 在此级别创建的节点数
    num_nodes = random.randint(1, 3)  # 根据需要调整随机性
    for i in range(num_nodes):
        nm = ["A", "B", "C"][i]
        node_name = f"node_{current_node}_{nm}"
        builder.add_node(node_name, MyNode(node_name))
        builder.add_edge(current_node, node_name)
        # 递归添加更多节点
        r = random.random()
        if r > 0.2 and level + 1 < max_level:
            add_fractal_nodes(builder, node_name, level + 1, max_level)
        elif r > 0.05:
            builder.add_conditional_edges(node_name, route, node_name)
        else:
            # 结束
            builder.add_edge(node_name, END)

def build_fractal_graph(max_level: int):
    builder = StateGraph(State)
    entry_point = "entry_node"
    builder.add_node(entry_point, MyNode(entry_point))
    builder.add_edge(START, entry_point)
    add_fractal_nodes(builder, entry_point, 1, max_level)
    # 可选：如果需要，设置一个完成点
    builder.add_edge(entry_point, END)  # 或任何特定节点
    return builder.compile()

app = build_fractal_graph(3)
```

### Mermaid

我们还可以将图类转换为 Mermaid 语法。

```python
print(app.get_graph().draw_mermaid())
```

```
%%{init: {'flowchart': {'curve': 'linear'}}}%%
graph TD;
    tart__([__start__]):::first
    ry_node(entry_node)
    e_entry_node_A(node_entry_node_A)
    e_entry_node_B(node_entry_node_B)
    e_node_entry_node_B_A(node_node_entry_node_B_A)
    e_node_entry_node_B_B(node_node_entry_node_B_B)
    e_node_entry_node_B_C(node_node_entry_node_B_C)
    nd__([__end__]):::last
    tart__ --> entry_node;
    ry_node --> __end__;
    ry_node --> node_entry_node_A;
    ry_node --> node_entry_node_B;
    e_entry_node_B --> node_node_entry_node_B_A;
    e_entry_node_B --> node_node_entry_node_B_B;
    e_entry_node_B --> node_node_entry_node_B_C;
    e_entry_node_A -.-> entry_node;
    e_entry_node_A -.-> __end__;
    e_node_entry_node_B_A -.-> entry_node;
    e_node_entry_node_B_A -.-> __end__;
    e_node_entry_node_B_B -.-> entry_node;
    e_node_entry_node_B_B -.-> __end__;
    e_node_entry_node_B_C -.-> entry_node;
    e_node_entry_node_B_C -.-> __end__;
    ssDef default fill:#f2f0ff,line-height:1.2
    ssDef first fill-opacity:0
    ssDef last fill:#bfb6fc
```

### PNG

如果愿意，我们可以将图渲染为 `.png`。这里我们可以使用三个选项：

*   使用 Mermaid.ink API（不需要额外的包）
*   使用 Mermaid + Pyppeteer（需要 `pip install pyppeteer`）
*   使用 graphviz（需要 `pip install graphviz`）

**使用 Mermaid.Ink**

默认情况下，`draw_mermaid_png()` 使用 Mermaid.Ink 的 API 来生成图表。

```python
from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles

display(Image(app.get_graph().draw_mermaid_png()))
```

**使用 Mermaid + Pyppeteer**

```python
import nest_asyncio

nest_asyncio.apply()  # Jupyter Notebook 运行异步函数所需

display(
    Image(
        app.get_graph().draw_mermaid_png(
            curve_style=CurveStyle.LINEAR,
            node_colors=NodeStyles(first="#ffdfba", last="#baffc9", default="#fad7de"),
            wrap_label_n_words=9,
            output_file_path=None,
            draw_method=MermaidDrawMethod.PYPPETEER,
            background_color="white",
            padding=10,
        )
    )
)
```

**使用 Graphviz**

```python
try:
    display(Image(app.get_graph().draw_png()))
except ImportError:
    print(
        "您可能需要安装 pygraphviz 的依赖项，更多信息请参见 https://github.com/pygraphviz/pygraphviz/blob/main/INSTALL.txt"
    )
```