---
name: deep-agents-orchestration
description: "INVOKE THIS SKILL when using subagents, task planning, or human approval in Deep Agents. Covers SubAgentMiddleware (dict-based and CompiledSubAgent), TodoList for planning, async subagents, structured output for subagents, and HITL interrupts."
---

<overview>
Deep Agents 包含三项编排能力：

1. **SubAgentMiddleware**: 通过 `task` 工具将工作委派给专门的代理（支持同步和异步子代理）
2. **TodoListMiddleware**: 通过 `write_todos` 工具规划和跟踪任务
3. **HumanInTheLoopMiddleware**: 在敏感操作之前要求审批

三者均在 `create_deep_agent()` 中自动包含。
</overview>

---

## 子代理（任务委派）

<when-to-use-subagents>

| 使用子代理 | 直接使用主代理 |
|---|---:|
| 任务需要专门工具 | 通用工具足够 |
| 想要隔离复杂工作 | 单步操作 |
| 需要保持主代理上下文干净 | 上下文膨胀可接受 |

**为什么使用子代理？** 子代理解决**上下文膨胀问题**。当代理使用会产生大量输出的工具时，上下文窗口会很快被中间结果填满。子代理隔离这些工作——主代理仅接收最终结果。
</when-to-use-subagents>

<how-subagents-work>
主代理拥有 `task` 工具 -> 创建新的子代理 -> 子代理自主执行 -> 返回最终报告。

**默认子代理**: `general-purpose` — 自动可用，具有与主代理相同的工具/配置。除非提供了同名自定义子代理。
</how-subagents-work>

---

### SubAgent（基于字典）

根据 `SubAgent` 规范将子代理定义为字典：

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | `str` | **必需**。唯一标识符，主代理在调用 `task()` 时使用 |
| `description` | `str` | **必需**。具体面向操作的功能描述 |
| `system_prompt` | `str` | **必需**。子代理的指令，不从主代理继承 |
| `tools` | `list[Callable]` | 可选。完全覆盖主代理的工具 |
| `model` | `str` \| `BaseChatModel` | 可选。覆盖主代理的模型 |
| `middleware` | `list[Middleware]` | 可选。额外中间件，不从主代理继承 |
| `interrupt_on` | `dict[str, bool]` | 可选。为特定工具配置 HITL |
| `skills` | `list[str]` | 可选。子代理的技能源路径（不从主代理继承，通用子代理除外） |
| `response_format` | `ResponseFormat` | 可选。结构化输出模式，父代理以 JSON 形式接收结果 |
| `permissions` | `list[FilesystemPermission]` | 可选。完全替换父代理的权限 |

<ex-custom-subagents>
<python>
创建自定义 "researcher" 子代理，具有专门的学术论文搜索工具。

```python
from deepagents import create_deep_agent
from langchain.tools import tool

@tool
def search_papers(query: str) -> str:
    """搜索学术论文。"""
    return f"找到 10 篇关于 {query} 的论文"

agent = create_deep_agent(
    subagents=[
        {
            "name": "researcher",
            "description": "进行网络研究并整理发现",
            "system_prompt": "彻底搜索，返回简洁摘要",
            "tools": [search_papers],
            "model": "openai:gpt-5.4",  # 可选覆盖
        }
    ]
)

# 主代理委派：task(agent="researcher", instruction="研究 AI 趋势")
```
</python>
<typescript>
创建自定义 "researcher" 子代理，具有专门的学术论文搜索工具。

```typescript
import { createDeepAgent } from "deepagents";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const searchPapers = tool(
  async ({ query }) => `Found 10 papers about ${query}`,
  { name: "search_papers", description: "搜索论文", schema: z.object({ query: z.string() }) }
);

const agent = await createDeepAgent({
  subagents: [
    {
      name: "researcher",
      description: "进行网络研究并整理发现",
      systemPrompt: "彻底搜索，返回简洁摘要",
      tools: [searchPapers],
    }
  ]
});
```
</typescript>
</ex-custom-subagents>

---

### CompiledSubAgent

对于复杂工作流，使用预构建的 LangGraph 图作为 `CompiledSubAgent`：

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | `str` | **必需**。唯一标识符 |
| `description` | `str` | **必需**。功能描述 |
| `runnable` | `Runnable` | **必需**。已编译的 LangGraph 图（必须先调用 `.compile()`） |

<ex-compiled-subagent>
<python>
使用 `create_agent` 创建自定义子代理并通过 `CompiledSubAgent` 注册。

