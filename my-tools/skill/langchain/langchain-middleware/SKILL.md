---
name: langchain-middleware
description: "INVOKE THIS SKILL when you need human-in-the-loop approval, custom middleware, prebuilt middleware (Summarization, ModelCallLimit, ModelFallback, PII, etc.), or structured output. Covers HumanInTheLoopMiddleware, custom middleware hooks, Command resume patterns, and the full prebuilt middleware catalog."
---

<overview>
生产级 LangChain agent 的中间件模式：

- **预构建中间件**: 用于常见用例（Summary、HITL、CallLimit、Fallback、PII、TodoList、ToolRetry 等）
- **HumanInTheLoopMiddleware** / **humanInTheLoopMiddleware**: 在危险工具调用前暂停以进行人工审批
- **自定义中间件**: 通过 hooks 拦截工具调用、模型调用、agent 生命周期
- **Command resume**: 人工决策（approve、edit、reject）后继续执行

**要求：** 所有 HITL 工作流都需要 Checkpointer + thread_id 配置。
</overview>

---

## 预构建中间件目录

<prebuilt-middleware-table>

| 中间件 | 描述 |
|--------|------|
| **Summarization** | 接近 token 限制时自动总结对话历史 |
| **Human-in-the-loop** | 暂停执行以进行人工审批工具调用 |
| **ModelCallLimit** | 限制模型调用次数以防止过度成本 |
| **ToolCallLimit** | 通过限制调用次数控制工具执行 |
| **ModelFallback** | 主模型失败时自动回退到备选模型 |
| **PII Detection** | 检测并处理个人身份信息（PII） |
| **TodoList** | 为 agent 配备任务规划和跟踪能力 |
| **LLM Tool Selector** | 在调用主模型之前使用 LLM 选择相关工具 |
| **ToolRetry** | 使用指数退避自动重试失败的工具调用 |
| **ModelRetry** | 使用指数退避自动重试失败的模型调用 |
| **ContextEditing** | 通过修剪或清除工具使用来管理对话上下文 |
| **Filesystem** | 为 agent 提供文件系统用于存储上下文和长期记忆 |
| **Subagent** | 添加生成子 agent 的能力 |

</prebuilt-middleware-table>

<ex-summarization-middleware>
<python>
当接近 token 限制时自动总结对话历史。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[weather_tool, calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",        # 用于生成摘要的模型
            trigger=("tokens", 4000),      # 何时触发总结
            keep=("messages", 20),         # 保留多少条最近消息
        ),
    ],
)
```

`trigger` 和 `keep` 支持以下条件：
- `("tokens", N)` — token 数量阈值
- `("messages", N)` — 消息数量阈值
- `("fraction", 0.8)` — context window 使用比例（需要 `langchain>=1.1`）

支持列表中多个条件（OR 逻辑）。
</python>
</ex-summarization-middleware>

<ex-model-retry-middleware>
<python>
使用指数退避自动重试失败的模型调用。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware

agent = create_agent(
    model="gpt-5.4",
    middleware=[
        ModelRetryMiddleware(
            max_retries=3,
            initial_delay=1.0,
            backoff_factor=2.0,
        ),
    ],
)
```
</python>
</ex-model-retry-middleware>

<ex-model-fallback-middleware>
<python>
主模型失败时自动回退到备选模型。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

agent = create_agent(
    model=ChatOpenAI(model="gpt-5.4"),
    middleware=[
        ModelFallbackMiddleware(
            fallback_model=ChatAnthropic(model="claude-sonnet-4-6"),
            max_retries=3,
        ),
    ],
)
```
</python>
</ex-model-fallback-middleware>

---

## Human-in-the-Loop

<ex-basic-hitl-setup>
<python>
设置一个带有 HITL 中间件的 agent，在发送邮件前暂停以进行审批。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件。"""
    return f"邮件已发送至 {to}"

agent = create_agent(
    model="gpt-4.1",
    tools=[send_email],
    checkpointer=MemorySaver(),  # HITL 必需
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},
            }
        )
    ],
)
```
</python>
<typescript>
设置一个带有 HITL 的 agent，在发送邮件前暂停以进行人工审批。

```typescript
import { createAgent, humanInTheLoopMiddleware } from "langchain";
import { MemorySaver } from "@langchain/langgraph";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const sendEmail = tool(
  async ({ to, subject, body }) => `Email sent to ${to}`,
  {
    name: "send_email",
    description: "Send an email",
    schema: z.object({ to: z.string(), subject: z.string(), body: z.string() }),
  }
);

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-6",
  tools: [sendEmail],
  checkpointer: new MemorySaver(),
  middleware: [
    humanInTheLoopMiddleware({
      interruptOn: { send_email: { allowedDecisions: ["approve", "edit", "reject"] } },
    }),
  ],
});
```
</typescript>
</ex-basic-hitl-setup>

