# Guardrails

> 这是 LangChain Agent 中**安全护栏（Guardrails）**的胖索引，覆盖内置护栏（PII 检测、人机协同）、自定义护栏（Agent 前/后钩子）、组合策略及实现范式。
> 阅读本文档可一次性掌握安全护栏领域的全部概念及其关联，为构建合规、安全的 Agent 应用提供决策支撑。

---

## 概念全景

护栏是在 Agent 执行的关键节点插入的验证与过滤逻辑，用于在问题发生前阻断不安全行为。LangChain 通过**中间件（Middleware）**系统实现护栏，支持在 Agent 启动前、完成后、模型调用或工具执行前后介入。

| 维度             | 描述                                                         |
| ---------------- | ------------------------------------------------------------ |
| **实现方式**     | 规则式（正则、关键词、显式检查）——快速、可预测、低成本；LLM 式（模型评估语义）——能捕获细微违规，但慢且成本高 |
| **作用阶段**     | 请求进入时（`before_agent`）、响应返回前（`after_agent`）、模型调用前后、工具执行前后 |
| **内置护栏**     | PII 检测中间件（`PIIMiddleware`）、人机协同中间件（`HumanInTheLoopMiddleware`） |
| **自定义护栏**   | 基于类或装饰器实现 `before_agent` / `after_agent` 钩子，任意逻辑均可嵌入 |
| **组合策略**     | 多个护栏按顺序堆叠，形成分层防护（输入过滤 → PII 脱敏 → 人工审批 → 输出安全检查） |

核心决策点：**选择规则式还是模型式护栏、在哪个阶段介入（越早阻断成本越低）、如何处理检测到的问题（脱敏/阻断/人工审批）、如何组合多个护栏以形成纵深防御**。

---

## 1. 内置护栏

### PII 检测 (`PIIMiddleware`)

自动检测并处理对话中的个人身份信息。支持的策略：

| 策略      | 行为                             |
| --------- | -------------------------------- |
| `redact`  | 替换为 `[REDACTED_<TYPE>]`       |
| `mask`    | 部分遮盖（如显示后四位）         |
| `hash`    | 替换为确定性哈希                 |
| `block`   | 检测到时阻断并抛出异常           |

内置检测类型：`email`, `credit_card`（Luhn 验证）, `ip`, `mac_address`, `url`。可传入自定义正则表达式检测特定格式（如 `sk-[a-zA-Z0-9]{32}` 匹配 API 密钥）。

配置选项：`pii_type`（必填）、`strategy`（默认 `"redact"`）、`detector`（自定义检测函数/正则）、`apply_to_input` / `apply_to_output` / `apply_to_tool_results`（选择应用的消息类型）。

```python
from langchain.agents.middleware import PIIMiddleware

PIIMiddleware("email", strategy="redact", apply_to_input=True)
PIIMiddleware("credit_card", strategy="mask", apply_to_input=True)
PIIMiddleware("api_key", detector=r"sk-[a-zA-Z0-9]{32}", strategy="block", apply_to_input=True)
```

### 人机协同 (`HumanInTheLoopMiddleware`)

在敏感工具执行前强制暂停并等待人工审批。通过 `interrupt_on` 配置需审批的工具名列表。

必须配合 Checkpointer 使用（`InMemorySaver` 用于开发，`PostgresSaver` 用于生产），并通过 `Command(resume={"decisions": [...]})` 恢复执行。

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

HumanInTheLoopMiddleware(
    interrupt_on={"send_email": True, "delete_database": True, "search": False}
)
```

决策类型：`{"type": "approve"}` / `{"type": "edit", "edited_action": {...}}` / `{"type": "reject"}`。

---

## 2. 自定义护栏

### Agent 前钩子 (`before_agent`)

在**每次调用的最开始**执行一次，适合会话级检查（身份验证、速率限制、关键词过滤）。可通过返回 `{"jump_to": "end"}` 直接终止本次调用。

```python
from langchain.agents.middleware import before_agent

@before_agent(can_jump_to=["end"])
def content_filter(state: AgentState, runtime: Runtime) -> dict | None:
    first_message = state["messages"][0]
    if "hack" in first_message.content.lower():
        return {
            "messages": [{"role": "assistant", "content": "I cannot process that request."}],
            "jump_to": "end"
        }
    return None
