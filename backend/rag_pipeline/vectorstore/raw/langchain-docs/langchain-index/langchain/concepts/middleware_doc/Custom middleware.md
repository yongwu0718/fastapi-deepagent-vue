# 自定义中间件 (Custom middleware)

通过实现在 agent 执行流程特定节点上运行的钩子 (hooks) 来构建自定义中间件。

## Hooks
中间件提供两种风格的 hooks 来拦截 agent 的执行：在特定的执行点按顺序运行。围绕每个模型或工具调用运行。

### 节点风格 hooks
在特定的执行点按顺序运行。用于日志记录、验证和状态更新。选择您的中间件需要的钩子。您可以在节点风格 hooks 和包装风格 hooks 之间进行选择。

**节点风格 hooks** 在特定的执行点运行：

| Hook           | 运行时机                                |
| -------------- | ------------------------------------------- |
| `before_agent` | agent 启动之前（每次调用一次）   |
| `before_model` | 每次模型调用之前                      |
| `after_model`  | 每次模型响应之后                   |
| `after_agent`  | agent 完成之后（每次调用一次） |

**包装风格 hooks** 围绕每次调用运行，让您控制执行过程：

| Hook              | 运行时机           |
| ----------------- | ---------------------- |
| `wrap_model_call` | 围绕每次模型调用 |
| `wrap_tool_call`  | 围绕每次工具调用  |

**示例：**
使用装饰器实现节点风格 hooks：
```python
from langchain.agents.middleware import before_model, after_model, AgentState
from langchain.messages import AIMessage
from langgraph.runtime import Runtime
from typing import Any

@before_model(can_jump_to=["end"])
def check_message_limit(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
	if len(state["messages"]) >= 50:
		return {
			"messages": [AIMessage("Conversation limit reached.")],
			"jump_to": "end"
		}
	return None

@after_model
def log_response(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
	print(f"Model returned: {state['messages'][-1].content}")
	return None
```
使用 `AgentMiddleware` 实现节点风格 hooks：
```python
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain.messages import AIMessage
from langgraph.runtime import Runtime
from typing import Any

class MessageLimitMiddleware(AgentMiddleware):
	def __init__(self, max_messages: int = 50):
		super().__init__()
		self.max_messages = max_messages

	@hook_config(can_jump_to=["end"])
	def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
		if len(state["messages"]) >= self.max_messages:
			return {
				"messages": [AIMessage("Conversation limit reached.")],
				"jump_to": "end"
			}
		return None

	def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
		print(f"Model returned: {state['messages'][-1].content}")
		return None
```

### 包装风格 hooks
拦截执行并控制何时调用处理器。用于重试、缓存和转换。您可以决定处理器是被调用零次（短路）、一次（正常流程）还是多次（重试逻辑）。

**可用 hooks：**

- `wrap_model_call` - 围绕每次模型调用
- `wrap_tool_call` - 围绕每次工具调用

**示例：**
使用装饰器实现包装风格 hooks：
```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def retry_model(
	request: ModelRequest,
	handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
	for attempt in range(3):
		try:
			return handler(request)
		except Exception as e:
			if attempt == 2:
				raise
			print(f"Retry {attempt + 1}/3 after error: {e}")
```
使用 `AgentMiddleware` 实现包装风格 hooks：
```python
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from typing import Callable

class RetryMiddleware(AgentMiddleware):
	def __init__(self, max_retries: int = 3):
		super().__init__()
		self.max_retries = max_retries

	def wrap_model_call(
		self,
		request: ModelRequest,
		handler: Callable[[ModelRequest], ModelResponse],
	) -> ModelResponse:
		for attempt in range(self.max_retries):
			try:
				return handler(request)
			except Exception as e:
				if attempt == self.max_retries - 1:
					raise
				print(f"Retry {attempt + 1}/{self.max_retries} after error: {e}")
```

## 状态更新

节点风格和包装风格的 hooks 都可以更新 agent 状态。机制有所不同：

