---
name: langgraph-persistence
description: "INVOKE THIS SKILL when your LangGraph needs to persist state, remember conversations, travel through history, or configure subgraph checkpointer scoping. Covers checkpointers (InMemory/Sqlite/Postgres), thread_id, time travel with v2 API, Store for long-term memory, Overwrite, and subgraph persistence modes."
---

<overview>
LangGraph 的持久化层通过为图状态创建检查点来实现持久化执行：

- **Checkpointer**: 在每个超级步骤保存/加载图状态
- **Thread ID**: 标识分开的检查点序列（对话）
- **Store**: 用于用户偏好、事实的跨线程记忆
- **Overwrite**: 绕过 reducers 直接覆盖状态值

**两种记忆类型：**
- **短期**（checkpointer）: 线程作用域的对话历史
- **长期**（store）: 跨线程用户偏好、事实
</overview>

<checkpointer-selection>

| Checkpointer | 使用场景 | 生产就绪 |
|--------------|----------|----------|
| `InMemorySaver` | 测试、开发 | 否 |
| `SqliteSaver` | 本地开发 | 部分 |
| `PostgresSaver` | 生产 | 是 |

</checkpointer-selection>

---

## Checkpointer Setup

<ex-basic-persistence>
<python>
设置带有内存检查点的基本图，实现基于线程的状态持久化。

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
import operator

class State(TypedDict):
    messages: Annotated[list, operator.add]

def add_message(state: State) -> dict:
    return {"messages": ["Bot response"]}

checkpointer = InMemorySaver()

graph = (
    StateGraph(State)
    .add_node("respond", add_message)
    .add_edge(START, "respond")
    .add_edge("respond", END)
    .compile(checkpointer=checkpointer)  # 在编译时传入
)

# 始终提供 thread_id
config = {"configurable": {"thread_id": "conversation-1"}}

result1 = graph.invoke({"messages": ["你好"]}, config)
print(len(result1["messages"]))  # 2

result2 = graph.invoke({"messages": ["你好吗？"]}, config)
print(len(result2["messages"]))  # 4（之前 + 新的）
```
</python>
<typescript>
设置带有内存检查点的基本图，实现基于线程的状态持久化。

```typescript
import { MemorySaver, StateGraph, StateSchema, MessagesValue, START, END } from "@langchain/langgraph";
import { HumanMessage } from "@langchain/core/messages";

const State = new StateSchema({ messages: MessagesValue });

const addMessage = async (state: typeof State.State) => {
  return { messages: [{ role: "assistant", content: "Bot response" }] };
};

const checkpointer = new MemorySaver();

const graph = new StateGraph(State)
  .addNode("respond", addMessage)
  .addEdge(START, "respond")
  .addEdge("respond", END)
  .compile({ checkpointer });

const config = { configurable: { thread_id: "conversation-1" } };

const result1 = await graph.invoke({ messages: [new HumanMessage("Hello")] }, config);
console.log(result1.messages.length);  // 2

const result2 = await graph.invoke({ messages: [new HumanMessage("How are you?")] }, config);
console.log(result2.messages.length);  // 4（之前 + 新的）
```
</typescript>
</ex-basic-persistence>

<ex-production-postgres>
<python>
为生产部署配置 PostgreSQL 支持的检查点。

```python
import os
from langgraph.checkpoint.postgres import PostgresSaver

# 部署期间运行一次（非应用启动时）：
#   PostgresSaver.from_conn_string(os.environ["DATABASE_URL"]).setup()

with PostgresSaver.from_conn_string(os.environ["DATABASE_URL"]) as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
```
</python>
<typescript>
为生产部署配置 PostgreSQL 支持的检查点。

```typescript
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";

// 部署期间运行一次：
//   await PostgresSaver.fromConnString(process.env.DATABASE_URL!).setup();

const checkpointer = PostgresSaver.fromConnString(process.env.DATABASE_URL!);
const graph = builder.compile({ checkpointer });
```
</typescript>
</ex-production-postgres>

---

## Thread Management

<ex-separate-threads>
<python>
演示不同 thread ID 之间的隔离状态。

```python
alice_config = {"configurable": {"thread_id": "user-alice"}}
bob_config = {"configurable": {"thread_id": "user-bob"}}

