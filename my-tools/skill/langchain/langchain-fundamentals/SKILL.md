---
name: langchain-fundamentals
description: "Create LangChain agents with create_agent, define tools with @tool decorator / tool() function, use middleware for dynamic model/tool selection, streaming, structured output, short-term memory, and error handling."
---

<oneliner>
使用 `create_agent()`、中间件模式和 `@tool` 装饰器 / `tool()` 函数构建生产级 agent。创建 LangChain agent 时，**必须**使用 `create_agent()`。所有其他替代方案都已过时。
</oneliner>

<create_agent>
## 使用 create_agent 创建 agent

`create_agent()` 是构建 agent 的推荐方式。它处理 agent 循环、工具执行和状态管理。

### Agent 配置选项

| 参数 | 用途 | 示例 |
|------|------|------|
| `model` | 要使用的 LLM | `"anthropic:claude-sonnet-4-6"` 或模型实例 |
| `tools` | 工具列表 | `[search, calculator]` |
| `system_prompt` / `systemPrompt` | Agent 指令 | `"你是一个有用的助手"` |
| `checkpointer` | 状态持久化 | `MemorySaver()` |
| `middleware` | 处理钩子 | `[HumanInTheLoopMiddleware]` |
| `response_format` | 结构化输出 | Pydantic 模型 / `ToolStrategy` / `ProviderStrategy` |
| `store` | 长期记忆 | `InMemoryStore()` / `PostgresStore` |
| `name` | Agent 名称（用于流式元数据） | `"research-agent"` |
</create_agent>

<ex-basic-agent>
<python>

```python
from langchain.agents import create_agent
from langchain.tools import tool

@tool
def get_weather(location: str) -> str:
    """获取某个位置的当前天气。

    Args:
        location: 城市名称
    """
    return f"{location} 天气：晴天，22°C"

agent = create_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="你是一个有用的助手。",
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "巴黎的天气怎么样？"}]
})
print(result["messages"][-1].content)
```
</python>
<typescript>

```typescript
import { createAgent } from "langchain";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const getWeather = tool(
  async ({ location }) => `Weather in ${location}: Sunny, 72F`,
  {
    name: "get_weather",
    description: "获取某个位置的当前天气。",
    schema: z.object({ location: z.string().describe("城市名称") }),
  }
);

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-6",
  tools: [getWeather],
  systemPrompt: "你是一个有用的助手。",
});

const result = await agent.invoke({
  messages: [{ role: "user", content: "巴黎的天气怎么样？" }],
});
console.log(result.messages[result.messages.length - 1].content);
```
</typescript>
</ex-basic-agent>

<ex-agent-with-persistence>
<python>
添加 MemorySaver checkpointer 以在多次调用间维护对话状态。

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

agent = create_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[search],
    checkpointer=checkpointer,
)

config = {"configurable": {"thread_id": "user-123"}}
agent.invoke({"messages": [{"role": "user", "content": "我叫 Alice"}]}, config=config)
result = agent.invoke({"messages": [{"role": "user", "content": "我叫什么名字？"}]}, config=config)
# Agent 记住了："你叫 Alice"
```
</python>
<typescript>
添加 MemorySaver checkpointer 以在多次调用间维护对话状态。

```typescript
import { createAgent } from "langchain";
import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-6",
  tools: [search],
  checkpointer,
});

const config = { configurable: { thread_id: "user-123" } };
await agent.invoke({ messages: [{ role: "user", content: "My name is Alice" }] }, config);
const result = await agent.invoke({ messages: [{ role: "user", content: "What's my name?" }] }, config);
// Agent remembers: "Your name is Alice"
```
</typescript>
</ex-agent-with-persistence>

<tools>
## 定义工具

工具是 agent 可以调用的函数。使用 `@tool` 装饰器（Python）或 `tool()` 函数（TypeScript）。

**必须**提供类型提示——它们定义了工具输入模式。文档字符串应信息丰富且简洁。工具名称建议使用 `snake_case`（某些 provider 拒绝包含空格的名称）。
</tools>

<ex-basic-tool>
<python>

```python
from langchain.tools import tool