```

也可以用类的方式实现（继承 `AgentMiddleware` 并重写 `before_agent`）。

### Agent 后钩子 (`after_agent`)

在**Agent 返回最终响应前**执行一次，适合输出质量验证、合规扫描、敏感内容过滤。可以修改最后一条 `AIMessage` 的内容来替换不安全响应。

```python
@after_agent(can_jump_to=["end"])
def safety_guardrail(state: AgentState, runtime: Runtime) -> dict | None:
    last_message = state["messages"][-1]
    # 使用另一个模型进行安全评估
    safety_result = safety_model.invoke(...)
    if "UNSAFE" in safety_result.content:
        last_message.content = "I cannot provide that response."
    return None
```

**规则式 vs 模型式**：
- 规则式（关键词、正则）在 `before_agent` 中更常见，因为它极快且不消耗 token。
- 模型式（调用另一个 LLM）通常在 `after_agent` 中使用，因为需要对完整响应做语义理解；注意它会增加延迟和成本。

---

## 3. 组合与分层防护

多个护栏按 middleware 列表顺序依次执行，形成从外到内的多层防御：

```
请求 → [关键词过滤] → [PII 脱敏输入] → [Agent 执行] → [人机审批] → [PII 脱敏输出] → [LLM 安全评估] → 响应
```

堆叠顺序建议：**确定性规则前置**（最快失败、最低成本），**人工审批居中**（高风险操作），**模型式评估后置**（最终把关）。

---

## 4. 关键约束与最佳实践

- **尽早阻断**：在 `before_agent` 中用规则式护栏过滤明显违规，避免浪费 LLM 调用。
- **PII 策略选择**：`redact` 是最常用的平衡选项；`block` 会中断执行，适用于绝对不能出现的类型（如 API 密钥）；`mask` 适用于需保留部分信息的场景。
- **人机协同依赖 Checkpointer**：必须提供 checkpointer 并始终使用相同的 `thread_id` 来恢复暂停的执行。
- **模型式护栏的延迟**：`after_agent` 中调用另一个 LLM 会使总响应时间加倍，应仅用于高风险场景或作为最后一道防线。
- **护栏的可组合性**：多个护栏共享同一个 `state`，前一个护栏对状态的修改（如脱敏后的消息）会影响后续护栏的视野。
- **自定义护栏的返回值**：返回 `None` 表示通过；返回包含 `"jump_to": "end"` 的字典会跳过剩余步骤直接终止。
- **测试**：对每个护栏单独测试，对组合护栏进行集成测试，确保分层逻辑不会互相干扰。

---

## 5. 与全局概念的关联

- **中间件系统 (Middleware)**：护栏基于中间件实现，`before_agent` / `after_agent` 是中间件钩子体系的一部分，与 `@before_model` / `@after_model` / `SummarizationMiddleware` 等共享同一架构。
- **消息 (Messages)**：PII 脱敏和人机中断都直接操作 `state["messages"]`；护栏可以检查或修改任何类型的消息（`HumanMessage`、`AIMessage`、`ToolMessage`）。
- **短期记忆 (Short-term memory)**：人机协同依赖 Checkpointer 持久化状态，即短期记忆的基础设施。
- **工具 (Tools)**：人机协同通过 `interrupt_on` 精确拦截特定工具的调用；工具执行前后的护栏可以检查工具的输入输出。
- **模型 (Models)**：模型式护栏需要调用额外的模型进行安全评估，涉及模型选择、延迟和成本权衡。
- **上下文压缩**：在 `after_agent` 中修剪响应内容可视为一种护栏，但通常由专门的压缩中间件处理。
- **流式传输**：自定义护栏中可通过 `get_stream_writer()` 推送事件（见 Streaming 文档中的 safety guardrail 示例），但护栏本身不阻断流式。

---

## 链接原文

### 语义检索（聚焦查询）

- `PIIMiddleware email credit_card redact mask block` → PII 检测策略与配置
- `HumanInTheLoopMiddleware interrupt_on checkpointer Command resume` → 人机协同工作流
- `before_agent can_jump_to end 关键词过滤` → Agent 前钩子与快速阻断
- `after_agent 安全评估 safety model UNSAFE` → Agent 后模型式护栏
- `自定义 detector 正则 API key` → 自定义 PII 检测模式
- `堆叠 middleware 组合分层防护` → 多护栏组合策略

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 内置 Guardrails`、`### 在 Agent 之前的 Guardrails`、`### 组合多个 Guardrails`），可用 `read_file` 精确定位对应章节。