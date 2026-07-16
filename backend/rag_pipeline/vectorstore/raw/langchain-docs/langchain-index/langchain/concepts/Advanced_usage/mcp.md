# Model Context Protocol (MCP)

> 这是 LangChain 中 **Model Context Protocol (MCP)** 的胖索引，覆盖协议适配、工具加载、资源/提示使用、传输方式、有状态会话、拦截器、进度通知、征询机制以及最佳实践。
> 阅读本文档可一次性掌握 MCP 集成的全部概念及其关联，为通过标准化协议扩展 Agent 能力提供决策支撑。

---

## 概念全景

MCP 是一个开放协议，标准化了 LLM 获取工具和上下文的方式。LangChain 通过 `langchain-mcp-adapters` 库将 MCP 服务器上定义的工具、资源和提示转换为 Agent 可直接使用的组件。

| 维度               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **协议适配**       | `MultiServerMCPClient` 连接多个 MCP 服务器，将远程工具转换为 LangChain 工具 |
| **核心功能**       | 工具（Tools）、资源（Resources）、提示（Prompts）              |
| **传输方式**       | stdio（本地子进程）、HTTP（`streamable-http`，支持自定义 headers 和认证） |
| **会话管理**       | 默认无状态（每次工具调用独立会话）；支持 `client.session()` 创建持久会话 |
| **高级控制**       | 拦截器（访问运行时上下文、修改请求/响应、重试、短路）、进度通知、日志记录、征询（Elicitation） |
| **多模态与结构化** | 工具可返回结构化内容、多模态内容；资源以 Blob 提供；提示为消息模板 |

核心决策点：**选择 stdio 还是 HTTP 传输、是否启用有状态会话、是否编写拦截器以注入上下文或实现重试、如何处理征询请求**。

---

## 1. 快速开始与配置

安装适配器并创建客户端：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({
    "math": {
        "transport": "stdio",
        "command": "python",
        "args": ["/path/to/math_server.py"],
    },
    "weather": {
        "transport": "http",
        "url": "http://localhost:8000/mcp",
    }
})
tools = await client.get_tools()
agent = create_agent("claude-sonnet-4-6", tools)
```

- `MultiServerMCPClient` 可同时管理多个服务器，每个配置一个名称和传输参数。
- 可通过 `fastmcp` 库快速编写自定义 MCP 服务器，使用 `@mcp.tool()` 装饰器定义工具。

---

## 2. 传输方式

| 传输方式 | 描述                                                         | 配置示例                                  |
| -------- | ------------------------------------------------------------ | ----------------------------------------- |
| **stdio** | 将服务器作为子进程启动，通过标准输入/输出通信；适合本地工具   | `{"transport": "stdio", "command": "python", "args": [...]}` |
| **HTTP**  | 使用 `streamable-http` 通过 HTTP 请求通信；适合远程或共享服务 | `{"transport": "http", "url": "http://localhost:8000/mcp"}` |

HTTP 传输支持：
- 自定义 `headers`（如认证令牌、追踪 ID）
- 自定义认证（通过 `httpx.Auth` 接口或内置 OAuth）

---

## 3. 有状态会话

默认情况下，每次工具调用都会创建新的 MCP 会话然后清理（无状态）。当服务器需要在工具调用之间保持上下文时（如累积状态），可创建持久会话：

```python
async with client.session("server_name") as session:
    tools = await load_mcp_tools(session)
    agent = create_agent("...", tools)
```

使用 `client.session()` 配合 `load_mcp_tools` 可完全控制会话生命周期。

---

## 4. 核心功能

### 工具 (Tools)

- **加载**：`await client.get_tools()` 将所有服务器工具转换为 LangChain 工具。
- **结构化内容**：工具可返回 `structuredContent`，存储在 `ToolMessage.artifact` 中。可通过拦截器自动追加到对话中让模型可见。
- **多模态内容**：工具响应中的图像等非文本内容自动转换为 LangChain 标准 content blocks，可通过 `ToolMessage.content_blocks` 统一访问。

### 资源 (Resources)

服务器暴露的数据（文件、数据库记录等）转换为 `Blob` 对象，提供文本和二进制访问。

```python
blobs = await client.get_resources("server_name")
# 或按 URI 过滤
blobs = await client.get_resources("server_name", uris=["file:///path/to/file.txt"])
```

### 提示 (Prompts)

服务器提供的可重用提示模板转换为消息列表，可按名称加载并传入参数：

```python
messages = await client.get_prompt("server_name", "code_review",
                                   arguments={"language": "python", "focus": "security"})
