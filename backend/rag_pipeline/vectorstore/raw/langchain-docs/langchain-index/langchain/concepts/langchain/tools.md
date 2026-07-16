# Tools

> 这是 Deep Agents / LangChain 中 **工具（Tools）** 的胖索引，覆盖工具创建、运行时上下文访问、`ToolNode` 执行与路由、错误处理及最佳实践。
> 阅读本文档可一次性掌握工具领域的全部概念及其关联，为扩展 agent 能力提供决策支撑。

---
## 概念全景

工具是 agent 连接外部世界的桥梁——执行代码、查询数据库、调用 API。每个工具都是一个有明确输入和输出的可调用函数，模型根据对话上下文决定何时调用以及传递什么参数。

| 环节               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **工具定义**       | 用 `@tool` 装饰器将普通函数转化为工具，类型提示即 schema，文档字符串即描述 |
| **高级输入**       | 通过 Pydantic 模型或 JSON Schema 定义复杂参数、校验和默认值 |
| **运行时上下文**   | 通过 `ToolRuntime` 透明注入，可访问 state、context、store、stream_writer 等 |
| **返回值类型**     | 字符串（人类可读）、对象（结构化数据）、`Command`（更新状态） |
| **执行节点**       | `ToolNode` 处理并行工具调用、错误捕获和结果返回               |
| **预置工具**       | 网络搜索、代码解释、数据库等开箱即用工具                     |

核心决策点：**工具输入的严格性、是否需要读写状态或长期记忆、返回值是否改变 graph 状态、错误时是中断还是向模型反馈**，共同决定了 agent 的鲁棒性和可维护性。

---
## 1. 创建工具

### 基本定义

```python
from langchain.tools import tool

@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the customer database for records matching the query."""
    return f"Found {limit} results for '{query}'"
```

- 函数签名中的类型提示自动成为工具输入 schema。
- 文档字符串自动成为工具描述（帮助模型判断何时调用）。
- 工具名默认使用函数名（推荐 `snake_case`，避免空格和特殊字符以保证跨 provider 兼容）。

### 自定义属性

```python
@tool("web_search")                     # 自定义名称
def search(query: str) -> str:
    ...

@tool("calculator", description="...")  # 自定义描述
def calc(expression: str) -> str:
    ...
```

### 高级 schema（Pydantic / JSON Schema）

适用于有校验、默认值、枚举等复杂输入的场景：

```python
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    location: str = Field(description="City name or coordinates")
    units: Literal["celsius", "fahrenheit"] = Field(default="celsius")

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius") -> str:
    ...
```

也可以直接传入 JSON Schema 字典。

### 保留参数名

不可作为工具参数使用的名称：`config`（保留给 `RunnableConfig`）和 `runtime`（保留给 `ToolRuntime`）。要获取运行时信息，请使用 `ToolRuntime` 参数注入。

---
## 2. 访问上下文（ToolRuntime）

通过 `ToolRuntime` 参数，工具可以无感地访问 agent 的运行时信息——该参数对模型完全隐藏，不出现在工具 schema 中。

| 组件              | 用途                                                     | 关键方法/属性                    |
| ----------------- | -------------------------------------------------------- | -------------------------------- |
| **State**         | 当前对话的短期记忆（消息历史、自定义字段）                | `runtime.state["messages"]`      |
| **Context**       | 不可变配置（用户 ID、会话信息）                           | `runtime.context.user_id`        |
| **Store**         | 跨会话长期记忆（持久化）                                  | `runtime.store.get(...)`         |
| **Stream Writer** | 实时推送执行进度                                         | `runtime.stream_writer("...")`   |
| **Execution Info**| 当前 thread ID、run ID、重试次数                          | `runtime.execution_info.thread_id` |
| **Server Info**   | LangGraph Server 上的 assistant ID、graph ID、用户身份     | `runtime.server_info.assistant_id` |

### 访问 state

```python
@tool
def get_last_user_message(runtime: ToolRuntime) -> str:
    messages = runtime.state["messages"]
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return "No user messages found"
```

### 更新 state（返回 Command）

需要改变 state 字段时，返回 `Command` 并附带可选的 `ToolMessage`（让模型看到操作结果）：

```python
from langgraph.types import Command
from langchain.messages import ToolMessage

@tool
def set_user_name(new_name: str, runtime: ToolRuntime) -> Command:
    return Command(
        update={
            "user_name": new_name,
            "messages": [
                ToolMessage(content=f"Name set to {new_name}.", tool_call_id=runtime.tool_call_id)
            ]
        }
    )
```

> 若多个并行工具可能更新同一 state 字段，需为该字段定义 reducer，避免冲突。

### 访问 context（用户/会话配置）

```python
@dataclass
class UserContext:
    user_id: str

@tool
def get_account_info(runtime: ToolRuntime[UserContext]) -> str:
    return f"Balance for {runtime.context.user_id} ..."
```

### 访问 store（长期记忆）

```python
@tool
def save_preference(key: str, value: str, runtime: ToolRuntime) -> str:
    runtime.store.put(("preferences",), key, value)
    return "Saved"
```

生产环境应使用持久化 store（如 `PostgresStore`）。

### 流式进度推送

```python
@tool
def long_task(runtime: ToolRuntime) -> str:
    runtime.stream_writer("Fetching data...")
    # ... work ...
    return "Done"
```

