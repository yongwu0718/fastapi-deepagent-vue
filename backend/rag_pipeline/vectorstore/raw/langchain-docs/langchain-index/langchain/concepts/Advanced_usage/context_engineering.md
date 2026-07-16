# Agents 中的上下文工程 (Context Engineering)

> 这是 Deep Agents / LangChain 中**上下文工程**的胖索引，覆盖模型上下文、工具上下文、生命周期上下文的动态控制，以及如何通过中间件从 State、Store 和 Runtime Context 三个数据源精准组装 Agent 所需的信息。
> 阅读本文档可一次性掌握上下文工程的全部概念及其关联，为构建可靠、可扩展的 Agent 提供决策支撑。

---

## 概念全景

Agent 不可靠的主因通常不是模型能力不足，而是**没有将“正确的”上下文传递给 LLM**。上下文工程以正确的格式、在正确的时机为模型和工具提供正确的信息与工具选择。

| 上下文类型       | 控制范围                                           | 持久性   | 典型控制手段                                   |
| ---------------- | -------------------------------------------------- | -------- | ---------------------------------------------- |
| **模型上下文**   | 进入每次模型调用的内容（系统提示、消息、工具、模型） | 瞬态     | `dynamic_prompt`、`wrap_model_call`              |
| **工具上下文**   | 工具可读取和写入的数据（State / Store / Context）   | 持久化   | `ToolRuntime`、`Command` 更新状态               |
| **生命周期上下文** | 模型调用与工具调用之间发生的处理（总结、护栏等）    | 持久化   | `before_model`、`after_model`、`SummarizationMiddleware` |

三个数据源支撑整个上下文工程：

| 数据源             | 别名         | 作用域     | 典型内容                                      |
| ------------------ | ------------ | ---------- | --------------------------------------------- |
| **Runtime Context** | 静态配置     | 会话       | user_id、API key、角色、权限、环境            |
| **State**          | 短期记忆     | 会话/线程  | 消息历史、认证状态、上传文件、工具结果        |
| **Store**          | 长期记忆     | 跨会话     | 用户偏好、写作风格、功能开关、长期知识        |

核心决策点：**哪些信息应从哪个数据源抽取、以何种方式注入模型提示或工具调用、何时进行持久化更新、如何避免上下文过载或冲突**。

---

## 1. 模型上下文

控制每次 LLM 调用所接收的指令、消息、工具集、模型选择和输出格式，全部可从 State、Store、Runtime Context 动态生成。

### 系统提示

通过 `@dynamic_prompt` 中间件，根据对话长度、用户偏好或角色动态构建系统指令：

- **State 驱动**：检查消息数量，自动追加“长对话请简洁”等指令。
- **Store 驱动**：读取用户偏好的沟通风格，注入提示。
- **Context 驱动**：根据用户角色（admin / viewer）和环境（production）添加权限或合规声明。

### 消息

使用 `@wrap_model_call` 在每次模型调用前**瞬态地**插入或修改消息，不改变持久化状态：

- 从 State 注入上传的文件摘要，告知模型可用文档。
- 从 Store 注入用户的写作风格示例，优化邮件起草。
- 从 Runtime Context 注入 GDPR/HIPAA 合规约束。

> 如需持久化修改消息历史，应在 `before_model` 或 `after_model` 等生命周期钩子中进行。

### 工具选择

通过 `@wrap_model_call` 按权限、认证状态或功能开关动态筛选可用工具：

- State 驱动：未认证时仅暴露 `public_*` 工具；对话早期隐藏高级工具。
- Store 驱动：根据用户启用的功能标志过滤工具列表。
- Context 驱动：按角色（admin / editor / viewer）限制写操作或仅保留只读工具。

### 模型选择

根据对话复杂度、用户偏好或成本层级，在 `@wrap_model_call` 中替换调用模型：

- State 驱动：消息超阈值时切换至大上下文窗口模型。
- Store 驱动：读取用户偏好的模型名（如 `gpt-5.4` vs `claude-sonnet`）。
- Context 驱动：按 `cost_tier` 和 `environment` 选择 premium / standard / budget 模型。

### 响应格式

动态设置 `response_format`（Pydantic schema），让模型输出符合下游需求：

