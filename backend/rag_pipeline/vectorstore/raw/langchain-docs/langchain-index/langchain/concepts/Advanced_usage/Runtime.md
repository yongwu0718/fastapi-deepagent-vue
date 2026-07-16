# Runtime

> 这是 LangChain / LangGraph 中 **Runtime** 的胖索引，覆盖运行时依赖注入、Context、Store、Stream Writer 及 Execution/Server 信息的访问方法，以及在工具与中间件中的实际应用。
> 阅读本文档可一次性掌握 Runtime 的全部概念及其关联，为构建可测试、可配置且上下文感知的 Agent 提供决策支撑。

---

## 概念全景

Runtime 是 LangGraph 为 Agent 提供的**依赖注入容器**，它在每次调用时携带当前会话的静态配置（Context）、长期记忆（Store）、流式写入器（Stream Writer）、执行标识（Execution Info）以及服务器元数据（Server Info）。通过将数据与逻辑解耦，Runtime 让工具和中间件无需依赖全局状态即可访问所需资源。

| 组件              | 描述                                                                 | 访问方式（工具）                 | 访问方式（中间件）                               |
| ----------------- | -------------------------------------------------------------------- | -------------------------------- | ------------------------------------------------ |
| **Context**       | 会话级静态配置（用户 ID、API 密钥、环境等），通过 `context_schema` 定义 | `runtime.context`                | `request.runtime.context` / `runtime.context`    |
| **Store**         | 跨会话长期记忆，持久化 JSON 文档                                     | `runtime.store`                  | `runtime.store`                                  |
| **Stream Writer** | 向客户端推送自定义流式事件                                           | `runtime.stream_writer`          | 不常用；可通过 `get_stream_writer` 在节点内使用  |
| **Execution Info**| 当前线程 ID、运行 ID、重试次数                                       | `runtime.execution_info`         | `runtime.execution_info`                         |
| **Server Info**   | LangGraph Server 上的 assistant ID、graph ID、已认证用户（本地为 None）| `runtime.server_info`            | `runtime.server_info`                            |

核心决策点：**如何设计 `context_schema` 以涵盖所有必要的会话级配置、哪些数据适合放入 Context 而非 Store、是否需要访问执行或服务器元数据**。

---

## 1. 定义与注入

通过 `create_agent` 的 `context_schema` 定义 Context 结构，并在调用时传入具体实例：

```python
from dataclasses import dataclass

@dataclass
class Context:
    user_name: str

agent = create_agent("gpt-5-nano", tools=[...], context_schema=Context)
agent.invoke({"messages": [...]}, context=Context(user_name="John Smith"))
```

Context 在每次 `invoke` 时提供，同一个 Agent 可接受不同 Context 实例，便于多租户复用。

---

## 2. 在工具中访问

工具通过 `ToolRuntime` 参数透明注入 Runtime（该参数对模型隐藏）：

```python
@tool
def fetch_preferences(runtime: ToolRuntime[Context]) -> str:
    user_id = runtime.context.user_id
    # 读取长期记忆
    if runtime.store:
        mem = runtime.store.get(("users",), user_id)
        if mem:
            return mem.value["preferences"]
    return "No preferences found"
```

可访问的内容：
- `runtime.context`：获取注入的 Context 字段
- `runtime.store`：读写 Store（可能为 None，需检查）
- `runtime.stream_writer`：推送自定义事件
- `runtime.execution_info.thread_id / run_id / node_attempt`：获取执行标识
- `runtime.server_info.assistant_id / graph_id / user.identity`：获取服务器元数据（非 Server 环境下为 `None`）

**注意**：`execution_info` 和 `server_info` 需要 `deepagents>=0.5.0` 或 `langgraph>=1.1.5`。

---

## 3. 在中间件中访问

中间件的不同钩子通过各自方式获取 Runtime：

- **`@dynamic_prompt`**：通过 `request.runtime.context` 读取 Context，动态构建系统提示。
- **`@before_model` / `@after_model`**：直接在函数签名中接收 `runtime: Runtime[Context]` 参数。
- **`wrap_model_call` 等包装器**：`request.runtime` 提供完整 Runtime 对象。

```python
@dynamic_prompt
def prompt(request: ModelRequest) -> str:
    return f"Address the user as {request.runtime.context.user_name}"

@before_model
def log(state: AgentState, runtime: Runtime[Context]) -> dict | None:
    print(f"User: {runtime.context.user_name}, Thread: {runtime.execution_info.thread_id}")
    return None
```

同样可以访问 `execution_info` 和 `server_info`，后者可用于在 LangGraph Server 上实现认证守卫。

---

## 4. 关键约束与最佳实践

- **Context 放置静态、会话级信息**：如用户 ID、角色、API 密钥、功能标志。避免存放动态消息或随时间变化的状态（这些应放在 State 中）。
- **Store 用于跨会话持久化**：偏好、长期知识等。需检查 `runtime.store` 是否为 None（取决于是否配置了 Store）。
- **依赖注入提升可测试性**：测试工具时可直接传入模拟的 `ToolRuntime`，无需启动完整图。
- **类型安全**：使用泛型 `ToolRuntime[YourContext]` 和 `Runtime[YourContext]` 以获得精确的类型推断。
- **Server Info 为空处理**：本地开发时 `server_info` 为 `None`，代码中应做防御性判断。

---

## 5. 与全局概念的关联

- **上下文工程 (Context Engineering)**：Runtime 是上下文工程实现的基础设施。Context 提供静态配置，Store 提供长期记忆，两者通过 Runtime 注入到提示、消息、工具和模型选择的全过程。
- **工具 (Tools)**：`ToolRuntime` 是工具访问所有运行时资源的入口，是工具具备上下文感知、记忆读写、流式推送能力的前提。
- **中间件 (Middleware)**：Runtime 使中间件能够根据用户身份、配置等动态控制 Agent 行为，如动态提示、权限检查、日志记录。
- **长期记忆 (Long-term memory)**：Store 通过 Runtime 暴露给工具和中间件，是实现记忆功能的核心通道。
- **短期记忆 (Short-term memory)**：State 不在 Runtime 中，而是通过 `state` 参数直接在中间件钩子中访问；工具中通过 `runtime.state` 桥接。
- **流式传输 (Streaming)**：`runtime.stream_writer` 通过 `custom` 流式模式推送自定义事件，与 `stream_events` / `stream` 配合使用。
- **MCP**：在 MCP 拦截器中，`request.runtime` 同样可用，用于注入用户凭证、读取 Store 等，连接外部工具与 Agent 内部上下文。

---

## 链接原文

### 语义检索（聚焦查询）

- `context_schema create_agent invoke` → 定义与注入
- `ToolRuntime context store stream_writer` → 工具中访问
- `execution_info server_info thread_id` → 执行与服务器元数据
- `dynamic_prompt ModelRequest runtime.context` → 中间件中访问
- `before_model Runtime auth_gate` → 中间件认证示例

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 概述`、`### 在工具内部`、`### 在中间件内部`），可用 `read_file` 精确展开对应章节。