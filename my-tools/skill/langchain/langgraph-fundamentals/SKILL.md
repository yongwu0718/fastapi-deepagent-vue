---
name: langgraph-fundamentals
description: "INVOKE THIS SKILL when writing ANY LangGraph code. Covers StateGraph, state schemas (single and multiple), reducers, nodes, edges, Command, Send, Runtime context, invoke, streaming, error handling, and Overwrite."
---

<overview>
LangGraph 将 agent 工作流建模为**有向图**：

- **StateGraph**: 构建有状态图的主类
- **State**: 表示应用当前快照的共享数据结构
- **Nodes**: 执行工作的函数——可以是 LLM 或纯代码
- **Edges**: 决定执行顺序（静态或条件）
- **START/END**: 标记入口和出口的特殊节点
- **Reducers**: 控制状态更新如何合并

**节点负责工作，边决定下一步做什么。**

图在执行前**必须** `compile()`。
</overview>

<design-methodology>

### 设计 LangGraph 应用

构建新图时遵循以下 5 步：

1. **勾勒离散步骤** — 绘制工作流流程图。每个步骤成为一个节点。
2. **识别每个步骤的功能** — 分类节点：LLM 步骤、数据步骤、操作步骤或用户输入步骤。对每个节点确定静态上下文（提示）、动态上下文（来自状态）、重试策略和期望结果。
3. **设计状态** — 状态是所有节点的共享内存。存储原始数据，在节点内按需格式化提示。
4. **构建节点** — 将每个步骤实现为一个接收状态并返回部分更新的函数。
5. **连接它们** — 用边连接节点，添加条件路由，按需使用 checkpointer 编译。

</design-methodology>

<when-to-use-langgraph>

| 使用 LangGraph | 使用替代方案 |
|---|---:|
| 需要对 agent 编排的精细控制 | 快速原型 → LangChain agents |
| 构建带分支/循环的复杂工作流 | 简单无状态工作流 → LangChain 直接调用 |
| 需要人机协同、持久化 | 电池全含功能 → Deep Agents |

</when-to-use-langgraph>

---

## 状态管理

<state-update-strategies>

| 需求 | 方案 | 示例 |
|------|------|------|
| 覆盖值 | 无 reducer（默认） | 简单字段如 counter |
| 追加到列表 | Reducer（operator.add / concat） | 消息历史、日志 |
| 智能消息合并 | add_messages | 消息列表（支持 ID 跟踪、反序列化） |
| 自定义逻辑 | 自定义 reducer 函数 | 复杂合并 |
| 绕过 reducer 覆盖 | Overwrite 类型 | update_state 中替换值 |

</state-update-strategies>

<ex-state-with-reducer>
<python>
使用 reducers 定义状态模式以累积列表和求和整数。

```python
from typing_extensions import TypedDict, Annotated
import operator
from langgraph.graph.message import add_messages

class State(TypedDict):
    name: str  # 默认：更新时覆盖
    messages: Annotated[list, add_messages]  # ID 感知合并
    total: Annotated[int, operator.add]  # 求和整数

# MessagesState 预构建快捷方式
from langgraph.graph import MessagesState

class State(MessagesState):
    documents: list[str]  # 额外字段
```
</python>
<typescript>
使用带有 ReducedValue 的 StateSchema 进行数组累积。

```typescript
import { StateSchema, ReducedValue, MessagesValue } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  name: z.string(),  // 默认：覆盖
  messages: MessagesValue,  // 内置消息处理
  items: new ReducedValue(
    z.array(z.string()).default(() => []),
    { reducer: (current, update) => current.concat(update) }
  ),
});
```
</typescript>
</ex-state-with-reducer>

### 多模式（Multiple Schemas）

节点可以读写不同的模式，实现关注点分离和输入/输出约束：

<ex-multiple-schemas>
<python>
定义输入、输出、整体和私有模式。

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class InputState(TypedDict):
    user_input: str

class OutputState(TypedDict):
    graph_output: str

class OverallState(TypedDict):
    foo: str
    user_input: str
    graph_output: str

class PrivateState(TypedDict):
    bar: str