```python
from deepagents import create_deep_agent, CompiledSubAgent
from langchain.agents import create_agent

# 创建自定义代理图
custom_graph = create_agent(
    model=your_model,
    tools=specialized_tools,
    prompt="你是一个专门用于数据分析的代理..."
)

# 将其用作子代理
custom_subagent = CompiledSubAgent(
    name="data-analyzer",
    description="用于复杂数据分析任务的专门代理",
    runnable=custom_graph
)

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    tools=[internet_search],
    system_prompt=research_instructions,
    subagents=[custom_subagent]
)
```
</python>
</ex-compiled-subagent>

---

### 通用子代理（General-purpose）

每个 Deep Agent 都有一个默认的 `general-purpose` 子代理。它：
- 与主代理共享相同的系统提示、工具和模型
- 从主代理继承技能
- 可通过提供同名自定义子代理替换
- 可通过 HarnessProfile 禁用

<ex-general-purpose-override>
<python>
覆盖通用子代理使用不同的模型。

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    tools=[internet_search],
    subagents=[
        {
            "name": "general-purpose",
            "description": "用于研究和多步骤任务的通用代理",
            "system_prompt": "你是一个通用助手。",
            "tools": [internet_search],
            "model": "openai:gpt-5.4",  # 为委派任务使用不同模型
        },
    ],
)
```
</python>
</ex-general-purpose-override>

---

### 异步子代理（预览功能）

异步子代理允许监督者启动后台任务并立即返回，在子代理并发工作的同时继续与用户交互。

| 维度 | 同步子代理 | 异步子代理 |
|------|-----------|-----------|
| **执行模型** | 监督者阻塞直到完成 | 立即返回任务 ID |
| **并发性** | 并行但阻塞 | 并行且非阻塞 |
| **任务中途更新** | 不可能 | 通过 `update_async_task` |
| **取消** | 不可能 | 通过 `cancel_async_task` |
| **状态性** | 无状态 | 有状态（跨交互维护） |

```python
from deepagents import AsyncSubAgent, create_deep_agent

async_subagents = [
    AsyncSubAgent(
        name="researcher",
        description="用于信息收集的研究代理",
        graph_id="researcher",
    ),
]

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    subagents=async_subagents,
)
```

异步子代理提供五个工具：`start_async_task`、`check_async_task`、`update_async_task`、`cancel_async_task`、`list_async_tasks`。

> 异步子代理是 `deepagents` 0.5.0 中的预览功能，API 可能会变化。
</ex-async-subagents>

---

### 子代理结构化输出

子代理支持结构化输出，父代理会收到可解析的 JSON 而不是自由格式文本。

```python
from pydantic import BaseModel, Field
from deepagents import create_deep_agent

class ResearchFindings(BaseModel):
    """研究任务的结构化发现。"""
    summary: str = Field(description="发现摘要")
    confidence: float = Field(description="置信度分数，0到1")
    sources: list[str] = Field(description="来源URL列表")

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    subagents=[{
        "name": "researcher",
        "description": "研究并返回结构化发现",
        "system_prompt": "彻底研究给定主题。",
        "tools": [web_search],
        "response_format": ResearchFindings,  # 结构化输出
    }],
)
```

---

### 流式传输和多代理

代理名称作为 `lc_agent_name` 在流式元数据中可用，用于区分不同代理的输出。

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    subagents=subagents,
    name="main-agent"  # 名称出现在元数据中
)
```

<ex-subagent-with-hitl>
<python>
配置子代理，对敏感操作进行 HITL 审批。

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    subagents=[
        {
            "name": "code-deployer",
            "description": "将代码部署到生产环境",
            "system_prompt": "你会在测试通过后部署代码。",
            "tools": [run_tests, deploy_to_prod],
            "interrupt_on": {"deploy_to_prod": True},  # 需要审批
        }
    ],
    checkpointer=MemorySaver()  # 中断必需
)
```
</python>
</ex-subagent-with-hitl>

<fix-subagents-are-stateless>
<python>
子代理是无状态的——在单次调用中提供完整指令。

```python
# 错误：子代理不记得之前调用
# task(agent='research', instruction='查找数据')
# task(agent='research', instruction='你找到了什么？')  # 从头开始！

# 正确：一次性提供完整指令
# task(agent='research', instruction='查找 AI 数据，保存到 /research/，返回摘要')
```
</python>
<typescript>
子代理是无状态的——在单次调用中提供完整指令。

```typescript
// 错误：子代理不记得之前调用
// task research: 查找数据
// task research: 你找到了什么？  // 从头开始！

// 正确：一次性提供完整指令
// task research: 查找 AI 数据，保存到 /research/，返回摘要
```
</typescript>
</fix-subagents-are-stateless>

<fix-custom-subagents-dont-inherit-skills>
<python>
自定义子代理不会从主代理继承技能（通用子代理除外）。

```python
# 错误：自定义子代理不会有主代理的技能
agent = create_deep_agent(
    skills=["/main-skills/"],
    subagents=[{"name": "helper", ...}]  # 没有技能继承
)

