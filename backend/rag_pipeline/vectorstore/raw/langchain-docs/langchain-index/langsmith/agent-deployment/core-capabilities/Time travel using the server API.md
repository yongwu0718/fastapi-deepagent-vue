# 使用服务器 API 进行时间旅行

LangGraph 提供了**时间旅行**功能，可以从先前的 checkpoint 恢复执行，要么重放相同的状态，要么修改它以探索替代路径。在所有情况下，恢复过去的执行都会在历史记录中产生一个新的分支。

要使用 LangSmith Deployment API（通过 LangGraph SDK）进行时间旅行：

1. **运行 graph**：使用 LangGraph SDK 的 `client.runs.wait` 或 `client.runs.stream` API 以初始输入运行 graph。
2. **识别现有 thread 中的 checkpoint**：使用 `client.threads.get_history` 方法检索特定 `thread_id` 的执行历史，并找到所需的 `checkpoint_id`。或者，在希望执行暂停的 node 之前设置断点。然后您可以找到记录到该断点的最新 checkpoint。
3. **（可选）修改 graph 状态**：使用 `client.threads.update_state` 方法修改 checkpoint 处的 graph 状态，并从替代状态恢复执行。
4. **从 checkpoint 恢复执行**：使用 `client.runs.wait` 或 `client.runs.stream` API，传入 `input=None` 以及相应的 `thread_id` 和 `checkpoint_id`。

## 在工作流中使用时间旅行

```python
from typing_extensions import TypedDict, NotRequired
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

class State(TypedDict):
    topic: NotRequired[str]
    joke: NotRequired[str]

model = init_chat_model(
    "claude-sonnet-4-6",
    temperature=0,
)

def generate_topic(state: State):
    """LLM 调用，生成笑话主题"""
    msg = model.invoke("Give me a funny topic for a joke")
    return {"topic": msg.content}

def write_joke(state: State):
    """LLM 调用，根据主题写笑话"""
    msg = model.invoke(f"Write a short joke about {state['topic']}")
    return {"joke": msg.content}

# 构建工作流
builder = StateGraph(State)

# 添加节点
builder.add_node("generate_topic", generate_topic)
builder.add_node("write_joke", write_joke)

# 添加边连接节点
builder.add_edge(START, "generate_topic")
builder.add_edge("generate_topic", "write_joke")

# 编译
graph = builder.compile()
```

### 1. 运行 graph

```python
from langgraph_sdk import get_client
client = get_client(url=<your_url>)

# 使用名为 "agent" 部署的 graph
assistant_id = "agent"

# 创建一个 thread
thread = await client.threads.create()
thread_id = thread["thread_id"]

# 运行 graph
result = await client.runs.wait(
    thread_id,
    assistant_id,
    input={}
)
```
### 2. 识别 checkpoint

```python
# 返回的状态按时间倒序排列
states = await client.threads.get_history(thread_id)
selected_state = states[1]
print(selected_state)
```
### 3. 更新状态

`update_state` 将创建一个新的 checkpoint。新 checkpoint 将与同一个 thread 关联，但具有新的 checkpoint ID。

```python
new_config = await client.threads.update_state(
    thread_id,
    {"topic": "chickens"},
    checkpoint_id=selected_state["checkpoint_id"]
)
print(new_config)
```
### 4. 从 checkpoint 恢复执行

```python
await client.runs.wait(
    thread_id,
    assistant_id,
    input=None,
    checkpoint_id=new_config["checkpoint_id"]
)
```
## 了解更多

* **LangGraph 时间旅行指南**：了解更多关于在 LangGraph 中使用时间旅行的内容。