# 1. 模块总览

模块导出了三个可供外部使用的核心对象：

| 名称 | 类型 | 职责 |
|------|------|------|
| `SummarizationMiddleware` | 类（`_DeepAgentsSummarizationMiddleware` 的别名） | **自动压缩**：当 token 用量达到阈值时，自动调用 LLM 生成摘要，并将早期消息卸载到后端，替换为摘要消息。 |
| `SummarizationToolMiddleware` | 类 | **手动压缩**：提供一个 `compact_conversation` 工具，让模型或人工审批流可以主动触发压缩，复用前者的摘要引擎。 |
| `create_summarization_middleware` / `create_summarization_tool_middleware` | 工厂函数 | 快捷创建上述中间件，自动根据模型配置选择合理的触发/保留策略。 |

---

## 2. 核心数据结构

### 2.1 `SummarizationEvent` (TypedDict)
```python
class SummarizationEvent(TypedDict):
    cutoff_index: int        # 摘要发生位置在消息列表中的索引
    summary_message: HumanMessage  # 包含摘要文本的 HumanMessage
    file_path: str | None    # 卸载历史记录的路径，失败时为 None
```
这是压缩操作产生的“事件”，被存入 `AgentState` 的私有字段 `_summarization_event`，用于后续重建模型看到的有效消息。

### 2.2 `SummarizationState`
```python
class SummarizationState(AgentState):
    _summarization_event: Annotated[NotRequired[SummarizationEvent | None], PrivateStateAttr]
```
扩展标准 `AgentState`，增加一个**私有属性**（不会暴露给模型），记录最近一次压缩事件。

### 2.3 `TruncateArgsSettings`
```python
class TruncateArgsSettings(TypedDict, total=False):
    trigger: ContextSize | None  # 触发参数截断的阈值（可选）
    keep: ContextSize            # 不截断的最近消息范围
    max_length: int              # 参数值最大字符长度
    truncation_text: str         # 截断后追加的文本
```
控制**工具参数截断**（轻量级预压缩），在摘要压缩之前运行，只截断旧消息中 `write_file` / `edit_file` 的大参数。

### 2.4 `SummarizationDefaults` 和 `compute_summarization_defaults`
- 根据模型 profile 中的 `max_input_tokens` 是否可用，自动选择默认的 `trigger` 和 `keep`：
  - 有 profile → 基于分数 (`("fraction", 0.85)` / `("fraction", 0.10)`)
  - 无 profile → 保守的固定值 (`("tokens", 170000)` / `("messages", 6)`)
- 同时为参数截断生成合适的默认值。

---

## 3. `_DeepAgentsSummarizationMiddleware`（别名 `SummarizationMiddleware`）

这是自动压缩的主中间件，通过覆盖 `wrap_model_call` / `awrap_model_call` 来实现**非侵入式**的上下文管理——它**不会直接修改 LangGraph state 中的 messages**，而是利用 `_summarization_event` 和 `ExtendedModelResponse` 来间接影响模型看到的有效消息。

### 3.1 初始化参数
- `model`：用于生成摘要的 LLM。
- `backend`：后端实例或工厂函数，用于持久化完整对话历史。
- `trigger`：触发压缩的上下文大小（token 数 / 分数 / 消息数）。
- `keep`：压缩后至少保留的消息范围。
- `truncate_args_settings`：参数截断配置，`None` 则禁用。
- 其他辅助参数（`token_counter`, `summary_prompt`, `trim_tokens_to_summarize` 等）。

内部维护一个 `_lc_helper`（LangChain 的 `LCSummarizationMiddleware` 实例），复用其核心的摘要逻辑（阈值判断、cutoff 计算、摘要生成），但添加了 DeepAgents 特有的 **后端 offload**、**参数截断** 和 **事件驱动状态管理**。

### 3.2 消息处理流水线（`wrap_model_call` 核心流程）

1. **重建有效消息**  
   调用 `_get_effective_messages(request)` 根据上一次的 `_summarization_event` 重建当前真正应该被模型看到的消息列表（如果之前已压缩，有效消息 = `[摘要消息] + [cutoff_index 之后的消息]`；否则为完整消息列表）。

