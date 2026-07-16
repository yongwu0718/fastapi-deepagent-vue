# 代理自定义配置深度索引

> `create_deep_agent` 的**概念地图**，涵盖模型、工具、提示、中间件、子代理、后端、人机协同、技能、记忆、配置文件等全部配置维度。  

---

## 函数签名

```python
create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: Sequence[SubAgent | CompiledSubAgent | AsyncSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    permissions: list[FilesystemPermission] | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    response_format: ResponseFormat[ResponseT] | type[ResponseT] | dict[str, Any] | None = None,
    context_schema: type[ContextT] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None
) -> CompiledStateGraph
```

---

## 核心配置项速查

| 参数 | 类型/默认值 | 作用 | 关键约束 |
|------|------------|------|---------|
| `model` | `str` 或 `BaseChatModel`，默认 `"claude-sonnet-4-6"` | 选择 LLM，支持 `provider:model` 字符串或实例 | OpenAI 字符串默认用 Responses API；可用 `init_chat_model` 细调 |
| `tools` | 可选列表 | 附加自定义工具，与内置工具合并 | 内置工具：`write_todos`、文件系统工具、`execute`、`task` |
| `system_prompt` | 可选字符串 | 追加在基础提示前，定义代理角色 | 严格按 USER → BASE/CUSTOM → SUFFIX 顺序组装 |
| `middleware` | 可选列表 | 在基础栈和尾部栈之间插入自定义中间件 | 不能移除核心中间件（`FilesystemMiddleware` 等）；动态状态需用图状态而非实例属性 |
| `subagents` | 可选列表 | 定义同步/编译/异步子代理 | 无 `general-purpose` 时自动添加；子代理可覆盖模型、工具、提示、权限等 |
| `skills` | 可选字符串列表 | 技能源路径，按需渐进式加载 | 路径用正斜杠，相对于后端根目录；后列同名技能覆盖前 |
| `memory` | 可选字符串列表 | 记忆文件路径，始终全量加载 | `AGENTS.md` 格式；记忆总是注入系统提示 |
| `response_format` | 可选 | 强制代理输出结构化 JSON | 支持 Pydantic 模型、`ToolStrategy` 等 |
| `context_schema` | 可选 `Dataclass`/`TypedDict` | 定义不可变运行时上下文结构 | 传递给 `create_agent`，供工具和中间件读取 |
| `checkpointer` | 可选 | 持久化代理状态 | 人机协同必需 |
| `store` | 可选 | 持久化存储 | 使用 `StoreBackend` 时必需；部署到 LangSmith 时可省略 |
| `backend` | 可选 `Backend` 实例 | 文件存储和代码执行后端 | 默认 `StateBackend`；沙箱需实现 `SandboxBackendProtocol` |
| `permissions` | 可选列表 | 文件系统权限规则，先匹配优先 | 子代理可继承或完全替换；不适用于沙箱 `execute` |
| `interrupt_on` | 可选字典 | 工具调用的中断配置，实现人机协同 | 子代理可覆盖；`CompiledSubAgent` 需内部配置，`AsyncSubAgent` 不继承 |
| `debug` | 可选布尔 | 开启调试模式 | 传递给内部 `create_agent` |
| `name` | 可选字符串 | 代理名称，用于流式元数据 | 便于区分多代理 |
| `cache` | 可选 | 缓存实例 | 传递给内部 `create_agent` |

---
## 示例配置

```python
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents import create_agent

agent = create_agent(
    model="deepseek-v4-flash",
    tools=[],
    system_prompt="You are a helpful assistant.",
    middleware=[],
    subagents=[],
    skills=[],
    memory=[],
    permissions=[],
    backend=None,
    interrupt_on=None,
    response_format=None,
    context_schema=None,
    checkpointer=None,
    store=None,
    debug=False,
    name=None,
    cache=None
    )
result = await agent.invoke({"messages": [HumanMessage("Help me refactor my codebase")]})
print(result["todos"])  # 包含进度跟踪的 Todo 列表
```

## 提示组装机制

最终系统提示由四个命名槽按顺序拼接：`USER` → (`BASE` 或 `CUSTOM`) → `SUFFIX`。

