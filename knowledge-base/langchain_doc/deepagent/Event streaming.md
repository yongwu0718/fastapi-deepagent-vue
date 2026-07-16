# 事件流式传输

> 从 Deep Agents 中流式传输 subagents、messages、tool calls 以及最终输出。

本页介绍 Deep Agents 特有的流式传输关注点——最重要的是，通过 `stream.subagents` 从委托的 subagents 进行流式传输。有关一般 agent 流式传输（`stream.messages`、`stream.values`、tool calls、自定义更新），请参阅 LangChain Event Streaming。
## 流式传输 subagents

Deep Agents 在 LangGraph 流式传输之上增加了 subagent 投影。当你希望每个委托的 `task` 调用都有一个独立的流句柄时，可以使用 `stream.subagents`。该投影是轻量级的：它首先发现 subagent 任务，而 message、tool-call 和 value 流仅在你访问 subagent 句柄上的相应内容时才会打开。

```python
stream = agent.stream_events({
    "messages": [{"role": "user", "content": "Write me a haiku about the sea"}],
}, version="v3")

for subagent in stream.subagents:
    print(subagent.name, subagent.path, subagent.status)

    for message in subagent.messages:
        print(message.text)
```

## Subagent 流字段

每个 subagent 流都暴露与父级运行相同类型的投影，例如 messages、tool calls、嵌套的 subagents 以及最终输出。有关一般父级运行的流式传输模型，请参阅 LangChain Event Streaming。

Python 使用 snake_case 风格的投影名称，例如 `tool_calls`。每个 subagent 流可暴露 `.messages`、`.tool_calls`、`.values`、`.subagents` 和 `.output`。

| 字段           | 描述                                                                 |
| -------------- | -------------------------------------------------------------------- |
| `name`         | Subagent 名称。                                                      |
| `messages`     | 由 subagent 发出的 messages。                                        |
| `subagents`    | 嵌套的 subagent 调用。                                               |
| `output`       | 最终 subagent 状态，或委托任务的完成信号。                           |
| `path`         | subagent 流的命名空间路径。                                          |
| `status`       | 生命周期状态，例如 `started`、`completed`、`failed` 或 `interrupted`。 |
| `tool_calls`   | 限定在 subagent 范围内的 tool calls。                                |

## 跟踪 subagent 生命周期

当你只需要展示哪些 subagents 已启动和已完成时，可以使用 `stream.subagents`。除非你访问单个 subagent 上的这些投影，否则你无需订阅 message 或 value 流。

```python
stream = agent.stream_events(input, version="v3")

running = 0
completed = 0
failed = 0

for subagent in stream.subagents:
    running += 1
    print(f"{subagent.name}: started")

    try:
        _ = subagent.output
        running -= 1
        completed += 1
        print(f"{subagent.name}: completed")
    except Exception:
        running -= 1
        failed += 1
        print(f"{subagent.name}: failed")
```

## 流式传输 messages

Deep Agents 可以从 coordinator agent 以及委托的 subagents 发出 messages。使用 `stream.messages` 获取顶层 messages，使用 `subagent.messages` 获取每个委托的 subagent 的 messages。

```python
stream = agent.stream_events(input, version="v3")

for message in stream.messages:
    print("[coordinator]", message.text)

for subagent in stream.subagents:
    for message in subagent.messages:
        print(f"[{subagent.name}]", message.text)
```

## 流式传输 tool calls

Deep Agents 在 agent 树的每个层级都暴露 tool calls。使用顶层的 `stream.tool_calls` 获取 coordinator 的 tools，使用每个 `subagent.tool_calls` 获取委托工作的 tools。

```python
stream = agent.stream_events(input, version="v3")

for call in stream.tool_calls:
    print("[coordinator tool]", call.tool_name, call.input)
    print(call.completed, call.error)

for subagent in stream.subagents:
    for call in subagent.tool_calls:
        print(f"[{subagent.name} tool]", call.tool_name, call.input)
        for delta in call.output_deltas:
            print(delta, end="", flush=True)

        if call.completed and call.error is None:
            print(call.output)
        elif call.error is not None:
            print(call.error)
```

## 流式传输嵌套工作

你可以递归进入 subagent 流，以观察嵌套的 subagents、messages 和 tool calls。

```python
stream = agent.stream_events(input, version="v3")

for subagent in stream.subagents:
    print(f"subagent {subagent.name}: {subagent.status}")

    for tool_call in subagent.tool_calls:
        print(f"{tool_call.tool_name}({tool_call.input})")
        for delta in tool_call.output_deltas:
            print(delta, end="", flush=True)

    for nested in subagent.subagents:
        print(f"nested subagent {nested.name}: {nested.status}")
```

## 并发消费

Coordinator 和 subagent 的输出常常交错出现。当需要实时 UI 更新时，可以并发消费各个投影。

当你需要对多个投影进行单个同步循环时，可以使用 `stream.interleave(...)`：

```python
stream = agent.stream_events(input, version="v3")

for name, item in stream.interleave("messages", "subagents"):
    if name == "messages":
        print("[coordinator]", item.text)
    else:
        for message in item.messages:
            print(f"[{item.name}]", message.text)
```

当需要跨 coordinator 和所有 subagents 的精确到达顺序时，可以遍历原始协议事件，并使用 `namespace` 来标识来源：

```python
stream = agent.stream_events(input, version="v3")

for event in stream:
    if event.get("method") != "messages":
        continue

    payload = event["params"]["data"]
    if payload.get("event") != "content-block-delta":
        continue

    block = payload.get("delta") or {}
    if block.get("type") == "text":
        source = "subagent" if event["params"]["namespace"] else "coordinator"
        print(f"[{source}] {block['text']}", end="", flush=True)
```

## Subagents 与 subgraphs 对比

`stream.subgraphs` 展示图的执行结构。`stream.subagents` 展示产品级的 Deep Agents 任务委托。应使用 `stream.subagents` 来构建面向用户的 UI，因为它隐藏了内部图节点，并直接暴露 subagent 概念。

## 相关链接

* LangChain Event Streaming 涵盖了一般 agent 的 message 和 tool-call 流式传输概念。
* Subagent 前端流式传输展示了将 coordinator messages 与 subagent 卡片分离的 UI 模式。
* LangGraph Event Streaming 涵盖了底层的图流式传输模型。