<ex-running-with-interrupts>
<python>
运行 agent，检测中断，然后在人工审批后恢复执行。

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "session-1"}}

# 步骤 1：Agent 运行直到需要调用工具
result1 = agent.invoke({
    "messages": [{"role": "user", "content": "发送邮件给 john@example.com"}]
}, config=config)

# 检查中断
if "__interrupt__" in result1:
    print(f"等待审批: {result1['__interrupt__']}")

# 步骤 2：人工批准
result2 = agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config
)
```
</python>
<typescript>
运行 agent，检测中断，然后在人工审批后恢复执行。

```typescript
import { Command } from "@langchain/langgraph";

const config = { configurable: { thread_id: "session-1" } };

const result1 = await agent.invoke({
  messages: [{ role: "user", content: "Send email to john@example.com" }]
}, config);

if (result1.__interrupt__) {
  console.log(`Waiting for approval: ${result1.__interrupt__}`);
}

const result2 = await agent.invoke(
  new Command({ resume: { decisions: [{ type: "approve" }] } }),
  config
);
```
</typescript>
</ex-running-with-interrupts>

<ex-editing-tool-arguments>
<python>
在批准前编辑工具参数以修正原始值。

```python
result2 = agent.invoke(
    Command(resume={
        "decisions": [{
            "type": "edit",
            "edited_action": {
                "name": "send_email",
                "args": {
                    "to": "alice@company.com",  # 修正后的邮箱
                    "subject": "项目会议 - 已更新",
                    "body": "...",
                },
            },
        }]
    }),
    config=config
)
```
</python>
<typescript>
在批准前编辑工具参数以修正原始值。

```typescript
const result2 = await agent.invoke(
  new Command({
    resume: {
      decisions: [{
        type: "edit",
        editedAction: {
          name: "send_email",
          args: {
            to: "alice@company.com",
            subject: "Project Meeting - Updated",
            body: "...",
          },
        },
      }]
    }
  }),
  config
);
```
</typescript>
</ex-editing-tool-arguments>

<ex-rejecting-with-feedback>
<python>
拒绝工具调用并提供反馈解释拒绝原因。

```python
result2 = agent.invoke(
    Command(resume={
        "decisions": [{
            "type": "reject",
            "feedback": "未经经理批准不能删除客户数据",
        }]
    }),
    config=config
)
```
</python>
</ex-rejecting-with-feedback>

<ex-multiple-tools-different-policies>
<python>
根据风险级别为每个工具配置不同的 HITL 策略。

```python
agent = create_agent(
    model="gpt-4.1",
    tools=[send_email, read_email, delete_email],
    checkpointer=MemorySaver(),
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},
                "delete_email": {"allowed_decisions": ["approve", "reject"]},  # 禁止编辑
                "read_email": False,  # 读取不需要 HITL
            }
        )
    ],
)
```
</python>
</ex-multiple-tools-different-policies>

---

## 自定义中间件 Hooks

六种 hooks 可用，分为两种模式：

- **包装 hooks**（`wrap_tool_call`、`wrap_model_call`）: `(request, handler)` — 调用 `handler(request)` 继续，或提前返回来短路。
- **前后 hooks**（`before_model`、`after_model`、`before_agent`、`after_agent`）: `(state, runtime)` — 检查或修改状态。返回 `None` 或状态更新 dict。

<hooks-table>

| Hook | 运行时机 | 风格 |
|------|----------|------|
| `before_agent` | agent 启动前（每次调用一次） | 前后 |
| `before_model` | 每次模型调用前 | 前后 |
| `after_model` | 每次模型响应后 | 前后 |
| `after_agent` | agent 完成后（每次调用一次） | 前后 |
| `wrap_model_call` | 围绕每次模型调用 | 包装 |
| `wrap_tool_call` | 围绕每次工具调用 | 包装 |

</hooks-table>

<ex-wrap-tool-call>
<python>
`@wrap_tool_call` 拦截工具执行。**不要使用 `yield`**——它会创建生成器并导致 `NotImplementedError`。

```python
from langchain.agents.middleware import wrap_tool_call

@wrap_tool_call
def retry_middleware(request, handler):
    for attempt in range(3):
        try:
            return handler(request)
        except Exception:
            if attempt == 2:
                raise

@wrap_tool_call
def guard_middleware(request, handler):
    if request.tool_call["name"] == "dangerous_tool":
        return "This tool is disabled"  # 短路
    return handler(request)