2. **参数截断（可选）**  
   调用 `_truncate_args()`，如果触发条件满足，将早期消息中 `AIMessage.tool_calls` 里 `write_file` / `edit_file` 的大参数截短（只保留前 20 个字符 + 截断提示），减少 token 占用而不必立即压缩。

3. **判断是否需要摘要压缩**  
   对截断后的消息进行 token 计数，若达到触发阈值 `_should_summarize` 返回 `True`，或下方的 `ContextOverflowError` 捕获，则进入压缩阶段。

4. **确定截止索引并卸载**  
   - 使用 `_determine_cutoff_index` 计算出一个 `cutoff_index`，将消息分为 `messages_to_summarize`（旧消息）和 `preserved_messages`（保留的近期消息）。
   - 调用 `_offload_to_backend` 将旧消息（过滤掉之前已产生的摘要消息）追加写入 `/conversation_history/{thread_id}.md` 文件，写入失败时发出警告但仍继续。

5. **生成摘要**  
   调用 `_create_summary`（或异步 `_acreate_summary`）让 LLM 生成摘要字符串。

6. **构建摘要消息及事件**  
   - 利用 `_build_new_messages_with_path` 构造一个 `HumanMessage`，内容包含文件路径提示（若卸载成功）和摘要文本，并标记 `additional_kwargs={"lc_source": "summarization"}`。
   - 计算相对于原始 state 的绝对 `cutoff_index`（处理链式压缩的情况）。
   - 组装新的 `SummarizationEvent`。

7. **修改请求并返回**  
   构造 `modified_messages = [summary_msg] + preserved_messages`，用 `request.override(messages=modified_messages)` 调用 handler 得到模型响应。最后通过 `ExtendedModelResponse` 将 `_summarization_event` 更新到 state 中。

### 3.3 后端卸载细节
- 使用传入的 `backend`（可能是 `StateBackend`、`FilesystemBackend` 或 `CompositeBackend` 等）。
- 卸载时读取已有文件内容（Markdown 格式），追加一个新小节：
  ```markdown
  ## Summarized at 2026-05-22T10:00:00+00:00
  [完整对话 buffer]
  ```
- 若写入失败，`file_path` 为 `None`，摘要消息仍会生成，但提示“历史未保存”。
- 链式压缩时，下一次卸载会过滤掉包含 `lc_source="summarization"` 的 `HumanMessage`，避免重复存储。

### 3.4 参数截断 (`_truncate_args`)
- 独立于摘要压缩，阈值通常更低（如 20 条消息或 0.85 比例）。
- 只截断 `write_file` / `edit_file` 的 args 值，因为这些文件内容往往极大。
- 截断后的 `tool_calls` 修改了原始 `AIMessage` 的副本，不影响原始 state。

### 3.5 状态保护设计
自动压缩**不直接删除** state 中的 `messages`，而是通过 `_summarization_event` 改变每次模型调用时看到的“有效视图”。这带来几个好处：
- 原始消息历史完整保留，可用于评估、回放、调试。
- 可与 `SummarizationToolMiddleware` 共享状态（两者都读写 `_summarization_event`）。
- 避免了与 LangGraph 消息修改相关的复杂性。

---

## 4. `SummarizationToolMiddleware` —— 手动压缩工具

这个中间件提供一个名为 `compact_conversation` 的 **StructuredTool**，让模型可以主动调用。它不执行自动压缩，而是在工具被执行时，委托给绑定的 `SummarizationMiddleware` 实例来完成实际压缩。

### 4.1 初始化与工具创建
```python
def __init__(self, summarization: _DeepAgentsSummarizationMiddleware):
    self._summarization = summarization
    self.tools = [self._create_compact_tool()]
```
`_create_compact_tool` 生成一个无参数的 StructuredTool，同步函数为 `sync_compact`，异步为 `async_compact`。

### 4.2 压缩资格检查 (`_is_eligible_for_compaction`)
在工具实际执行前，先检查是否“有资格”压缩，防止过早触发：
- 使用 LangChain helper 的 `_should_summarize_based_on_reported_tokens` 方法。
- 资格阈值约为自动触发阈值的 **50%**（例如自动触发设为 0.85 fraction，则资格阈值为 0.425 fraction；token 触发类似）。
- 若未达到资格，直接返回 `ToolMessage` 提示“Nothing to compact”。