def node_1(state: InputState) -> OverallState:
    # 从 InputState 读取，写入 OverallState
    return {"foo": state["user_input"] + " name"}

def node_2(state: OverallState) -> PrivateState:
    # 从 OverallState 读取，写入 PrivateState
    return {"bar": state["foo"] + " is"}

def node_3(state: PrivateState) -> OutputState:
    # 从 PrivateState 读取，写入 OutputState
    return {"graph_output": state["bar"] + " Lance"}

builder = StateGraph(OverallState, input_schema=InputState, output_schema=OutputState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)

graph = builder.compile()
result = graph.invoke({"user_input": "My"})
# {'graph_output': 'My name is Lance'}
```

关键点：
- 节点可以写入图中任何状态通道
- 图状态是初始化时所有状态通道的并集
- 节点可以声明额外的状态通道
</python>
</ex-multiple-schemas>

<fix-forgot-reducer-for-list>
<python>
没有 reducer，返回列表会覆盖之前的值。

```python
# 错误：列表会被覆盖
class State(TypedDict):
    messages: list  # 没有 reducer！

# 节点 1 返回：{"messages": ["A"]}
# 节点 2 返回：{"messages": ["B"]}
# 最终：{"messages": ["B"]}  # "A" 丢失！

# 正确：使用 add_messages
from langgraph.graph.message import add_messages
from typing import Annotated

class State(TypedDict):
    messages: Annotated[list, add_messages]
# 最终：{"messages": ["A", "B"]}
```
</python>
<typescript>
没有 ReducedValue，数组会被覆盖而非追加。

```typescript
// 错误：数组会被覆盖
const State = new StateSchema({
  items: z.array(z.string()),  // 没有 reducer！
});
// 节点 1: { items: ["A"] }, 节点 2: { items: ["B"] }
// 最终: { items: ["B"] }  // A 丢失！

// 正确：使用 ReducedValue
const State = new StateSchema({
  items: new ReducedValue(
    z.array(z.string()).default(() => []),
    { reducer: (current, update) => current.concat(update) }
  ),
});
// 最终: { items: ["A", "B"] }
```
</typescript>
</fix-forgot-reducer-for-list>

<fix-state-must-return-dict>
<python>
节点必须返回部分更新，而非变异并返回完整状态。

```python
# 错误：返回整个状态对象
def my_node(state: State) -> State:
    state["field"] = "updated"
    return state  # 不要变异和返回！

# 正确：返回仅包含更新的 dict
def my_node(state: State) -> dict:
    return {"field": "updated"}
```
</python>
<typescript>
仅返回部分更新，而非完整状态对象。

```typescript
// 错误：返回整个状态
const myNode = async (state: typeof State.State) => {
  state.field = "updated";
  return state;  // 不要这样做！
};

// 正确：返回部分更新
const myNode = async (state: typeof State.State) => {
  return { field: "updated" };
};
```
</typescript>
</fix-state-must-return-dict>

---

## 节点

<node-function-signatures>

节点函数接受以下参数：

<python>

| 签名 | 使用场景 |
|------|----------|
| `def node(state: State)` | 仅需要状态的简单节点 |
| `def node(state: State, config: RunnableConfig)` | 需要 thread_id、tags 或可配置值 |
| `def node(state: State, runtime: Runtime[Context])` | 需要运行时上下文、store 或 stream_writer |

```python
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from dataclasses import dataclass

@dataclass
class Context:
    user_id: str

def plain_node(state: State):
    return {"results": "done"}

def node_with_config(state: State, config: RunnableConfig):
    thread_id = config["configurable"]["thread_id"]
    return {"results": f"Thread: {thread_id}"}