# 正确：显式提供技能
agent = create_deep_agent(
    skills=["/main-skills/"],
    subagents=[{"name": "helper", "skills": ["/helper-skills/"], ...}]
)
```
</python>
</fix-custom-subagents-dont-inherit-skills>

<fix-disable-general-purpose>
<python>
通过 HarnessProfile 禁用通用子代理。

```python
from deepagents import HarnessProfile, register_harness_profile, GeneralPurposeSubagentProfile

register_harness_profile(
    "anthropic:claude-sonnet-4-6",
    HarnessProfile(
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
)

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    subagents=[],  # 不传任何同步子代理
)
```
</python>
</fix-disable-general-purpose>

---

## TodoList（任务规划）

<when-to-use-todolist>

| 使用 TodoList | 跳过 TodoList |
|---|---:|
| 复杂的多步骤任务 | 简单单步骤任务 |
| 长时间运行的操作 | 快速操作（少于 3 步） |

</when-to-use-todolist>

<todolist-tool>

```
write_todos(todos: list[dict]) -> None
```

每个 todo 项包含：
- `content`: 任务描述
- `status`: `"pending"`、`"in_progress"` 或 `"completed"`
</todolist-tool>

<ex-todolist-usage>
<python>
调用会自动创建 todo 列表的 agent 执行多步骤任务。

```python
from deepagents import create_deep_agent

agent = create_deep_agent()  # TodoListMiddleware 默认包含

result = agent.invoke({
    "messages": [{"role": "user", "content": "创建 REST API：设计模型、实现 CRUD、添加认证、编写测试"}]
}, config={"configurable": {"thread_id": "session-1"}})

# Agent 通过 write_todos 的规划：
# [
#   {"content": "设计数据模型", "status": "in_progress"},
#   {"content": "实现 CRUD 端点", "status": "pending"},
#   {"content": "添加认证", "status": "pending"},
#   {"content": "编写测试", "status": "pending"}
# ]
```
</python>
<typescript>
调用会自动创建 todo 列表的 agent 执行多步骤任务。

```typescript
import { createDeepAgent } from "deepagents";

const agent = await createDeepAgent();  // TodoListMiddleware 默认包含

const result = await agent.invoke({
  messages: [{ role: "user", content: "创建 REST API：设计模型、实现 CRUD、添加认证、编写测试" }]
}, { configurable: { thread_id: "session-1" } });
```
</typescript>
</ex-todolist-usage>

<ex-access-todo-state>
<python>
从 agent 的最终状态中访问 todo 列表。

```python
result = agent.invoke({...}, config={"configurable": {"thread_id": "session-1"}})

# 从最终状态中访问
todos = result.get("todos", [])
for todo in todos:
    print(f"[{todo['status']}] {todo['content']}")
```
</python>
</ex-access-todo-state>

<fix-todolist-requires-thread-id>
<python>
Todo 列表状态需要 thread_id 来在多次调用间持久化。

```python
# 错误：没有 thread_id 每次都是新状态
agent.invoke({"messages": [...]})

# 正确：使用 thread_id
config = {"configurable": {"thread_id": "user-session"}}
agent.invoke({"messages": [...]}, config=config)  # Todos 被保留
```
</python>
</fix-todolist-requires-thread-id>

---

## 人机协同（审批工作流）

<when-to-use-hitl>

| 使用 HITL | 跳过 HITL |
|---|---:|
| 高风险操作（数据库写入、部署） | 只读操作 |
| 合规要求人工监督 | 全自动工作流 |

</when-to-use-hitl>

<ex-hitl-setup>
<python>
配置哪些工具在执行前需要人工审批。

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    interrupt_on={
        "write_file": True,  # 允许所有决策
        "execute_sql": {"allowed_decisions": ["approve", "reject"]},
        "read_file": False,  # 不中断
    },
    checkpointer=MemorySaver()  # 中断必需！
)
```
</python>
<typescript>
配置哪些工具在执行前需要人工审批。

```typescript
import { createDeepAgent } from "deepagents";
import { MemorySaver } from "@langchain/langgraph";

const agent = await createDeepAgent({
  interruptOn: {
    write_file: true,
    execute_sql: { allowedDecisions: ["approve", "reject"] },
    read_file: false,
  },
  checkpointer: new MemorySaver()  // 必需！
});
```
</typescript>
</ex-hitl-setup>

<ex-approval-workflow>
<python>
完整工作流：触发中断、检查状态、批准并恢复执行。

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

agent = create_deep_agent(
    interrupt_on={"write_file": True},
    checkpointer=MemorySaver()
)

config = {"configurable": {"thread_id": "session-1"}}