### 4.3 压缩执行 (`_run_compact` / `_arun_compact`)
流程与自动压缩类似，但通过 `ToolRuntime` 获取当前状态：
1. 从 `runtime.state` 拿到 `messages` 和 `_summarization_event`。
2. 根据事件重建有效消息列表。
3. 资格检查（不通过则提前返回）。
4. 用绑定的 `summarization` 中间件计算 cutoff、分区消息。
5. 生成摘要（同步/异步）。
6. 卸载历史到后端（复用 `_offload_to_backend`）。
7. 调用 `_build_compact_result` 构建 `Command`，包含：
   - 更新 `_summarization_event` 为新事件。
   - 追加一条 `ToolMessage` 告知压缩成功。

失败时返回错误 `ToolMessage`，绝不抛出异常（工具规范要求）。

### 4.4 系统提示注入
在 `wrap_model_call` 中，该中间件会调用 `append_to_system_message`，将 `SUMMARIZATION_SYSTEM_PROMPT` 追加到系统消息末尾，提示模型何时应该使用 `compact_conversation` 工具：
```text
## Compact conversation Tool `compact_conversation`

You have access to a `compact_conversation` tool...
```

---

## 5. 工厂函数

### 5.1 `create_summarization_middleware(model, backend)`
- 接受一个已解析的 `BaseChatModel` 实例和一个 `backend`。
- 调用 `compute_summarization_defaults(model)` 获取自动配置。
- 返回配置好的 `SummarizationMiddleware`。
- 适用于自动压缩场景。

### 5.2 `create_summarization_tool_middleware(model, backend)`
- 接受模型字符串或实例，先解析模型。
- 内部调用 `create_summarization_middleware` 创建自动压缩中间件。
- 用该实例创建 `SummarizationToolMiddleware` 并返回。
- 方便快速获得一个手动压缩工具，同时该工具绑定的引擎与自动压缩共享同一套后端和模型。

用法示例：
```python
from deepagents import create_deep_agent
from deepagents.middleware.summarization import create_summarization_tool_middleware
from deepagents.backends import StateBackend

agent = create_deep_agent(
    model="openai:gpt-5.4",
    middleware=[create_summarization_tool_middleware("openai:gpt-5.4", StateBackend())],
)
```

---

## 6. 与 LangChain 标准实现的区别

文档中强调了 DeepAgents 版独有的增强：

- **后端 offload**：不再丢弃被摘要的消息，而是保存到文件，摘要消息中提供路径，方便 `FilesystemMiddleware` 的 `read_file` 重新查阅。
- **工具参数截断**：在完全压缩前先尝试截断大参数，可能直接避免压缩。
- **`ContextOverflowError` 兜底**：当模型调用因为上下文超限而失败时，自动进行一次压缩并重试。
- **非破坏性状态管理**：不直接删除 state 中的 messages，而是通过事件维护有效视图，支持回放和状态共享。
- **模型感知的默认阈值**：根据 `max_input_tokens` 自动选择分数比例。

---

## 7. 配置示例与协同工作

若要同时启用自动压缩和手动压缩工具：
```python
from deepagents.middleware.summarization import (
    SummarizationMiddleware,
    SummarizationToolMiddleware,
)
from deepagents.backends import FilesystemBackend

backend = FilesystemBackend(root_dir="/data")

summ = SummarizationMiddleware(
    model="gpt-4o-mini",
    backend=backend,
    trigger=("fraction", 0.85),
    keep=("fraction", 0.10),
)
tool_mw = SummarizationToolMiddleware(summ)

agent = create_deep_agent(middleware=[summ, tool_mw])
```
此时：
- 自动压缩在占用 85% 上下文窗口时触发，保留 10% 窗口的近期消息。
- 手动工具会在 ~42.5% 占用时就获得资格，模型可主动压缩以提前释放空间。
- 两者共享同一个 `_summarization_event`，因此无论谁先压缩，后续的事件都会正确更新有效视图。

---

## 8. 小结