@tool
def add(a: float, b: float) -> float:
    """将两个数字相加。

    Args:
        a: 第一个数字
        b: 第二个数字
    """
    return a + b
```
</python>
<typescript>

```typescript
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const add = tool(
  async ({ a, b }) => a + b,
  {
    name: "add",
    description: "将两个数字相加。",
    schema: z.object({
      a: z.number().describe("第一个数字"),
      b: z.number().describe("第二个数字"),
    }),
  }
);
```
</typescript>
</ex-basic-tool>

<ex-advanced-tool>
<python>
使用 Pydantic 模型定义复杂输入的 tool。

```python
from pydantic import BaseModel, Field
from typing import Literal
from langchain.tools import tool

class WeatherInput(BaseModel):
    """天气查询输入。"""
    location: str = Field(description="城市名称或坐标")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius", description="温度单位偏好"
    )
    include_forecast: bool = Field(
        default=False, description="包含 5 天预报"
    )

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
    """获取天气信息。"""
    return f"{location}: 晴天, 22°C ({units})"
```
</python>
</ex-advanced-tool>

<middleware>
## 用于 agent 控制的中间件

中间件拦截 agent 循环以添加人工审批、错误处理、日志记录等。深入理解中间件对于生产级 agent 至关重要。

**关键导入：**

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware, wrap_tool_call, wrap_model_call, before_model, after_model
```

```typescript
import { humanInTheLoopMiddleware, createMiddleware } from "langchain";
```

**关键模式：**
- **HITL**: `middleware=[HumanInTheLoopMiddleware(interrupt_on={"dangerous_tool": True})]` — 需要 `checkpointer` + `thread_id`
- **中断后恢复**: `agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)`
- **自定义中间件**: `@wrap_tool_call` 装饰器（Python）或 `createMiddleware({ wrapToolCall: ... })`（TypeScript）
- **动态模型**: `@wrap_model_call` — 根据对话状态切换模型（见下文）
- **动态工具**: `@wrap_model_call` — 根据状态/权限筛选工具（见下文）
</middleware>

<ex-dynamic-model>
<python>
根据对话复杂度动态选择模型。

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

basic_model = ChatOpenAI(model="gpt-5.4-mini")
advanced_model = ChatOpenAI(model="gpt-5.4")

@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """根据对话复杂度选择模型。"""
    message_count = len(request.state["messages"])
    if message_count > 10:
        model = advanced_model
    else:
        model = basic_model
    return handler(request.override(model=model))

agent = create_agent(
    model=basic_model,  # 默认模型
    tools=tools,
    middleware=[dynamic_model_selection]
)
```
</python>
</ex-dynamic-model>

<ex-dynamic-tools>
<python>
根据认证状态和对话阶段动态筛选可用工具。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

@wrap_model_call
def state_based_tools(request: ModelRequest, handler) -> ModelResponse:
    """根据对话状态筛选工具。"""
    state = request.state
    is_authenticated = state.get("authenticated", False)
    message_count = len(state["messages"])

    if not is_authenticated:
        tools = [t for t in request.tools if t.name.startswith("public_")]
        request = request.override(tools=tools)
    elif message_count < 5:
        tools = [t for t in request.tools if t.name != "advanced_search"]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[public_search, private_search, advanced_search],
    middleware=[state_based_tools]
)
```
</python>
</ex-dynamic-tools>

<structured_output>
## 结构化输出

使用 `response_format` 从 agent 获取经过类型验证的结构化响应。

### Response Format 策略

| 策略 | 描述 | 使用场景 |
|------|------|----------|
| `ToolStrategy[SchemaT]` | 使用 tool calling 产生结构化输出 | 不支持原生结构化输出的模型 |
| `ProviderStrategy[SchemaT]` | 使用 provider 原生结构化输出 API | OpenAI、Anthropic、xAI 等 |
| `type[SchemaT]` | Schema 类型——自动选择最佳策略 | **推荐**：根据模型能力自动选择 |
| `None` | 无显式结构化输出请求 | 默认 |

