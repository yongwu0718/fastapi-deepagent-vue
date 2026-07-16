# Models

> 这是 Deep Agents / LangChain 中 **模型（Models）** 的胖索引，覆盖模型初始化、调用方式、工具调用、结构化输出、高级配置与最佳实践。
> 阅读本文档可一次性掌握模型领域的全部概念及其关联，为模型选型、切换和性能调优提供决策支撑。

---
## 概念全景

模型是 Agent 的**推理引擎**，负责决策、工具选择、结果解释与最终回答生成。LangChain 通过统一的标准接口支持数十个模型提供商，使你能够灵活替换而无需修改应用逻辑。

| 能力               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **文本生成**       | 对话、翻译、摘要、代码生成等基础能力                         |
| **Tool calling**   | 模型请求调用外部工具（API、数据库、代码执行等）并消化结果     |
| **Structured output** | 约束输出为 Pydantic、TypedDict 或 JSON Schema 定义的结构 |
| **Multimodality**  | 处理图像、音频、视频等非文本输入，部分模型可生成多模态输出   |
| **Reasoning**      | 多步推理过程，可提取、展示模型的思考链                       |
| **Profiles**       | 暴露模型能力元数据（上下文窗口、是否支持工具调用等），供程序动态适配 |

核心决策点：**模型的提供者、模型名称、参数（temperature/max_tokens/timeout）以及是否绑定工具/结构化输出**，直接决定 Agent 的可靠性、成本和延迟。

---
## 1. 模型初始化与配置

### 初始化方式

- **便捷方式**：`init_chat_model()` 通过字符串标识符和可选参数快速创建模型。
- **显式方式**：直接使用提供者类（如 `ChatOpenAI`）以获取更细粒度的控制。

```python
from langchain.chat_models import init_chat_model

# 默认通过环境变量读取 API Key
model = init_chat_model("openai:gpt-5.4", temperature=0.7, max_tokens=1000)
```

所有模型都实现了统一接口，因此切换提供者只需更换标识符：

```python
model = init_chat_model("anthropic:claude-sonnet-4-6")      # Anthropic
model = init_chat_model("google_genai:gemini-2.5-flash-lite") # Google
model = init_chat_model("azure_openai:gpt-5.4")              # Azure
```

### 关键参数

| 参数            | 作用                                                         |
| --------------- | ------------------------------------------------------------ |
| `model`         | 模型名称，格式 `"provider:name"` 或直接名称                  |
| `temperature`   | 控制输出随机性，0 为确定，1+ 为更富创造性                     |
| `max_tokens`    | 限制响应总 token 数                                          |
| `timeout`       | 请求超时时间（秒），用于取消挂起的调用                        |
| `max_retries`   | 失败重试次数，对不可靠网络建议 10-15                          |
| `rate_limiter`  | 速率限制器，避免触发提供商的速率限制                          |
| `profile`       | 手动提供模型能力 profile（用于修复缺失或错误的数据）          |
| `api_key`       | 直接传入 API 密钥，但推荐使用环境变量                          |

**安全铁律**：永远不要在代码中硬编码 API 密钥，使用环境变量或密钥管理服务。

---
## 2. 调用方式

模型通过消息进行交互，主要有三种调用模式：

| 方法                 | 行为                                                         |
| -------------------- | ------------------------------------------------------------ |
| `invoke()`           | 发送单条消息或对话历史，返回完整的 `AIMessage`               |
| `stream()`           | 流式输出，每次产生一个 `AIMessageChunk`，可实时显示生成内容   |
| `batch()`            | 并行发送多个独立请求，返回结果列表（支持 `batch_as_completed` 乱序处理） |

### 消息格式

支持字典列表或 LangChain 消息对象：

```python
# 字典格式
messages = [
    {"role": "system", "content": "You are a translator."},
    {"role": "user", "content": "Hello"}
]

# LangChain 消息
from langchain.messages import SystemMessage, HumanMessage
messages = [SystemMessage("..."), HumanMessage("...")]
```

流式处理时，LangChain 在后台自动聚合 `AIMessageChunk`，也可使用 `astream_events()` 监听语义事件（token 流、工具调用块等）。