def node_with_runtime(state: State, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
    thread_id = runtime.execution_info.thread_id
    return {"results": f"User: {user_id}, Thread: {thread_id}"}
```
</python>
<typescript>

| 签名 | 使用场景 |
|------|----------|
| `(state) => {...}` | 仅需要状态的简单节点 |
| `(state, config) => {...}` | 需要 thread_id、tags 或可配置值 |

```typescript
import { GraphNode, StateSchema } from "@langchain/langgraph";

const plainNode: GraphNode<typeof State> = (state) => {
  return { results: "done" };
};

const nodeWithConfig: GraphNode<typeof State> = (state, config) => {
  const threadId = config?.configurable?.thread_id;
  return { results: `Thread: ${threadId}` };
};
```
</typescript>

</node-function-signatures>

### START 和 END 节点

- **START**: 特殊节点，代表将用户输入发送到图。用于确定首先调用哪些节点。
- **END**: 特殊节点，代表终端节点。表示完成后无后续操作。

---

## 边

<edge-type-selection>

| 需求 | 边类型 | 使用时机 |
|------|--------|----------|
| 始终去同一节点 | `add_edge()` | 固定、确定性流程 |
| 基于状态路由 | `add_conditional_edges()` | 动态分支 |
| 更新状态并路由 | `Command` | 在单个节点中组合逻辑 |
| 扇出到多个节点 | `Send` | 动态输入的并行处理 |

</edge-type-selection>

<ex-basic-graph>
<python>
简单的双节点图，线性边连接。

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class State(TypedDict):
    input: str
    output: str

def process_input(state: State) -> dict:
    return {"output": f"已处理: {state['input']}"}

def finalize(state: State) -> dict:
    return {"output": state["output"].upper()}

graph = (
    StateGraph(State)
    .add_node("process", process_input)
    .add_node("finalize", finalize)
    .add_edge(START, "process")
    .add_edge("process", "finalize")
    .add_edge("finalize", END)
    .compile()
)

result = graph.invoke({"input": "hello"})
print(result["output"])  # "已处理: HELLO"
```
</python>
<typescript>
使用 addEdge 连接节点，调用前先 compile。

```typescript
import { StateGraph, StateSchema, START, END } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  input: z.string(),
  output: z.string().default(""),
});

const processInput = async (state: typeof State.State) => {
  return { output: `Processed: ${state.input}` };
};

const finalize = async (state: typeof State.State) => {
  return { output: state.output.toUpperCase() };
};

const graph = new StateGraph(State)
  .addNode("process", processInput)
  .addNode("finalize", finalize)
  .addEdge(START, "process")
  .addEdge("process", "finalize")
  .addEdge("finalize", END)
  .compile();

const result = await graph.invoke({ input: "hello" });
console.log(result.output);  // "PROCESSED: HELLO"
```
</typescript>
</ex-basic-graph>

<ex-conditional-edges>
<python>
使用条件边根据状态路由到不同节点。

```python
from typing import Literal
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    query: str
    route: str
    result: str

def classify(state: State) -> dict:
    if "weather" in state["query"].lower():
        return {"route": "weather"}
    return {"route": "general"}

def route_query(state: State) -> Literal["weather", "general"]:
    return state["route"]

graph = (
    StateGraph(State)
    .add_node("classify", classify)
    .add_node("weather", lambda s: {"result": "晴天, 22°C"})
    .add_node("general", lambda s: {"result": "通用响应"})
    .add_edge(START, "classify")
    .add_conditional_edges("classify", route_query, ["weather", "general"])
    .add_edge("weather", END)
    .add_edge("general", END)
    .compile()
)
```
</python>
<typescript>
addConditionalEdges 根据函数返回值路由。

```typescript
import { StateGraph, StateSchema, START, END } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  query: z.string(),
  route: z.string().default(""),
  result: z.string().default(""),
});

const classify = async (state: typeof State.State) => {
  if (state.query.toLowerCase().includes("weather")) {
    return { route: "weather" };
  }
  return { route: "general" };
};

const routeQuery = (state: typeof State.State) => state.route;

const graph = new StateGraph(State)
  .addNode("classify", classify)
  .addNode("weather", async () => ({ result: "Sunny, 72F" }))
  .addNode("general", async () => ({ result: "General response" }))
  .addEdge(START, "classify")
  .addConditionalEdges("classify", routeQuery, ["weather", "general"])
  .addEdge("weather", END)
  .addEdge("general", END)
  .compile();
```
</typescript>
</ex-conditional-edges>

---

## Command

Command 在单个返回值中组合状态更新和路由。字段：
- **`update`**: 要应用的状态更新（类似从节点返回 dict）
- **`goto`**: 下一步导航到的节点名称
- **`resume`**: 在 `interrupt()` 之后恢复的值——参见 HITL 技能

<ex-command-state-and-routing>
<python>
Command 让你在一次返回中同时更新状态和选择下一个节点。

```python
from langgraph.types import Command
from typing import Literal

class State(TypedDict):
    count: int
    result: str

def node_a(state: State) -> Command[Literal["node_b", "node_c"]]:
    """一次返回中更新状态并决定下一个节点。"""
    new_count = state["count"] + 1
    if new_count > 5:
        return Command(update={"count": new_count}, goto="node_c")
    return Command(update={"count": new_count}, goto="node_b")

graph = (
    StateGraph(State)
    .add_node("node_a", node_a)
    .add_node("node_b", lambda s: {"result": "B"})
    .add_node("node_c", lambda s: {"result": "C"})
    .add_edge(START, "node_a")
    .add_edge("node_b", END)
    .add_edge("node_c", END)
    .compile()
)
```
</python>
<typescript>
返回带有 update 和 goto 的 Command 以组合状态变更和路由。

```typescript
import { StateGraph, StateSchema, START, END, Command } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  count: z.number().default(0),
  result: z.string().default(""),
});

const nodeA = async (state: typeof State.State) => {
  const newCount = state.count + 1;
  if (newCount > 5) {
    return new Command({ update: { count: newCount }, goto: "node_c" });
  }
  return new Command({ update: { count: newCount }, goto: "node_b" });
};

const graph = new StateGraph(State)
  .addNode("node_a", nodeA, { ends: ["node_b", "node_c"] })
  .addNode("node_b", async () => ({ result: "B" }))
  .addNode("node_c", async () => ({ result: "C" }))
  .addEdge(START, "node_a")
  .addEdge("node_b", END)
  .addEdge("node_c", END)
  .compile();
```
</typescript>
</ex-command-state-and-routing>

<command-return-type-annotations>

**Python**: 使用 `Command[Literal["node_a", "node_b"]]` 作为返回类型注解来声明有效的 goto 目标。

**TypeScript**: 将 `{ ends: ["node_a", "node_b"] }` 作为第三个参数传给 `addNode` 以声明有效的 goto 目标。

</command-return-type-annotations>

<warning-command-static-edges>

**警告**: `Command` 仅添加**动态**边——`add_edge` / `addEdge` 定义的静态边仍会执行。如果 `node_a` 返回 `Command(goto="node_c")` 且你还有 `graph.add_edge("node_a", "node_b")`，则 **`node_b` 和 `node_c` 都会运行**。

</warning-command-static-edges>

---

## Send API

<ex-orchestrator-worker>
<python>
使用 Send API 将任务扇出到并行 worker 并聚合结果。

```python
from langgraph.types import Send
from typing import Annotated
import operator

class OrchestratorState(TypedDict):
    tasks: list[str]
    results: Annotated[list, operator.add]
    summary: str

def orchestrator(state: OrchestratorState):
    """将任务扇出到 workers。"""
    return [Send("worker", {"task": task}) for task in state["tasks"]]

def worker(state: dict) -> dict:
    return {"results": [f"已完成: {state['task']}"]}

def synthesize(state: OrchestratorState) -> dict:
    return {"summary": f"处理了 {len(state['results'])} 个任务"}

graph = (
    StateGraph(OrchestratorState)
    .add_node("worker", worker)
    .add_node("synthesize", synthesize)
    .add_conditional_edges(START, orchestrator, ["worker"])
    .add_edge("worker", "synthesize")
    .add_edge("synthesize", END)
    .compile()
)

result = graph.invoke({"tasks": ["任务 A", "任务 B", "任务 C"]})
```
</python>
<typescript>
使用 Send API 将任务扇出到并行 worker 并聚合结果。

```typescript
import { Send, StateGraph, StateSchema, ReducedValue, START, END } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  tasks: z.array(z.string()),
  results: new ReducedValue(
    z.array(z.string()).default(() => []),
    { reducer: (curr, upd) => curr.concat(upd) }
  ),
  summary: z.string().default(""),
});

const orchestrator = (state: typeof State.State) => {
  return state.tasks.map((task) => new Send("worker", { task }));
};

const worker = async (state: { task: string }) => {
  return { results: [`Completed: ${state.task}`] };
};

const synthesize = async (state: typeof State.State) => {
  return { summary: `Processed ${state.results.length} tasks` };
};

const graph = new StateGraph(State)
  .addNode("worker", worker)
  .addNode("synthesize", synthesize)
  .addConditionalEdges(START, orchestrator, ["worker"])
  .addEdge("worker", "synthesize")
  .addEdge("synthesize", END)
  .compile();
```
</typescript>
</ex-orchestrator-worker>

<fix-send-accumulator>
<python>
使用 reducer 累积并行 worker 结果（否则最后一个 worker 覆盖）。

```python
# 错误：无 reducer——最后一个 worker 覆盖
class State(TypedDict):
    results: list

# 正确
class State(TypedDict):
    results: Annotated[list, operator.add]  # 累积
```
</python>
<typescript>
使用 ReducedValue 累积并行 worker 结果。

```typescript
// 错误：无 reducer
const State = new StateSchema({ results: z.array(z.string()) });

// 正确
const State = new StateSchema({
  results: new ReducedValue(z.array(z.string()).default(() => []), { reducer: (curr, upd) => curr.concat(upd) }),
});
```
</typescript>
</fix-send-accumulator>

---

## 运行图：Invoke 和 Stream

<invoke-basics>

调用 `graph.invoke(input, config)` 运行图到完成并返回最终状态。

<python>

```python
result = graph.invoke({"input": "hello"})
# 带 config（用于持久化、tags 等）
result = graph.invoke({"input": "hello"}, {"configurable": {"thread_id": "1"}})
```
</python>
<typescript>

```typescript
const result = await graph.invoke({ input: "hello" });
// 带 config
const result = await graph.invoke({ input: "hello" }, { configurable: { thread_id: "1" } });
```
</typescript>

</invoke-basics>

<stream-mode-selection>

| 模式 | 流式内容 | 使用场景 |
|------|----------|----------|
| `values` | 每个步骤后的完整状态 | 监控完整状态 |
| `updates` | 状态增量 | 跟踪增量更新 |
| `messages` | LLM tokens + 元数据 | 聊天 UI |
| `custom` | 用户定义数据 | 进度指示器 |

</stream-mode-selection>

<ex-stream-llm-tokens>
<python>
实时流式传输 LLM tokens 用于聊天 UI 显示。

```python
for chunk in graph.stream(
    {"messages": [HumanMessage("你好")]},
    stream_mode="messages"
):
    token, metadata = chunk
    if hasattr(token, "content"):
        print(token.content, end="", flush=True)
```
</python>
<typescript>
实时流式传输 LLM tokens 用于聊天 UI 显示。

```typescript
for await (const chunk of graph.stream(
  { messages: [new HumanMessage("Hello")] },
  { streamMode: "messages" }
)) {
  const [token, metadata] = chunk;
  if (token.content) {
    process.stdout.write(token.content);
  }
}
```
</typescript>
</ex-stream-llm-tokens>

<ex-stream-custom-data>
<python>
使用 stream writer 从节点内部发出自定义进度更新。

```python
from langgraph.config import get_stream_writer

def my_node(state):
    writer = get_stream_writer()
    writer("处理步骤 1...")
    # 工作
    writer("完成！")
    return {"result": "done"}

for chunk in graph.stream({"data": "test"}, stream_mode="custom"):
    print(chunk)
```
</python>
<typescript>
使用 stream writer 从节点内部发出自定义进度更新。

```typescript
import { getWriter } from "@langchain/langgraph";

const myNode = async (state: typeof State.State) => {
  const writer = getWriter();
  writer("处理步骤 1...");
  writer("完成！");
  return { result: "done" };
};

for await (const chunk of graph.stream({ data: "test" }, { streamMode: "custom" })) {
  console.log(chunk);
}
```
</typescript>
</ex-stream-custom-data>

---

## 错误处理

<error-handling-table>

| 错误类型 | 谁修复 | 策略 | 示例 |
|----------|--------|------|------|
| 瞬态（网络、限流） | 系统 | `RetryPolicy(max_attempts=3)` | `add_node(..., retry_policy=...)` |
| LLM 可恢复（工具失败） | LLM | `ToolNode(tools, handle_tool_errors=True)` | 错误以 ToolMessage 返回 |
| 用户可修复（缺失信息） | 人 | `interrupt({"message": ...})` | 收集缺失数据（见 HITL 技能） |
| 预期外 | 开发者 | 让异常冒泡 | `raise` |

</error-handling-table>

<ex-retry-policy>
<python>
对瞬态错误（网络问题、限流）使用 RetryPolicy。

```python
from langgraph.types import RetryPolicy

workflow.add_node(
    "search_documentation",
    search_documentation,
    retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0)
)
```
</python>
<typescript>
对瞬态错误使用 retryPolicy。

```typescript
workflow.addNode(
  "searchDocumentation",
  searchDocumentation,
  {
    retryPolicy: { maxAttempts: 3, initialInterval: 1.0 },
  },
);
```
</typescript>
</ex-retry-policy>

<ex-tool-node-error-handling>
<python>
使用 langgraph.prebuilt 的 ToolNode 处理工具执行和错误。handle_tool_errors=True 时，错误以 ToolMessages 返回，让 LLM 可以恢复。

```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode(tools, handle_tool_errors=True)

workflow.add_node("tools", tool_node)
```
</python>
<typescript>
使用 @langchain/langgraph/prebuilt 的 ToolNode 处理工具执行和错误。

```typescript
import { ToolNode } from "@langchain/langgraph/prebuilt";

const toolNode = new ToolNode(tools, { handleToolErrors: true });

workflow.addNode("tools", toolNode);
```
</typescript>
</ex-tool-node-error-handling>

---

## 常见修复

<fix-compile-before-execution>
<python>
必须 compile() 才能获得可执行图。

```python
# 错误
builder.invoke({"input": "test"})  # AttributeError!

# 正确
graph = builder.compile()
graph.invoke({"input": "test"})
```
</python>
<typescript>
必须 compile() 才能获得可执行图。

```typescript
// 错误
await builder.invoke({ input: "test" });

// 正确
const graph = builder.compile();
await graph.invoke({ input: "test" });
```
</typescript>
</fix-compile-before-execution>

<fix-infinite-loop-needs-exit>
<python>
提供到 END 的条件路径以避免无限循环。

```python
# 错误：永远循环
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", "node_a")

# 正确
def should_continue(state):
    return END if state["count"] > 10 else "node_b"
builder.add_conditional_edges("node_a", should_continue)
```
</python>
<typescript>
使用带 END 返回的条件边来打破循环。

```typescript
// 错误：永远循环
builder.addEdge("node_a", "node_b").addEdge("node_b", "node_a");

// 正确
builder.addConditionalEdges("node_a", (state) => state.count > 10 ? END : "node_b");
```
</typescript>
</fix-infinite-loop-needs-exit>

<fix-common-mistakes>
其他常见错误：

```python
# Router 必须返回图中已存在节点的名称
builder.add_node("my_node", func)  # 在边中引用之前先添加节点
builder.add_conditional_edges("node_a", router, ["my_node"])

# Command 返回类型需要 Literal 用于路由目标 (Python)
def node_a(state) -> Command[Literal["node_b", "node_c"]]:
    return Command(goto="node_b")

# START 仅限入口——无法路由回它
builder.add_edge("node_a", START)  # 错误！
builder.add_edge("node_a", "entry")  # 使用命名入口节点

# Reducer 期望匹配的类型
return {"items": ["项"]}  # 列表 reducer 使用列表，而非字符串
```

```typescript
// 始终 await graph.invoke()——它返回 Promise
const result = await graph.invoke({ input: "test" });

// TS Command 节点需要 { ends } 声明路由目标
builder.addNode("router", routerFn, { ends: ["node_b", "node_c"] });
```
</fix-common-mistakes>

<boundaries>
### 不应该做的事情

- 直接修改状态——始终从节点返回部分更新 dict
- 路由回 START——它仅限入口；使用命名节点代替
- 忘记列表字段的 reducer——没有 reducer，最后写入的生效
- 混合使用静态边和 Command goto，而不理解两者都会执行
</boundaries>
