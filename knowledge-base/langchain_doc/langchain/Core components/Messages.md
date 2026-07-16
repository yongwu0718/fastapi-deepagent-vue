# Messages

Messages 是 LangChain 中模型的基本上下文单元。它们代表模型的输入和输出，携带与 LLM 交互时表示对话状态所需的内容和元数据。

Messages 是包含以下内容的对象：

- **Role** – 标识消息类型（例如 `system`、`user`）
- **Content** – 表示消息的实际内容（如文本、图像、音频、文档等）
- **Metadata** – 可选字段，例如响应信息、消息 ID 和 token 使用情况

LangChain 提供了一个标准的 message 类型，适用于所有模型 provider，确保无论调用哪个模型都能保持一致的行为。

## Basic usage

使用 messages 最简单的方法是创建 message 对象并在调用时将它们传递给模型。

```python
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage, SystemMessage

model = init_chat_model("gpt-5-nano")

system_msg = SystemMessage("You are a helpful assistant.")
human_msg = HumanMessage("Hello, how are you?")

# 与 chat model 一起使用
messages = [system_msg, human_msg]
response = model.invoke(messages)  # 返回 AIMessage
```

### Text prompts

文本提示是字符串——适用于不需要保留对话历史的直接生成任务。

```python
response = model.invoke("Write a haiku about spring")
```

**在以下情况下使用 text prompts：**

- 您有一个独立的单次请求
- 您不需要对话历史
- 您希望代码尽可能简单

### Message prompts

或者，您可以通过提供 message 对象列表来向模型传递消息列表。

```python
from langchain.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage("You are a poetry expert"),
    HumanMessage("Write a haiku about spring"),
    AIMessage("Cherry blossoms bloom...")
]
response = model.invoke(messages)
```

**在以下情况下使用 message prompts：**

- 管理多轮对话
- 处理多模态内容（图像、音频、文件）
- 包含系统指令

### Dictionary format

您也可以直接以 OpenAI chat completions 格式指定消息。

```python
messages = [
    {"role": "system", "content": "You are a poetry expert"},
    {"role": "user", "content": "Write a haiku about spring"},
    {"role": "assistant", "content": "Cherry blossoms bloom..."}
]
response = model.invoke(messages)
```

## Message types

- **System message** – 告诉模型如何行为并为交互提供上下文
- **Human message** – 代表用户输入和与模型的交互
- **AI message** – 模型生成的响应，包括文本内容、tool calls 和元数据
- **Tool message** – 代表 tool calls 的输出结果

### System message

`SystemMessage` 代表一组初始指令，用于预设模型的行为。您可以使用 system message 来设定语气、定义模型角色以及为响应建立指南。

```python
system_msg = SystemMessage("You are a helpful coding assistant.")

messages = [
    system_msg,
    HumanMessage("How do I create a REST API?")
]
response = model.invoke(messages)
```

```python
from langchain.messages import SystemMessage, HumanMessage

system_msg = SystemMessage("""
You are a senior Python developer with expertise in web frameworks.
Always provide code examples and explain your reasoning.
Be concise but thorough in your explanations.
""")

messages = [
    system_msg,
    HumanMessage("How do I create a REST API?")
]
response = model.invoke(messages)
```

***

### Human message

`HumanMessage` 代表用户输入和交互。它们可以包含文本、图像、音频、文件以及任何形式的多模态内容。

#### Text content

```python
  response = model.invoke([
    HumanMessage("What is machine learning?")
  ])
```

```python
# 使用字符串是单个 HumanMessage 的快捷方式
response = model.invoke("What is machine learning?")
```

#### Message metadata

```python
human_msg = HumanMessage(
    content="Hello!",
    name="alice",  # 可选：标识不同用户
    id="msg_123",  # 可选：用于跟踪的唯一标识符
)
```

`name` 字段的行为因 provider 而异——有些用于用户识别，有些则忽略。请查阅模型 provider 的参考文档。

***

### AI message

`AIMessage` 代表模型调用的输出。它们可以包含多模态数据、tool calls 以及 provider 特定的元数据，供您稍后访问。

```python
response = model.invoke("Explain AI")
print(type(response))  # <class 'langchain.messages.ai.AIMessage'>
```