- `USER`：来自 `system_prompt` 参数，始终在最前。
- `BASE`：Deep Agents 内置基础提示，除非被 `CUSTOM` 覆盖。
- `CUSTOM`：通过 `HarnessProfile.base_system_prompt` 完全替换基础提示。
- `SUFFIX`：通过 `HarnessProfile.system_prompt_suffix` 追加在末尾，最靠近对话历史。

子代理和通用子代理复用相同的覆盖逻辑，但 `USER` 槽无效（子代理的 `system_prompt` 充当 `BASE`）。通用子代理的专属提示可通过 `GeneralPurposeSubagentProfile` 设置，且优先级高于全局 `base_system_prompt`。

---

## 中间件栈顺序

基础中间件 → 自定义中间件 → 尾部中间件：

**基础栈**（按顺序）：
`TodoListMiddleware` → `SkillsMiddleware`（若有技能） → `FilesystemMiddleware` → `SubAgentMiddleware` → `SummarizationMiddleware` → `PatchToolCallsMiddleware` → `AsyncSubAgentMiddleware`（若有异步子代理）

**自定义**：通过 `middleware` 参数插入，位于基础栈之后。

**尾部栈**（按顺序）：
配置文件 `extra_middleware` → `_ToolExclusionMiddleware` → `AnthropicPromptCachingMiddleware` → `MemoryMiddleware` → `HumanInTheLoopMiddleware` → `_PermissionMiddleware`

核心中间件（`FilesystemMiddleware`、`SubAgentMiddleware` 等）禁止通过 `excluded_middleware` 移除；隐藏其工具应使用 `excluded_tools` 或配置文件。

---

## 后端与沙箱

- **StateBackend**（默认）：线程作用域，适合临时暂存。
- **FilesystemBackend**：本地磁盘，需谨慎并启用 `virtual_mode`。
- **LocalShellBackend**：本地磁盘 + shell，极度危险，仅限可信开发环境。
- **StoreBackend**：跨线程持久化，需 `store` 参数，通过命名空间隔离。
- **ContextHubBackend**：基于 LangSmith Hub 的持久化。
- **CompositeBackend**：按路径前缀路由不同后端，常用 `/memories/` → `StoreBackend`。
- **沙箱后端**（Modal、Daytona 等）：提供隔离环境 + `execute` 工具，用于安全执行任意代码。

技能和记忆必须提前存入后端。使用 `CompositeBackend` 时，记忆和技能可独立路由到持久化后端。

---

## 子代理与技能/记忆继承

- **通用子代理**：自动继承主代理的技能和记忆。
- **自定义同步子代理**：不继承技能和记忆，需显式配置 `skills`、`memory` 和 `interrupt_on`；权限可继承或完全替换。
- **异步子代理**：通过 `AsyncSubAgent` 指定远程图，不继承 `interrupt_on`，需在远程代理内部配置。

---

## 配置文件集成

`HarnessProfile` 允许在不修改 `create_deep_agent` 调用的情况下，根据所选模型自动应用：
- 系统提示后缀
- 基础提示替换
- 工具描述覆盖
- 排除工具或中间件
- 额外中间件
- 通用子代理设置

`ProviderProfile` 仅影响模型构建参数（如 `temperature`），适用于 `provider:model` 字符串解析时。

配置文件支持 YAML/JSON 持久化（`HarnessProfileConfig`）和插件入口点自动注册。

---

## 关键约束与最佳实践

- **模型**：使用 `provider:model` 字符串可快速切换；需自定义参数时用 `init_chat_model`。
- **系统提示**：始终遵循组装顺序；配置文件是调整提示的首选方式，而非直接修改基础提示。
- **中间件**：不要修改实例属性作为状态；用图状态跨钩子共享数据；严禁排除核心中间件。
- **人机协同**：必须提供 `checkpointer`；子代理可覆盖中断配置，但异步子代理需远程配置。
- **权限**：不适用于沙箱 `execute` 工具；`CompositeBackend` 中不能对沙箱默认路径设置权限。
- **技能与记忆**：技能按需加载，记忆全量注入；两者均依赖后端提供文件。
- **性能**：必要时使用 `cache`；调试用 `debug=True`。
