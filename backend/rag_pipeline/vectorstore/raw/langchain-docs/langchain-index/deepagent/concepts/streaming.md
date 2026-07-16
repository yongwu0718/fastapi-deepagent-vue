# Streaming 深度索引

> 这是 Deep Agents 流式传输系统的**概念地图**，涵盖基础流式传输、subagent 投影、命名空间、LLM token 流、工具调用流、自定义更新和多种模式组合。  
> 阅读本文档可一次性掌握如何从代理及其子代理获取实时执行事件，并构建响应式 UI。

---

## 概念全景

Deep Agents 流式传输建立在 LangGraph 的 subgraph streaming 之上，为 subagent 委派任务提供**一等支持**。你可以独立地从每个 subagent 获取进度、token、工具调用和自定义事件，而无需手动解析嵌套结构。

推荐使用 **v2 流式传输格式** (`version="v2"`)，它提供统一的 `StreamPart` 字典，包含 `type`、`ns`（命名空间）和 `data`。

**能实现的核心功能**：
- 实时跟踪 subagent 执行进度
- 从主代理和每个 subagent 流式传输 LLM token
- 捕获 subagent 内部的工具调用及其结果
- 通过 `get_stream_writer` 发送自定义事件

> 对于新应用，Deep Agents v0.6 引入的**事件流式传输**（typed projection API）是更高级的选择，它提供独立的迭代器（`stream.subagents`、`stream.messages` 等）。本索引覆盖基础流式传输（`agent.stream`），事件流式传输见[事件流式传输深度索引](./event_streaming.md)。

---

## 1. 启用 subgraph 流式传输

要接收 subagent 事件，必须在调用 `agent.stream` 时设置 `subgraphs=True`，并指定 `version="v2"`。

```python
for chunk in agent.stream(
    input,
    stream_mode="updates",
    subgraphs=True,
    version="v2",
):
    # chunk 包含 'type', 'ns', 'data'
```

- `stream_mode` 可以为单个字符串或列表，支持 `"updates"`、`"messages"`、`"custom"`。
- 省略 `subgraphs=True` 则只接收顶层代理的事件。

---

## 2. 命名空间 (Namespace)

每个事件携带一个命名空间元组 `ns`，用于标识事件来源：

| Namespace | 来源 |
|-----------|------|
| `()` 空元组 | 主代理 |
| `("tools:<call_id>",)` | 由 `task` 工具调用 `call_id` 产生的 subagent |
| `("tools:<call_id>", "model_request:...")` | subagent 内部的特定节点 |

利用 `ns` 可以将事件路由到不同的 UI 组件。判断是否为 subagent 事件的标准：`any(s.startswith("tools:") for s in chunk["ns"])`。

---

## 3. 流模式详解

### 3.1 Subagent 进度 (`stream_mode="updates"`)

以节点为粒度报告代理的执行步骤。每个更新包含一个节点名称到数据的映射。通过 `chunk["ns"]` 区分主代理与子代理，适合展示“谁在做什么”。

- 主代理的 `tools` 节点返回 subagent 的最终结果时，消息类型为 `tool`，包含 `msg.name` 和 `msg.content`。
- 使用 `INTERESTING_NODES` 过滤掉中间件内部节点（如保留 `model_request`、`tools`）。

### 3.2 LLM Token 流 (`stream_mode="messages"`)

实时流式传输模型生成的 token。`chunk["data"]` 为 `(token, metadata)` 元组。

- `token.tool_call_chunks`：包含增量工具调用参数，可用于构建工具调用 UI。
- `token.type == "tool"`：工具结果消息。
- 可根据 `ns` 切换来源标签（main agent 或具体 subagent）。

### 3.3 工具调用流 (Tool Calls)

工具调用信息嵌入在 `messages` 模式中。可通过检查 `token.tool_call_chunks` 获取名称和参数增量，通过 `token.type == "tool"` 获取结果。适用于显示每个 subagent 内部正在使用哪些工具。

### 3.4 自定义更新 (`stream_mode="custom"`)