- **节点风格 hooks** (`before_agent`、`before_model`、`after_model`、`after_agent`)：直接返回一个字典。该字典使用图的 reducer 应用到 agent 状态。
- **包装风格 hooks** (`wrap_model_call`、`wrap_tool_call`)：对于模型调用，返回带有 `Command` 的 `ExtendedModelResponse`，以便在模型响应旁边注入状态更新。对于工具调用，直接返回 `Command`。**当您需要根据在模型或工具调用期间运行的逻辑（例如总结触发点、使用元数据或从请求或响应计算的自定义字段）来跟踪或更新状态时，请使用这些 hooks。**

### 节点风格 hooks

从节点风格 hook 返回一个字典，以将更新合并到 agent 状态中。字典的键映射到状态字段。

```python
from langchain.agents.middleware import after_model, AgentState
from langgraph.runtime import Runtime
from typing import Any
from typing_extensions import NotRequired

class TrackingState(AgentState):
    model_call_count: NotRequired[int]

@after_model(state_schema=TrackingState)
def increment_after_model(state: TrackingState, runtime: Runtime) -> dict[str, Any] | None:
    return {"model_call_count": state.get("model_call_count", 0) + 1}
```

### 包装风格 hooks

从 `wrap_model_call` 返回带有 `Command` 的 `ExtendedModelResponse`，以从模型调用层注入状态更新：

```python
from typing import Callable
from langchain.agents.middleware import (
    wrap_model_call,
    ModelRequest,
    ModelResponse,
    AgentState,
    ExtendedModelResponse
)
from langgraph.types import Command
from typing_extensions import NotRequired

class UsageTrackingState(AgentState):
    """具有 token 使用跟踪的 Agent 状态。"""

    last_model_call_tokens: NotRequired[int]

@wrap_model_call(state_schema=UsageTrackingState)
def track_usage(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ExtendedModelResponse:
    response = handler(request)
    return ExtendedModelResponse(
        model_response=response,
        command=Command(update={"last_model_call_tokens": 150}),
    )
```

`Command` 通过图的 reducer 流动，因此更新被正确应用，并且消息是累加的，而不是替换现有状态。

#### 与多个中间件组合使用

当多个中间件层返回 `ExtendedModelResponse` 时，它们的 Command 会组合：

- **Commands 通过 reducers 应用：** 每个 `Command` 成为一个单独的状态更新。对于消息，这意味着它们是累加的。
- **冲突时外层获胜：** 对于非 reducer 状态字段，commands 先内层后外层应用。在最外层中间件的值在冲突键上具有优先权。
- **重试安全：** 如果外部中间件实现了可能导致再次多次调用 `handler()` 的逻辑（例如重试逻辑），则来自早期调用的 commands 将被丢弃。

```python
from typing import Annotated, Callable

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ExtendedModelResponse,
    ModelRequest,
    ModelResponse,
)
from langchain.messages import SystemMessage
from langgraph.types import Command
from typing_extensions import NotRequired

def _last_wins(_a: str, b: str) -> str:
    """Reducer: 最后写入者获胜（外层覆盖内层）。"""
    return b

class CustomMiddlewareState(AgentState):
    """Agent 状态：trace_layer 使用 last-wins（外层获胜），messages 使用累加 reducer。"""

    # 非 reducer 字段使用 last-wins：两个中间件都写入；最外层的值获胜
    trace_layer: NotRequired[Annotated[str, _last_wins]]

class OuterMiddleware(AgentMiddleware):
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ExtendedModelResponse:
        response = handler(request)
        return ExtendedModelResponse(
            model_response=response,
            command=Command(update={
                "trace_layer": "outer",
                "messages": [SystemMessage(content="[Outer ran]")],
            }),
        )

class InnerMiddleware(AgentMiddleware):
    """添加 trace_layer 和 message。Outer 添加到相同的键；trace_layer：外层获胜，messages：累加。"""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ):
        response = handler(request)
        return ExtendedModelResponse(
            model_response=response,
            command=Command(update={
                "trace_layer": "inner",
                "messages": [SystemMessage(content="[Inner ran]")],
            }),
        )
```