当调用模型时，模型会返回 `AIMessage` 对象，其中包含响应中的所有相关元数据。

Providers 对不同类型消息的权重/上下文处理方式不同，这意味着有时手动创建一个新的 `AIMessage` 对象并将其插入到消息历史中（就像它来自模型一样）会很有帮助。

```python
from langchain.messages import AIMessage, SystemMessage, HumanMessage

# 手动创建一个 AI message（例如，用于对话历史）
ai_msg = AIMessage("I'd be happy to help you with that question!")

# 添加到对话历史
messages = [
    SystemMessage("You are a helpful assistant"),
    HumanMessage("Can you help me?"),
    ai_msg,  # 像来自模型一样插入
    HumanMessage("Great! What's 2+2?")
]

response = model.invoke(messages)
```

`id`  
消息的唯一标识符（由 LangChain 自动生成或从 provider 响应中返回）

`usage_metadata`  
消息的使用元数据，可用时包含 token 计数。

`response_metadata`  
消息的响应元数据。

#### Tool calls

当模型进行 tool calls 时，它们会包含在 `AIMessage` 中：

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5-nano")

def get_weather(location: str) -> str:
    """获取某个位置的天气。"""
    ...

model_with_tools = model.bind_tools([get_weather])
response = model_with_tools.invoke("What's the weather in Paris?")

for tool_call in response.tool_calls:
    print(f"Tool: {tool_call['name']}")
    print(f"Args: {tool_call['args']}")
    print(f"ID: {tool_call['id']}")
```

其他结构化数据，例如推理或引用，也可能出现在 message content 中。

#### Token usage

`AIMessage` 可以在其 `usage_metadata` 字段中保存 token 计数和其他使用元数据：

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5-nano")

response = model.invoke("Hello!")
response.usage_metadata
```

```
{'input_tokens': 8,
 'output_tokens': 304,
 'total_tokens': 312,
 'input_token_details': {'audio': 0, 'cache_read': 0},
 'output_token_details': {'audio': 0, 'reasoning': 256}}
```

有关详细信息，请参阅 `UsageMetadata`。

#### Streaming and chunks

在流式传输期间，您将收到 `AIMessageChunk` 对象，这些对象可以组合成一个完整的 message 对象：

```python
chunks = []
full_message = None
for chunk in model.stream("Hi"):
    chunks.append(chunk)
    print(chunk.text)
    full_message = chunk if full_message is None else full_message + chunk
```

了解更多：

- 从 chat models 流式传输 tokens
- 从 agents 流式传输 tokens 和/或步骤

***

### Tool message

对于支持 tool calling 的模型，AI messages 可以包含 tool calls。Tool messages 用于将单个 tool 执行的结果传递回模型。

Tools 可以直接生成 `ToolMessage` 对象。下面我们展示一个简单的示例。在 tools guide 中阅读更多内容。

```python
from langchain.messages import AIMessage
from langchain.messages import ToolMessage

# 在模型进行 tool call 之后
# （这里为了简洁，我们演示手动创建消息）
ai_message = AIMessage(
    content=[],
    tool_calls=[{
        "name": "get_weather",
        "args": {"location": "San Francisco"},
        "id": "call_123"
    }]
)

# 执行 tool 并创建结果消息
weather_result = "Sunny, 72°F"
tool_message = ToolMessage(
    content=weather_result,
    tool_call_id="call_123"  # 必须与 call ID 匹配
)

# 继续对话
messages = [
    HumanMessage("What's the weather in San Francisco?"),
    ai_message,  # 模型的 tool call
    tool_message,  # Tool 执行结果
]
response = model.invoke(messages)  # 模型处理结果
```

`content`  
tool call 输出的字符串化结果。

`tool_call_id`  
此消息响应的 tool call 的 ID。必须与 `AIMessage` 中的 tool call ID 匹配。

`name`  
被调用的 tool 的名称。

`artifact`  
不发送给模型但可以通过编程方式访问的附加数据。

`artifact` 字段存储不会被发送给模型但可以编程访问的补充数据。这对于存储原始结果、调试信息或用于下游处理的数据非常有用，而不会使模型的上下文混乱。

例如，一个检索 tool 可以从文档中检索一个段落供模型参考。当消息 `content` 包含模型将引用的文本时，`artifact` 可以包含文档标识符或其他应用程序可以使用的元数据（例如，用于呈现页面）。参见下面的示例：

