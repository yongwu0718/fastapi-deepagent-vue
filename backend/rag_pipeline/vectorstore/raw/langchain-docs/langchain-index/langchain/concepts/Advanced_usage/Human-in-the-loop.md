# Human-in-the-loop

> 这是 LangChain Agent 中**人机协同（Human-in-the-loop, HITL）**的胖索引，覆盖中断配置、决策类型、响应处理、流式集成以及自定义逻辑。
> 阅读本文档可一次性掌握人机协同的全部概念及其关联，为构建需要人工审查的敏感操作流程提供决策支撑。

---

## 概念全景

人机协同中间件（`HumanInTheLoopMiddleware`）在 Agent 的工具调用与执行之间插入人工审核环节。当模型请求执行需审查的操作时，中间件通过 LangGraph 的中断机制暂停执行，持久化当前状态，等待人工决策后恢复。

| 维度               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **触发机制**       | 基于工具名称配置 `interrupt_on` 映射，匹配的工具调用会触发中断 |
| **决策类型**       | `approve`（批准）、`edit`（编辑后执行）、`reject`（拒绝并反馈）、`respond`（人工直接回复） |
| **状态持久化**     | 依赖 Checkpointer（`InMemorySaver` 或 `PostgresSaver`），通过 `thread_id` 关联会话 |
| **恢复方式**       | 使用 `Command(resume={"decisions": [...]})` 传入决策列表，继续执行 |
| **流式支持**       | 兼容 `stream()` 方法，在 `updates` 模式中捕获 `__interrupt__` 事件 |

核心决策点：**哪些工具需要审查、允许哪些决策类型、中断时如何向用户展示操作信息、决策顺序如何保证与中断请求一致**。

---

## 1. 配置中断

在创建 Agent 时，将 `HumanInTheLoopMiddleware` 加入 `middleware` 列表，并通过 `interrupt_on` 指定每个工具的审查策略：

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-5.4",
    tools=[write_file, execute_sql, read_data],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": True,
                "execute_sql": {"allowed_decisions": ["approve", "reject"]},
                "read_data": False,
            },
            description_prefix="Tool execution pending approval",
        ),
    ],
    checkpointer=InMemorySaver(),  # 必须提供 checkpointer
)
```

**`interrupt_on` 配置项**：
- `True`：使用默认配置，允许所有四种决策类型。
- `False`：自动批准，不触发中断。
- `{"allowed_decisions": [...]}`：`InterruptOnConfig` 对象，可指定允许的决策列表（`approve`、`edit`、`reject`、`respond`），并可自定义 `description`（静态字符串或可调用对象）。

**必须配置 Checkpointer**：生产环境使用 `AsyncPostgresSaver` 等持久化方案；开发测试可用 `InMemorySaver`。调用 Agent 时必须传入包含 `thread_id` 的 `config`。

---

## 2. 决策类型

人工审查后可做出以下四种决策，通过 `Command(resume={"decisions": [...]})` 返回：

| 决策类型   | 行为                                                         | 示例                             |
| ---------- | ------------------------------------------------------------ | -------------------------------- |
| `approve`  | 原样执行工具调用                                             | `{"type": "approve"}`            |
| `edit`     | 修改工具名称或参数后执行，需提供 `edited_action`             | `{"type": "edit", "edited_action": {"name": "...", "args": {...}}}` |
| `reject`   | 拒绝执行，并附加反馈消息，Agent 会收到解释并可能调整后续行为 | `{"type": "reject", "message": "原因及建议"}` |
| `respond`  | 不执行工具，人工回复直接作为 `ToolMessage` 返回（用于“询问用户”类工具） | `{"type": "respond", "message": "Blue."}` |

**多个工具同时中断**时，决策列表必须严格按照 `action_requests` 的顺序提供。

**编辑注意事项**：保守地修改参数；大幅改动可能导致模型重新评估并多次调用工具。

---

## 3. 响应中断流程

1. 调用 `agent.invoke(..., config=config, version="v2")`。
2. 若触发中断，返回的 `GraphOutput` 对象包含 `interrupts` 属性，其中是 `Interrupt` 元组。
3. 从 `interrupt.value` 提取 `action_requests`（待审查操作）和 `review_configs`（各操作允许的决策）。
4. 人工做出决策后，通过 `agent.invoke(Command(resume={"decisions": [...]}), config=config, version="v2")` 恢复执行。

```python
result = agent.invoke({"messages": [...]}, config=config, version="v2")
print(result.interrupts[0].value["action_requests"])
# 收集决策后恢复
agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config, version="v2")
```

---

## 4. 流式传输中的 HITL

使用 `stream()` 方法，并指定 `stream_mode=["updates", "messages"]` 及 `version="v2"`，可在 `updates` 模式的 `chunk["data"]` 中检测 `__interrupt__` 键，从而在流式交互中捕获中断。

```python
for chunk in agent.stream(input, config=config, stream_mode=["updates", "messages"], version="v2"):
    if chunk["type"] == "updates" and "__interrupt__" in chunk["data"]:
        print("Interrupt:", chunk["data"]["__interrupt__"])