这个模块通过 **摘要 + 后端卸载 + 事件驱动** 的设计，优雅地解决了长对话的上下文窗口管理问题。它既提供了无需人工干预的自动压缩能力，也暴露了可由模型或用户触发的工具接口。通过私有状态事件和模型请求的包装，实现了非破坏性的消息管理，同时保证了与 LangGraph 的兼容性和可观察性。

# 使用示例
下面详细说明 `SummarizationMiddleware`、`SummarizationToolMiddleware` 以及两个工厂函数的参数配置。我会按组件分节，逐个参数说明类型、含义、默认值与使用示例。

---

## 1. `SummarizationMiddleware`（即 `_DeepAgentsSummarizationMiddleware`）

这是核心中间件，负责自动摘要与历史卸载。构造函数签名：

```python
def __init__(
    self,
    model: str | BaseChatModel,
    *,
    backend: BACKEND_TYPES,
    trigger: ContextSize | list[ContextSize] | None = None,
    keep: ContextSize = ("messages", _DEFAULT_MESSAGES_TO_KEEP),
    token_counter: TokenCounter = count_tokens_approximately,
    summary_prompt: str = DEFAULT_SUMMARY_PROMPT,
    trim_tokens_to_summarize: int | None = _DEFAULT_TRIM_TOKEN_LIMIT,
    truncate_args_settings: TruncateArgsSettings | None = None,
    **deprecated_kwargs,
)
```

### 1.1 `model`
- **类型**：`str | BaseChatModel`
- **说明**：用于生成摘要的 LLM。可以是模型实例，也可以是能被 LangChain 解析的模型字符串。该模型仅在摘要生成时调用，不影响主对话模型。
- **必填**。

### 1.2 `backend`
- **类型**：`BACKEND_TYPES`（即 `BackendProtocol | Callable[[ToolRuntime], BackendProtocol]`）
- **说明**：后端存储，用于将压缩掉的完整对话历史写入持久化文件。可以是 `StateBackend`、`FilesystemBackend`、`CompositeBackend` 等实例，也可以是一个工厂函数，该函数会收到一个 `ToolRuntime` 并返回后端实例。这样可以在多租户或多会话场景下动态选择存储。
- **必填**。

### 1.3 `trigger`
- **类型**：`ContextSize | list[ContextSize] | None`
  - `ContextSize` = `tuple[str, int | float]`，格式如：
    - `("tokens", 100000)` —— 总 token 数达 100k 时触发。
    - `("fraction", 0.85)` —— 达到模型最大输入 token 的 85% 时触发。
    - `("messages", 50)` —— 消息数达到 50 时触发。
- **默认值**：`None`，由 LangChain 内部决定（实际当 `None` 时不会自动触发，除非触发 `ContextOverflowError`，但 DeepAgents 的工厂函数会赋予一个分数默认值）。
- **说明**：可以同时传入多个条件（列表），任何一个满足即触发。
- **重要**：通常建议与 `keep` 配合，避免过度压缩。

### 1.4 `keep`
- **类型**：`ContextSize`
- **默认值**：`("messages", 20)` （LangChain 定义的 `_DEFAULT_MESSAGES_TO_KEEP`）
- **说明**：压缩后必须保留的最近消息范围。格式同 `trigger`：
  - `("messages", 6)` —— 保留最近 6 条消息。
  - `("fraction", 0.10)` —— 保留模型最大上下文 10% 的 token 对应的消息。
  - `("tokens", 20000)` —— 保留总 token 数不超过 2 万的消息。
- **逻辑**：`cutoff_index` 之后的保留消息将不会被摘要，直接附加在摘要消息后面。

### 1.5 `token_counter`
- **类型**：`TokenCounter` （可调用对象，接收消息列表和工具列表，返回 token 数）
- **默认值**：`langchain_core.messages.utils.count_tokens_approximately` （一个近似计数器）
- **说明**：用于评估当前上下文大小的函数。若模型有精确 tokenizer，可替换为该 tokenizer 的计数函数。DeepAgents 在 token 计数时会传入 `tools` 参数，但若该函数不接受 `tools`，内部会捕获 `TypeError` 并回退到无工具版本。