graph.invoke({"messages": ["来自 Alice 的问候"]}, alice_config)
graph.invoke({"messages": ["来自 Bob 的问候"]}, bob_config)

# Alice 的状态与 Bob 的状态是隔离的
```
</python>
<typescript>
演示不同 thread ID 之间的隔离状态。

```typescript
const aliceConfig = { configurable: { thread_id: "user-alice" } };
const bobConfig = { configurable: { thread_id: "user-bob" } };

await graph.invoke({ messages: [new HumanMessage("Hi from Alice")] }, aliceConfig);
await graph.invoke({ messages: [new HumanMessage("Hi from Bob")] }, bobConfig);
```
</typescript>
</ex-separate-threads>

---

## State History & Time Travel

<ex-resume-from-checkpoint>
<python>
时间旅行：浏览检查点历史并从过去状态重放或分支。

```python
config = {"configurable": {"thread_id": "session-1"}}

result = graph.invoke({"messages": ["start"]}, config)

# 浏览检查点历史
states = list(graph.get_state_history(config))

# 从过去检查点重放
past = states[-2]
result = graph.invoke(None, past.config)  # None = 从检查点恢复

# 或分支：在过去检查点更新状态，然后恢复
fork_config = graph.update_state(past.config, {"messages": ["edited"]})
result = graph.invoke(None, fork_config)
```
</python>
<typescript>
时间旅行：浏览检查点历史并从过去状态重放或分支。

```typescript
const config = { configurable: { thread_id: "session-1" } };

const result = await graph.invoke({ messages: ["start"] }, config);

// 浏览检查点历史（async iterable，收集到数组）
const states: Awaited<ReturnType<typeof graph.getState>>[] = [];
for await (const state of graph.getStateHistory(config)) {
  states.push(state);
}

// 从过去检查点重放
const past = states[states.length - 2];
const replayed = await graph.invoke(null, past.config);

// 或分支：在过去检查点更新状态，然后恢复
const forkConfig = await graph.updateState(past.config, { messages: ["edited"] });
const forked = await graph.invoke(null, forkConfig);
```
</typescript>
</ex-resume-from-checkpoint>

<ex-update-state>
<python>
在恢复执行前手动更新图状态。

```python
config = {"configurable": {"thread_id": "session-1"}}

# 在恢复前修改状态
graph.update_state(config, {"data": "manually_updated"})

# 使用更新后的状态恢复
result = graph.invoke(None, config)
```
</python>
<typescript>
在恢复执行前手动更新图状态。

```typescript
const config = { configurable: { thread_id: "session-1" } };

await graph.updateState(config, { data: "manually_updated" });

const result = await graph.invoke(null, config);
```
</typescript>
</ex-update-state>

---

## Overwrite — 绕过 Reducers

<ex-overwrite>
<python>
使用 Overwrite 类绕过 reducers 并直接替换状态值。

```python
from langgraph.types import Overwrite

# State with reducer: items: Annotated[list, operator.add]
# Current state: {"items": ["A", "B"]}

# update_state 会经过 reducers
graph.update_state(config, {"items": ["C"]})  # 结果: ["A", "B", "C"] —— 追加！

# 使用 Overwrite 来替换
graph.update_state(config, {"items": Overwrite(["C"])})  # 结果: ["C"] —— 替换
```
</python>
<typescript>
使用 Overwrite 类绕过 reducers 并直接替换状态值。

```typescript
import { Overwrite } from "@langchain/langgraph";

// 当前状态: { items: ["A", "B"] }

// updateState 会经过 reducers
await graph.updateState(config, { items: ["C"] });  // 结果: ["A", "B", "C"] —— 追加！

