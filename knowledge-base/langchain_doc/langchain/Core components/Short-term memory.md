# 短期记忆 (Short-term memory)

## 概述 (Overview)

记忆 (Memory) 是一个能够记住先前交互信息的系统。对于 AI agents 来说，记忆至关重要，因为它让 agents 能够记住之前的交互、从反馈中学习并适应用户偏好。随着 agents 处理涉及大量用户交互的复杂任务，这种能力对于效率和用户满意度都变得至关重要。

短期记忆 (Short-term memory) 让您的应用程序能够在单个线程 (thread) 或对话中记住之前的交互。

一个线程将一次会话中的多次交互组织起来，类似于电子邮件将消息分组到单个会话中的方式。

对话历史 (Conversation history) 是最常见的短期记忆形式。长对话对当今的 LLM 构成了挑战；完整的历史可能无法容纳在 LLM 的上下文窗口内，导致上下文丢失或错误。

即使您的模型支持完整的上下文长度，大多数 LLM 在长上下文上的表现仍然不佳。它们会被陈旧或不相关的内容“分散注意力”，同时还会受到响应时间变慢和成本升高的影响。

聊天模型使用消息 (messages) 来接受上下文，其中包括指令（系统消息）和输入（人类消息）。在聊天应用程序中，消息在人类输入和模型响应之间交替，导致消息列表随时间变长。由于上下文窗口有限，许多应用程序可以通过使用技术来移除或“遗忘”陈旧信息而受益。

需要**跨**对话记住信息吗？使用长期记忆 (long-term memory) 在不同的线程和会话中存储和检索用户特定或应用级别的数据。

## 使用方法 (Usage)

要为 agent 添加短期记忆（线程级持久化），您需要在创建 agent 时指定一个 `checkpointer`。

LangChain 的 agent 将短期记忆作为 agent 状态 (state) 的一部分进行管理。

  通过将这些存储在 graph 的状态中，agent 可以访问给定对话的完整上下文，同时保持不同线程之间的隔离。

  状态使用 checkpointer 持久化到数据库（或内存）中，以便线程可以随时恢复。

  当 agent 被调用或完成一个步骤（如 tool call）时，短期记忆会更新，并且在每个步骤开始时读取状态。

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver  

agent = create_agent(
    "gpt-5.4",
    tools=[get_user_info],
    checkpointer=InMemorySaver(),  
)

agent.invoke(
    {"messages": [{"role": "user", "content": "Hi! My name is Bob."}]},
    {"configurable": {"thread_id": "1"}},  
)
```

### 在生产环境中 (In production)

在生产环境中，使用由数据库支持的 checkpointer：

```shell
pip install langgraph-checkpoint-postgres
```

```python
from langchain.agents import create_agent

from langgraph.checkpoint.postgres import PostgresSaver  

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup() # 在 PostgreSQL 中自动创建表
    agent = create_agent(
        "gpt-5.4",
        tools=[get_user_info],
        checkpointer=checkpointer,  
    )
```

有关更多 checkpointer 选项，包括 SQLite、Postgres 和 Azure Cosmos DB，请参阅 Persistence 文档中的 checkpointer 库列表。

## 自定义 agent 记忆 (Customizing agent memory)

默认情况下，agents 使用 `AgentState` 来管理短期记忆，特别是通过 `messages` 键管理对话历史。

您可以扩展 `AgentState` 来添加额外的字段。自定义状态模式 (state schemas) 使用 `state_schema` 参数传递给 `create_agent`。

```python
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver

class CustomAgentState(AgentState):  
    user_id: str  
    preferences: dict  

agent = create_agent(
    "gpt-5.4",
    tools=[get_user_info],
    state_schema=CustomAgentState,  
    checkpointer=InMemorySaver(),
)

# 自定义状态可以在 invoke 时传递
result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "Hello"}],
        "user_id": "user_123",  
        "preferences": {"theme": "dark"}  
    },
    {"configurable": {"thread_id": "1"}})