```python
from langchain.messages import ToolMessage

# 发送给模型
message_content = "It was the best of times, it was the worst of times."

# 下游可用的 artifact
artifact = {"document_id": "doc_123", "page": 0}

tool_message = ToolMessage(
    content=message_content,
    tool_call_id="call_123",
    name="search_books",
    artifact=artifact,
)
```

有关使用 LangChain 构建检索 agent 的端到端示例，请参阅 RAG tutorial。

## Message content

您可以将消息的 content 视为发送给模型的数据载荷。消息有一个 `content` 属性，该属性是弱类型的，支持字符串和未类型化对象（例如字典）的列表。这允许在 LangChain chat models 中直接支持 provider 原生结构，例如多模态内容和其他数据。

另外，LangChain 为文本、推理、引用、多模态数据、服务端 tool calls 和其他消息内容提供了专用的 content types。请参阅下面的 content blocks。

LangChain chat models 接受 `content` 属性中的消息内容。

它可以包含以下之一：

1.  一个字符串
2.  一个 provider 原生格式的 content blocks 列表
3.  一个 LangChain 标准 content blocks 列表

下面是一个使用多模态输入的示例：

```python
from langchain.messages import HumanMessage

# 字符串内容
human_message = HumanMessage("Hello, how are you?")

# Provider 原生格式（例如 OpenAI）
human_message = HumanMessage(content=[
    {"type": "text", "text": "Hello, how are you?"},
    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
])

# 标准 content blocks 列表
human_message = HumanMessage(content_blocks=[
    {"type": "text", "text": "Hello, how are you?"},
    {"type": "image", "url": "https://example.com/image.jpg"},
])
```

初始化消息时指定 `content_blocks` 仍然会填充消息的 `content`，但提供了一种类型安全的方式来这样做。

### Standard content blocks

LangChain 为消息内容提供了一种跨 provider 工作的标准表示形式。

Message 对象实现了一个 `content_blocks` 属性，该属性会将 `content` 属性惰性解析为标准的、类型安全的表示形式。例如，从 `ChatAnthropic` 或 `ChatOpenAI` 生成的消息将以各自 provider 的格式包含 `thinking` 或 `reasoning` 块，但可以惰性解析为一致的 `ReasoningContentBlock` 表示形式：

```python
from langchain.messages import AIMessage

message = AIMessage(
	content=[
		{"type": "thinking", "thinking": "...", "signature": "WaUjzkyp..."},
		{"type": "text", "text": "..."},
	],
	response_metadata={"model_provider": "anthropic"}
)
message.content_blocks
```

```
[{'type': 'reasoning',
  'reasoning': '...',
  'extras': {'signature': 'WaUjzkyp...'}},
 {'type': 'text', 'text': '...'}]
```

```python
from langchain.messages import AIMessage

message = AIMessage(
	content=[
		{
			"type": "reasoning",
			"id": "rs_abc123",
			"summary": [
				{"type": "summary_text", "text": "summary 1"},
				{"type": "summary_text", "text": "summary 2"},
			],
		},
		{"type": "text", "text": "...", "id": "msg_abc123"},
	],
	response_metadata={"model_provider": "openai"}
)
message.content_blocks
```

```
[{'type': 'reasoning', 'id': 'rs_abc123', 'reasoning': 'summary 1'},
 {'type': 'reasoning', 'id': 'rs_abc123', 'reasoning': 'summary 2'},
 {'type': 'text', 'text': '...', 'id': 'msg_abc123'}]
```

请参阅集成指南以开始使用您选择的 inference provider。