// 使用 Overwrite 来替换
await graph.updateState(config, { items: new Overwrite(["C"]) });  // 结果: ["C"] —— 替换
```
</typescript>
</ex-overwrite>

---

## Subgraph Checkpointer Scoping

<subgraph-checkpointer-scoping-table>

| 特性 | `checkpointer=False` | `None`（默认） | `True` |
|------|----------------------|----------------|--------|
| 中断（HITL） | 否 | 是 | 是 |
| 多轮记忆 | 否 | 否 | 是 |
| 多次调用（不同子图） | 是 | 是 | 警告（可能命名空间冲突） |
| 多次调用（相同子图） | 是 | 是 | 否 |
| 状态检查 | 否 | 警告（仅当前调用） | 是 |

</subgraph-checkpointer-scoping-table>

<subgraph-checkpointer-when-to-use>

### 何时使用每种模式

- **`checkpointer=False`** — 子图不需要中断或持久化。最简单，无检查点开销。
- **`None`（默认/省略）** — 子图需要 `interrupt()` 但不需要多轮记忆。每次调用重新开始但可以暂停/恢复。
- **`checkpointer=True`** — 子图需要在多次调用间记住状态（多轮对话）。每次调用从上次离开的地方继续。

</subgraph-checkpointer-when-to-use>

<ex-subgraph-checkpointer-modes>
<python>
为子图选择正确的 checkpointer 模式。

```python
# 不需要中断 —— 选择退出检查点
subgraph = subgraph_builder.compile(checkpointer=False)

# 需要中断但不需要跨调用持久化（默认）
subgraph = subgraph_builder.compile()

# 需要跨调用持久化（有状态）
subgraph = subgraph_builder.compile(checkpointer=True)
```
</python>
<typescript>
为子图选择正确的 checkpointer 模式。

```typescript
const subgraph = subgraphBuilder.compile({ checkpointer: false });  // 无中断
const subgraph = subgraphBuilder.compile();                           // 中断，无多轮记忆
const subgraph = subgraphBuilder.compile({ checkpointer: true });    // 有状态子图
```
</typescript>
</ex-subgraph-checkpointer-modes>

---

## Long-Term Memory (Store)

<ex-long-term-memory-store>
<python>
使用 Store 实现跨线程记忆，跨对话共享用户偏好。

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# 保存用户偏好（在所有线程中可用）
store.put(("alice", "preferences"), "language", {"preference": "简短回复"})

# 带有 store 的节点——通过 runtime 访问
from langgraph.runtime import Runtime

def respond(state, runtime: Runtime):
    prefs = runtime.store.get((state["user_id"], "preferences"), "language")
    return {"response": f"使用偏好: {prefs.value}"}

# 同时使用 checkpointer 和 store 编译
graph = builder.compile(checkpointer=checkpointer, store=store)

# 两个线程访问相同的长期记忆
graph.invoke({"user_id": "alice"}, {"configurable": {"thread_id": "thread-1"}})
graph.invoke({"user_id": "alice"}, {"configurable": {"thread_id": "thread-2"}})  # 相同偏好！
```
</python>
<typescript>
使用 Store 实现跨线程记忆，跨对话共享用户偏好。

```typescript
import { MemoryStore } from "@langchain/langgraph";

const store = new MemoryStore();

await store.put(["alice", "preferences"], "language", { preference: "short responses" });

const respond = async (state: typeof State.State, runtime: any) => {
  const item = await runtime.store?.get(["alice", "preferences"], "language");
  return { response: `Using preference: ${item?.value?.preference}` };
};

const graph = builder.compile({ checkpointer, store });

await graph.invoke({ userId: "alice" }, { configurable: { thread_id: "thread-1" } });
await graph.invoke({ userId: "alice" }, { configurable: { thread_id: "thread-2" } });
```
</typescript>
</ex-long-term-memory-store>

<ex-store-operations>
<python>
基本 store 操作：put、get、search 和 delete。

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

store.put(("user-123", "facts"), "location", {"city": "旧金山"})  # Put
item = store.get(("user-123", "facts"), "location")  # Get
results = store.search(("user-123", "facts"), filter={"city": "旧金山"})  # Search
store.delete(("user-123", "facts"), "location")  # Delete
```
</python>
</ex-store-operations>

---

## Fixes

<fix-thread-id-required>
<python>
始终在 config 中提供 thread_id 以启用状态持久化。

```python
# 错误：没有 thread_id——状态未持久化！
graph.invoke({"messages": ["你好"]})
graph.invoke({"messages": ["我说了什么？"]})  # 不记得！

