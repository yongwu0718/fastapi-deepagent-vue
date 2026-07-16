# Streaming

> 从 deep agent 运行和 subagent 执行中流式传输实时更新

对于新应用，我们推荐事件流式传输——Deep Agents v0.6 中引入的类型化 projection API。事件流式传输为每个 projection（subagents、messages、tool calls、values）提供独立的迭代器，因此你可以独立消费它们，而无需根据 `stream_mode` 块进行分支。

Deep Agents 构建在 LangGraph 的流式传输基础设施之上，为 subagent streams 提供一流支持。当 deep agent 将工作委托给 subagents 时，你可以独立地从每个 subagent 流式传输更新——实时跟踪进度、LLM tokens 和 tool calls。

Deep agent 流式传输能实现的功能：

*  **流式传输 subagent 进度**——在每个 subagent 并行运行时跟踪其执行。
*  **流式传输 LLM tokens**——从 main agent 和每个 subagent 流式传输 tokens。
*  **流式传输 tool calls**——查看 subagent 执行内部的 tool calls 和结果。
*  **流式传输自定义更新**——从 subagent 节点内部发出用户定义的信号。

## 启用 subgraph 流式传输

Deep Agents 使用 LangGraph 的 subgraph streaming 来呈现来自 subagent 执行的事件。要接收 subagent 事件，请在流式传输时启用 `stream_subgraphs`。

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    system_prompt="You are a helpful research assistant",
    subagents=[
        {
            "name": "researcher",
            "description": "Researches a topic in depth",
            "system_prompt": "You are a thorough researcher.",
        },
    ],
)

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Research quantum computing advances"}]},
    stream_mode="updates",
    subgraphs=True,  
    version="v2",  
):
    if chunk["type"] == "updates":
        if chunk["ns"]:
            # Subagent 事件——namespace 标识来源
            print(f"[subagent: {chunk['ns']}]")
        else:
            # Main agent 事件
            print("[main agent]")
        print(chunk["data"])
```

## 命名空间

当启用 `subgraphs` 时，每个流式传输事件都包含一个 **namespace**，用于标识是哪个 agent 产生了该事件。namespace 是一个由节点名称和任务 ID 组成的路径，表示 agent 层级结构。

| Namespace                                  | 来源                                                               |
| ------------------------------------------ | ------------------------------------------------------------------ |
| `()`（空）                                 | Main agent                                                         |
| `("tools:abc123",)`                        | 由 main agent 的 `task` tool call `abc123` 产生的 subagent         |
| `("tools:abc123", "model_request:def456")` | subagent 内部的 model request 节点                                  |

使用 namespace 将事件路由到正确的 UI 组件：

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Plan my vacation"}]},
    stream_mode="updates",
    subgraphs=True,
    version="v2",
):
    if chunk["type"] == "updates":
        # 检查此事件是否来自 subagent
        is_subagent = any(
            segment.startswith("tools:") for segment in chunk["ns"]
        )

        if is_subagent:
            # 从 namespace 中提取 tool call ID
            tool_call_id = next(
                s.split(":")[1] for s in chunk["ns"] if s.startswith("tools:")
            )
            print(f"Subagent {tool_call_id}: {chunk['data']}")
        else:
            print(f"Main agent: {chunk['data']}")
```

## Subagent 进度

使用 `stream_mode="updates"` 在每个步骤完成时跟踪 subagent 进度。这对于显示哪些 subagents 处于活动状态以及它们完成了哪些工作非常有用。

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    system_prompt=(
        "You are a project coordinator. Always delegate research tasks "
        "to your researcher subagent using the task tool. Keep your final response to one sentence."
    ),
    subagents=[
        {
            "name": "researcher",
            "description": "Researches topics thoroughly",
            "system_prompt": (
                "You are a thorough researcher. Research the given topic "
                "and provide a concise summary in 2-3 sentences."
            ),
        },
    ],
)

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Write a short summary about AI safety"}]},
    stream_mode="updates",
    subgraphs=True,
    version="v2",
):
    if chunk["type"] == "updates":
        # Main agent 更新（空 namespace）
        if not chunk["ns"]:
            for node_name, data in chunk["data"].items():
                if node_name == "tools":
                    # 返回给 main agent 的 subagent 结果
                    for msg in data.get("messages", []):
                        if msg.type == "tool":
                            print(f"\nSubagent complete: {msg.name}")
                            print(f"  Result: {str(msg.content)[:200]}...")
                else:
                    print(f"[main agent] step: {node_name}")

        # Subagent 更新（非空 namespace）
        else:
            for node_name, data in chunk["data"].items():
                print(f"  [{chunk['ns'][0]}] step: {node_name}")
```

```shell
[main agent] step: model_request
  [tools:call_abc123] step: model_request
  [tools:call_abc123] step: tools
  [tools:call_abc123] step: model_request

Subagent complete: task
  Result: ## AI Safety Report...