### 支持的 Schema 类型
- **Pydantic 模型**：返回经过验证的 Pydantic 实例
- **数据类 (Dataclasses)**：返回 dict
- **TypedDict**：返回 dict
- **JSON Schema**：返回 dict
</structured_output>

<ex-structured-output>
<python>
使用 Pydantic 模型获取结构化输出。

```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent

class ContactInfo(BaseModel):
    """联系信息。"""
    name: str = Field(description="联系人姓名")
    email: str = Field(description="联系人邮箱")
    phone: str = Field(description="电话号码")

agent = create_agent(
    model="gpt-5.4",
    response_format=ContactInfo  # 自动选择 ProviderStrategy
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "提取联系方式：张三, zhang@example.com, 138-0000-1234"}]
})
print(result["structured_response"])
# ContactInfo(name='张三', email='zhang@example.com', phone='138-0000-1234')
```
</python>
</ex-structured-output>

<ex-structured-output-provider-strategy>
<python>
显式使用 ProviderStrategy 并启用严格模式。

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from pydantic import BaseModel

class ContactInfo(BaseModel):
    name: str
    email: str

agent = create_agent(
    model="gpt-5.4",
    response_format=ProviderStrategy(schema=ContactInfo, strict=True),
)
```
</python>
</ex-structured-output-provider-strategy>

<streaming>
## 流式传输

LangChain 支持多种流式模式：

| 模式 | 流式内容 | 使用场景 |
|------|----------|----------|
| `updates` | 每个步骤后的状态更新 | 监控 agent 进度 |
| `messages` | LLM tokens + 元数据 | 聊天 UI |
| `custom` | 用户自定义数据 | 进度指示器 |
</streaming>

<ex-streaming-updates>
<python>
流式传输 agent 进度——每一步之后发出状态更新。

```python
agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "SF 的天气？"}]},
    stream_mode="updates",
    version="v2",
):
    if chunk["type"] == "updates":
        for step, data in chunk["data"].items():
            print(f"Step: {step}")
```
</python>
</ex-streaming-updates>

<ex-streaming-messages>
<python>
实时流式传输 LLM tokens。

```python
for token, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "讲个笑话"}]},
    stream_mode="messages",
):
    if hasattr(token, "content") and token.content:
        print(token.content, end="", flush=True)
```
</python>
</ex-streaming-messages>

<short-term-memory>
## 短期记忆

短期记忆使 agent 能够在一个线程内记住之前的交互。需要 `checkpointer` + `thread_id`。

**生产环境**: 使用 PostgreSQL 支持的 checkpointer 替代 InMemorySaver。

```python
from langchain.agents import create_agent
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    agent = create_agent(
        "gpt-5.4",
        tools=[get_user_info],
        checkpointer=checkpointer,
    )
```
</short-term-memory>

<model_config>
## 模型配置

`create_agent` 接受模型字符串（`"anthropic:claude-sonnet-4-6"`、`"openai:gpt-5.4"`）或模型实例：

```python
from langchain_openai import ChatOpenAI
agent = create_agent(model=ChatOpenAI(model="gpt-5.4", temperature=0), tools=[...])
```

模型标识符字符串支持自动推断（`"gpt-5.4"` 推断为 `"openai:gpt-5.4"`）。

**注意**: 使用结构化输出时不支持预绑定模型（已调用 `bind_tools` 的模型）。
</model_config>

<fix-missing-tool-description>
<python>
清晰的描述帮助 agent 知道何时使用每个工具。

```python
# 错误：模糊或缺失描述
@tool
def bad_tool(input: str) -> str:
    """做事情。"""
    return "result"

# 正确：清晰具体的描述，包含 Args
@tool
def search(query: str) -> str:
    """搜索网络获取当前信息。

    当你需要最新数据或事实时使用此工具。

    Args:
        query: 搜索查询（建议 2-10 个词）
    """
    return web_search(query)
```
</python>
<typescript>
清晰的描述帮助 agent 知道何时使用每个工具。

```typescript
// 错误：描述模糊
const badTool = tool(async ({ input }) => "result", {
  name: "bad_tool",
  description: "Does stuff.",
  schema: z.object({ input: z.string() }),
});

