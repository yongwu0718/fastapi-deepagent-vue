# Streaming

> 这是 LangChain Agent 中**传统流式传输（Stream / Astream）**的胖索引，覆盖 `updates`、`messages`、`custom` 三种流式模式、组合使用、常见流式场景（推理、工具调用、人机协同、子 Agent）、v2 统一格式及最佳实践。
> 阅读本文档可一次性掌握传统流式体系的全部概念及其关联，为构建实时交互式 Agent 应用提供决策支撑。

---

## 概念全景

LangChain 基于 LangGraph 的 `stream()` / `astream()` 方法提供了一套灵活的流式系统。你可以通过传递不同的 `stream_mode` 来获取 Agent 运行过程中的不同维度的实时更新，并结合 `version="v2"` 获得统一的响应格式。

| 流式模式 (stream_mode) | 提供的能力                                                     | 典型用途                               |
| ---------------------- | -------------------------------------------------------------- | -------------------------------------- |
| `updates`              | 每个 Agent 步骤后的状态更新（如 `model` → `tools` → `model`）   | 展示 Agent 执行进度、状态快照          |
| `messages`             | LLM 调用时流出的 token 与元数据（包含推理、工具调用块）         | 打字机效果、实时工具调用参数展示       |
| `custom`               | 通过 `get_stream_writer()` 从工具或节点内部发出的任意自定义数据  | 进度条、自定义事件、非标准输出         |

核心决策点：**选择一种或多种流式模式组合、是否启用 v2 格式、如何命名 Agent 以区分多 Agent 输出、是否禁用部分模型的流式**，共同决定了前端展示的丰富度和复杂度。

---

## 1. 流式模式详解

### Agent 进度 (`updates`)

每次 Agent 步进（节点完成）时返回该节点的状态变更，让你了解 Agent 正在做什么。

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "..."}]},
    stream_mode="updates",
    version="v2",
):
    if chunk["type"] == "updates":
        for step, data in chunk["data"].items():
            print(step, data["messages"][-1].content_blocks)
```

典型输出顺序：`model` → `tools` → `model`（若需要再调用工具则循环）。

### LLM tokens (`messages`)

实时流式传输模型生成的每个 token 及其元数据（节点名、Agent 名等）。对于理解模型“正在想什么”和展示打字机效果至关重要。

```python
for chunk in agent.stream(..., stream_mode="messages", version="v2"):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        print(metadata["langgraph_node"], token.content_blocks)
```

### 自定义更新 (`custom`)

工具或节点内部通过 `get_stream_writer()` 推送任意字符串或对象，非常适合进度反馈、调试信息或业务事件。

```python
def get_weather(city: str) -> str:
    writer = get_stream_writer()
    writer(f"Fetching {city} ...")
    return f"It's always sunny in {city}!"
```

随后在流式循环中通过 `stream_mode="custom"` 捕获。

---

## 2. 组合多种流式模式

你可以同时使用多种模式，只需将 `stream_mode` 设为列表，如 `["updates", "messages", "custom"]`。v2 格式下每个 chunk 都是 `{"type": "...", "ns": [...], "data": ...}` 的统一字典，很容易按 `type` 字段分发。

```python
for chunk in agent.stream(input, stream_mode=["updates", "custom"], version="v2"):
    if chunk["type"] == "updates":
        ...
    elif chunk["type"] == "custom":
        ...
```

---

## 3. 常见流式场景

### 推理/思考 tokens

筛选 `messages` 模式中 `content_blocks` 里 `type="reasoning"` 的块即可展示模型的思考过程（需模型支持且启用推理）。

```python
for token, metadata in agent.stream(..., stream_mode="messages"):
    reasoning = [b for b in token.content_blocks if b["type"] == "reasoning"]
    if reasoning:
        print(reasoning[0]["reasoning"], end="")