```

## 常见模式 (Common patterns)

启用短期记忆后，长对话可能会超出 LLM 的上下文窗口。常见的解决方案有：

- 移除前 N 条或后 N 条消息（在调用 LLM 之前）
- 从 LangGraph 状态中永久删除消息
- 总结历史中较早的消息并用摘要替换它们
- 自定义策略（例如，消息过滤等）

这使得 agent 能够跟踪对话而不会超出 LLM 的上下文窗口。

### 修剪消息 (Trim messages)

大多数 LLM 都有一个最大支持的上下文窗口（以 tokens 计）。

决定何时截断消息的一种方法是计算消息历史中的 token 数量，并在接近该限制时进行截断。如果您使用 LangChain，可以使用消息修剪工具，并指定要从列表中保留的 token 数量，以及用于处理边界的 `strategy`（例如，保留最后 `max_tokens` 条消息）。

要在 agent 中修剪消息历史，请使用 `@before_model` 中间件装饰器：

```python
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig
from typing import Any

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """仅保留最后几条消息以适应上下文窗口。"""
    messages = state["messages"]

    if len(messages) <= 3:
        return None  # 无需更改

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

agent = create_agent(
    your_model_here,
    tools=your_tools_here,
    middleware=[trim_messages],
    checkpointer=InMemorySaver(),
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

agent.invoke({"messages": "hi, my name is bob"}, config)
agent.invoke({"messages": "write a short poem about cats"}, config)
agent.invoke({"messages": "now do the same but for dogs"}, config)
final_response = agent.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
"""
================================== Ai Message ==================================

你的名字是 Bob。你之前告诉过我。
如果你想让我叫你的昵称或使用不同的名字，尽管说。
"""
```

### 删除消息 (Delete messages)

您可以从 graph 状态中删除消息以管理消息历史。

当您想要删除特定消息或清除整个消息历史时，这非常有用。

要从 graph 状态中删除消息，您可以使用 `RemoveMessage`。

要使 `RemoveMessage` 生效，您需要使用带有 `add_messages` reducer 的状态键。

默认的 `AgentState` 提供了这一点。

要删除特定消息：

```python
from langchain.messages import RemoveMessage  

def delete_messages(state):
    messages = state["messages"]
    if len(messages) > 2:
        # 移除最早的两条消息
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}  
```

要删除**所有**消息：

```python
from langgraph.graph.message import REMOVE_ALL_MESSAGES  

def delete_messages(state):
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}  
```

删除消息时，**请确保**生成的消息历史是有效的。请检查您正在使用的 LLM provider 的限制。例如：

  * 某些 providers 期望消息历史以 `user` 消息开头
  * 大多数 providers 要求带有 tool calls 的 `assistant` 消息后必须跟随相应的 `tool` 结果消息。

```python
from langchain.messages import RemoveMessage
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import after_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig

@after_model
def delete_old_messages(state: AgentState, runtime: Runtime) -> dict | None:
    """删除旧消息以保持对话可管理。"""
    messages = state["messages"]
    if len(messages) > 2:
        # 移除最早的两条消息
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}
    return None

agent = create_agent(
    "gpt-5-nano",
    tools=[],
    system_prompt="请保持简洁并切中要点。",
    middleware=[delete_old_messages],
    checkpointer=InMemorySaver(),
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

for event in agent.stream(
    {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
    config,
    stream_mode="values",
):
    print([(message.type, message.content) for message in event["messages"]])

for event in agent.stream(
    {"messages": [{"role": "user", "content": "what's my name?"}]},
    config,
    stream_mode="values",
):
    print([(message.type, message.content) for message in event["messages"]])
```

```
[('human', "hi! I'm bob")]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! Nice to meet you. How can I help you today? I can answer questions, brainstorm ideas, draft text, explain things, or help with code.')]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! Nice to meet you. How can I help you today? I can answer questions, brainstorm ideas, draft text, explain things, or help with code.'), ('human', "what's my name?")]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! Nice to meet you. How can I help you today? I can answer questions, brainstorm ideas, draft text, explain things, or help with code.'), ('human', "what's my name?"), ('ai', 'Your name is Bob. How can I help you today, Bob?')]
[('human', "what's my name?"), ('ai', 'Your name is Bob. How can I help you today, Bob?')]
```

### 总结消息 (Summarize messages)

如上所示，修剪或删除消息的问题在于，您可能会因为删除消息队列而丢失信息。
因此，一些应用程序受益于使用聊天模型对消息历史进行总结的更复杂方法。

要在 agent 中总结消息历史，请使用内置的 `SummarizationMiddleware`：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig

checkpointer = InMemorySaver()

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("tokens", 4000),
            keep=("messages", 20)
        )
    ],
    checkpointer=checkpointer,
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}
agent.invoke({"messages": "hi, my name is bob"}, config)
agent.invoke({"messages": "write a short poem about cats"}, config)
agent.invoke({"messages": "now do the same but for dogs"}, config)
final_response = agent.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
"""
================================== Ai Message ==================================

你的名字是 Bob！
"""
```