**序列化标准内容**

  如果 LangChain 之外的应用程序需要访问标准 content block 表示形式，您可以选择将 content blocks 存储在 message content 中。

  为此，您可以将 `LC_OUTPUT_VERSION` 环境变量设置为 `v1`。或者，使用 `output_version="v1"` 初始化任何 chat model：

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5-nano", output_version="v1")
```

### Multimodal

**多模态**是指处理不同形式数据的能力，例如文本、音频、图像和视频。LangChain 包含这些数据的标准类型，可以跨 providers 使用。

Chat models 可以接受多模态数据作为输入，并生成其作为输出。下面我们展示包含多模态数据的输入消息的简短示例。

额外的键可以包含在 content block 的顶层，或嵌套在 `"extras": {"key": value}` 中。

例如，OpenAI 和 AWS Bedrock Converse 需要 PDF 的文件名。有关详细信息，请参阅您所选模型的 provider 页面。

```python
  # 从 URL
  message = {
      "role": "user",
      "content": [
          {"type": "text", "text": "Describe the content of this image."},
          {"type": "image", "url": "https://example.com/path/to/image.jpg"},
      ]
  }

  # 从 base64 数据
  message = {
      "role": "user",
      "content": [
          {"type": "text", "text": "Describe the content of this image."},
          {
              "type": "image",
              "base64": "AAAAIGZ0eXBtcDQyAAAAAGlzb21tcDQyAAACAGlzb2...",
              "mime_type": "image/jpeg",
          },
      ]
  }

  # 从 provider 管理的 File ID
  message = {
      "role": "user",
      "content": [
          {"type": "text", "text": "Describe the content of this image."},
          {"type": "image", "file_id": "file-abc123"},
      ]
  }
```

```python
# 从 URL
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this document."},
        {"type": "file", "url": "https://example.com/path/to/document.pdf"},
    ]
}

# 从 base64 数据
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this document."},
        {
            "type": "file",
            "base64": "AAAAIGZ0eXBtcDQyAAAAAGlzb21tcDQyAAACAGlzb2...",
            "mime_type": "application/pdf",
        },
    ]
}

# 从 provider 管理的 File ID
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this document."},
        {"type": "file", "file_id": "file-abc123"},
    ]
}
```

```python
# 从 base64 数据
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this audio."},
        {
            "type": "audio",
            "base64": "AAAAIGZ0eXBtcDQyAAAAAGlzb21tcDQyAAACAGlzb2...",
            "mime_type": "audio/wav",
        },
    ]
}

# 从 provider 管理的 File ID
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this audio."},
        {"type": "audio", "file_id": "file-abc123"},
    ]
}
```

```python
# 从 base64 数据
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this video."},
        {
            "type": "video",
            "base64": "AAAAIGZ0eXBtcDQyAAAAAGlzb21tcDQyAAACAGlzb2...",
            "mime_type": "video/mp4",
        },
    ]
}

# 从 provider 管理的 File ID
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this video."},
        {"type": "video", "file_id": "file-abc123"},
    ]
}
```

并非所有模型都支持所有文件类型。请查阅模型 provider 的参考文档以了解支持的格式和大小限制。

### Content block reference

Content blocks 在创建消息或访问 `content_blocks` 属性时表示为类型化字典的列表。列表中的每个项必须遵循以下块类型之一。

---

#### text

**用途:** 标准文本输出

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"text"` |
| text | str | 是 | 文本内容 |
| annotations | list | 否 | 文本的注释列表 |
| extras | dict | 否 | 附加的 provider 特定数据 |

**示例:**

```python
{
    "type": "text",
    "text": "Hello world",
    "annotations": []
}
```

---

#### reasoning

**用途:** 模型推理步骤

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"reasoning"` |
| reasoning | str | 是 | 推理内容 |
| extras | dict | 否 | 附加的 provider 特定数据 |

**示例:**

```python
{
    "type": "reasoning",
    "reasoning": "The user is asking about...",
    "extras": {"signature": "abc123"},
}
```

---

#### image

**用途:** 图像数据

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"image"` |
| url | str | 否 | 指向图像位置的 URL |
| base64 | str | 否 | Base64 编码的图像数据 |
| id | str | 否 | 此 content block 的唯一标识符（由 provider 或 LangChain 生成） |
| mime_type | str | 否 | 图像 MIME 类型（例如 `image/jpeg`、`image/png`）；base64 数据需要此字段 |

---

#### audio

**用途:** 音频数据

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"audio"` |
| url | str | 否 | 指向音频位置的 URL |
| base64 | str | 否 | Base64 编码的音频数据 |
| id | str | 否 | 此 content block 的唯一标识符（由 provider 或 LangChain 生成） |
| mime_type | str | 否 | 音频 MIME 类型（例如 `audio/mpeg`、`audio/wav`）；base64 数据需要此字段 |

---

#### video

**用途:** 视频数据

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"video"` |
| url | str | 否 | 指向视频位置的 URL |
| base64 | str | 否 | Base64 编码的视频数据 |
| id | str | 否 | 此 content block 的唯一标识符（由 provider 或 LangChain 生成） |
| mime_type | str | 否 | 视频 MIME 类型（例如 `video/mp4`、`video/webm`）；base64 数据需要此字段 |