[main agent] step: model_request
```

## LLM tokens

使用 `stream_mode="messages"` 从 main agent 和 subagents 流式传输单个 tokens。每个 message 事件都包含标识源 agent 的元数据。

```python
current_source = ""

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Research quantum computing advances"}]},
    stream_mode="messages",
    subgraphs=True,
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]

        # 检查此事件是否来自 subagent（namespace 包含 "tools:"）
        is_subagent = any(s.startswith("tools:") for s in chunk["ns"])

        if is_subagent:
            # 来自 subagent 的 token
            subagent_ns = next(s for s in chunk["ns"] if s.startswith("tools:"))
            if subagent_ns != current_source:
                print(f"\n\n--- [subagent: {subagent_ns}] ---")
                current_source = subagent_ns
            if token.content:
                print(token.content, end="", flush=True)
        else:
            # 来自 main agent 的 token
            if "main" != current_source:
                print("\n\n--- [main agent] ---")
                current_source = "main"
            if token.content:
                print(token.content, end="", flush=True)

print()
```

## Tool calls

当 subagents 使用工具时，你可以流式传输 tool call 事件以显示每个 subagent 正在做什么。Tool call 块出现在 `messages` stream mode 中。

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Research recent quantum computing advances"}]},
    stream_mode="messages",
    subgraphs=True,
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]

        # 标识来源："main" 或 subagent 的 namespace 段
        is_subagent = any(s.startswith("tools:") for s in chunk["ns"])
        source = next((s for s in chunk["ns"] if s.startswith("tools:")), "main") if is_subagent else "main"

        # Tool call 块（流式传输工具调用）
        if token.tool_call_chunks:
            for tc in token.tool_call_chunks:
                if tc.get("name"):
                    print(f"\n[{source}] Tool call: {tc['name']}")
                # 参数以块的形式流式传输——增量写入
                if tc.get("args"):
                    print(tc["args"], end="", flush=True)

        # Tool 结果
        if token.type == "tool":
            print(f"\n[{source}] Tool result [{token.name}]: {str(token.content)[:150]}")

        # 常规 AI 内容（跳过 tool call 消息）
        if token.type == "ai" and token.content and not token.tool_call_chunks:
            print(token.content, end="", flush=True)

print()
```

## 自定义更新

在 subagent 工具内部使用 `get_stream_writer` 来发出自定义进度事件：

```python
import time
from langchain.tools import tool
from langgraph.config import get_stream_writer
from deepagents import create_deep_agent

@tool
def analyze_data(topic: str) -> str:
    """对给定主题运行数据分析。

    此工具执行实际分析并发出进度更新。
    对于任何分析请求，你必须调用此工具。
    """
    writer = get_stream_writer()

    writer({"status": "starting", "topic": topic, "progress": 0})
    time.sleep(0.5)

    writer({"status": "analyzing", "progress": 50})
    time.sleep(0.5)

    writer({"status": "complete", "progress": 100})
    return (
        f'Analysis of "{topic}": Customer sentiment is 85% positive, '
        "driven by product quality and support response times."
    )

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    system_prompt=(
        "You are a coordinator. For any analysis request, you MUST delegate "
        "to the analyst subagent using the task tool. Never try to answer directly. "
        "After receiving the result, summarize it in one sentence."
    ),
    subagents=[
        {
            "name": "analyst",
            "description": "Performs data analysis with real-time progress tracking",
            "system_prompt": (
                "You are a data analyst. You MUST call the analyze_data tool "
                "for every analysis request. Do not use any other tools. "
                "After the analysis completes, report the result."
            ),
            "tools": [analyze_data],
        },
    ],
)

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Analyze customer satisfaction trends"}]},
    stream_mode="custom",
    subgraphs=True,
    version="v2",
):
    if chunk["type"] == "custom":
        is_subagent = any(s.startswith("tools:") for s in chunk["ns"])
        if is_subagent:
            subagent_ns = next(s for s in chunk["ns"] if s.startswith("tools:"))
            print(f"[{subagent_ns}]", chunk["data"])
        else:
            print("[main]", chunk["data"])
```

```shell
[tools:call_abc123] {'status': 'starting', 'topic': 'customer satisfaction trends', 'progress': 0}
[tools:call_abc123] {'status': 'analyzing', 'progress': 50}
[tools:call_abc123] {'status': 'complete', 'progress': 100}
```

## 流式传输多种模式

组合多种 stream modes 以获取 agent 执行的完整图景：

```python
# 跳过内部中间件步骤——仅显示有意义的节点名称
INTERESTING_NODES = {"model_request", "tools"}

last_source = ""
mid_line = False  # 当我们写入 tokens 而没有尾随换行时为 True

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Analyze the impact of remote work on team productivity"}]},
    stream_mode=["updates", "messages", "custom"],
    subgraphs=True,
    version="v2",
):
    is_subagent = any(s.startswith("tools:") for s in chunk["ns"])
    source = "subagent" if is_subagent else "main"

    if chunk["type"] == "updates":
        for node_name in chunk["data"]:
            if node_name not in INTERESTING_NODES:
                continue
            if mid_line:
                print()
                mid_line = False
            print(f"[{source}] step: {node_name}")

    elif chunk["type"] == "messages":
        token, metadata = chunk["data"]
        if token.content:
            # 当源发生变化时打印标题
            if source != last_source:
                if mid_line:
                    print()
                    mid_line = False
                print(f"\n[{source}] ", end="")
                last_source = source
            print(token.content, end="", flush=True)
            mid_line = True

    elif chunk["type"] == "custom":
        if mid_line:
            print()
            mid_line = False
        print(f"[{source}] custom event:", chunk["data"])

print()
```