在工具或节点内部使用 `get_stream_writer()` 发出任意字典事件，用于报告进度、阶段性状态等。在 `stream_mode="custom"` 下会收到这些事件，同样通过 `ns` 区分来源。

---

## 4. 组合多种流模式

通过 `stream_mode=["updates", "messages", "custom"]` 可同时接收多种类型的事件。在处理循环中根据 `chunk["type"]` 分支处理。注意处理 token 流时保持行内打印状态（`mid_line` 标志），以便在不同来源切换时插入换行和标题。

---

## 5. 常见模式

### 跟踪 Subagent 生命周期

通过监听主代理 `model_request` 中的 `task` 工具调用检测启动；通过 `tools:` namespace 事件检测运行；通过主代理 `tools` 节点中的 `tool` 消息检测完成。可实现一个状态字典追踪 `pending → running → complete`。

### 前端集成

LangGraph 的 v2 流式传输格式兼容 `useStream` 等 React Hook，可构建实时多面板 UI，并利用 namespace 区分 coordinator 和 subagent 卡片。

---

## 6. v2 流式传输格式优势

相比于传统的 `(namespace, (mode, data))` 嵌套元组，v2 格式统一为 `{"type": ..., "ns": ..., "data": ...}` 字典，消除了解包歧义，尤其简化了 subgraph streaming 的多层级事件处理。

---

## 与全局概念的关联

- **[子代理系统](index/langchain-index/deepagent/concepts/subagent.md)**：流式传输的 subagent 命名空间和生命周期直接对应 `SubAgent` 的创建与完成。
- **[事件流式传输](stream_event.md)**：当需要更高阶的独立迭代器（`stream.subagents`、`subagent.messages` 等）时，应使用 v0.6 引入的事件流式传输 API。
- **[上下文工程](index/langchain-index/deepagent/concepts/context_engineering.md)**：通过实时观察代理输出和工具使用，可动态触发上下文压缩、中断或人工干预。
- **[人机协同](index/langchain-index/deepagent/concepts/Human-in-the-loop.md)**：可在检测到中断事件 (`interrupted` 状态) 时暂停 UI 并等待决策。
- **生产部署**：支持并发消费、token 级别增量渲染，适合构建聊天界面、任务控制台等交互式应用。

## 链接原文

当本索引中的概要无法满足你（例如需要完整代码实现、方法签名、罕见配置示例）时，请通过以下方式从原始文档中获取精确信息。

### 语义检索（聚焦查询）

原始文档已按 `#` 级别标题切分并向量化。构造查询时，**使用当前索引章节的标题或段落内出现的关键概念、特殊术语作为锚点**，而不是全文反复出现的通用词。有效的查询往往短而具体。

例如，当你在本索引的“命名空间 (Namespace)”一节需要更多细节时：

- **好的查询**：`命名空间 ns tools:call_id 空元组`、`chunk["ns"] 区分主代理与子代理`、`any(s.startswith("tools:") for s in chunk["ns"])`
- **差的查询**：`如何流式传输`（整个文档都在讲流式传输，无法聚焦）

将标题词和段落内的特有术语组合，可以快速锁定目标段落。

### 利用索引页提升检索精度

如果单靠关键术语检索结果仍不够集中，从本索引中提取**所在章节的标题**或**当前段落的特有表述**作为附加上下文，与你的问题组合成更完整的查询。索引页的标题本身就是高质量的语义锚点。例如：

- 想了解“LLM Token 流”中 `tool_call_chunks` 的增量渲染方式，用 `LLM Token 流 tool_call_chunks 增量工具调用参数` 组合查询。
- 想了解“组合多种流模式”时处理跨来源 token 流中断的 `mid_line` 标志，用 `组合多种流模式 mid_line 行内打印状态` 定位。
- 想查询“跟踪 Subagent 生命周期”中状态字典的实现，用 `常见模式 跟踪 Subagent 生命周期 pending running complete` 找到示例。

### 标题路径兜底

语义检索返回的每个片段都携带其**原文标题和文件路径**。若需读取该章节的完整内容或进入相邻段落，可直接用返回结果中的标题坐标通过 `read_file` 精确定位——标题始终精确，因为它来自原文本身。