# Model Context Protocol (MCP)

Model Context Protocol (MCP) 是一个开放协议，它标准化了应用程序向 LLM 提供工具和上下文的方式。LangChain agents 可以使用 `langchain-mcp-adapters` 库来使用定义在 MCP 服务器上的工具。

## 快速开始

安装 `langchain-mcp-adapters` 库：

```bash
pip install langchain-mcp-adapters
```

`langchain-mcp-adapters` 使 agents 能够使用定义在一个或多个 MCP 服务器上的工具。

`MultiServerMCPClient` 默认是 **无状态 (stateless)** 的。每次工具调用都会创建一个新的 MCP `ClientSession`，执行工具，然后清理。有关更多详细信息，请参阅有状态会话部分。

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient  
from langchain.agents import create_agent

async def main():
    client = MultiServerMCPClient(  
        {
            "math": {
                "transport": "stdio",  # 本地子进程通信
                "command": "python",
                # math_server.py 文件的绝对路径
                "args": ["/path/to/math_server.py"],
            },
            "weather": {
                "transport": "http",  # 基于 HTTP 的远程服务器
                # 确保您的 weather server 在 8000 端口运行
                "url": "http://localhost:8000/mcp",
            }
        }
    )

    tools = await client.get_tools()  
    agent = create_agent(
        "claude-sonnet-4-6",
        tools  
    )
    math_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what's (3 + 5) x 12?"}]}
    )
    weather_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what is the weather in nyc?"}]}
    )
    print(math_response)
    print(weather_response)

if __name__ == "__main__":
    asyncio.run(main())
```

## 自定义服务器

要创建自定义 MCP 服务器，请使用 FastMCP 库：

```bash
pip install fastmcp
```

要使用 MCP 工具服务器测试您的 agent，请使用以下示例：

```python
from fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
  """Add two numbers"""
  return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
  """Multiply two numbers"""
  return a * b

if __name__ == "__main__":
  mcp.run(transport="stdio")
```

```python
from fastmcp import FastMCP

mcp = FastMCP("Weather")

@mcp.tool()
async def get_weather(location: str) -> str:
  """Get weather for location."""
  return "It's always sunny in New York"

if __name__ == "__main__":
  mcp.run(transport="streamable-http")
```

## 传输方式 (Transports)

MCP 支持不同的客户端-服务器通信传输机制。

### HTTP

`http` 传输（也称为 `streamable-http`）使用 HTTP 请求进行客户端-服务器通信。有关更多详细信息，请参阅 MCP HTTP transport specification。

```python
client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
        }
    }
)
```

#### 传递 Headers

当通过 HTTP 连接到 MCP 服务器时，您可以使用连接配置中的 `headers` 字段包含自定义 headers（例如，用于身份验证或跟踪）。这对于 `sse`（已被 MCP 规范弃用）和 `streamable_http` 传输方式受支持。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {  
                "Authorization": "Bearer YOUR_TOKEN",  
                "X-Custom-Header": "custom-value"  
            },  
        }
    }
)
tools = await client.get_tools()
agent = create_agent("openai:gpt-5.4", tools)
response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
```

#### 身份验证 (Authentication)

`langchain-mcp-adapters` 库在底层使用官方的 MCP SDK，它允许您通过实现 `httpx.Auth` 接口来提供自定义的身份验证机制。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
            "auth": auth, 
        }
    }
)
```

*   自定义身份验证实现示例
*   内置 OAuth 流程

### stdio

客户端将服务器作为子进程启动，并通过标准输入/输出进行通信。最适合本地工具和简单设置。

与 HTTP 传输不同，`stdio` 连接本质上是**有状态 (stateful)** 的：子进程在客户端连接的整个生命周期内持续存在。但是，当使用 `MultiServerMCPClient` 而没有显式会话管理时，每次工具调用仍然会创建一个新会话。有关管理持久连接，请参阅有状态会话。

```python
client = MultiServerMCPClient(
    {
        "math": {
            "transport": "stdio",
            "command": "python",
            "args": ["/path/to/math_server.py"],
        }
    }
)
```

## 有状态会话 (Stateful sessions)

默认情况下，`MultiServerMCPClient` 是**无状态 (stateless)** 的：每次工具调用都会创建一个新的 MCP 会话，执行工具，然后清理。

如果您需要控制 MCP 会话的生命周期（例如，当使用一个在工具调用之间维护上下文的有状态服务器时），您可以使用 `client.session()` 创建一个持久的 `ClientSession`。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent

client = MultiServerMCPClient({...})

# 显式创建一个会话
async with client.session("server_name") as session:  
    # 将会话传递给加载工具、资源或提示的函数
    tools = await load_mcp_tools(session)  
    agent = create_agent(
        "google_genai:gemini-3.1-pro-preview",
        tools
    )
```