```

---

## 5. 高级功能

### 拦截器 (Interceptors)

拦截器是围绕工具执行的异步中间件，能访问 LangGraph 运行时上下文、修改请求/响应、实现重试等。

- **注入运行时上下文**：从 `ToolRuntime` 中获取 `context`、`state`、`store`，可向工具参数注入用户 ID、API 密钥等。
- **状态更新与命令**：可返回 `Command` 更新 Agent 状态或跳转到其他节点（如提前结束）。
- **请求修改与重试**：使用 `request.override()` 修改参数或 headers；捕获异常实现指数退避重试。
- **组合**：多个拦截器以“洋葱模式”按列表顺序执行（第一个是最外层）。

```python
async def inject_user_context(request: MCPToolCallRequest, handler):
    runtime = request.runtime
    modified = request.override(args={**request.args, "user_id": runtime.context.user_id})
    return await handler(modified)

client = MultiServerMCPClient({...}, tool_interceptors=[inject_user_context])
```

### 进度通知

订阅 `on_progress` 回调，接收服务器推送的进度（百分比、消息、服务器/工具名）。

### 日志记录

通过 `Callbacks(on_logging_message=...)` 接收服务器日志（级别、数据、服务器名）。

### 征询 (Elicitation)

允许 MCP 服务器在工具执行过程中通过预定义 schema 向用户请求额外输入。客户端需提供 `on_elicitation` 回调，返回 `accept`（带数据）、`decline` 或 `cancel`。

---

## 6. 关键约束与最佳实践

- **默认无状态**：若服务器需要维持上下文（如累积计数器），必须使用 `client.session()` 创建持久会话。
- **拦截器顺序**：列表顺序即为洋葱层次，注意先执行的拦截器会包裹后执行的。
- **安全**：通过拦截器注入权限、过滤参数；HTTP 传输时使用自定义 headers 传递令牌而非硬编码。
- **结构化/多模态内容处理**：模型默认看不到 `artifact` 中的结构化内容，若要展示给模型，需通过拦截器追加到 `content` 中。
- **征询交互**：需设计好用户交互流程；`accept` 时必须提供符合 schema 的数据。
- **工具名称冲突**：多服务器加载工具时，注意工具名可能重复，可通过命名或前缀区分。

---

## 7. 与全局概念的关联

- **工具 (Tools)**：MCP 工具被转换为 LangChain 工具，可像普通工具一样绑定到模型、参与 Agent 循环。
- **上下文工程 (Context Engineering)**：拦截器能从 Runtime Context 注入用户信息、偏好，这正是上下文工程中工具上下文的体现。
- **中间件 (Middleware)**：拦截器的设计思想与 Agent 中间件相似，允许在工具调用前后插入逻辑。
- **护栏 (Guardrails)**：可通过拦截器实现权限检查、输入过滤等安全机制。
- **流式传输 (Streaming)**：进度通知可与自定义流式更新结合，提供实时反馈。
- **记忆 (Memory)**：拦截器可读写 Store，将工具结果持久化到长期记忆。
- **模型 (Models)**：MCP 提示可加载为模型消息，动态构建系统指令。

---

## 链接原文

### 语义检索（聚焦查询）

- `MultiServerMCPClient get_tools` → 快速开始
- `stdio HTTP transport headers` → 传输方式配置
- `有状态会话 client.session load_mcp_tools` → 会话管理
- `结构化内容 structuredContent artifact` → 工具结构化输出
- `多模态 content_blocks image` → 工具多模态响应
- `拦截器 inject_user_context 重试` → 自定义拦截器
- `on_elicitation ElicitResult accept decline` → 征询机制
- `load_mcp_resources load_mcp_prompt` → 资源与提示
- `fastmcp 自定义服务器` → 服务器编写

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 快速开始`、`### Tools`、`### 拦截器`、`### 征询`），可用 `read_file` 精确定位对应章节。