---

#### file

**用途:** 通用文件（PDF 等）

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"file"` |
| url | str | 否 | 指向文件位置的 URL |
| base64 | str | 否 | Base64 编码的文件数据 |
| id | str | 否 | 此 content block 的唯一标识符（由 provider 或 LangChain 生成） |
| mime_type | str | 否 | 文件 MIME 类型（例如 `application/pdf`）；base64 数据需要此字段 |

---

#### text-plain

**用途:** 文档文本（`.txt`、`.md`）

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"text-plain"` |
| text | str | 是 | 文本内容 |
| mime_type | str | 是 | 文本的 MIME 类型（例如 `text/plain`、`text/markdown`） |

---

#### tool_call

**用途:** 函数调用

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"tool_call"` |
| name | str | 是 | 要调用的 tool 的名称 |
| args | dict | 是 | 传递给 tool 的参数 |
| id | str | 是 | 此 tool call 的唯一标识符 |

**示例:**

```python
{
    "type": "tool_call",
    "name": "search",
    "args": {"query": "weather"},
    "id": "call_123"
}
```

---

#### tool_call_chunk

**用途:** 流式 tool call 片段

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"tool_call_chunk"` |
| name | str | 否 | 被调用的 tool 的名称 |
| args | str | 否 | 部分 tool 参数（可能是不完整的 JSON） |
| id | str | 否 | Tool call 标识符 |
| index | int | 是 | 此 chunk 在流中的位置 |

---

#### invalid_tool_call

**用途:** 格式错误的调用，旨在捕获 JSON 解析错误

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"invalid_tool_call"` |
| name | str | 是 | 调用失败的 tool 的名称 |
| args | str | 是 | 传递给 tool 的参数 |
| error | str | 是 | 出错描述 |

---

#### server_tool_call

**用途:** 在服务端执行的 tool call

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"server_tool_call"` |
| id | str | 是 | 与 tool call 关联的标识符 |
| name | str | 是 | 要调用的 tool 的名称 |
| args | str | 否 | 部分 tool 参数（可能是不完整的 JSON） |

---

#### server_tool_call_chunk

**用途:** 流式服务端 tool call 片段

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"server_tool_call_chunk"` |
| id | str | 是 | 与 tool call 关联的标识符 |
| name | str | 是 | 被调用的 tool 的名称 |
| args | str | 否 | 部分 tool 参数（可能是不完整的 JSON） |
| index | int | 是 | 此 chunk 在流中的位置 |

---

#### server_tool_result

**用途:** 搜索结果

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"server_tool_result"` |
| tool_call_id | str | 是 | 相应服务端 tool call 的标识符 |
| id | str | 否 | 与服务端 tool result 关联的标识符 |
| status | str | 是 | 服务端 tool 的执行状态（`"success"` 或 `"error"`） |
| content | str | 否 | 执行 tool 的输出 |

---

#### non_standard

**用途:** Provider 特定的应急方案

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| type | str | 是 | 始终为 `"non_standard"` |
| data | any | 是 | Provider 特定的数据结构 |

**用法:** 用于实验性或 provider 独有的功能。

---

其他 provider 特定的 content types 可以在每个模型 provider 的参考文档中找到。在 API 参考中查看规范的类型定义。

Content blocks 在 LangChain v1 中作为消息的新属性引入，目的是标准化跨 provider 的内容格式，同时保持与现有代码的向后兼容性。Content blocks 不是 `content` 属性的替代品，而是一个新属性，可用于以标准化格式访问消息内容。

## Use with chat models

Chat models 接受一系列 message 对象作为输入，并返回一个 `AIMessage` 作为输出。交互通常是无状态的，因此一个简单的对话循环涉及使用不断增长的消息列表调用模型。

请参考以下指南以了解更多信息：

- 持久化和管理对话历史的内置功能
- 管理上下文窗口的策略，包括修剪和总结消息