## 核心功能

### Tools

Tools 允许 MCP 服务器暴露可执行函数，LLMs 可以调用这些函数来执行操作——例如查询数据库、调用 API 或与外部系统交互。LangChain 将 MCP tools 转换为 LangChain tools，使它们可以直接在任何 LangChain agent 或工作流中使用。

#### 加载 Tools

使用 `client.get_tools()` 从 MCP 服务器检索 tools 并将它们传递给您的 agent：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({...})
tools = await client.get_tools()  
agent = create_agent("claude-sonnet-4-6", tools)
```

#### 结构化内容 (Structured content)

MCP tools 除了返回人类可读的文本响应外，还可以返回结构化内容。当工具需要返回机器可解析的数据（如 JSON）以及显示给模型的文本时，这非常有用。

当 MCP tool 返回 `structuredContent` 时，适配器会将其包装在 `MCPToolArtifact` 中，并作为工具的 artifact 返回。您可以使用 `ToolMessage` 上的 `artifact` 字段来访问它。您还可以使用拦截器 (interceptors) 来自动处理或转换结构化内容。

**从 artifact 中提取结构化内容**

在调用您的 agent 后，您可以从响应中的 tool messages 中访问结构化内容：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.messages import ToolMessage

client = MultiServerMCPClient({...})
tools = await client.get_tools()
agent = create_agent("claude-sonnet-4-6", tools)

result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "Get data from the server"}]}
)

# 从 tool messages 中提取结构化内容
for message in result["messages"]:
    if isinstance(message, ToolMessage) and message.artifact:
        structured_content = message.artifact["structured_content"]
```

**通过拦截器追加结构化内容**

如果您希望结构化内容在对话历史中可见（对模型可见），您可以使用拦截器自动将结构化内容附加到工具结果中：

```python
import json

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from mcp.types import TextContent

async def append_structured_content(request: MCPToolCallRequest, handler):
    """从 artifact 中将结构化内容追加到工具消息。"""
    result = await handler(request)
    if result.structuredContent:
        result.content += [
            TextContent(type="text", text=json.dumps(result.structuredContent)),
        ]
    return result

client = MultiServerMCPClient({...}, tool_interceptors=[append_structured_content])
```

#### 多模态工具内容 (Multimodal tool content)

MCP tools 可以在其响应中返回多模态内容（图像、文本等）。当 MCP 服务器返回包含多个部分（例如文本和图像）的内容时，适配器会将它们转换为 LangChain 的标准 content blocks。您可以通过 `ToolMessage` 上的 `content_blocks` 属性访问标准化表示：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({...})
tools = await client.get_tools()
agent = create_agent("claude-sonnet-4-6", tools)

result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "Take a screenshot of the current page"}]}
)

# 从 tool messages 中访问多模态内容
for message in result["messages"]:
    if message.type == "tool":
        # Provider 原生格式的原始内容
        print(f"Raw content: {message.content}")

        # 标准化的 content blocks  
        for block in message.content_blocks:  
            if block["type"] == "text":  
                print(f"Text: {block['text']}")  
            elif block["type"] == "image":  
                print(f"Image URL: {block.get('url')}")  
                print(f"Image base64: {block.get('base64', '')[:50]}...")  