```

恢复时同样使用 `stream()` 并传入 `Command`，持续接收后续的 `messages` 和 `updates`。

---

## 5. 执行生命周期

中间件基于 `after_model` 钩子运行，具体步骤：

1. Agent 调用模型，生成响应（可能包含工具调用）。
2. 中间件检查响应中的工具调用，匹配 `interrupt_on` 规则。
3. 若需审查，构建 `HITLRequest`（含 `action_requests` 和 `review_configs`）并触发 `interrupt`。
4. 状态通过 Checkpointer 持久化，Agent 暂停。
5. 人工通过 `Command` 提供 `HITLResponse`。
6. 根据决策类型执行工具、合成 `ToolMessage`，或直接返回人工回复，然后恢复执行。

---

## 6. 关键约束与最佳实践

- **Checkpointer 必不可少**：未配置 checkpointer 将无法暂停和恢复，HITL 形同虚设。
- **Thread ID 唯一性**：每个会话必须使用唯一的 `thread_id`，并确保恢复时使用相同的 ID。
- **决策顺序严格匹配**：多个操作的中断，决策列表顺序必须与 `action_requests` 一致。
- **编辑操作要克制**：仅修改必要的参数，避免引发模型循环或意外行为。
- **描述信息清晰**：通过 `description_prefix` 或自定义 `description`，使审查者清楚了解即将执行的操作。
- **生产环境持久化**：使用 `AsyncPostgresSaver` 等持久化 checkpointer，避免内存存储丢失状态。
- **与护栏结合**：HITL 常与 PII 检测、内容过滤等护栏堆叠使用，实现多层防护。

---

## 7. 与全局概念的关联

- **检查点（Checkpointer）**：HITL 依赖 LangGraph 的持久化层来保存中断状态，是短期记忆基础设施的一部分。
- **中间件（Middleware）**：`HumanInTheLoopMiddleware` 是中间件体系的一员，可与其他中间件（如 `PIIMiddleware`、`SummarizationMiddleware`）组合。
- **流式传输（Streaming）**：通过 `stream()` 的 `updates` 模式捕获中断，实现前端实时交互。
- **工具（Tools）**：中断直接作用于工具调用，工具的输入输出在审查过程中可能被修改或替换。
- **护栏（Guardrails）**：HITL 本身是一种特殊护栏，针对高风险操作进行人工把关。
- **上下文工程（Context Engineering）**：人工反馈（如 `reject` 中的 `message`）作为新消息注入对话，影响后续模型决策，属于生命周期上下文的调整。

---

## 链接原文

### 语义检索（聚焦查询）

- `HumanInTheLoopMiddleware interrupt_on checkpointer` → 配置中断
- `approve edit reject respond 决策类型` → 四种决策详解
- `Command resume decisions 恢复执行` → 中断响应
- `stream_mode updates messages __interrupt__` → 流式 HITL
- `InterruptOnConfig allowed_decisions description_prefix` → 细粒度配置
- `GraphOutput interrupts action_requests` → v2 中断结构
- `after_model hook HITLRequest` → 执行生命周期

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 配置中断`、`### 决策类型`、`## 响应中断`、`## 使用 Human-in-the-loop 进行流式传输`），可用 `read_file` 精确定位对应章节。