# 步骤 1：Agent 提议 write_file — 执行暂停
result = agent.invoke({
    "messages": [{"role": "user", "content": "将配置写入 /prod.yaml"}]
}, config=config)

# 步骤 2：检查中断
state = agent.get_state(config)
if state.next:
    print(f"有待决操作")

# 步骤 3：批准并恢复
result = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)
```
</python>
<typescript>
完整工作流：触发中断、检查状态、批准并恢复执行。

```typescript
import { createDeepAgent } from "deepagents";
import { MemorySaver, Command } from "@langchain/langgraph";

const agent = await createDeepAgent({
  interruptOn: { write_file: true },
  checkpointer: new MemorySaver()
});

const config = { configurable: { thread_id: "session-1" } };

let result = await agent.invoke({
  messages: [{ role: "user", content: "将配置写入 /prod.yaml" }]
}, config);

const state = await agent.getState(config);
if (state.next) {
  console.log("待决操作");
}

result = await agent.invoke(
  new Command({ resume: { decisions: [{ type: "approve" }] } }), config
);
```
</typescript>
</ex-approval-workflow>

<ex-reject-with-feedback>
<python>
拒绝待决操作并给出反馈。

```python
result = agent.invoke(
    Command(resume={"decisions": [{"type": "reject", "message": "先运行测试"}]}),
    config=config,
)
```
</python>
<typescript>
拒绝待决操作并给出反馈。

```typescript
const result = await agent.invoke(
  new Command({ resume: { decisions: [{ type: "reject", message: "先运行测试" }] } }),
  config,
);
```
</typescript>
</ex-reject-with-feedback>

<ex-edit-before-execution>
<python>
在执行前编辑提议的操作参数。

```python
result = agent.invoke(
    Command(resume={"decisions": [{
        "type": "edit",
        "edited_action": {
            "name": "execute_sql",
            "args": {"query": "DELETE FROM users WHERE last_login < '2020-01-01' LIMIT 100"},
        },
    }]}),
    config=config,
)
```
</python>
</ex-edit-before-execution>

<boundaries>
### Agent 可以配置的内容

- 子代理名称、工具、模型、系统提示
- 子代理的结构化输出（response_format）
- CompiledSubAgent（LangGraph 图作为子代理）
- 异步子代理（启动/检查/更新/取消后台任务）
- 哪些工具需要审批
- 每个工具允许的决策类型
- TodoList 内容和结构
- 通过 HarnessProfile 禁用/定制通用子代理

### Agent 不能配置的内容

- 工具名称（`task`、`write_todos`）
- HITL 协议（approve/edit/reject 结构）
- 跳过中断的 checkpointer 要求
- 使子代理有状态（它们是临时的——异步子代理除外）
</boundaries>

<fix-checkpointer-required>
<python>
使用 interrupt_on 进行 HITL 工作流时需要 checkpointer。

```python
# 错误
agent = create_deep_agent(interrupt_on={"write_file": True})

# 正确
agent = create_deep_agent(interrupt_on={"write_file": True}, checkpointer=MemorySaver())
```
</python>
<typescript>
使用 interruptOn 进行 HITL 工作流时需要 checkpointer。

```typescript
// 错误
const agent = await createDeepAgent({ interruptOn: { write_file: true } });

// 正确
const agent = await createDeepAgent({ interruptOn: { write_file: true }, checkpointer: new MemorySaver() });
```
</typescript>
</fix-checkpointer-required>

<fix-thread-id-required-for-resumption>
<python>
恢复中断的工作流需要一致的 thread_id。

```python
# 错误：没有 thread_id 无法恢复
agent.invoke({"messages": [...]})

# 正确
config = {"configurable": {"thread_id": "session-1"}}
agent.invoke({...}, config=config)
# 使用相同 config 通过 Command 恢复
agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)
```
</python>
<typescript>
恢复中断的工作流需要一致的 thread_id。

```typescript
// 错误：没有 thread_id 无法恢复
await agent.invoke({ messages: [...] });

// 正确
const config = { configurable: { thread_id: "session-1" } };
await agent.invoke({ messages: [...] }, config);
await agent.invoke(new Command({ resume: { decisions: [{ type: "approve" }] } }), config);
```
</typescript>
</fix-thread-id-required-for-resumption>

<fix-interrupt-checks-between-invocations>
<python>
中断发生在 invoke() 调用**之间**，而非执行过程中。

```python
result = agent.invoke({...}, config=config)       # 步骤 1：触发中断
if "__interrupt__" in result:                      # 步骤 2：检查中断
    result = agent.invoke(                         # 步骤 3：恢复
        Command(resume={"decisions": [{"type": "approve"}]}),
        config=config,
    )
```
</python>
</fix-interrupt-checks-between-invocations>