---
## 3. ToolNode

`ToolNode` 是 LangGraph 中执行工具的预构建节点，自动处理并行调用、错误和状态注入。

### 基本用法

```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode([search, calculator])
# 在 graph 中：builder.add_node("tools", tool_node)
```

### 工具返回值选项

| 返回类型    | 说明                                                         |
| ----------- | ------------------------------------------------------------ |
| `str`       | 人类可读文本，自动包装为 `ToolMessage`，模型看到后继续推理   |
| `object`    | 结构化数据（如 `dict`），模型可细粒度利用其字段               |
| `Command`   | 更新 graph 状态，可附带 `ToolMessage` 向模型反馈操作结果     |

### 错误处理

```python
# 默认：捕获调用错误，抛出执行错误
ToolNode(tools)

# 所有错误都反馈给模型（消息为默认格式）
ToolNode(tools, handle_tool_errors=True)

# 自定义错误消息
ToolNode(tools, handle_tool_errors="Something went wrong, please try again.")

# 自定义错误处理函数
def handle_error(e: ValueError) -> str:
    return f"Invalid input: {e}"
ToolNode(tools, handle_tool_errors=handle_error)

# 仅捕获特定异常
ToolNode(tools, handle_tool_errors=(ValueError, TypeError))
```

### 条件路由

配合 `tools_condition`，根据模型是否发起工具调用自动路由：

```python
from langgraph.prebuilt import tools_condition

builder.add_conditional_edges("llm", tools_condition)  # → "tools" 或 END
```

### 状态注入

`ToolNode` 自动向工具注入 `ToolRuntime`，工具无需特殊处理即可访问 state。

---

## 4. 预置工具

LangChain 提供大量开箱即用的工具（网络搜索、代码解释、数据库查询等），直接集成即可。完整列表见 tools and toolkits integration 页面。

---
## 5. 服务端工具使用

某些模型（如 OpenAI）内置了服务端工具（网页搜索、代码解释器），由 provider 执行，无需你定义实现。使用时只需绑定工具，模型返回的 `content_blocks` 会包含 `server_tool_call` 和 `server_tool_result`。详情参考对应 provider 的文档和 Tool calling 章节。

---

## 6. 关键约束与最佳实践

### 定义阶段

- **类型提示不可省略**，否则工具 schema 为空。
- 工具名用 `snake_case`，无空格，以兼容所有 provider。
- 复杂输入用 Pydantic 模型，利用 `Field(description=...)` 为模型提供清晰指导。
- 文档字符串应简明扼要，只描述工具做什么和何时使用。

### 运行时上下文

- 使用 `ToolRuntime` 获取 state/context/store，不要自定义 `config` 或 `runtime` 参数。
- 需要更新 state 时，务必返回 `Command`；若希望模型知晓操作结果，在 `Command` 中附带 `ToolMessage`，并传入 `runtime.tool_call_id`。
- 并行工具可能并发写入同一字段时，为该字段声明 reducer。

### 执行与错误处理

- 使用 `ToolNode` 而非手动循环以利用并行执行和内置错误处理。
- 根据业务需求选择错误策略：向模型暴露错误信息使其自我纠正（`handle_tool_errors=True`），或让流程中断。
- 对长时间运行的任务，使用 `runtime.stream_writer` 推送进度，避免前端无响应。

### 安全

- 避免工具执行任意代码或未校验的 SQL，防止注入。
- 对写入 store 或文件系统的工具，结合权限策略限制路径和操作。

---
## 7. 与全局概念的关联

- **模型 (Models)**：工具由模型通过 `bind_tools()` 绑定，模型决定调用时机和参数；模型的 tool calling 能力是工具可用的前提。
- **后端 (Backends)**：文件系统工具（`read_file`、`write_file` 等）本质是内置工具，通过可插拔后端执行；自定义后端实现与工具的模式设计思路一致。
- **记忆 (Memory)**：`Store` 通过 `ToolRuntime` 暴露给工具，实现长期记忆的读写；短期记忆则来自 `state["messages"]`。
- **权限 (Permissions)**：文件系统权限在工具调用后端之前评估；工具本身不直接处理权限，但自定义工具可内嵌检查逻辑。
- **上下文压缩 (Context Compression)**：工具返回的大段内容可能触发压缩；`ToolRuntime` 中的 state 和 store 帮助决定保留哪些信息。
- **安全执行**：提供沙箱后端的 `execute` 工具及服务端工具，均涉及代码/命令执行，需要独立的安全策略。

---
## 链接原文

### 语义检索（聚焦查询）

使用以下关键词组合可精准命中原始文档中的对应章节：

- `@tool 装饰器 类型提示` → 基本工具定义
- `args_schema Pydantic BaseModel` → 高级输入模式
- `ToolRuntime state context store` → 运行时上下文访问
- `返回 Command ToolMessage update` → 更新状态的返回值
- `ToolNode handle_tool_errors` → 错误处理配置
- `tools_condition 路由 ToolNode` → LangGraph 条件路由
- `服务端工具 server_tool_call` → 服务端工具使用
- `预置工具 toolkits integration` → 开箱即用工具列表

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 创建 tools`、`### 访问上下文`、`### ToolNode`），可用 `read_file` 精确展开对应章节。