// 正确：清晰具体的描述
const search = tool(async ({ query }) => webSearch(query), {
  name: "search",
  description: "搜索网络获取最新信息。需要最新数据或事实时使用。",
  schema: z.object({
    query: z.string().describe("搜索查询（建议 2-10 个词）"),
  }),
});
```
</typescript>
</fix-missing-tool-description>

<fix-no-checkpointer>
<python>
添加 checkpointer 和 thread_id 以实现跨调用的对话记忆。

```python
# 错误：无持久化——agent 在调用之间遗忘
agent = create_agent(model="anthropic:claude-sonnet-4-6", tools=[search])
agent.invoke({"messages": [{"role": "user", "content": "我叫 Bob"}]})
agent.invoke({"messages": [{"role": "user", "content": "我叫什么？"}]})
# Agent 不记得！

# 正确：添加 checkpointer 和 thread_id
from langgraph.checkpoint.memory import MemorySaver

agent = create_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[search],
    checkpointer=MemorySaver(),
)
config = {"configurable": {"thread_id": "session-1"}}
agent.invoke({"messages": [{"role": "user", "content": "我叫 Bob"}]}, config=config)
agent.invoke({"messages": [{"role": "user", "content": "我叫什么？"}]}, config=config)
# Agent 记住了："你叫 Bob"
```
</python>
<typescript>
添加 checkpointer 和 thread_id 以实现跨调用的对话记忆。

```typescript
// 错误：无持久化
const agent = createAgent({ model: "anthropic:claude-sonnet-4-6", tools: [search] });
await agent.invoke({ messages: [{ role: "user", content: "I'm Bob" }] });
await agent.invoke({ messages: [{ role: "user", content: "What's my name?" }] });
// Agent doesn't remember!

// 正确：添加 checkpointer 和 thread_id
import { MemorySaver } from "@langchain/langgraph";

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-6",
  tools: [search],
  checkpointer: new MemorySaver(),
});
const config = { configurable: { thread_id: "session-1" } };
await agent.invoke({ messages: [{ role: "user", content: "I'm Bob" }] }, config);
await agent.invoke({ messages: [{ role: "user", content: "What's my name?" }] }, config);
// Agent remembers: "Your name is Bob"
```
</typescript>
</fix-no-checkpointer>

<fix-infinite-loop>
<python>
在 invoke config 中设置 recursion_limit 以防止 agent 失控循环。

```python
# 错误：无迭代限制——可能无限循环
result = agent.invoke({"messages": [("user", "做研究")]})

# 正确：在 config 中设置 recursion_limit
result = agent.invoke(
    {"messages": [("user", "做研究")]},
    config={"recursion_limit": 10},  # 10 步后停止
)
```
</python>
<typescript>
在 invoke config 中设置 recursionLimit 以防止 agent 失控循环。

```typescript
// 错误：无迭代限制
const result = await agent.invoke({ messages: [["user", "做研究"]] });

// 正确：在 config 中设置 recursionLimit
const result = await agent.invoke(
  { messages: [["user", "做研究"]] },
  { recursionLimit: 10 },
);
```
</typescript>
</fix-infinite-loop>

<fix-accessing-result-wrong>
<python>
从结果的 messages 数组中访问内容，而非 result.content。

```python
# 错误：直接访问 result.content
result = agent.invoke({"messages": [{"role": "user", "content": "你好"}]})
print(result.content)  # AttributeError!

# 正确：从结果 dict 中访问 messages
result = agent.invoke({"messages": [{"role": "user", "content": "你好"}]})
print(result["messages"][-1].content)  # 最后一条消息内容

# 结构化输出：访问 structured_response
print(result["structured_response"])  # 验证后的结构化数据
```
</python>
<typescript>
从结果的 messages 数组中访问内容，而非 result.content。

```typescript
// 错误：直接访问 result.content
const result = await agent.invoke({ messages: [{ role: "user", content: "Hello" }] });
console.log(result.content); // undefined!

// 正确：从结果对象中访问 messages
const result = await agent.invoke({ messages: [{ role: "user", content: "Hello" }] });
console.log(result.messages[result.messages.length - 1].content);
```
</typescript>
</fix-accessing-result-wrong>
