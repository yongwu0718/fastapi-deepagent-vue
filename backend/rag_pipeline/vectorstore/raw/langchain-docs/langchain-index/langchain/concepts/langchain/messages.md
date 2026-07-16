# Messages

> 这是 LangChain 中 **消息（Messages）** 的胖索引，覆盖消息类型、内容表示、多模态、流式与元数据、以及跨 provider 的标准内容块体系。
> 阅读本文档可一次性掌握消息领域的全部概念及其关联，为构建健壮的多轮对话和工具调用流程提供支撑。

---

## 概念全景

消息是 LangChain 中模型交互的基础单元，承载着对话角色、内容载荷与响应元数据。统一的 `Message` 体系使得同一套代码可无缝适配不同模型 provider。

| 维度               | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| **角色（Role）**    | `system`（系统指令）、`user`（人类输入）、`assistant`（AI 回复）、`tool`（工具结果） |
| **内容（Content）** | 文本字符串、标准 content blocks 列表、或 provider 原生格式；支持文本、图像、音频、视频、文件等模态 |
| **元数据**         | `id`、`name`、`usage_metadata`（token 用量）、`response_metadata`（provider 特定信息） |
| **工具调用**       | AI 消息中可携带 `tool_calls`，工具消息通过 `tool_call_id` 对应 |
| **流式支持**       | `AIMessageChunk` 可聚合为完整消息，`content_blocks` 支持逐步构建的 `tool_call_chunk` 等 |
| **标准内容块**     | 跨 provider 的统一内容表示：`text`、`reasoning`、`image`、`audio`、`video`、`file`、`tool_call` 等 |

核心决策点：**消息格式（字典 / LangChain 对象）、内容提供方式（`content` 或 `content_blocks`）、是否包含多模态数据、工具调用 id 的匹配**，决定了对话管理的灵活性和跨 provider 的可移植性。

---

## 1. 消息类型

### SystemMessage
- 设定模型行为、语气、角色
- 通常作为对话列表的第一条消息

### HumanMessage
- 代表用户输入，可包含文本和多模态内容
- `name` 字段用于区分不同用户（支持因 provider 而异）

### AIMessage
- 模型生成的回复
- 可包含文本、工具调用、推理内容、使用元数据
- 流式模式下为 `AIMessageChunk`，可累加为完整消息

### ToolMessage
- 工具执行结果，必须通过 `tool_call_id` 与相应的 `AIMessage` 中的工具调用关联
- 可包含 `artifact`（不发送给模型的附加数据），用于传递原始结果或调试信息

---

## 2. 内容表示

消息的 `content` 属性接受三种形式：

1. **纯字符串**：直接文本
2. **provider 原生格式**：如 OpenAI 的 `[{"type": "text", "text": "..."}, {"type": "image_url", ...}]`
3. **LangChain 标准 content blocks**：通过 `content_blocks` 属性提供类型安全、跨 provider 的统一视图

初始化时可直接传入 `content_blocks`，最终仍会填充 `content` 以保证兼容。

### 关键行为
- `content_blocks` 是惰性解析的，能将 Anthropic 的 `thinking`、OpenAI 的 `reasoning` 等不同 provider 的表示统一转化为 `reasoning` 块。
- 设置环境变量 `LC_OUTPUT_VERSION=v1` 或初始化模型时指定 `output_version="v1"` 可直接将标准块存储在 `content` 中，便于外部系统消费。

---

## 3. 标准内容块类型

| 块类型                  | 用途                       | 关键字段                                |
| ----------------------- | -------------------------- | --------------------------------------- |
| `text`                  | 纯文本输出                 | `text`, `annotations`                   |
| `reasoning`             | 模型推理步骤               | `reasoning`, `extras`（如签名）         |
| `image`                 | 图像数据                   | `url` / `base64` / `file_id`, `mime_type` |
| `audio`                 | 音频数据                   | 同上                                    |
| `video`                 | 视频数据                   | 同上                                    |
| `file`                  | 通用文件（如 PDF）         | 同上，`mime_type` 必填                  |
| `text-plain`            | 文档文本（.txt, .md）      | `text`, `mime_type`                     |
| `tool_call`             | 工具调用                   | `name`, `args`, `id`                    |
| `tool_call_chunk`       | 流式工具调用片段           | `name`, `args`, `id`, `index`           |
| `invalid_tool_call`     | 格式错误的工具调用         | `name`, `args`, `error`                 |
| `server_tool_call`      | 服务端工具调用             | `name`, `args`, `id`                    |
| `server_tool_call_chunk`| 服务端工具调用流片段       | 同上 + `index`                          |
| `server_tool_result`    | 服务端工具执行结果         | `tool_call_id`, `status`, `content`     |
| `non_standard`          | provider 特定数据的后备块  | `data`（任意类型）                       |

