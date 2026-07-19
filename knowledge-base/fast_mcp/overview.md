# FastMCP 服务器

> 用于构建 MCP 应用程序的核心 FastMCP 服务器类

`FastMCP` 类是每一个 FastMCP 应用程序的核心。它充当工具、资源和提示的容器，管理与 MCP 客户端的通信，并编排整个服务器的生命周期。

## 创建服务器

最简单的形式，FastMCP 服务器只需要一个名字。其余所有配置都有合理的默认值。

```python
from fastmcp import FastMCP

mcp = FastMCP("MyServer")
```

`instructions` 帮助客户端（以及其背后的 LLM）理解您的服务器做什么以及如何有效使用它。

```python
mcp = FastMCP(
    "DataAnalysis",
    instructions="提供用于分析数值数据集的工具。请从 get_summary() 开始获取概览。",
)
```

## 组件

FastMCP 服务器向客户端公开三种组件，每种在 MCP 协议中承担不同的角色。

**Tools** 是客户端调用的函数，用于执行操作或访问外部系统。

```python
@mcp.tool
def multiply(a: float, b: float) -> float:
    """将两个数相乘。"""
    return a * b
```

**Resources** 公开客户端可读取的数据 —— 是被动的数据源，而非可调用的函数。

```python
@mcp.resource("data://config")
def get_config() -> dict:
    return {"theme": "dark", "version": "1.0"}
```

**Prompts** 是可重用的消息模板，用于引导 LLM 交互。

```python
@mcp.prompt
def analyze_data(data_points: list[float]) -> str:
    formatted_data = ", ".join(str(point) for point in data_points)
    return f"请分析这些数据点：{formatted_data}"
```

每种组件类型都有详细的文档：Tools、Resources（包括 Resource Templates）以及 Prompts。

## 运行服务器

通过调用 `mcp.run()` 启动服务器。`if __name__` 守卫确保了与将您的服务器作为子进程启动的 MCP 客户端的兼容性。