### 1.6 `summary_prompt`
- **类型**：`str`
- **默认值**：`langchain.agents.middleware.summarization.DEFAULT_SUMMARY_PROMPT`（一个预设的摘要提示词）
- **说明**：用于生成摘要的提示模板。可以自定义，例如要求 LLM 保留关键决策或文件改动。

### 1.7 `trim_tokens_to_summarize`
- **类型**：`int | None`
- **默认值**：`_DEFAULT_TRIM_TOKEN_LIMIT`（LangChain 内部定义为 4000）
- **说明**：生成摘要时，被摘要的原始消息总 token 不得超过此值，超出部分会被裁剪（以最先消息为优先）。设为 `None` 表示不裁剪，允许将所有待摘要消息全部传给 LLM。长时间对话可能很大，适当裁剪可避免摘要调用本身也超出上下文。

### 1.8 `truncate_args_settings`
- **类型**：`TruncateArgsSettings | None`
  `TruncateArgsSettings` 是一个 `TypedDict`，字段：
  - `trigger`：`ContextSize | None` —— 触发参数截断的阈值。
  - `keep`：`ContextSize` —— 不截断的最近消息范围。
  - `max_length`：`int` —— 参数值的最大字符数，超过的部分会被截短。
  - `truncation_text`：`str` —— 截短后追加的后缀，如 `"...(truncated)"`。
- **默认值**：`None`，表示禁用参数截断。
- **说明**：这是一个**预摘要优化**。当对话中早先的工具调用（如 `write_file`、`edit_file`）携带了非常大的参数（文件内容、补丁等），可以在真正压缩之前，先将这些旧消息中的参数值截短，从而显著降低 token 占用，可能直接避免触发摘要压缩。它比压缩更快，且不影响最近消息。
- **示例配置**：
  ```python
  truncate_args_settings={
      "trigger": ("messages", 20),   # 总消息超过 20 条时触发
      "keep": ("messages", 10),      # 最近 10 条不截断
      "max_length": 2000,            # 参数值超过 2000 字符则截断
      "truncation_text": "...(truncated)"
  }
  ```

### 1.9 已废弃参数 `history_path_prefix`
- 原本可以传入 `history_path_prefix`，现已废弃，建议使用 `CompositeBackend` 的 `artifacts_root` 来指定根目录。如果使用新的 `backend` 设置，历史文件的路径为 `<artifacts_root>/conversation_history/{thread_id}.md`。

---

## 2. `SummarizationToolMiddleware`

该中间件本身参数很少，但它依赖一个 `SummarizationMiddleware` 实例。

构造函数：

```python
def __init__(self, summarization: _DeepAgentsSummarizationMiddleware)
```

### 参数 `summarization`
- **类型**：`SummarizationMiddleware` 实例
- **说明**：工具中间件不直接配置摘要逻辑，而是**复用**传入的 `SummarizationMiddleware` 实例的所有参数（模型、后端、阈值等）。因此，所有压缩行为（摘要生成、后端卸载、资格检查）都由绑定的自动压缩中间件完成。
- **注意**：`SummarizationToolMiddleware` 会使用 `summarization` 的 `_is_eligible_for_compaction`（基于自动触发阈值的 50% 作为资格线）、`_determine_cutoff_index`、`_create_summary` 等方法。

配置 `SummarizationToolMiddleware` 时，你只需要先创建一个配置好的 `SummarizationMiddleware`，然后传给它即可：

```python
summ = SummarizationMiddleware(
    model="gpt-4o-mini",
    backend=backend,
    trigger=("fraction", 0.85),
    keep=("fraction", 0.10),
)
tool_mw = SummarizationToolMiddleware(summ)
```

---

## 3. 工厂函数 `create_summarization_middleware`

签名：

```python
def create_summarization_middleware(
    model: BaseChatModel,
    backend: BACKEND_TYPES,
) -> SummarizationMiddleware
```

### 参数
- **`model`**：必须是**已解析的 `BaseChatModel` 实例**，不能是字符串。如果你持有字符串，先用 `resolve_model` 解析。
- **`backend`**：同 `SummarizationMiddleware` 的 `backend`，可以是实例或工厂。

### 自动配置
该函数会根据模型 profile 自动设置以下参数：
- **`trigger`**：
  - 若模型 profile 提供了 `max_input_tokens`：`("fraction", 0.85)`
  - 否则：`("tokens", 170000)`
