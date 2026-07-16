# 事件流式传输

> 这是 LangChain / LangGraph Agent 中**事件流式传输**的胖索引，覆盖 Event Streaming v3 架构、核心投影（Projections）、子代理流、自定义更新、并发消费模式及最佳实践。
> 阅读本文档可一次性掌握流式传输体系的全部概念及其关联，为前端实时交互与调试提供决策支撑。

---

## 概念全景

事件流式传输通过 `agent.stream_events(input, version="v3")` 返回一个带类型化投影的实时运行对象。它摒弃了手动解析 `stream_mode` 元组的繁琐，直接提供 `messages`、`tool_calls`、`values`、`subgraphs` 等即用通道。

| 投影（Projection）      | 提供的能力                                     | 典型用途                       |
| ----------------------- | ---------------------------------------------- | ------------------------------ |
| `stream` (原始迭代)     | 完整事件信封，可访问所有 channel                 | 调试、访问未封装的底层事件     |
| `stream.messages`       | 每个 LLM 调用的消息流，含 `text`、`reasoning`、`tool_calls`、`output` | 流式对话展示、推理步骤         |
| `message.text`          | 文本增量与最终完整文本                           | 打字机效果                     |
| `message.reasoning`     | 模型推理增量（需模型支持）                       | 展示思维链                     |
| `message.tool_calls`    | 工具调用参数的构建过程及完成的调用列表           | 显示模型正在选择的工具和参数   |
| `stream.tool_calls`     | 工具执行的完整生命周期（输入、输出增量、结果）   | 展示工具执行进度与结果         |
| `stream.values`         | Agent 状态快照                                  | 实时状态监控                   |
| `stream.output`         | 最终 Agent 状态                                 | 运行结束后的完整上下文         |
| `stream.subgraphs`      | 嵌套子图（子 Agent / 子图）的事件，可按名称过滤 | 多 Agent 协作的流式监控        |
| `stream.extensions`     | 自定义 Transformer 生成的投影                   | 检索进度、领域特定事件         |

核心决策点：**选择哪些投影组合、如何命名子 Agent 以便过滤、是否编写自定义 Transformer、采用同步 `interleave` 还是异步 `gather` 进行多投影消费**。

---

## 1. 基础用法与架构

```python
stream = agent.stream_events({"messages": [...]}, version="v3")

for message in stream.messages:
    for delta in message.text:
        print(delta, end="", flush=True)

final_state = stream.output
```

- `stream_events` 返回的流对象支持多种投影属性，可独立迭代。
- 所有投影设计为既可实时消费增量，也可最终获取完整值（如 `str(message.text)` 或 `message.output`）。

---

## 2. 核心投影详解

### stream.messages —— 对话消息流

每个 LLM 调用产生一个 `ChatModelStream` 对象，提供：

- `message.text`：文本 delta 迭代器（`for delta in message.text: ...`），`str(message.text)` 获取最终文本。
- `message.reasoning`：推理 delta 迭代器（仅支持推理内容的模型）。
- `message.tool_calls`：工具调用参数 chunk 的迭代，`message.tool_calls.get()` 返回完成的调用列表。
- `message.output`：调用完成后的 `AIMessage`，含 `usage_metadata`。

```python
for message in stream.messages:
    full_message = message.output
    usage = full_message.usage_metadata  # token 统计
```

### stream.tool_calls —— 工具执行生命周期

提供 `tool_name`、`input`、`output_deltas`（实时输出增量）、`output`（最终结果）、`error`。

```python
for call in stream.tool_calls:
    print(f"{call.tool_name}({call.input})")
    for delta in call.output_deltas:
        print(delta, end="")
```

与 `message.tool_calls` 区分：前者是模型生成调用参数时的流，后者是工具实际执行时的流。

### stream.values / stream.output —— 状态快照

```python
for snapshot in stream.values:
    print(snapshot)
final_state = stream.output
```