## 创建中间件
### 基于装饰器的中间件

对于单钩子中间件快速简单。使用装饰器包装单个函数。

**可用装饰器：**

**节点风格：**
- `@before_agent` - 在 agent 启动前运行（每次调用一次）
- `@before_model` - 在每次模型调用前运行
- `@after_model` - 在每次模型响应后运行
- `@after_agent` - 在 agent 完成后运行（每次调用一次）

**包装风格：**
- `@wrap_model_call` - 使用自定义逻辑包装每次模型调用
- `@wrap_tool_call` - 使用自定义逻辑包装每次工具调用

**便捷性：**
- `@dynamic_prompt` - 生成动态系统提示

**示例：**

```python
from langchain.agents.middleware import (
    before_model,
    wrap_model_call,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.agents import create_agent
from langgraph.runtime import Runtime
from typing import Any, Callable

@before_model
def log_before_model(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    print(f"About to call model with {len(state['messages'])} messages")
    return None

@wrap_model_call
def retry_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    for attempt in range(3):
        try:
            return handler(request)
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Retry {attempt + 1}/3 after error: {e}")

agent = create_agent(
    model="gpt-5.4",
    middleware=[log_before_model, retry_model],
    tools=[...],
)
```

**何时使用装饰器：**

- 只需要单个钩子
- 没有复杂的配置
- 快速原型设计

### 基于类的中间件

对于具有多个钩子或配置的复杂中间件更强大。当您需要为同一个钩子定义同步和异步实现，或者想要在单个中间件中组合多个钩子时，请使用类。

**示例：**

```python
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime
from typing import Any, Callable

class LoggingMiddleware(AgentMiddleware):
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        print(f"About to call model with {len(state['messages'])} messages")
        return None

    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        print(f"Model returned: {state['messages'][-1].content}")
        return None

    async def abefore_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        # before_model 的异步版本
        return None

    async def aafter_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        # after_model 的异步版本
        print(f"Model returned: {state['messages'][-1].content}")
        return None

agent = create_agent(
    model="gpt-5.4",
    middleware=[LoggingMiddleware()],
    tools=[...],
)
```

**何时使用类：**

- 为同一钩子同时定义同步和异步实现
- 在单个中间件中需要多个钩子
- 需要复杂配置（例如，可配置的阈值、自定义模型）
- 通过初始化时配置跨项目重用

## 自定义状态模式

如果您的中间件需要跨 hooks 跟踪状态，中间件可以使用自定义属性扩展 agent 的状态。这使中间件能够：

- **跨执行跟踪状态**：维护在整个 agent 执行生命周期中持续存在的计数器、标志或其他值
- **在 hooks 之间共享数据**：将信息从 `before_model` 传递到 `after_model` 或在不同中间件实例之间传递
- **实现横切关注点**：添加诸如速率限制、使用跟踪、用户上下文或审计日志等功能，而无需修改核心 agent 逻辑
- **做出条件决策**：使用累积状态来决定是继续执行、跳转到不同节点还是动态修改行为

**装饰器示例：**
```python
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.agents.middleware import AgentState, before_model, after_model
from typing_extensions import NotRequired
from typing import Any
from langgraph.runtime import Runtime

class CustomState(AgentState):
	model_call_count: NotRequired[int]
	user_id: NotRequired[str]

@before_model(state_schema=CustomState, can_jump_to=["end"])
def check_call_limit(state: CustomState, runtime: Runtime) -> dict[str, Any] | None:
	count = state.get("model_call_count", 0)
	if count > 10:
		return {"jump_to": "end"}
	return None

@after_model(state_schema=CustomState)
def increment_counter(state: CustomState, runtime: Runtime) -> dict[str, Any] | None:
	return {"model_call_count": state.get("model_call_count", 0) + 1}

agent = create_agent(
	model="gpt-5.4",
	middleware=[check_call_limit, increment_counter],
	tools=[],
)

# 使用自定义状态调用
result = agent.invoke({
	"messages": [HumanMessage("Hello")],
	"model_call_count": 0,
	"user_id": "user-123",
})
```