- **`keep`**：
  - 有 profile：`("fraction", 0.10)`
  - 否则：`("messages", 6)`
- **`trim_tokens_to_summarize`**：`None` （不裁剪原始消息，避免丢失关键细节，适合 DeepAgents 的场景）
- **`truncate_args_settings`**：
  - 有 profile：`{"trigger": ("fraction", 0.85), "keep": ("fraction", 0.10)}` （其他字段取默认值）
  - 否则：`{"trigger": ("messages", 20), "keep": ("messages", 20)}` （即 20 条消息时触发截断，且保留所有最近 20 条，实际上所有消息都可能被截断，但这种设置相对保守）

该工厂让用户无需手动计算阈值，特别适合快速启动。

---

## 4. 工厂函数 `create_summarization_tool_middleware`

签名：

```python
def create_summarization_tool_middleware(
    model: str | BaseChatModel,
    backend: BACKEND_TYPES,
) -> SummarizationToolMiddleware
```

### 参数
- **`model`**：可以是模型字符串或实例。若为字符串，内部会调用 `resolve_model` 解析。
- **`backend`**：同前，实例或工厂。

### 行为
- 内部调用 `create_summarization_middleware(model_instance, backend)` 创建一个自动压缩中间件。
- 然后用该实例构造 `SummarizationToolMiddleware` 并返回。

**使用示例**：
```python
from deepagents.middleware.summarization import create_summarization_tool_middleware
from deepagents.backends import StateBackend

tool_mw = create_summarization_tool_middleware("openai:gpt-4o", StateBackend)
```

---

## 5. 综合配置案例

### 案例 1：仅自动压缩（自定义阈值）
```python
from deepagents.middleware.summarization import SummarizationMiddleware
from deepagents.backends import FilesystemBackend

backend = FilesystemBackend(root_dir="/data")
summ = SummarizationMiddleware(
    model="gpt-4o-mini",
    backend=backend,
    trigger=("tokens", 100000),
    keep=("messages", 20),
    summary_prompt="Summarize the conversation focusing on decisions and file changes.",
    trim_tokens_to_summarize=8000,
)
agent = create_deep_agent(middleware=[summ])
```

### 案例 2：同时启用自动压缩 + 手动工具（使用工厂，自动适配阈值）
```python
from deepagents.middleware.summarization import (
    create_summarization_middleware,
    create_summarization_tool_middleware,
)
from deepagents.backends import StateBackend

model = "claude-sonnet-4-6"
backend = StateBackend()

auto_mw = create_summarization_middleware(model, backend)
tool_mw = create_summarization_tool_middleware(model, backend)

agent = create_deep_agent(middleware=[auto_mw, tool_mw])
```

### 案例 3：启用参数截断 + 自定义后缀
```python
summ = SummarizationMiddleware(
    model="gpt-4o",
    backend=backend,
    trigger=("fraction", 0.8),
    keep=("fraction", 0.15),
    truncate_args_settings={
        "trigger": ("messages", 15),
        "keep": ("messages", 5),
        "max_length": 1500,
        "truncation_text": "...[content truncated]"
    }
)
```

---

## 6. 参数配置的影响总结

| 参数/配置项 | 影响 |
|------------|------|
| `trigger` | 控制何时自动触发压缩。值越小，压缩越频繁；值越大，越容易接近极限甚至溢出。 |
| `keep` | 决定压缩后保留多少近期上下文。过小可能导致模型丢失刚发生的关键信息；过大则压缩意义减弱。 |
| `truncate_args_settings` | 能在不调用 LLM 的情况下快速释放 token，适合包含大文件操作的对话。合理设置 `trigger` 可提前拦截，避免频繁压缩。 |
| `trim_tokens_to_summarize` | 传入摘要模型的上下文大小限制。若设置过小，可能丢失被摘要部分的重要细节；设为 `None` 则可能使摘要调用本身消耗大量 token。 |
| `token_counter` | 精确度影响阈值判断，若使用近似计数器，实际触发点可能与预期有偏差。 |
| 模型 profile | 工厂函数利用它选择分数阈值；若无 profile，则使用固定保守值，需注意上下文窗口大小。 |