```

这使您能够以与 provider 无关的方式处理多模态工具响应，无论底层 MCP 服务器如何格式化其内容。

### Resources

Resources 允许 MCP 服务器暴露数据——例如文件、数据库记录或 API 响应——客户端可以读取这些数据。LangChain 将 MCP resources 转换为 Blob 对象，这些对象为处理文本和二进制内容提供了统一的接口。

#### 加载 Resources

使用 `client.get_resources()` 从 MCP 服务器加载 resources：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({...})

# 从服务器加载所有 resources
blobs = await client.get_resources("server_name")  

# 或者按 URI 加载特定 resources
blobs = await client.get_resources("server_name", uris=["file:///path/to/file.txt"])  

for blob in blobs:
    print(f"URI: {blob.metadata['uri']}, MIME type: {blob.mimetype}")
    print(blob.as_string())  # 对于文本内容
```

您也可以直接使用 `load_mcp_resources` 配合会话以获得更多控制：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.resources import load_mcp_resources

client = MultiServerMCPClient({...})

async with client.session("server_name") as session:
    # 加载所有 resources
    blobs = await load_mcp_resources(session)

    # 或者按 URI 加载特定 resources
    blobs = await load_mcp_resources(session, uris=["file:///path/to/file.txt"])
```

### Prompts

Prompts 允许 MCP 服务器暴露可重用的提示模板，客户端可以检索和使用这些模板。LangChain 将 MCP prompts 转换为消息，使它们易于集成到基于聊天的流程中。

#### 加载 Prompts

使用 `client.get_prompt()` 从 MCP 服务器加载 prompt：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({...})

# 按名称加载 prompt
messages = await client.get_prompt("server_name", "summarize")  

# 带参数加载 prompt
messages = await client.get_prompt(  
    "server_name",  
    "code_review",  
    arguments={"language": "python", "focus": "security"}  
)  

# 在工作流中使用 messages
for message in messages:
    print(f"{message.type}: {message.content}")
```

您也可以直接使用 `load_mcp_prompt` 配合会话以获得更多控制：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.prompts import load_mcp_prompt

client = MultiServerMCPClient({...})

async with client.session("server_name") as session:
    # 按名称加载 prompt
    messages = await load_mcp_prompt(session, "summarize")

    # 带参数加载 prompt
    messages = await load_mcp_prompt(
        session,
        "code_review",
        arguments={"language": "python", "focus": "security"}
    )
```

## 高级功能

### Tool 拦截器 (Tool interceptors)

MCP 服务器作为独立进程运行——它们无法访问 LangGraph 运行时信息，如 store、context 或 agent 状态。**拦截器 (Interceptors) 弥补了这一差距**，通过在 MCP 工具执行期间让您访问此运行时上下文。

拦截器还提供类似中间件的对工具调用的控制：您可以修改请求、实现重试、动态添加 headers，或完全短路执行。

| 部分                                                       | 描述                                                                 |
| --------------------------------------------------------- | --------------------------------------------------------------------------- |
| 访问运行时上下文   | 读取用户 ID、API 密钥、存储数据和 agent 状态                        |
| 状态更新和命令 | 使用 `Command` 更新 agent 状态或控制图流程                     |
| 编写拦截器              | 修改请求、组合拦截器和错误处理的模式                                         |

#### 访问运行时上下文

当 MCP tools 在 LangChain agent 内部（通过 `create_agent`）使用时，拦截器可以访问 `ToolRuntime` 上下文。这提供了对 tool call ID、状态、配置和存储的访问——启用了访问用户数据、持久化信息和控制 agent 行为的强大模式。

访问用户特定的配置，如在调用时传递的用户 ID、API 密钥或权限：

```python
from dataclasses import dataclass
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.agents import create_agent

@dataclass
class Context:
	user_id: str
	api_key: str

async def inject_user_context(
	request: MCPToolCallRequest,
	handler,
):
	"""将用户凭证注入 MCP 工具调用。"""
	runtime = request.runtime
	user_id = runtime.context.user_id  
	api_key = runtime.context.api_key  

	# 将用户上下文添加到工具参数中
	modified_request = request.override(
		args={**request.args, "user_id": user_id}
	)
	return await handler(modified_request)

client = MultiServerMCPClient(
	{...},
	tool_interceptors=[inject_user_context],
)
tools = await client.get_tools()
agent = create_agent("gpt-5.4", tools, context_schema=Context)