**类示例：**
```python
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.agents.middleware import AgentState, AgentMiddleware
from typing_extensions import NotRequired
from typing import Any

class CustomState(AgentState):
	model_call_count: NotRequired[int]
	user_id: NotRequired[str]

class CallCounterMiddleware(AgentMiddleware[CustomState]):
	state_schema = CustomState

	def before_model(self, state: CustomState, runtime) -> dict[str, Any] | None:
		count = state.get("model_call_count", 0)
		if count > 10:
			return {"jump_to": "end"}
		return None

	def after_model(self, state: CustomState, runtime) -> dict[str, Any] | None:
		return {"model_call_count": state.get("model_call_count", 0) + 1}

agent = create_agent(
	model="gpt-5.4",
	middleware=[CallCounterMiddleware()],
	tools=[],
)

# 使用自定义状态调用
result = agent.invoke({
	"messages": [HumanMessage("Hello")],
	"model_call_count": 0,
	"user_id": "user-123",
})
```

## 执行顺序

当使用多个中间件时，了解它们的执行顺序：

```python
agent = create_agent(
    model="gpt-5.4",
    middleware=[middleware1, middleware2, middleware3],
    tools=[...],
)
```

**Before hooks 按顺序运行：**

  1. `middleware1.before_agent()`
  2. `middleware2.before_agent()`
  3. `middleware3.before_agent()`

  **Agent loop 开始**

  4. `middleware1.before_model()`
  5. `middleware2.before_model()`
  6. `middleware3.before_model()`

  **Wrap hooks 像函数调用一样嵌套：**

  7. `middleware1.wrap_model_call()` → `middleware2.wrap_model_call()` → `middleware3.wrap_model_call()` → model

  **After hooks 以相反顺序运行：**

  8. `middleware3.after_model()`
  9. `middleware2.after_model()`
  10. `middleware1.after_model()`

  **Agent loop 结束**

  11. `middleware3.after_agent()`
  12. `middleware2.after_agent()`
  13. `middleware1.after_agent()`

**关键规则：**

- `before_*` hooks：从第一个到最后一个
- `after_*` hooks：从最后一个到第一个（相反）
- `wrap_*` hooks：嵌套（第一个中间件包装所有其他中间件）

## Agent 跳转

要从中间件提前退出，请返回一个带有 `jump_to` 的字典：

**可用的跳转目标：**

- `'end'`：跳转到 agent 执行的结尾（或第一个 `after_agent` hook）
- `'tools'`：跳转到 tools 节点
- `'model'`：跳转到 model 节点（或第一个 `before_model` hook）

**装饰器示例：**
```python
from langchain.agents.middleware import after_model, hook_config, AgentState
from langchain.messages import AIMessage
from langgraph.runtime import Runtime
from typing import Any

@after_model
@hook_config(can_jump_to=["end"])
def check_for_blocked(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
	last_message = state["messages"][-1]
	if "BLOCKED" in last_message.content:
		return {
			"messages": [AIMessage("I cannot respond to that request.")],
			"jump_to": "end"
		}
	return None
```

**类示例：**
```python
from langchain.agents.middleware import AgentMiddleware, hook_config, AgentState
from langchain.messages import AIMessage
from langgraph.runtime import Runtime
from typing import Any

class BlockedContentMiddleware(AgentMiddleware):
	@hook_config(can_jump_to=["end"])
	def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
		last_message = state["messages"][-1]
		if "BLOCKED" in last_message.content:
			return {
				"messages": [AIMessage("I cannot respond to that request.")],
				"jump_to": "end"
			}
		return None
```

## 最佳实践

1.  保持中间件专注——每个中间件应该做好一件事
2.  优雅地处理错误——不要让中间件错误导致 agent 崩溃
3.  **使用适当的钩子类型**：
    - 节点风格用于顺序逻辑（日志记录、验证）
    - 包装风格用于控制流（重试、回退、缓存）
