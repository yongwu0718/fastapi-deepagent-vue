# Agents

> 这是 LangChain 中 **Agents** 的胖索引，覆盖 `create_agent` 构建的智能体核心组件、模型与工具的静态/动态配置、系统提示、调用与流式、结构化输出、记忆、中间件及最佳实践。
> 阅读本文档可一次性掌握 Agent 领域的全部概念及其关联，为构建生产级智能体提供决策支撑。

---
## 概念全景

[create_agent](\sdk\create_agent.md) 基于 LangGraph 将语言模型与工具结合，形成 ReAct（推理-行动）循环：模型决定调用哪个工具，工具返回观察结果，循环直到模型给出最终答案。所有 Agent 共享一个消息状态，并通过中间件在关键执行点注入自定义逻辑。

| 维度               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **推理引擎**       | 模型 (`model`) 负责理解任务并决策工具调用                    |
| **行动能力**       | 工具 (`tools`) 赋予 Agent 外部交互能力（搜索、计算、API 等） |
| **行为塑造**       | 系统提示 (`system_prompt`) 设定角色、语气和约束              |
| **执行控制**       | 中间件 (`middleware`) 在模型调用、工具调用前后插入逻辑       |
| **记忆与状态**     | 通过状态 (`state`) 管理短期记忆，可通过 `store` 实现长期记忆 |
| **结构化输出**     | `response_format` 支持 `ToolStrategy` 和 `ProviderStrategy` 强制输出格式 |
| **流式交互**       | `stream()` 方法提供实时 token 和工具调用进度                |

核心决策点：**选择哪个模型、提供哪些工具、如何设计系统提示、是否使用中间件动态调整模型/工具/提示、如何管理状态与记忆**。

---
## 1. [模型](\concepts\langchain\model.md)

### 静态模型
- 最常用方式：直接传递模型标识符字符串（如 `"openai:gpt-5.4"`）或模型实例（如 `ChatOpenAI(model=..., temperature=..., max_tokens=...)`）。
- 创建时指定，整个执行过程中保持不变。

### 动态模型选择
- 通过 `@wrap_model_call` 中间件，根据状态（如消息数量、用户角色）在运行时切换不同模型。
- 适用于根据对话复杂度、成本或能力动态调整模型。
- 注意：使用结构化输出时，不能使用预绑定的模型。

---
## 2. [工具](\concepts\langchain\tools.md)

### 静态工具
- 创建 Agent 时直接传入工具列表，支持 `@tool` 装饰器定义。
- 支持多步调用、并行调用、错误处理和状态持久化。

### 动态工具筛选
- 当所有工具事先已知，但需根据权限、对话阶段或用户偏好选择暴露哪些工具时，通过 `@wrap_model_call` 中间件动态过滤 `request.tools`。
- 可从 `state`、`store` 或 `runtime.context` 获取条件。

### 动态工具注册与执行
- 当工具在运行时才发现（如从 MCP 服务器加载），需同时使用 `wrap_model_call`（添加工具）和 `wrap_tool_call`（处理执行）。
- 适用于工具注册表动态变化、基于用户数据生成工具等场景。

### 工具错误处理
- 通过 `@wrap_tool_call` 中间件捕获异常，返回自定义 `ToolMessage` 告知模型错误原因，实现优雅降级。

### ReAct 循环
- Agent 遵循“推理→行动→观察”循环，模型在思考后调用工具，工具结果反馈给模型继续推理，直至输出最终答案。

---
## 3. [系统提示](\concepts\langchain\messages.md)

- `system_prompt` 参数接受字符串或 `SystemMessage`，可包含缓存控制等 provider 特定配置。
- **动态系统提示**：通过 `@dynamic_prompt` 中间件根据运行时上下文（如用户角色）生成不同提示。
- 不提供时，Agent 直接从消息推断任务。

---
## 4. [调用与流式](\concepts\langchain\streaming.md)

- 调用：`agent.invoke({"messages": [{"role": "user", "content": "..."}]})`。
- 流式：`agent.stream(..., stream_mode="values" 或 "messages")` 可获取中间状态或 LLM token，实时展示进度。

---
## 5. 结构化输出 (Structured output)

通过系统提示词指定模型输出格式，如 JSON、XML 等。模型参数`response_format` 参数可配置。
---
## 6. [记忆](\concepts\Advanced_usage\context_engineering.md)

- 短期记忆：由 Agent 状态中的 `messages` 自动管理。
- 可通过 `state_schema` 扩展自定义字段（必须为 `TypedDict`），在消息之外跟踪用户偏好等。
- 推荐通过 Middleware 定义状态，以便将状态扩展限定在相关中间件和工具范围内；`create_agent` 的 `state_schema` 仍支持向后兼容。
- 长期记忆：通过 `store` 参数配置跨会话持久化。

---
## 7. [中间件](\concepts\middleware_doc\overview.md)

中间件是 Agent 可扩展性的核心，可在以下阶段插入自定义逻辑：
- `wrap_model_call`：模型调用前修改请求（模型、工具、提示、消息）。
- `wrap_tool_call`：工具调用前/后处理或错误捕获。
- `before_model` / `after_model`：模型调用前后处理状态。
- `dynamic_prompt`：动态生成系统提示。
- `HumanInTheLoopMiddleware`、`PIIMiddleware`、`SummarizationMiddleware` 等内置中间件。

---
## 8. 命名 (Name)

- `name` 参数设置 Agent 标识，在多智能体系统中作为子图节点名。
- 建议 `snake_case`，仅使用字母数字、下划线和连字符以保证跨 provider 兼容。

---
## 9. 与全局概念的关联

- **模型(Models)**：Agent 的核心推理引擎，支持静态与动态选择。
- **工具(Tools)**：Agent 通过工具与外部世界交互，工具可动态增删。
- **中间件 (Middleware)**：Agent 行为扩展的主要手段，所有高级功能（动态模型、工具筛选、护栏、上下文注入）均通过中间件实现。
- **消息 (Messages)**：Agent 状态的基础，驱动整个 ReAct 循环。
- **记忆 (Memory)**：短期记忆由状态管理，长期记忆由 `Store` 支撑。
- **流式传输 (Streaming)**：Agent 支持 `stream` 方法输出中间 token 和工具调用。
- **结构化输出**：通过策略确保最终响应符合预定 schema。
- **子图 (Subgraphs)**：Agent 可作为子图嵌入更复杂的多智能体工作流。
- **上下文工程**：动态提示、工具筛选、消息注入均属于上下文工程范畴。

---
## 链接原文

### 语义检索（聚焦查询）

- `create_agent 静态 model 动态 model` → 模型配置
- `@wrap_model_call 动态模型选择` → 动态模型
- `静态 tools 动态 tools wrap_tool_call` → 工具配置与执行
- `tool 错误处理 ToolMessage` → 工具错误处理
- `ReAct 循环 推理 行动` → Agent 执行模式
- `system_prompt SystemMessage cache_control` → 系统提示
- `dynamic_prompt middleware` → 动态提示
- `response_format ToolStrategy ProviderStrategy` → 结构化输出
- `state_schema 自定义 state AgentState` → 记忆扩展
- `stream_mode values messages` → 流式调用
- `middleware 概述` → 中间件体系

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 核心组件`、`### 静态 model`、`### 动态 tools`），可用 `read_file` 精确定位对应章节。