# 使用用户上下文调用
result = await agent.ainvoke(
	{"messages": [{"role": "user", "content": "Search my orders"}]},
	context={"user_id": "user_123", "api_key": "sk-..."}
)
```

有关更多上下文工程模式，请参阅上下文工程和工具。

#### 状态更新和命令

拦截器可以返回 `Command` 对象来更新 agent 状态或控制图执行流程。这对于跟踪任务进度、在 agents 之间切换或提前结束执行非常有用。

```python
from langchain.agents import AgentState, create_agent
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.messages import ToolMessage
from langgraph.types import Command

async def handle_task_completion(
    request: MCPToolCallRequest,
    handler,
):
    """标记任务完成并移交给总结 agent。"""
    result = await handler(request)

    if request.name == "submit_order":
        return Command(
            update={
                "messages": [result] if isinstance(result, ToolMessage) else [],
                "task_status": "completed",  
            },
            goto="summary_agent",  
        )

    return result
```

使用带有 `goto="__end__"` 的 `Command` 提前结束执行：

```python
async def end_on_success(
    request: MCPToolCallRequest,
    handler,
):
    """当任务被标记为完成时结束 agent 运行。"""
    result = await handler(request)

    if request.name == "mark_complete":
        return Command(
            update={"messages": [result], "status": "done"},
            goto="__end__",  
        )

    return result
```

#### 自定义拦截器

拦截器是包装工具执行的异步函数，支持请求/响应修改、重试逻辑和其他横切关注点。它们遵循“洋葱”模式，其中列表中的第一个拦截器是最外层。

**基本模式**

拦截器是一个异步函数，它接收一个请求和一个处理器。您可以在调用处理器之前修改请求，在之后修改响应，或者完全跳过处理器。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

async def logging_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """在工具执行前后记录工具调用。"""
    print(f"Calling tool: {request.name} with args: {request.args}")
    result = await handler(request)
    print(f"Tool {request.name} returned: {result}")
    return result

client = MultiServerMCPClient(
    {"math": {"transport": "stdio", "command": "python", "args": ["/path/to/server.py"]}},
    tool_interceptors=[logging_interceptor],  
)
```

**修改请求**

使用 `request.override()` 创建修改后的请求。这遵循不可变模式，保持原始请求不变。

```python
async def double_args_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """在执行前将所有数字参数加倍。"""
    modified_args = {k: v * 2 for k, v in request.args.items()}
    modified_request = request.override(args=modified_args)  
    return await handler(modified_request)

# 原始调用：add(a=2, b=3) 变为 add(a=4, b=6)
```

**在运行时修改 Headers**

拦截器可以根据请求上下文动态修改 HTTP headers：

```python
async def auth_header_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """基于被调用的工具添加身份验证 headers。"""
    token = get_token_for_tool(request.name)
    modified_request = request.override(
        headers={"Authorization": f"Bearer {token}"}  
    )
    return await handler(modified_request)
```

**组合拦截器**

多个拦截器以“洋葱”顺序组合——列表中的第一个拦截器是最外层：

```python
async def outer_interceptor(request, handler):
    print("outer: before")
    result = await handler(request)
    print("outer: after")
    return result

async def inner_interceptor(request, handler):
    print("inner: before")
    result = await handler(request)
    print("inner: after")
    return result

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[outer_interceptor, inner_interceptor],  
)

# 执行顺序：
# outer: before -> inner: before -> tool execution -> inner: after -> outer: after
```

**错误处理**

使用拦截器捕获工具执行错误并实现重试逻辑：

```python
import asyncio

async def retry_interceptor(
    request: MCPToolCallRequest,
    handler,
    max_retries: int = 3,
    delay: float = 1.0,
):
    """使用指数退避重试失败的工具调用。"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await handler(request)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)  # 指数退避
                print(f"Tool {request.name} failed (attempt {attempt + 1}), retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
    raise last_error

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[retry_interceptor],  
)
```

您还可以捕获特定错误类型并返回回退值：