- State 驱动：对话早期返回 `SimpleResponse`，后期切换为带推理和置信度的 `DetailedResponse`。
- Store 驱动：用户偏好“详细”则使用包含来源的格式，否则使用简洁格式。
- Context 驱动：管理员在 production 环境得到包含 debug 信息的格式，普通用户仅得到简洁答案。

---

## 2. 工具上下文

工具既能**读取** State、Store、Context 中的信息，又能**写入**以持久化关键数据。

### 读取

通过 `ToolRuntime` 参数（对模型隐藏）访问运行时信息：

- `runtime.state` – 获取当前会话的认证状态、消息等。
- `runtime.store` – 查询跨会话的用户偏好、知识库。
- `runtime.context` – 获取 API 密钥、数据库连接、user_id 等静态配置。

### 写入

工具可以通过返回 `Command` 来更新 State（如设置 `authenticated=True`），或直接调用 `runtime.store.put()` 持久化用户偏好，实现对记忆的主动管理。

---

## 3. 生命周期上下文

控制核心 Agent 步骤**之间**发生的行为——通过中间件钩子插入横切关注点，并可**持久化**修改状态。

### 典型模式：自动总结

LangChain 提供内置 `SummarizationMiddleware`，当对话 token 数超过阈值时，自动调用小模型总结旧消息，并在 State 中用摘要替换原始消息，后续轮次永久受益。

```python
SummarizationMiddleware(
    model="gpt-5.4-mini",
    trigger={"tokens": 4000},
    keep={"messages": 20},
)
```

其他生命周期钩子（`before_model`、`after_model`、`wrap_tool_call`）可用于实现护栏、审计日志、内容过滤等，并在需要时通过 `jump_to` 跳过或重复步骤。

---

## 4. 关键约束与最佳实践

- **先简后繁**：从静态提示和固定工具开始，仅在明确需要时引入动态上下文。
- **瞬态 vs 持久化**：使用 `wrap_model_call` 做瞬态调整（不改变状态），使用生命周期钩子或 `Command` 做持久化更新。
- **避免过载**：动态工具或消息注入时，确保不会因过多信息导致模型性能下降；优先精简关键信息。
- **三个数据源各有分工**：Runtime Context 放配置和身份，State 放会话内临时数据，Store 放跨会话持久数据。不要混用。
- **监控与迭代**：跟踪模型调用次数、token 消耗和延迟，评估每次上下文工程的收益。
- **利用内置中间件**：`SummarizationMiddleware`、`PIIMiddleware`、`HumanInTheLoopMiddleware` 等可减少自定义开发量。

---

## 5. 与全局概念的关联

- **模型 (Models)**：上下文工程的核心是控制进入模型的信息；模型选择本身就是上下文工程的一部分。
- **工具 (Tools)**：工具通过 `ToolRuntime` 深度参与上下文读写，是连接上下文与外部系统的桥梁。
- **短期记忆 (Short-term memory)**：State 作为短期记忆，是消息注入、状态读写的主要载体。
- **长期记忆 (Store)**：Store 承载用户偏好、风格等长期数据，在提示和工具中被持续引用和更新。
- **中间件 (Middleware)**：整个上下文工程的实现基础，所有动态提示、消息修改、工具筛选、生命周期钩子均通过中间件系统实现。
- **安全护栏 (Guardrails)**：属于生命周期上下文的一种具体应用，用于在关键节点检查内容合规性。
- **上下文压缩**：总结中间件就是持久化的上下文压缩，修剪消息则属于瞬态压缩。

---

## 链接原文

### 语义检索（聚焦查询）

- `上下文工程 context engineering 可靠 agent` → 概念综述与失败原因
- `dynamic_prompt state store runtime context` → 系统提示动态化
- `wrap_model_call inject file writing style compliance` → 消息上下文注入
- `state_based_tools store_based_tools context_based_tools` → 动态工具选择
- `response_format Pydantic state store context` → 响应格式动态配置
- `ToolRuntime state store context 读取 写入 Command` → 工具上下文读写
- `SummarizationMiddleware trigger keep` → 生命周期总结
- `瞬态 vs 持久化 wrap_model_call before_model` → 更新模式区分

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 模型上下文`、`### 系统提示`、`### 工具`、`## 工具上下文`、`## 生命周期上下文`），可用 `read_file` 精确定位对应章节。