### stream.subgraphs —— 子 Agent 流

当父 Agent 通过工具调用子 Agent 时，子 Agent 的内部流通过 `subgraphs` 暴露。每个子图拥有独立的 `.messages`、`.values`、`.tool_calls`、`.output`。

通过 `subagent.graph_name` 过滤（即 `create_agent` 的 `name` 参数）：

```python
for subagent in stream.subgraphs:
    if subagent.graph_name == "weather_agent":
        for message in subagent.messages:
            print(message.text)
```

同样适用于通过 `.compile(name=...)` 命名的普通 `StateGraph`。

### stream.extensions —— 自定义投影

传递 `transformers` 列表，通过 `stream.extensions["key"]` 获取自定义事件流。

---

## 3. 多投影并发消费

### 异步：`asyncio.gather` + `astream_events`

```python
async def consume_messages():
    async for message in stream.messages:
        ...

async def consume_tool_calls():
    async for call in stream.tool_calls:
        ...

await asyncio.gather(consume_messages(), consume_tool_calls())
```

### 同步：`stream.interleave()`

```python
for name, item in stream.interleave("messages", "tool_calls", "values"):
    if name == "messages":
        print(item.text)
    elif name == "tool_calls":
        print(item.tool_name, item.input)
```

### 原始事件访问

```python
for event in stream:
    print(event["method"], event["params"]["namespace"], event["params"]["data"])
```

---

## 4. 最佳实践

- **v3 优先**：生产代码统一使用 `version="v3"`，不再手动处理 `stream_mode` 元组。
- **按需组合投影**：仅消费 UI 需要的通道，避免不必要的开销。
- **推理展示**：若模型支持推理，务必消费 `message.reasoning` 以向用户展示思考过程。
- **子 Agent 命名**：`create_agent(name=...)` 必须明确，便于在 `subgraphs` 中按名称过滤。
- **并发消费**：同步代码用 `interleave`，异步代码用 `gather`；避免在循环内混合阻塞操作。
- **最终值获取时机**：`message.output` 和 `message.tool_calls.get()` 应在对应消息流结束后使用。
- **自定义扩展**：当内置投影不足以表达业务事件时，编写 `Transformer` 并通过 `extensions` 访问，遵循 LangGraph 的 transformer 合约。

---

## 5. 与全局概念的关联

- **模型 (Models)**：流式输出直接依赖模型的流式能力；`reasoning` 投影需要模型支持推理内容块。
- **工具 (Tools)**：`stream.tool_calls` 展示了工具执行的全过程，与 `ToolRuntime` 中的 `stream_writer` 推送形成互补。
- **短期记忆 (Short-term memory)**：`stream.values` 和 `stream.output` 反映的正是 Agent 状态，即短期记忆的快照与最终态。
- **子代理 (Sub-agents)**：`stream.subgraphs` 是构建多 Agent 系统时进行监控和调试的核心通道。
- **后端 (Backends)**：后端工具（如 `execute`）的输出可通过 `stream.tool_calls` 或 `stream.extensions` 实时流式返回。
- **上下文压缩**：流式传输不直接影响压缩策略，但通过 `stream.values` 可观察消息长度变化，辅助触发压缩。

---

## 链接原文

### 语义检索（聚焦查询）

- `stream_events version="v3"` → 基础调用与架构
- `projections messages text reasoning tool_calls` → 核心投影清单
- `message.tool_calls get finalized` → 模型工具调用流
- `stream.tool_calls output_deltas output error` → 工具执行流
- `subgraphs graph_name weather_agent` → 子代理流过滤
- `interleave gather 并发消费` → 多投影消费模式
- `transformers extensions 自定义` → 自定义投影编写
- `stream.output usage_metadata` → 最终状态与 token 用量

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## Agent messages`、`### Tool calls`、`### 流式传输 sub-agents`），可用 `read_file` 精确展开对应章节。