```python
async def fallback_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """如果工具执行失败，返回回退值。"""
    try:
        return await handler(request)
    except TimeoutError:
        return f"Tool {request.name} timed out. Please try again later."
    except ConnectionError:
        return f"Could not connect to {request.name} service. Using cached data."
```

### 进度通知 (Progress notifications)

订阅长时间运行的工具执行的进度更新：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext

async def on_progress(
    progress: float,
    total: float | None,
    message: str | None,
    context: CallbackContext,
):
    """处理来自 MCP 服务器的进度更新。"""
    percent = (progress / total * 100) if total else progress
    tool_info = f" ({context.tool_name})" if context.tool_name else ""
    print(f"[{context.server_name}{tool_info}] Progress: {percent:.1f}% - {message}")

client = MultiServerMCPClient(
    {...},
    callbacks=Callbacks(on_progress=on_progress),  
)
```

`CallbackContext` 提供：

* `server_name`: MCP 服务器的名称
* `tool_name`: 正在执行的工具的名称（在工具调用期间可用）

### 日志记录 (Logging)

MCP 协议支持来自服务器的日志通知。使用 `Callbacks` 类订阅这些事件。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext
from mcp.types import LoggingMessageNotificationParams

async def on_logging_message(
    params: LoggingMessageNotificationParams,
    context: CallbackContext,
):
    """处理来自 MCP 服务器的日志消息。"""
    print(f"[{context.server_name}] {params.level}: {params.data}")

client = MultiServerMCPClient(
    {...},
    callbacks=Callbacks(on_logging_message=on_logging_message),  
)
```

### 征询 (Elicitation)

Elicitation 允许 MCP 服务器在工具执行期间向用户请求额外的输入。服务器无需提前要求所有输入，而是可以根据需要交互式地询问信息。

#### 服务器设置

定义一个使用 `ctx.elicit()` 通过模式请求用户输入的工具：

```python
from pydantic import BaseModel
from mcp.server.fastmcp import Context, FastMCP

server = FastMCP("Profile")

class UserDetails(BaseModel):
    email: str
    age: int

@server.tool()
async def create_profile(name: str, ctx: Context) -> str:
    """创建用户配置文件，通过征询请求详细信息。"""
    result = await ctx.elicit(  
        message=f"Please provide details for {name}'s profile:",  
        schema=UserDetails,  
    )  
    if result.action == "accept" and result.data:
        return f"Created profile for {name}: email={result.data.email}, age={result.data.age}"
    if result.action == "decline":
        return f"User declined. Created minimal profile for {name}."
    return "Profile creation cancelled."

if __name__ == "__main__":
    server.run(transport="http")
```

#### 客户端设置

通过向 `MultiServerMCPClient` 提供一个回调函数来处理 elicitation 请求：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext
from mcp.shared.context import RequestContext
from mcp.types import ElicitRequestParams, ElicitResult

async def on_elicitation(
    mcp_context: RequestContext,
    params: ElicitRequestParams,
    context: CallbackContext,
) -> ElicitResult:
    """处理来自 MCP 服务器的征询请求。"""
    # 在实际应用中，您将根据 params.message 和 params.requestedSchema 提示用户输入
    return ElicitResult(  
        action="accept",  
        content={"email": "user@example.com", "age": 25},  
    )  

client = MultiServerMCPClient(
    {
        "profile": {
            "url": "http://localhost:8000/mcp",
            "transport": "http",
        }
    },
    callbacks=Callbacks(on_elicitation=on_elicitation),  
)
```

#### 响应动作

Elicitation 回调可以返回三个动作之一：

| 动作      | 描述                                                         |
| --------- | ------------------------------------------------------------------- |
| `accept`  | 用户提供了有效输入。在 `content` 字段中包含数据。 |
| `decline` | 用户选择不提供所请求的信息。                |
| `cancel`  | 用户完全取消了操作。                              |

```python
# 接受并提供数据
ElicitResult(action="accept", content={"email": "user@example.com", "age": 25})

# 拒绝（用户不想提供信息）
ElicitResult(action="decline")

# 取消（中止操作）
ElicitResult(action="cancel")
```

## 其他资源

*   MCP 文档
*   MCP 传输文档
*   `langchain-mcp-adapters`