**关键点**：即使你使用 `invoke()`，在 LangGraph Agent 中 LangChain 也会自动切换到内部流式模式，以便通过回调系统将输出推送给前端。

---
## 3. Tool calling（[工具](/langchain-index/langchain/concepts/langchain/tools.md)(调用）

模型可以决定调用哪些工具以及传递什么参数。使用 `bind_tools()` 将工具绑定到模型：

```python
from langchain.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the weather."""
    return f"Sunny in {location}."

model_with_tools = model.bind_tools([get_weather])
```

### 工具调用循环

手动执行工具并将结果返回给模型：

```python
ai_msg = model_with_tools.invoke("What's the weather in Boston?")
for tc in ai_msg.tool_calls:
    result = get_weather.invoke(tc)   # 执行工具
    messages.append(result)           # 追加 ToolMessage
final = model_with_tools.invoke(messages)
```

在 Agent 中，这个循环由框架自动管理。

### 高级控制

- **强制工具选择**：`model.bind_tools([tool], tool_choice="any")` 强制使用任意工具，或 `tool_choice="tool_name"` 强制使用特定工具。
- **并行工具调用**：默认启用；可通过 `parallel_tool_calls=False` 关闭。
- **流式工具调用**：`stream()` 输出会包含 `ToolCallChunk`，可实时观察参数构建过程。

---

## 4. 结构化输出

通过 `with_structured_output()` 约束模型按指定 schema 返回数据。

| Schema 类型     | 特点                             |
| --------------- | -------------------------------- |
| Pydantic 模型   | 自动验证、字段描述、嵌套结构     |
| TypedDict       | 轻量级，无需运行时验证           |
| JSON Schema     | 最大控制，与外部系统互操作       |

```python
from pydantic import BaseModel

class Movie(BaseModel):
    title: str
    year: int

model_with_structure = model.with_structured_output(Movie)
result = model_with_structure.invoke("...")
```

- **方法**：`json_schema`（使用提供商原生支持）、`function_calling`（通过工具调用强约束）、`json_mode`（旧版）。
- **嵌套 schema** 直接使用 Pydantic 或 TypedDict 的嵌套定义。
- **原始消息**：设置 `include_raw=True` 可同时获得解析结果和原始 `AIMessage`（包含 token 用量等）。

---
## 5. 高级特性

### Model profiles（能力发现）

模型的 `profile` 属性暴露能力元数据（最大输入 token、是否支持图片输入、工具调用、推理输出等），可在程序中动态适配：

```python
profile = model.profile
# {"max_input_tokens": 200000, "tool_calling": True, "image_inputs": True, ...}
```

数据来自 models.dev 开源项目，可手动修复或通过 CLI 工具更新。

### 多模态

- **输入**：使用标准内容块（或 provider 原生格式）传递图片、音频、视频。所有支持多模态的 LangChain 模型都兼容 OpenAI 消息格式。
- **输出**：某些模型能生成图片等内容，返回值包含 `"type": "image"` 的内容块。

### 推理链展示

如果模型支持推理（如 OpenAI o-series、Claude extended thinking），可提取 `content_blocks` 中 `type="reasoning"` 的部分。

### 速率限制

使用 `InMemoryRateLimiter` 控制每秒请求数：

```python
from langchain_core.rate_limiters import InMemoryRateLimiter
rate_limiter = InMemoryRateLimiter(requests_per_second=0.1)
model = init_chat_model("openai:gpt-5.4", rate_limiter=rate_limiter)
```

### 提示缓存

许多提供商（OpenAI、Anthropic、Gemini、Bedrock）提供隐式或显式缓存，可降低延迟和成本。缓存的命中状态反映在响应的 usage metadata 中。

### 服务端工具调用

某些模型（如 OpenAI）可在服务端完成工具调用循环，无需客户端传递 `ToolMessage`。响应包含 `server_tool_call` 和 `server_tool_result` 内容块，最终包含整合后的文本及引用注释。

### 可配置模型

创建可动态切换模型的运行时配置对象：

```python
configurable_model = init_chat_model(temperature=0)
configurable_model.invoke(
    "Hello", config={"configurable": {"model": "gpt-5-nano"}}
)
# 可绑定工具、结构化输出等，切换 model 后行为同步变化
```