有关更多配置选项，请参阅 `SummarizationMiddleware`。

## 访问记忆 (Access memory)

您可以通过多种方式访问和修改 agent 的短期记忆（状态）：

### Tools

#### 在 tool 中读取短期记忆

使用 `runtime` 参数（类型为 `ToolRuntime`）在 tool 中访问短期记忆（状态）。

`runtime` 参数对 tool 签名是隐藏的（因此模型看不到它），但 tool 可以通过它访问状态。

```python
from langchain.agents import create_agent, AgentState
from langchain.tools import tool, ToolRuntime

class CustomState(AgentState):
    user_id: str

@tool
def get_user_info(
    runtime: ToolRuntime
) -> str:
    """查找用户信息。"""
    user_id = runtime.state["user_id"]
    return "User is John Smith" if user_id == "user_123" else "Unknown user"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_user_info],
    state_schema=CustomState,
)

result = agent.invoke({
    "messages": "look up user information",
    "user_id": "user_123"
})
print(result["messages"][-1].content)
# > User is John Smith.
```

#### 从 tools 写入短期记忆

要修改 agent 在执行期间的短期记忆（状态），您可以直接从 tools 返回状态更新。

这对于持久化中间结果或使信息可用于后续 tools 或提示非常有用。

```python
from langchain.tools import tool, ToolRuntime
from langchain_core.runnables import RunnableConfig
from langchain.messages import ToolMessage
from langchain.agents import create_agent, AgentState
from langgraph.types import Command
from pydantic import BaseModel

class CustomState(AgentState):  
    user_name: str

class CustomContext(BaseModel):
    user_id: str

@tool
def update_user_info(
    runtime: ToolRuntime[CustomContext, CustomState],
) -> Command:
    """查找并更新用户信息。"""
    user_id = runtime.context.user_id
    name = "John Smith" if user_id == "user_123" else "Unknown user"
    return Command(update={  
        "user_name": name,
        # 更新消息历史
        "messages": [
            ToolMessage(
                "Successfully looked up user information",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })

@tool
def greet(
    runtime: ToolRuntime[CustomContext, CustomState]
) -> str | Command:
    """找到用户信息后，使用此工具向用户打招呼。"""
    user_name = runtime.state.get("user_name", None)
    if user_name is None:
       return Command(update={
            "messages": [
                ToolMessage(
                    "Please call the 'update_user_info' tool it will get and update the user's name.",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })
    return f"Hello {user_name}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[update_user_info, greet],
    state_schema=CustomState, 
    context_schema=CustomContext,
)

agent.invoke(
    {"messages": [{"role": "user", "content": "greet the user"}]},
    context=CustomContext(user_id="user_123"),
)
```

### 提示 (Prompt)

在中间件中访问短期记忆（状态），以基于对话历史或自定义状态字段创建动态提示。