```python
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool
def greet(name: str) -> str:
    """按名字问候用户。"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

FastMCP 支持多种 transport：

*   **STDIO**（默认）：用于本地集成和 CLI 工具
*   **HTTP**：用于使用 Streamable HTTP 协议的 Web 服务
*   **SSE**：旧的 Web transport（已弃用）

```python
# 使用 HTTP transport 运行
mcp.run(transport="http", host="127.0.0.1", port=9000)
```

服务器也可以使用 FastMCP CLI 来运行。关于 transport 和部署的详细信息，请参阅运行您的服务器。

## 配置参考

`FastMCP` 构造函数接受的参数可以分为四类：identity、composition、behavior 以及 handlers 和 storage。

### Identity

这些参数控制服务器向客户端展示自己的方式。

- `name`：服务器的人类可读名称，显示在客户端应用程序和日志中
- `instructions`：如何与此服务器交互的描述。客户端会将这些指令呈现给 LLM，以帮助它们了解服务器的用途和可用功能
- `version`：服务器的版本字符串。如未提供，则默认使用 FastMCP 库的版本
- `website_url`：指向包含服务器更多信息的网站的 URL。显示在客户端应用程序中
- `icons`：服务器图标表示的列表。详情参见 Icons
- `experimental`：在 MCP `initialize` 响应中声明的任意实验性能力。用于声明跨服务器互操作约定或符合 MCP 规范 `experimental` 字段的草案扩展。键是能力名称，值是自由格式的字典。FastMCP 内置的派生能力（`tools`、`resources` 等）不受影响 —— 这只会填充 `capabilities.experimental`

### Composition

这些参数控制服务器的构建基础 —— 包括其组件、middleware、provider 和生命周期。

- `tools`：要注册到服务器的工具。当您需要以编程方式添加工具时，它是 `@mcp.tool` 装饰器的替代方式
- `auth`：用于保护基于 HTTP 的 transport 的认证提供程序。参见 Authentication 了解配置
- `middleware`：拦截并转换通过服务器的每条 MCP 消息（双向的请求、响应和通知）的中间件。用于横切关注点，如日志记录、错误处理和速率限制
- `providers`：动态提供工具、资源和提示的提供程序。provider 在请求时被查询，因此它们可以从数据库、API 或其他外部源提供组件
- `transforms`：应用于所有组件的服务器级转换。转换会修改工具、资源和提示向客户端的呈现方式 —— 例如，搜索转换会用按需发现来替换大型目录
- `lifespan`：服务器启动和停止时运行的服务器级设置与拆卸逻辑。有关可组合的生命周期，请参见 Lifespans

### Behavior

这些参数调整服务器处理请求以及与客户端通信的方式。

- `duplicate_behavior`：如何处理重复的组件注册
- `strict_input_validation`：当为 `False`（默认）时，FastMCP 使用 Pydantic 的灵活验证，会强制转换兼容的输入（例如，对于 int 参数，`"10"` → `10`）。当为 `True` 时，在调用函数之前会根据确切的 JSON Schema 验证输入，拒绝类型不匹配的情况。详情见输入验证模式
- `mask_error_details`：当为 `True` 时，会将工具/资源响应中的内部错误细节替换为通用消息，以避免向客户端泄露实现细节。默认为环境变量 `FASTMCP_MASK_ERROR_DETAILS` 的值
- `list_page_size`：列表操作（`tools/list`、`resources/list` 等）每页的最大条目数。当为 `None` 时，所有结果都在一次响应中返回。详情见分页
- `enable_tasks`：启用后台任务支持。当为 `True` 时，工具和资源可以返回 `CreateTaskResult` 以异步运行工作，而客户端则轮询结果
- `log_level`：通过 `context.log()` 发送给 MCP 客户端的消息的默认最低日志级别。设置后，低于此级别的消息将被抑制。单个客户端可以使用 MCP `logging/setLevel` 请求为每个会话覆盖此级别。可选值包括 `"debug"`、`"info"`、`"notice"`、`"warning"`、`"error"`、`"critical"`、`"alert"` 或 `"emergency"`
- `dereference_schemas`：自动解析从复杂 Pydantic 模型生成的 JSON schemas 中的 `$ref` 指针。大多数客户端需要没有 `$ref` 的平面 schema，因此通常应保持启用此选项

### Handlers and Storage

这些参数为 MCP 能力提供自定义 handler，并为会话状态提供持久化存储。

- `sampling_handler`：用于 MCP 采样请求（服务器发起的 LLM 调用）的自定义 handler。详情见 Sampling
- `sampling_handler_behavior`：当为 `"fallback"` 时，仅当不存在工具特定的 handler 时才使用采样 handler。当为 `"always"` 时，所有采样请求都使用此 handler
- `session_store`：用于会话状态的持久化键值存储，可在多个请求间保留。默认使用内存存储。如需在服务器重启后持久化，请提供自定义实现

## 基于标签的过滤

Tags 允许您对组件进行分类并有选择地公开它们。这对于为不同环境或用户类型创建不同的服务器视图非常有用。

```python
@mcp.tool(tags={"public", "utility"})
def public_tool() -> str:
    return "此工具是公开的"

@mcp.tool(tags={"internal", "admin"})
def admin_tool() -> str:
    return "此工具仅限管理员使用"
```

过滤逻辑如下：

*   **使用 `only=True` 开启**：切换到允许列表模式 —— 只公开至少带有一个匹配 tag 的组件
*   **禁用**：隐藏带有任何匹配 tag 的组件
*   **优先级**：后调用的会覆盖先调用的，因此在 `enable` 之后调用 `disable` 可以从允许列表中排除

为确保某个组件永不被公开，您可以在组件本身上设置 `enabled=False`。详情请参阅组件特定文档。

```python
# 只公开带有 "public" 标签的组件
mcp = FastMCP()
mcp.enable(tags={"public"}, only=True)

# 隐藏带有 "internal" 或 "deprecated" 标签的组件
mcp = FastMCP()
mcp.disable(tags={"internal", "deprecated"})

# 组合使用：显示管理员工具但隐藏已弃用的
mcp = FastMCP()
mcp.enable(tags={"admin"}, only=True).disable(tags={"deprecated"})
```

此过滤适用于所有组件类型（tools、resources、resource templates 和 prompts），并同时影响列表和访问。

## 自定义路由

在使用 HTTP transport 运行时，您可以使用 `@custom_route` 装饰器在 MCP 端点旁边添加自定义 Web 路由。

```python
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

mcp = FastMCP("MyServer")

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

if __name__ == "__main__":
    mcp.run(transport="http")  # 健康检查地址为 http://localhost:8000/health
```

自定义路由对于健康检查、状态端点和简单的 webhook 非常有用。对于更复杂的 Web 应用程序，可考虑将您的 MCP 服务器挂载到 FastAPI 或 Starlette 应用中。