# 事件流式传输深度索引

> 这是 Deep Agents 事件流式传输的**概念地图**，涵盖 subagent 投影、消息与工具调用流、生命周期跟踪、嵌套消费和并发交错。  
> 阅读本文档可一次性掌握如何从代理及其子代理中实时获取结构化的执行事件。

---

## 概念全景

Deep Agents 在 LangGraph 流式传输基础上提供**subagent 投影**，使每个委派任务（`task` 调用）都有独立的流句柄。核心入口是 `agent.stream_events()`，返回的流对象提供 `messages`、`tool_calls`、`subagents`、`output` 等投影，并支持递归进入嵌套子代理。

通过 `version="v3"` 启用最新的流式传输协议。

---

## 1. Subagent 流投影

### 访问方式
```python
stream = agent.stream_events(input, version="v3")
for subagent in stream.subagents:
    # 每个 subagent 有独立的流句柄
```

### 可用字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | `str` | 子代理名称 |
| `path` | `tuple` | 子代理流的命名空间路径 |
| `status` | `str` | 生命周期状态：`started`、`completed`、`failed`、`interrupted` |
| `messages` | 可迭代 | 子代理发出的消息（延迟加载） |
| `tool_calls` | 可迭代 | 子代理范围内的工具调用（延迟加载） |
| `subagents` | 可迭代 | 嵌套的子代理（递归结构） |
| `output` | 阻塞属性 | 最终子代理状态或完成信号；访问会阻塞直到完成或失败 |

---

## 2. 跟踪生命周期

仅使用 `stream.subagents` 和 `subagent.status`/`subagent.output` 即可展示子代理的启动和完成情况，无需订阅具体消息流。

```python
for subagent in stream.subagents:
    print(f"{subagent.name}: started")
    try:
        _ = subagent.output   # 等待完成
        print(f"{subagent.name}: completed")
    except Exception:
        print(f"{subagent.name}: failed")
```

---

## 3. 流式传输消息与工具调用

- **协调器消息**：`stream.messages`
- **子代理消息**：`subagent.messages`
- **协调器工具调用**：`stream.tool_calls`
- **子代理工具调用**：`subagent.tool_calls`

工具调用提供 `tool_name`、`input`、`output`（完成时）和 `output_deltas`（实时增量）。

### 工具调用增量流示例
```python
for call in subagent.tool_calls:
    print(f"{call.tool_name}({call.input})")
    for delta in call.output_deltas:
        print(delta, end="", flush=True)
    if call.completed and not call.error:
        print(call.output)
```

---

## 4. 嵌套工作递归消费

可以进入子代理的 `subagent.subagents` 以观察更深层级的委派，实现全树遍历。

```python
for subagent in stream.subagents:
    print(f"{subagent.name}: {subagent.status}")
    for nested in subagent.subagents:
        print(f"nested {nested.name}: {nested.status}")
```

---

## 5. 并发交错消费

协调器和子代理的输出常常交错。提供两种处理方式：

### 结构化交错
```python
for name, item in stream.interleave("messages", "subagents"):
    if name == "messages":
        print("[coordinator]", item.text)
    else:
        for msg in item.messages:
            print(f"[{item.name}]", msg.text)
```

### 原始协议遍历（精确到达顺序）
通过检查事件中的 `namespace` 字段区分来源：
```python
for event in stream:
    if event["method"] == "messages" and event["params"]["data"].get("event") == "content-block-delta":
        source = "subagent" if event["params"]["namespace"] else "coordinator"
        print(f"[{source}] {event['params']['data']['delta']['text']}")
```

---

## 6. Subagents 与 Subgraphs 的区别

| 投影 | 用途 | 面向 |
|------|------|------|
| `stream.subgraphs` | 展示底层图执行结构（内部节点） | 调试、框架开发者 |
| `stream.subagents` | 展示产品级任务委派，隐藏内部细节 | 用户界面构建 |

构建面向用户的 UI 时应使用 `stream.subagents`。

---

## 与全局概念的关联

- **[子代理系统](index/langchain-index/deepagent/concepts/subagent.md)**：`stream.subagents` 直接映射到同步和异步子代理的创建与完成事件，是子代理可观测性的基础。
- **[上下文工程](index/langchain-index/deepagent/concepts/context_engineering.md)**：通过流式传输可以实时监控代理的输出和工具使用，辅助动态上下文调整（如触发摘要或中断）。
- **[人机协同](index/langchain-index/deepagent/concepts/Human-in-the-loop.md)**：在流式传输中可集成中断处理，当 `status` 为 `interrupted` 时暂停 UI 等待决策。
- **LangGraph 底层**：Deep Agents 流式传输基于 LangGraph 事件流，`version="v3"` 使用最新的流式协议；`stream.subgraphs` 可提供更底层的调试视图。
- **生产部署**：流式传输设计支持并发消费，适合构建实时多面板 UI（如同时展示协调器对话和子代理任务卡片）。

## 链接原文

当本索引中的概要无法满足你（例如需要完整代码实现、方法签名、罕见配置示例）时，请通过以下方式从原始文档中获取精确信息。

### 语义检索（聚焦查询）

原始文档已按 `#` 级别标题切分并向量化。构造查询时，**使用当前索引章节的标题或段落内出现的关键概念、特殊术语作为锚点**，而不是全文反复出现的通用词。有效的查询往往短而具体。

例如，当你在本索引的“Subagent 流投影”一节需要更多细节时：

- **好的查询**：`subagent 流投影 name path status`、`output 阻塞属性 延迟加载`、`stream_events version v3`
- **差的查询**：`如何流式传输`（整个文档都在讲流式传输，无法聚焦）

将标题词和段落内的特有术语组合，可以快速锁定目标段落。

### 利用索引页提升检索精度

如果单靠关键术语检索结果仍不够集中，从本索引中提取**所在章节的标题**或**当前段落的特有表述**作为附加上下文，与你的问题组合成更完整的查询。索引页的标题本身就是高质量的语义锚点。例如：

- 想了解“工具调用增量流”的具体代码，用 `流式传输消息与工具调用 output_deltas 增量流` 组合查询。
- 想了解“嵌套工作递归消费”如何遍历深层子代理，用 `嵌套工作递归消费 全树遍历 subagent.subagents` 定位。
- 想查询“并发交错消费”的两种处理方式，用 `并发交错消费 结构化交错 interleave 原始协议遍历` 找到示例。

### 标题路径兜底

语义检索返回的每个片段都携带其**原文标题和文件路径**。若需读取该章节的完整内容或进入相邻段落，可直接用返回结果中的标题坐标通过 `read_file` 精确定位——标题始终精确，因为它来自原文本身。