### 其他

- **本地模型**：通过 Ollama 或 HuggingFace 集成运行本地 LLM。
- **Token 用量**：`AIMessage.response_metadata["token_usage"]` 或使用 `UsageMetadataCallbackHandler` 聚合多模型用量。
- **代理配置**：部分集成支持 `base_url` 和 HTTP 代理，用于连接自定义端点。
- **调用配置**：通过 `RunnableConfig` 传递 `run_name`、`tags`、`metadata`、`callbacks` 等，便于调试和追踪。

---
## 6. 关键约束与最佳实践

### 安全与成本

- API 密钥通过环境变量注入，永远不硬编码。
- 合理设置 `max_tokens` 和 `timeout`，防止失控。
- 使用速率限制器与重试机制（`max_retries`），避免因限流导致 Agent 中断。
- 关注模型的计费方式（输入/输出 token 价格不同）和提示缓存带来的成本优化。

### 模型选型

- 需要精确工具调用和复杂推理 → 选择支持 function calling 且推理能力强的模型（如 Claude、GPT-4.5+、Gemini Pro）。
- 需要大规模并行批量处理 → 使用 `batch()` 和 `max_concurrency` 控制并发。
- 需要实时流式反馈 → 优先使用支持流式的模型，并结合 `astream_events()` 获取细粒度事件。
- 多模态任务 → 确保模型配置文件报告 `image_inputs` 等标志为 True。

### 兼容性与迁移

- 模型名称可直接传递，无需等待 LangChain 更新；新模型立即可用。
- 使用 `init_chat_model` 和统一的提供商包，切换模型时无需更改消息格式或工具定义。
- 当 profile 数据缺失或错误时，可通过 `profile` 参数手动注入或向上游提交修复。

---
## 7. 与全局概念的关联

- **Agent 决策**：模型是所有 Agent 行为的决策核心，调用工具、读取文件、写入内容最终都由模型决定。
- **工具调用与后端**：后端提供的 `ls`、`read_file`、`execute` 等工具由 Agent 通过模型 `bind_tools` 暴露给模型，模型决定何时调用。
- **结构化输出**：可与后端自定义协议结合，例如要求模型返回符合 `BackendProtocol` 结构的结果；也可用于 Agent 状态的解析。
- **记忆与上下文**：模型的上下文窗口大小直接影响记忆管理的策略（何时触发摘要、哪些信息需要存入 `StoreBackend`）。模型 profiles 的 `max_input_tokens` 是上下文压缩的重要依据。
- **技能（Skills）**：模型调用绑定的工具（技能），工具可以是 LangChain 工具、后端操作或自定义函数。
- **执行环境**：在沙箱或本地 Shell 后端中，`execute` 工具由模型发起调用，安全策略应约束模型触发的命令风险。
- **框架配置**：`profile.yaml` 中可以通过 `excluded_tools` 隐藏工具，但模型本身的选择决定了工具调用的下限质量。

---
## 链接原文

### 语义检索（聚焦查询）

原始文档已按标题切分并向量化。构造查询时，使用**当前胖索引中出现的章节标题或特有术语作为锚点**，以获得精准结果。例如：

- `init_chat_model` → 找到模型初始化示例
- `工具调用循环 ToolMessage` → 找到手动执行工具的完整流程
- `结构化输出 json_schema function_calling` → 找到方法对比段落
- `model profiles max_input_tokens` → 找到能力元数据字段说明
- `速率限制 InMemoryRateLimiter` → 找到限流器代码和参数
- `服务端工具调用 server_tool_result` → 找到 OpenAI 服务端工具调用示例

避免使用通用词如“模型怎么用”“如何调用”，这些无法聚焦到具体段落。

### 利用索引页提升检索精度

将你感兴趣的章节标题（如“调用方式”“高级特性”“结构化输出”）与问题组合成查询，可以进一步提高检索精度。本索引页中带 `*` 的术语均为高质量语义锚点。

### 标题路径兜底

语义检索返回的每个片段都包含其**原文标题路径**（如 `## Basic usage`、`### Tool calling`、`### Model profiles`），你可以直接使用这些精确标题通过 `read_file` 定位到该章节的完整上下文。