```python
from langchain.agents import create_agent
from typing import TypedDict
from langchain.agents.middleware import dynamic_prompt, ModelRequest

class CustomContext(TypedDict):
    user_name: str

def get_weather(city: str) -> str:
    """获取城市的天气。"""
    return f"The weather in {city} is always sunny!"

@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context["user_name"]
    system_prompt = f"You are a helpful assistant. Address the user as {user_name}."
    return system_prompt

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
    middleware=[dynamic_system_prompt],
    context_schema=CustomContext,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    context=CustomContext(user_name="John Smith"),
)
for msg in result["messages"]:
    msg.pretty_print()

```

```shell
================================ Human Message =================================

What is the weather in SF?
================================== Ai Message ==================================
Tool Calls:
  get_weather (call_WFQlOGn4b2yoJrv7cih342FG)
 Call ID: call_WFQlOGn4b2yoJrv7cih342FG
  Args:
    city: San Francisco
================================= Tool Message =================================
Name: get_weather

The weather in San Francisco is always sunny!
================================== Ai Message ==================================

Hi John Smith, the weather in San Francisco is always sunny!
```

### 模型之前 (Before model)

在 `@before_model` 中间件中访问短期记忆（状态），以在模型调用之前处理消息。

```mermaid
graph TD
    S(["\_\_start\_\_"])
    PRE(before_model)
    MODEL(model)
    TOOLS(tools)
    END(["\_\_end\_\_"])
    S --> PRE
    PRE --> MODEL
    MODEL -.-> TOOLS
    MODEL -.-> END
    TOOLS --> PRE
    classDef blueHighlight fill:#E5F4FF,stroke:#006DDD,color:#030710;
    classDef neutral fill:#F2FAFF,stroke:#40668D,stroke-width:2px,color:#2F4B68;
    class S blueHighlight;
    class END blueHighlight;
    class PRE,MODEL,TOOLS neutral;
```

```python
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from typing import Any

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """仅保留最后几条消息以适应上下文窗口。"""
    messages = state["messages"]

    if len(messages) <= 3:
        return None  # 无需更改

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

agent = create_agent(
    "gpt-5-nano",
    tools=[],
    middleware=[trim_messages],
    checkpointer=InMemorySaver()
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

agent.invoke({"messages": "hi, my name is bob"}, config)
agent.invoke({"messages": "write a short poem about cats"}, config)
agent.invoke({"messages": "now do the same but for dogs"}, config)
final_response = agent.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
"""
================================== Ai Message ==================================

你的名字是 Bob。你之前告诉过我。
如果你想让我叫你的昵称或使用不同的名字，尽管说。
"""
```

### 模型之后 (After model)

在 `@after_model` 中间件中访问短期记忆（状态），以在模型调用之后处理消息。

```mermaid
%%{
    init: {
        "fontFamily": "monospace",
        "flowchart": {
        "curve": "basis"
        }
    }
}%%
graph TD
    S(["\_\_start\_\_"])
    MODEL(model)
    POST(after_model)
    TOOLS(tools)
    END(["\_\_end\_\_"])
    S --> MODEL
    MODEL --> POST
    POST -.-> END
    POST -.-> TOOLS
    TOOLS --> MODEL
    classDef blueHighlight fill:#E5F4FF,stroke:#006DDD,color:#030710;
    classDef greenHighlight fill:#F6FFDB,stroke:#6E8900,color:#2E3900;
    classDef neutral fill:#F2FAFF,stroke:#40668D,stroke-width:2px,color:#2F4B68;
    class S blueHighlight;
    class END blueHighlight;
    class POST greenHighlight;
    class MODEL,TOOLS neutral;
```

```python
from langchain.messages import RemoveMessage
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import after_model
from langgraph.runtime import Runtime

@after_model
def validate_response(state: AgentState, runtime: Runtime) -> dict | None:
    """移除包含敏感词的消息。"""
    STOP_WORDS = ["password", "secret"]
    last_message = state["messages"][-1]
    if any(word in last_message.content for word in STOP_WORDS):
        return {"messages": [RemoveMessage(id=last_message.id)]}
    return None

agent = create_agent(
    model="gpt-5-nano",
    tools=[],
    middleware=[validate_response],
    checkpointer=InMemorySaver(),
)
```