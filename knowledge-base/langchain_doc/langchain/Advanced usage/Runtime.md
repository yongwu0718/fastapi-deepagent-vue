# Runtime

## 概述

LangChain 的 `create_agent` 底层运行在 LangGraph 的 Runtime 之上。

LangGraph 公开了一个 `Runtime` 对象，其中包含以下信息：

1. **Context**：静态信息，例如用户 ID、数据库连接或 agent 调用的其他依赖项
2. **Store**：一个用于长期记忆的 BaseStore 实例
3. **Stream writer**：一个用于通过 `"custom"` 流模式流式传输信息的对象
4. **Execution info**：当前执行的标识和重试信息（thread ID, run ID, attempt number）
5. **Server info**：在 LangGraph Server 上运行时的服务器特定元数据（assistant ID, graph ID, authenticated user）

Runtime context 为您的工具和中间件提供了**依赖注入**。您无需硬编码值或使用全局状态，而是可以在调用 agent 时注入运行时依赖项（例如数据库连接、用户 ID 或配置）。这使得您的工具更易于测试、重用和灵活。

您可以在工具和中间件中访问运行时信息。

## 访问

使用 `create_agent` 创建 agent 时，您可以指定一个 `context_schema` 来定义存储在 agent `Runtime` 中的 `context` 的结构。

在调用 agent 时，传递 `context` 参数以及该次运行的相关配置：

```python
from dataclasses import dataclass

from langchain.agents import create_agent

@dataclass
class Context:
    user_name: str

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    context_schema=Context  
)

agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")  
)
```

### 在工具内部

您可以在工具内部访问运行时信息，以便：

* 访问 context
* 读取或写入长期记忆
* 写入自定义流（例如工具进度/更新）

使用 `ToolRuntime` 参数来访问工具内部的 `Runtime` 对象。

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime  

@dataclass
class Context:
    user_id: str

@tool
def fetch_user_email_preferences(runtime: ToolRuntime[Context]) -> str:  
    """从存储中获取用户的电子邮件偏好。"""
    user_id = runtime.context.user_id  

    preferences: str = "The user prefers you to write a brief and polite email."
    if runtime.store:  
        if memory := runtime.store.get(("users",), user_id):  
            preferences = memory.value["preferences"]

    return preferences
```

### 工具内部的执行信息和服务端信息

通过 `runtime.execution_info` 访问执行标识（thread ID, run ID），当在 LangGraph Server 上运行时，通过 `runtime.server_info` 访问服务器特定的元数据（assistant ID, authenticated user）：

```python
from langchain.tools import tool, ToolRuntime

@tool
def context_aware_tool(runtime: ToolRuntime) -> str:
    """一个使用执行信息和服务端信息的工具。"""
    # 访问 thread ID 和 run ID
    info = runtime.execution_info
    print(f"Thread: {info.thread_id}, Run: {info.run_id}")  

    # 访问服务端信息（仅在 LangGraph Server 上可用）
    server = runtime.server_info
    if server is not None:
        print(f"Assistant: {server.assistant_id}")  
        if server.user is not None:
            print(f"User: {server.user.identity}")  

    return "done"
```

当不在 LangGraph Server 上运行时（例如在本地开发期间），`server_info` 为 `None`。

`runtime.execution_info` 和 `runtime.server_info` 需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）。

### 在中间件内部

您可以在中间件中访问运行时信息，以创建动态提示、修改消息或根据用户上下文控制 agent 行为。

使用 `Runtime` 参数在节点风格的 hooks 中访问 `Runtime` 对象。对于包装风格的 hooks，`Runtime` 对象可以在 `ModelRequest` 参数中访问。

```python
from dataclasses import dataclass

from langchain.messages import AnyMessage
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import dynamic_prompt, ModelRequest, before_model, after_model
from langgraph.runtime import Runtime

@dataclass
class Context:
    user_name: str

# 动态提示
@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context.user_name  
    system_prompt = f"You are a helpful assistant. Address the user as {user_name}."
    return system_prompt

# 模型之前的 hook
@before_model
def log_before_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:  
    print(f"Processing request for user: {runtime.context.user_name}")  
    return None

# 模型之后的 hook
@after_model
def log_after_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:  
    print(f"Completed request for user: {runtime.context.user_name}")  
    return None

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    middleware=[dynamic_system_prompt, log_before_model, log_after_model],  
    context_schema=Context
)

agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")
)
```

### 中间件内部的执行信息和服务端信息

中间件 hooks 也可以访问 `runtime.execution_info` 和 `runtime.server_info`：

```python
from langchain.agents import AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime

@before_model
def auth_gate(state: AgentState, runtime: Runtime) -> dict | None:
    """在 LangGraph Server 上运行时阻止未认证的用户。"""
    server = runtime.server_info
    if server is not None and server.user is None:  
        raise ValueError("Authentication required")
    print(f"Thread: {runtime.execution_info.thread_id}")  
    return None
```

需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）。