4.  清楚地记录任何自定义状态属性
5.  在集成之前独立地对中间件进行单元测试
6.  考虑执行顺序——将关键中间件放在列表的前面
7.  尽可能使用内置中间件

## 示例

### 动态提示

在运行时动态修改系统提示，以便在每次模型调用之前注入上下文、用户特定指令或其他信息。这是最常见的中间件用例之一。

使用 `ModelRequest` 上的 `system_message` 字段来读取和修改系统提示。它包含一个 `SystemMessage` 对象（即使 agent 是使用字符串 `system_prompt` 创建的）。

**装饰器示例：**
```python
from collections.abc import Callable

from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.messages import SystemMessage

@wrap_model_call
def add_context(
	request: ModelRequest,
	handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
	new_content = list(request.system_message.content_blocks) + [
		{"type": "text", "text": "Additional context."}
	]
	new_system_message = SystemMessage(content=new_content)
	return handler(request.override(system_message=new_system_message))
```

- `ModelRequest.system_message` 始终是一个 `SystemMessage` 对象，即使 agent 是使用 `system_prompt="string"` 创建的。
  - 使用 `SystemMessage.content_blocks` 将内容作为块列表访问，无论原始内容是字符串还是列表。
  - 修改系统消息时，使用 `content_blocks` 并追加新块以保留现有结构。
  - 对于高级用例（如缓存控制），您可以将 `SystemMessage` 对象直接传递给 `create_agent` 的 `system_prompt` 参数。

### 动态模型选择

**装饰器示例：**
```python
from collections.abc import Callable

from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.chat_models import init_chat_model

complex_model = init_chat_model("claude-sonnet-4-6")
simple_model = init_chat_model("claude-haiku-4-5-20251001")


@wrap_model_call
def dynamic_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    if len(request.messages) > 10:
        model = complex_model
    else:
        model = simple_model
    return handler(request.override(model=model))
```

### 动态选择工具

在运行时选择相关工具以提高性能和准确性。本节介绍过滤预注册的工具。有关注册在运行时发现的工具（例如，来自 MCP 服务器），请参阅运行时工具注册。

**优点：**

- **更短的提示** - 仅暴露相关工具以降低复杂性
- **更好的准确性** - 模型从更少的选项中正确选择
- **权限控制** - 基于用户访问权限动态过滤工具

**装饰器示例：**
```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def select_tools(
	request: ModelRequest,
	handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
	"""根据状态/上下文选择相关工具的中间件。"""
	# 根据状态/上下文选择一小部分相关工具
	relevant_tools = select_relevant_tools(request.state, request.runtime)
	return handler(request.override(tools=relevant_tools))

agent = create_agent(
	model="gpt-5.4",
	tools=all_tools,  # 所有可用工具需要预先注册
	middleware=[select_tools],
)
```

### 工具调用监控

**装饰器示例：**
```python
from collections.abc import Callable

from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

@wrap_tool_call
def monitor_tool(
	request: ToolCallRequest,
	handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
	print(f"Executing tool: {request.tool_call['name']}")
	print(f"Arguments: {request.tool_call['args']}")
	try:
		result = handler(request)
		print("Tool completed successfully")
		return result
	except Exception as e:
		print(f"Tool failed: {e}")
		raise
```

**注意：**

- `ModelRequest.system_message` 始终是一个 `SystemMessage` 对象，即使 agent 是使用 `system_prompt="string"` 创建的。
- 使用 `SystemMessage.content_blocks` 将内容作为块列表访问，无论原始内容是字符串还是列表。
- 修改系统消息时，使用 `content_blocks` 并追加新块以保留现有结构。
- 对于高级用例（如缓存控制），您可以将 `SystemMessage` 对象直接传递给 `create_agent` 的 `system_prompt` 参数。

## 附加资源

- 中间件 API 参考
- 内置中间件
- 测试 agents