```

### 工具调用流式

通过 `messages` 模式可获得工具调用参数的增量构建过程（`tool_call_chunks`）；若要获取完整的已解析调用，可以同时使用 `messages` + `updates`，从 `updates` 中的完整 `AIMessage` 提取 `tool_calls`。或者使用自定义事件或手动聚合。

```python
# 同时使用 messages + updates 获得完整调用
for chunk in agent.stream(..., stream_mode=["messages", "updates"], version="v2):
    if chunk["type"] == "messages":
        # 增量参数
        token, _ = chunk["data"]
        print(token.tool_call_chunks)
    elif chunk["type"] == "updates":
        for _, update in chunk["data"].items():
            if hasattr(update["messages"][-1], "tool_calls"):
                print(update["messages"][-1].tool_calls)  # 完整调用列表
```

### 人机协同 (Human-in-the-loop)

使用 `HumanInTheLoopMiddleware` 并配置 checkpointer 后，在 `updates` 模式下可捕获 `__interrupt__` 源的中断。收集中断后可调用 `Command(resume=decisions)` 继续执行。

### 子 Agent 流式

为每个通过 `create_agent` 创建的 Agent 指定 `name`，并在流式调用时启用 `subgraphs=True`。通过 `metadata["lc_agent_name"]` 即可区分 token 来源，从而在前端按不同 Agent 分别展示。

```python
weather_agent = create_agent(..., name="weather_agent")
supervisor = create_agent(..., tools=[...], name="supervisor")

for chunk in supervisor.stream(..., stream_mode="messages", subgraphs=True, version="v2"):
    if chunk["type"] == "messages":
        _, metadata = chunk["data"]
        current_agent = metadata.get("lc_agent_name")
        ...
```

---

## 4. v2 流式格式

启用 `version="v2"` 后，所有 chunk 变为 `StreamPart` 字典，包含 `type`, `ns`, `data` 三个键，避免了旧版本中按模式解包元组的麻烦。同时 `invoke()` 返回 `GraphOutput` 对象，提供了 `.value` 和 `.interrupts` 属性，将最终状态与中断元数据清晰分离。

```python
result = agent.invoke(..., version="v2")
print(result.value)       # 最终状态
print(result.interrupts)  # 中断列表
```

建议新项目中统一采用 v2 格式。

---

## 5. 禁用流式

若需在多 Agent 场景中控制哪些模型输出被流式传输，可在初始化模型时设置 `streaming=False`。部署到 LangSmith 时同样适用。

```python
model = ChatOpenAI(model="gpt-5.4", streaming=False)
```

并非所有集成支持该参数，也可使用 `disable_streaming=True` 作为备选。

---

## 6. 关键约束与最佳实践

- **选择合适的模式组合**：不要为了“多用”而加入所有模式，仅流式传输前端真正需要的数据以降低开销。
- **v2 格式优先**：统一的结构让代码更简洁，且对中断、子图等支持更好。
- **子 Agent 命名**：在构建多 Agent 系统时，务必为每个 Agent 指定唯一的 `name`，以便在 `metadata["lc_agent_name"]` 中区分输出。
- **工具调用完整获取**：`messages` 模式仅提供增量，若需要完整调用，建议同时使用 `updates` 模式或自定义事件；避免在手动聚合时因流结束信号导致的时序问题。
- **人机中断处理**：中断决策的收集顺序必须与 `__interrupt__` 中 `action_requests` 的顺序严格一致。
- **推理展示**：使用 `content_blocks` 而非 provider 特定字段来提取推理内容，保证跨模型可移植性。
- **禁用部分流式**：在混合使用不同模型或需要控制前端流量时，合理禁用某些模型的 token 流式。

---

## 7. 与全局概念的关联

- **事件流式传输 (Event Streaming v3)**：传统 `stream()` 方法提供底层的流式模式；对于大多数新应用，推荐使用更高层的 `stream_events(version="v3")`，它内置了更友好的投影（如 `stream.messages`、`stream.tool_calls`）。
- **消息 (Messages)**：`messages` 模式流出的 `AIMessageChunk` 和完整 `AIMessage` 是消息体系的一部分，包含 `content_blocks`、`usage_metadata` 等。
- **工具 (Tools)**：工具调用参数通过 `tool_call_chunks` 流式输出；工具内部的 `get_stream_writer()` 通过 `custom` 模式推送进度。
- **短期记忆 (Short-term memory)**：`updates` 模式反映的正是 Agent 状态的变化，是短期记忆的快照流。
- **后端 (Backends)** / **子 Agent**：通过 `subgraphs` 参数可流式传输嵌套子 Agent 或子图内部的执行细节。
- **人机协同 (Human-in-the-loop)**：流式系统原生支持捕获中断并通过 `Command` 恢复，实现审查流程。

---

## 链接原文

### 语义检索（聚焦查询）

- `stream_mode updates messages custom` → 三种基本模式
- `get_stream_writer 自定义更新` → 自定义数据推送
- `stream_mode=["updates", "custom"] 组合` → 多模式组合
- `推理 thinking tokens reasoning content_blocks` → 流式思考
- `tool_call_chunks AIMessage tool_calls 完整调用` → 工具调用流式
- `HumanInTheLoopMiddleware interrupt __interrupt__ Command resume` → 人机中断流式
- `lc_agent_name 子 agent 流式 subgraphs=True` → 多 Agent 流式
- `version="v2" StreamPart GraphOutput` → v2 格式
- `streaming=False disable_streaming` → 禁用流式

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## Agent progress`、`### 流式传输思考 / 推理 tokens`、`### 从子 agents 流式传输`），可用 `read_file` 精确定位对应章节。