**多模态注意事项**：图片、音频、视频、文件可通过 URL、base64 或 provider 管理的 file_id 提供，`mime_type` 在使用 base64 时必须指定。

---

## 4. 使用模式与最佳实践

### 文本提示 vs. 消息列表
- **独立生成**：直接使用字符串（内部转为 `HumanMessage`）
- **多轮对话 / 多模态 / 系统指令**：传递消息列表（`SystemMessage`, `HumanMessage`, `AIMessage` 等）

### 工具调用消息链
模型返回包含 `tool_calls` 的 `AIMessage` → 执行工具 → 生成 `ToolMessage`（带 `tool_call_id`）→ 追加到消息列表 → 再次调用模型以生成最终回复。

### 流式处理
- 使用 `model.stream()` 获取 `AIMessageChunk`，可通过 `+` 累加为完整的 `AIMessage`
- `content_blocks` 会动态累积，工具调用等复杂内容也会逐步构建
- `ToolMessage` 的 `artifact` 字段可承载无需发送给模型的附加数据，避免污染上下文

### 元数据利用
- `usage_metadata` 提供输入/输出 token 细节（包括推理 token、缓存命中等），可用于成本分析和限流。
- `response_metadata` 包含 model provider 返回的原始信息（如 finish reason、model name）。

### 跨 provider 兼容
- 尽量使用 LangChain 消息对象而非裸字典，以便在不同 provider 间切换。
- 高级用法中，可手动构造 `AIMessage` 插入历史，模拟模型响应，但需注意不同 provider 对消息权重的处理差异。

---

## 5. 关键约束与提示

- **`content` vs `content_blocks`**：`content_blocks` 是标准化视图，但底层 `content` 仍保留原始格式，两者可共存。不要假设 `content` 总是字符串。
- **流式聚合**：务必在聚合完成后读取 `tool_calls` 或 `content_blocks`，因为流式过程中字段可能不完整。
- **工具调用 ID 匹配**：`ToolMessage` 的 `tool_call_id` 必须与触发它的 `AIMessage` 中的 `id` 完全一致，否则模型可能无法关联结果。
- **多模态输入限制**：不同模型支持的文件类型和大小不同，请查阅对应 provider 文档。
- **名称字段**：`HumanMessage` 的 `name` 属性不是所有 provider 都支持，用于区分用户时需验证兼容性。
- **手动插入 AI 消息**：可用于提示工程，但过度使用可能导致模型混淆。

---

## 6. 与全局概念的关联

- **模型调用**：所有模型接口（`invoke`、`stream`、`batch`）均以消息列表作为输入，返回 `AIMessage`。
- **工具（Tools）**：工具调用信息嵌入在 `AIMessage.tool_calls` 中，结果通过 `ToolMessage` 反馈；`ToolRuntime` 可自动生成相应的 `ToolMessage`。
- **后端（Backends）**：文件系统工具的执行结果最终以字符串或对象形式封装为 `ToolMessage` 返回给模型。
- **记忆（Memory）**：短期记忆即为消息列表（`state["messages"]`），长期记忆通过 `Store` 读写，其内容也可能以消息形式注入上下文。
- **上下文压缩（Context Compression）**：对消息列表进行修剪、总结时，直接操作消息对象或 `content_blocks`。
- **结构化输出**：模型的结构化输出最后体现为 `AIMessage`，可通过 `with_structured_output()` 自动解析，`include_raw=True` 可同时保留原始消息。
- **权限与安全**：消息本身不直接涉及权限，但用户输入（`HumanMessage`）和工具结果可能包含敏感数据，需结合内容过滤策略。

---

## 链接原文

### 语义检索（聚焦查询）

使用以下关键词组合可精准命中原始文档中的对应章节：

- `SystemMessage HumanMessage AIMessage ToolMessage` → 消息类型概览
- `content_blocks 标准块 text reasoning image` → 标准内容块体系
- `tool_call_id ToolMessage artifact` → 工具消息与 artifact
- `流式 AIMessageChunk 聚合` → 流式消息处理
- `多模态 image audio video base64 mime_type` → 多模态输入规范
- `server_tool_call server_tool_result` → 服务端工具调用消息
- `output_version v1 LC_OUTPUT_VERSION` → 序列化标准内容

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## Basic usage`、`### Standard content blocks`、`#### image`），可用 `read_file` 精确展开对应章节。