# 正确：始终提供 thread_id
config = {"configurable": {"thread_id": "session-1"}}
graph.invoke({"messages": ["你好"]}, config)
graph.invoke({"messages": ["我说了什么？"]}, config)  # 记得！
```
</python>
<typescript>
始终在 config 中提供 thread_id 以启用状态持久化。

```typescript
// 错误：没有 thread_id——状态未持久化！
await graph.invoke({ messages: [new HumanMessage("Hello")] });
await graph.invoke({ messages: [new HumanMessage("What did I say?")] });  // 不记得！

// 正确：始终提供 thread_id
const config = { configurable: { thread_id: "session-1" } };
await graph.invoke({ messages: [new HumanMessage("Hello")] }, config);
await graph.invoke({ messages: [new HumanMessage("What did I say?")] }, config);  // 记得！
```
</typescript>
</fix-thread-id-required>

<fix-inmemory-not-for-production>
<python>
生产环境使用 PostgresSaver，而非 InMemorySaver。

```python
# 错误：进程重启后数据丢失
checkpointer = InMemorySaver()

# 正确：生产环境使用持久化存储
from langgraph.checkpoint.postgres import PostgresSaver
with PostgresSaver.from_conn_string("postgresql://...") as checkpointer:
    checkpointer.setup()  # 仅首次使用时创建表
    graph = builder.compile(checkpointer=checkpointer)
```
</python>
<typescript>
生产环境使用 PostgresSaver，而非 MemorySaver。

```typescript
// 错误：进程重启后数据丢失
const checkpointer = new MemorySaver();

// 正确：生产环境使用持久化存储
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";
const checkpointer = PostgresSaver.fromConnString("postgresql://...");
await checkpointer.setup();
```
</typescript>
</fix-inmemory-not-for-production>

<fix-update-state-with-reducers>
<python>
使用 Overwrite 替换状态值，而非通过 reducers。

```python
from langgraph.types import Overwrite

# update_state 经过 reducers
graph.update_state(config, {"items": ["C"]})  # 追加：["A", "B", "C"]

# 使用 Overwrite 替换
graph.update_state(config, {"items": Overwrite(["C"])})  # 替换：["C"]
```
</python>
<typescript>
使用 Overwrite 替换状态值，而非通过 reducers。

```typescript
import { Overwrite } from "@langchain/langgraph";

await graph.updateState(config, { items: ["C"] });  // 追加
await graph.updateState(config, { items: new Overwrite(["C"]) });  // 替换
```
</typescript>
</fix-update-state-with-reducers>

<fix-store-injection>
<python>
在图节点中通过 Runtime 对象访问 store。

```python
# 错误：节点中不可直接使用 store
def my_node(state):
    store.put(...)  # NameError！store 未定义

# 正确：通过 runtime 访问 store
from langgraph.runtime import Runtime

def my_node(state, runtime: Runtime):
    runtime.store.put(...)  # 正确的 store 实例
```
</python>
<typescript>
在图节点中通过 runtime 参数访问 store。

```typescript
// 错误：节点中不可直接使用 store
const myNode = async (state) => {
  store.put(...);  // ReferenceError！
};

// 正确：通过 runtime 访问 store
const myNode = async (state, runtime) => {
  await runtime.store?.put(...);  // 正确的 store 实例
};
```
</typescript>
</fix-store-injection>

<boundaries>
### 不应该做的事情

- 在生产环境使用 `InMemorySaver`——数据在重启时丢失；使用 `PostgresSaver`
- 忘记 `thread_id`——没有它状态不会持久化
- 期望 `update_state` 绕过 reducers——它会经过它们；使用 `Overwrite` 来替换
- 在一个节点内并行运行相同有状态子图（`checkpointer=True`）——命名空间冲突
- 在节点中直接访问 store——通过 `Runtime` 参数使用 `runtime.store`
</boundaries>