```
</python>
<typescript>
`createMiddleware({ wrapToolCall })` 拦截工具执行。

```typescript
import { createMiddleware } from "langchain";

const retryMiddleware = createMiddleware({
  wrapToolCall: async (request, handler) => {
    for (let attempt = 0; attempt < 3; attempt++) {
      try { return await handler(request); }
      catch (e) { if (attempt === 2) throw e; }
    }
  },
});
```
</typescript>
</ex-wrap-tool-call>

<ex-before-after-hooks>
<python>
`before_model` / `after_model` / `before_agent` / `after_agent` 共享 `(state, runtime)` 签名。

```python
from langchain.agents.middleware import before_model, after_model, before_agent

@before_agent(can_jump_to=["end"])
def check_message_limit(state, runtime):
    if len(state["messages"]) >= 50:
        return {
            "messages": [AIMessage("已到达对话限制。")],
            "jump_to": "end"
        }
    return None

@before_model
def log_calls(state, runtime):
    print(f"使用 {len(state['messages'])} 条消息调用模型")

@after_model
def check_output(state, runtime):
    print(f"模型已响应")
```
</python>
<typescript>
通过 `createMiddleware`，所有前后 hooks 共享 `(state, runtime)` 签名。

```typescript
import { createMiddleware } from "langchain";

const loggingMiddleware = createMiddleware({
  beforeModel: (state, runtime) => {
    console.log(`Calling model with ${state.messages.length} messages`);
  },
  afterModel: (state, runtime) => {
    console.log("Model responded");
  },
});
```
</typescript>
</ex-before-after-hooks>

<boundaries>
### 可以配置的内容

- 哪些工具需要审批（每个工具的策略）
- 每个工具允许的决策（approve、edit、reject）
- 自定义中间件 hooks：`before_model`、`after_model`、`wrap_tool_call`、`wrap_model_call`、`before_agent`、`after_agent`
- 工具特定的中间件（仅应用于特定工具）
- 预构建中间件：Summarization、ModelCallLimit、ModelFallback、PII Detection、ToolRetry 等

### 不能配置的内容

- 在工具执行后中断（必须在之前）
- 跳过 HITL 的 checkpointer 要求
</boundaries>

<fix-missing-checkpointer>
<python>
HITL 中间件需要 checkpointer 来持久化状态。

```python
# 错误
agent = create_agent(model="gpt-4.1", tools=[send_email], middleware=[HumanInTheLoopMiddleware({...})])

# 正确
agent = create_agent(
    model="gpt-4.1", tools=[send_email],
    checkpointer=MemorySaver(),
    middleware=[HumanInTheLoopMiddleware({...})]
)
```
</python>
<typescript>
HITL 需要 checkpointer 来持久化状态。

```typescript
// 错误：无 checkpointer
const agent = createAgent({
  model: "anthropic:claude-sonnet-4-6", tools: [sendEmail],
  middleware: [humanInTheLoopMiddleware({ interruptOn: { send_email: true } })],
});

// 正确：添加 checkpointer
const agent = createAgent({
  model: "anthropic:claude-sonnet-4-6", tools: [sendEmail],
  checkpointer: new MemorySaver(),
  middleware: [humanInTheLoopMiddleware({ interruptOn: { send_email: true } })],
});
```
</typescript>
</fix-missing-checkpointer>

<fix-no-thread-id>
<python>
使用 HITL 时始终提供 thread_id 以跟踪对话状态。

```python
# 错误
agent.invoke(input)  # 没有 config！

# 正确
agent.invoke(input, config={"configurable": {"thread_id": "user-123"}})
```
</python>
</fix-no-thread-id>

<fix-wrong-resume-syntax>
<python>
使用 Command 类在中断后恢复执行。

```python
# 错误
agent.invoke({"resume": {"decisions": [...]}})

# 正确
from langgraph.types import Command
agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)
```
</python>
<typescript>
使用 Command 类在中断后恢复执行。

```typescript
// 错误
await agent.invoke({ resume: { decisions: [...] } });

// 正确
import { Command } from "@langchain/langgraph";
await agent.invoke(new Command({ resume: { decisions: [{ type: "approve" }] } }), config);
```
</typescript>
</fix-wrong-resume-syntax>

<fix-wrap-tool-call-no-yield>
<python>
`@wrap_tool_call` 中不要使用 `yield`——它会引起 `NotImplementedError`。始终使用 `return handler(request)`。

```python
# 错误：使用 yield 创建生成器
@wrap_tool_call
def bad_middleware(request, handler):
    yield handler(request)  # NotImplementedError！

# 正确：使用 return
@wrap_tool_call
def good_middleware(request, handler):
    return handler(request)
```
</python>
</fix-wrap-tool-call-no-yield>