## 常见模式

### 跟踪 subagent 生命周期

监视 subagents 何时启动、运行和完成：

```python
active_subagents = {}

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Research the latest AI safety developments"}]},
    stream_mode="updates",
    subgraphs=True,
    version="v2",
):
    if chunk["type"] == "updates":
        for node_name, data in chunk["data"].items():
            # ─── 阶段 1：检测 subagent 启动 ────────────────────────
            # 当 main agent 的 model_request 包含 task tool calls 时，
            # 一个 subagent 已被创建。
            if not chunk["ns"] and node_name == "model_request":
                for msg in data.get("messages", []):
                    for tc in getattr(msg, "tool_calls", []):
                        if tc["name"] == "task":
                            active_subagents[tc["id"]] = {
                                "type": tc["args"].get("subagent_type"),
                                "description": tc["args"].get("description", "")[:80],
                                "status": "pending",
                            }
                            print(
                                f'[lifecycle] PENDING  → subagent "{tc["args"].get("subagent_type")}" '
                                f'({tc["id"]})'
                            )

            # ─── 阶段 2：检测 subagent 运行 ─────────────────────────
            # 当我们接收到来自 tools:UUID namespace 的事件时，
            # 该 subagent 正在积极执行。
            if chunk["ns"] and chunk["ns"][0].startswith("tools:"):
                pregel_id = chunk["ns"][0].split(":")[1]
                # 检查是否有任何 pending 的 subagent 需要标记为 running。
                # 注意：pregel task ID 与 tool_call_id 不同，
                # 因此我们在第一个 subagent 事件时将任何 pending 的 subagent 标记为 running。
                for sub_id, sub in active_subagents.items():
                    if sub["status"] == "pending":
                        sub["status"] = "running"
                        print(
                            f'[lifecycle] RUNNING  → subagent "{sub["type"]}" '
                            f"(pregel: {pregel_id})"
                        )
                        break

            # ─── 阶段 3：检测 subagent 完成 ──────────────────────
            # 当 main agent 的 tools 节点返回一个 tool message 时，
            # subagent 已完成并返回了其结果。
            if not chunk["ns"] and node_name == "tools":
                for msg in data.get("messages", []):
                    if msg.type == "tool":
                        sub = active_subagents.get(msg.tool_call_id)
                        if sub:
                            sub["status"] = "complete"
                            print(
                                f'[lifecycle] COMPLETE → subagent "{sub["type"]}" '
                                f"({msg.tool_call_id})"
                            )
                            print(f"  Result preview: {str(msg.content)[:120]}...")

# 打印最终状态
print("\n--- Final subagent states ---")
for sub_id, sub in active_subagents.items():
    print(f"  {sub['type']}: {sub['status']}")
```

## v2 流式传输格式

需要 LangGraph >= 1.1。

本页所有示例都使用 v2 流式传输格式（`version="v2"`），这是推荐的方法。每个 chunk 都是一个 `StreamPart` 字典，包含 `type`、`ns` 和 `data` 键——无论 stream mode、模式数量或 subgraph 设置如何，其形状都相同。

v2 格式消除了嵌套元组解包，使得在 Deep Agents 中处理 subgraph streaming 变得简单直接。比较两种格式：

```python
  # 统一格式——无需嵌套元组解包
  for chunk in agent.stream(
      {"messages": [{"role": "user", "content": "Research quantum computing"}]},
      stream_mode=["updates", "messages", "custom"],
      subgraphs=True,
      version="v2",
  ):
      print(chunk["type"])  # "updates"、"messages" 或 "custom"
      print(chunk["ns"])    # main agent 为 ()，subagent 为 ("tools:",)
      print(chunk["data"])  # 载荷
  ```

  ```python
  # 必须处理 (namespace, (mode, data)) 嵌套元组
  for namespace, chunk in agent.stream(
      {"messages": [{"role": "user", "content": "Research quantum computing"}]},
      stream_mode=["updates", "messages", "custom"],
      subgraphs=True,
  ):
      mode, data = chunk[0], chunk[1]
      print(mode)       # "updates"、"messages" 或 "custom"
      print(namespace)  # main agent 为 ()，subagent 为 ("tools:",)
      print(data)       # 载荷
  ```

有关 v2 格式的更多详细信息，包括类型缩小和 Pydantic/dataclass 强制转换，请参阅 LangGraph 流式传输文档。

## 相关链接

* Subagents——配置和使用 Deep Agents 的 subagents
* Frontend streaming——使用 `useStream` 为 Deep Agents 构建 React UI
* LangChain Event Streaming——LangChain agents 的通用流式传输概念