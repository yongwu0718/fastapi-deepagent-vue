## 模块概览
**Planning and task management middleware for agents.**  
提供待办事项（Todo）管理中间件，允许 Agent 在复杂多步任务中创建和维护结构化任务列表，跟踪进度并向用户展示任务完成状态。

---
## 类型定义

### `Todo`
待办事项条目，包含内容和状态。

```python
class Todo(TypedDict):
    content: str
    status: Literal["pending", "in_progress", "completed"]
```

**字段**
- `content` (`str`)：待办事项的内容/描述。
- `status` (`Literal["pending", "in_progress", "completed"]`)：当前状态。
  - `"pending"`：未开始
  - `"in_progress"`：进行中
  - `"completed"`：已完成

---

### `PlanningState` (泛型类)
Todo 中间件使用的状态模式，继承自 `AgentState[ResponseT]`。

```python
class PlanningState(AgentState[ResponseT]):
    todos: Annotated[NotRequired[list[Todo]], OmitFromInput]
```

**类型参数**
- `ResponseT`：结构化响应的类型，默认为 `Any`。

**状态字段**
- `todos` (`list[Todo] | None`)：任务进度跟踪列表。注解 `NotRequired` 表示该字段可选；`OmitFromInput` 表示不应由用户输入提供。

---

### `WriteTodosInput`
`write_todos` 工具的输入模型。

```python
class WriteTodosInput(BaseModel):
    todos: list[Todo]
```

**字段**
- `todos` (`list[Todo]`)：要写入的待办事项列表。

---

## 常量

### `WRITE_TODOS_TOOL_DESCRIPTION`
`write_todos` 工具的详细描述文本，指导 Agent 何时及如何使用该工具。内容涵盖：
- 适用场景（复杂多步任务、用户明确要求、用户提供多个任务、可能需要修订的计划）
- 不适用场景（简单单步任务、纯对话信息）
- 任务状态管理规则（`pending`、`in_progress`、`completed` 的转换）
- 任务分解和完成要求

---

### `WRITE_TODOS_SYSTEM_PROMPT`
注入到系统消息中的提示文本，进一步指导 Agent 合理使用 `write_todos` 工具，强调：
- 仅对复杂目标使用，简单请求应直接完成
- 完成步骤后立即标记，不要批量标记
- `write_todos` 绝不能并行调用多次

---

## 工具函数

### `write_todos`
以 LangChain `@tool` 装饰器定义的公开工具，用于创建和管理当前工作会话的结构化任务列表。

```python
@tool(description=WRITE_TODOS_TOOL_DESCRIPTION)
def write_todos(
    todos: list[Todo],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command[Any]
```

**参数**
- `todos` (`list[Todo]`)：完整的待办事项列表（替换原有列表）。
- `tool_call_id` (`str`)：注入的工具调用 ID，用于生成对应的 `ToolMessage`。

**返回值**
- `Command[Any]`：更新状态的命令，将 `todos` 写入状态，并添加一条确认消息。

**行为**
替换状态中的整个 `todos` 列表，并返回一条 `ToolMessage`，通知用户列表已更新。

---

## 中间件类

### `TodoListMiddleware`
为 Agent 提供待办列表管理能力的中间件。

**继承**
`AgentMiddleware[PlanningState[ResponseT], ContextT, ResponseT]`

```python
class TodoListMiddleware(AgentMiddleware[PlanningState[ResponseT], ContextT, ResponseT]):
    state_schema = PlanningState

    def __init__(
        self,
        *,
        system_prompt: str = WRITE_TODOS_SYSTEM_PROMPT,
        tool_description: str = WRITE_TODOS_TOOL_DESCRIPTION,
    ) -> None
```

**构造参数**
- `system_prompt` (`str`)：自定义系统提示，用于指导 Agent 使用 todo 工具。默认为 `WRITE_TODOS_SYSTEM_PROMPT`。
- `tool_description` (`str`)：`write_todos` 工具的自定义描述。默认为 `WRITE_TODOS_TOOL_DESCRIPTION`。

**公开属性**
- `state_schema`：状态模式类 `PlanningState`。
- `system_prompt`、`tool_description`：构造时传入的提示文本。
- `tools`：包含 `write_todos` 的 `StructuredTool` 列表。

---

#### `wrap_model_call`
同步包装模型调用，将 todo 系统提示注入到系统消息中。

```python
def wrap_model_call(
    self,
    request: ModelRequest[ContextT],
    handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]]
) -> ModelResponse[ResponseT] | AIMessage
```

**参数**
- `request` (`ModelRequest[ContextT]`)：模型请求，包含状态和运行时。
- `handler` (`Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]]`)：执行模型请求并返回响应的回调。

**返回值**
- `ModelResponse[ResponseT]` 或 `AIMessage`：模型调用的结果。

**行为**
在请求的系统消息末尾追加 todo 系统提示文本，然后调用原始处理器。

---

#### `awrap_model_call`
异步包装模型调用，与 `wrap_model_call` 功能相同。

```python
async def awrap_model_call(
    self,
    request: ModelRequest[ContextT],
    handler: Callable[[ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]]
) -> ModelResponse[ResponseT] | AIMessage
```

**参数**
- `request`：同 `wrap_model_call`。
- `handler`：异步回调，返回 `ModelResponse[ResponseT]` 的 Awaitable。

**返回值**
- 异步模型调用结果。

---

#### `after_model`
模型生成消息后调用，检测是否出现多个并行的 `write_todos` 工具调用，若存在则返回错误。

```python
def after_model(
    self,
    state: PlanningState[ResponseT],
    runtime: Runtime[ContextT]
) -> dict[str, Any] | None
```

**参数**
- `state` (`PlanningState[ResponseT]`)：当前 Agent 状态（包含消息）。
- `runtime` (`Runtime[ContextT]`)：LangGraph 运行时。

**返回值**
- 若最后一条 AI 消息中包含多个 `write_todos` 工具调用，则返回 `{"messages": [ToolMessage, ...]}` 形式的错误消息字典；否则返回 `None`（正常执行）。

**行为**
由于 `write_todos` 每次调用会完整替换 todo 列表，并行调用会造成歧义。此方法阻止此类冲突，为每个违规调用生成错误 `ToolMessage`。

---

#### `aafter_model`
异步版本，行为与 `after_model` 一致。

```python
async def aafter_model(
    self,
    state: PlanningState[ResponseT],
    runtime: Runtime[ContextT]
) -> dict[str, Any] | None
```

**参数与返回值**
同 `after_model`。

**实现**
直接委托给 `self.after_model(state, runtime)`。

---

## 示例用法

```python
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents import create_agent

agent = create_agent("openai:gpt-4o", middleware=[TodoListMiddleware()])
result = await agent.invoke({"messages": [HumanMessage("Help me refactor my codebase")]})
print(result["todos"])  # 包含进度跟踪的 Todo 列表
```