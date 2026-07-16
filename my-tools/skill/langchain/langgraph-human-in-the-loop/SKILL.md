---
name: langgraph-human-in-the-loop
description: "INVOKE THIS SKILL when implementing human-in-the-loop patterns, pausing for approval, or handling errors in LangGraph. Covers interrupt(), Command(resume=...), approval/validation workflows, v2 streaming interrupt detection, and idempotency requirements."
---

<overview>
LangGraph 的人机协同模式让你暂停图执行、向用户展示数据，并通过他们的输入恢复：

- **`interrupt(value)`** — 暂停执行，向调用者展示一个值
- **`Command(resume=value)`** — 恢复执行，将值提供给 `interrupt()`
- **`version="v2"`** — 使用 `result.interrupts` 而非 `result["__interrupt__"]` 获取中断数据
- **Checkpointer** — 暂停时保存状态所必需
- **Thread ID** — 识别要恢复哪个暂停执行所必需
</overview>

---

## 要求

中断工作需要三样东西：

1. **Checkpointer** — 使用 `checkpointer=InMemorySaver()`（开发）或 `PostgresSaver`（生产）编译
2. **Thread ID** — 每次 `invoke`/`stream` 调用传入 `{"configurable": {"thread_id": "..."}}`
3. **JSON 可序列化负载** — 传给 `interrupt()` 的值必须是 JSON 可序列化的

---

## 基本 Interrupt + Resume

`interrupt(value)` 暂停图。值在 `__interrupt__`（v1）或 `.interrupts`（v2）下返回。`Command(resume=value)` 恢复——恢复值成为 `interrupt()` 的返回值。

**关键**：当图恢复时，节点从**开头**重新开始——`interrupt()` 之前的所有代码都会重新运行。

<ex-basic-interrupt-resume>
<python>
暂停执行以进行人工审查并使用 Command 恢复（v2 API）。

```python
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class State(TypedDict):
    approved: bool

def approval_node(state: State):
    # 暂停并请求批准
    approved = interrupt("你批准这个操作吗？")
    # 恢复时，Command(resume=...) 在此处返回该值
    return {"approved": approved}

checkpointer = InMemorySaver()
graph = (
    StateGraph(State)
    .add_node("approval", approval_node)
    .add_edge(START, "approval")
    .add_edge("approval", END)
    .compile(checkpointer=checkpointer)
)

config = {"configurable": {"thread_id": "thread-1"}}

# 初始运行——遇到中断并暂停（v2）
result = graph.invoke({"approved": False}, config, version="v2")
print(result.interrupts)
# (Interrupt(value='你批准这个操作吗？'),)

# 使用人工响应恢复
result = graph.invoke(Command(resume=True), config, version="v2")
print(result["approved"])  # True
```
</python>
<typescript>
暂停执行以进行人工审查并使用 Command 恢复。

```typescript
import { interrupt, Command, MemorySaver, StateGraph, StateSchema, START, END } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  approved: z.boolean().default(false),
});

const approvalNode = async (state: typeof State.State) => {
  const approved = interrupt("Do you approve this action?");
  return { approved };
};

const checkpointer = new MemorySaver();
const graph = new StateGraph(State)
  .addNode("approval", approvalNode)
  .addEdge(START, "approval")
  .addEdge("approval", END)
  .compile({ checkpointer });

const config = { configurable: { thread_id: "thread-1" } };

let result = await graph.invoke({ approved: false }, config);
console.log(result.__interrupt__);

result = await graph.invoke(new Command({ resume: true }), config);
console.log(result.approved);  // true
```
</typescript>
</ex-basic-interrupt-resume>

---

## Approval Workflow

常见模式：中断以展示草稿，然后根据人工决定路由。

<ex-approval-workflow>
<python>
中断以进行人工审查，然后根据决定路由到发送或结束。

```python
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, START, END
from typing import Literal
from typing_extensions import TypedDict

class EmailAgentState(TypedDict):
    email_content: str
    draft_response: str
    classification: dict

def human_review(state: EmailAgentState) -> Command[Literal["send_reply", "__end__"]]:
    """使用 interrupt 暂停以进行人工审查并根据决定路由。"""
    classification = state.get("classification", {})

    # interrupt() 必须放在最前面——它之前的任何代码在恢复时都会重新运行
    human_decision = interrupt({
        "email_id": state.get("email_content", ""),
        "draft_response": state.get("draft_response", ""),
        "urgency": classification.get("urgency"),
        "action": "请审查并批准/编辑此响应"
    })

    if human_decision.get("approved"):
        return Command(
            update={"draft_response": human_decision.get("edited_response", state.get("draft_response", ""))},
            goto="send_reply"
        )
    else:
        return Command(update={}, goto=END)
```
</python>
<typescript>
中断以进行人工审查，然后根据决定路由到发送或结束。

```typescript
import { interrupt, Command, END, GraphNode } from "@langchain/langgraph";

const humanReview: GraphNode<typeof EmailAgentState> = async (state) => {
  const classification = state.classification!;

  const humanDecision = interrupt({
    emailId: state.emailContent,
    draftResponse: state.responseText,
    urgency: classification.urgency,
    action: "Please review and approve/edit this response",
  });

  if (humanDecision.approved) {
    return new Command({
      update: { responseText: humanDecision.editedResponse || state.responseText },
      goto: "sendReply",
    });
  } else {
    return new Command({ update: {}, goto: END });
  }
};
```
</typescript>
</ex-approval-workflow>

---

## Validation Loop

在循环中使用 `interrupt()` 验证人工输入，无效时重新提示。

<ex-validation-loop>
<python>
在循环中验证人工输入，直到有效才重新提示。

```python
from langgraph.types import interrupt

def get_age_node(state):
    prompt = "你的年龄是多少？"

    while True:
        answer = interrupt(prompt)

        if isinstance(answer, int) and answer > 0:
            break
        else:
            prompt = f"'{answer}' 不是有效的年龄。请输入正整数。"

    return {"age": answer}
```

每次 `Command(resume=...)` 调用提供下一个答案。如果无效，循环用更清晰的消息重新中断。

```python
config = {"configurable": {"thread_id": "form-1"}}
first = graph.invoke({"age": None}, config)
# __interrupt__: "你的年龄是多少？"

retry = graph.invoke(Command(resume="三十"), config)
# __interrupt__: "'三十' 不是有效的年龄..."

final = graph.invoke(Command(resume=30), config)
print(final["age"])  # 30
```
</python>
<typescript>
在循环中验证人工输入，直到有效才重新提示。

```typescript
import { interrupt } from "@langchain/langgraph";

const getAgeNode = (state: typeof State.State) => {
  let prompt = "What is your age?";

  while (true) {
    const answer = interrupt(prompt);

    if (typeof answer === "number" && answer > 0) {
      return { age: answer };
    } else {
      prompt = `'${answer}' is not a valid age. Please enter a positive number.`;
    }
  }
};
```
</typescript>
</ex-validation-loop>

---

## Multiple Interrupts

当并行分支各自调用 `interrupt()` 时，在一次调用中通过将每个中断 ID 映射到恢复值来恢复所有中断。

<ex-multiple-interrupts>
<python>
通过将中断 ID 映射到值来恢复多个并行中断。

```python
from typing import Annotated, TypedDict
import operator
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command, interrupt

class State(TypedDict):
    vals: Annotated[list[str], operator.add]

def node_a(state):
    answer = interrupt("question_a")
    return {"vals": [f"a:{answer}"]}

def node_b(state):
    answer = interrupt("question_b")
    return {"vals": [f"b:{answer}"]}

graph = (
    StateGraph(State)
    .add_node("a", node_a)
    .add_node("b", node_b)
    .add_edge(START, "a")
    .add_edge(START, "b")
    .add_edge("a", END)
    .add_edge("b", END)
    .compile(checkpointer=InMemorySaver())
)

config = {"configurable": {"thread_id": "1"}}

# 两个并行节点都遇到 interrupt() 并暂停
result = graph.invoke({"vals": []}, config)

# 一次性通过 id -> value 的映射恢复所有待决中断
resume_map = {
    i.id: f"answer for {i.value}"
    for i in result["__interrupt__"]
}
result = graph.invoke(Command(resume=resume_map), config)
```
</python>
</ex-multiple-interrupts>

---

## Interrupt 前副作用必须幂等

图恢复时，节点从**开头**重新开始——`interrupt()` 之前的所有代码都会重新运行。在子图中，父节点和子图节点**都会**重新执行。

<idempotency-rules>

**应该：**
- 在 `interrupt()` 前使用 **upsert**（非 insert）操作
- 使用 **check-before-create** 模式
- 尽可能将副作用放在 `interrupt()` **之后**
- 将副作用分离到各自的节点中

**不应该：**
- 在 `interrupt()` 前创建新记录——每次恢复都会重复
- 在 `interrupt()` 前追加到列表——每次恢复都会重复条目

</idempotency-rules>

<ex-idempotent-patterns>
<python>
中断前的幂等操作 vs 非幂等（错误）。

```python
# 好：Upsert 是幂等的——在 interrupt 前安全
def node_a(state: State):
    db.upsert_user(user_id=state["user_id"], status="pending_approval")
    approved = interrupt("批准此更改？")
    return {"approved": approved}

# 好：副作用在 interrupt 之后——只运行一次
def node_a(state: State):
    approved = interrupt("批准此更改？")
    if approved:
        db.create_audit_log(user_id=state["user_id"], action="approved")
    return {"approved": approved}

# 坏：Insert 在每次恢复时创建重复！
def node_a(state: State):
    audit_id = db.create_audit_log({  # 恢复时再次运行！
        "user_id": state["user_id"],
        "action": "pending_approval",
    })
    approved = interrupt("批准此更改？")
    return {"approved": approved}
```
</python>
<typescript>
中断前的幂等操作 vs 非幂等（错误）。

```typescript
// 好：Upsert 是幂等的
const nodeA = async (state: typeof State.State) => {
  await db.upsertUser({ userId: state.userId, status: "pending_approval" });
  const approved = interrupt("Approve this change?");
  return { approved };
};

// 好：副作用在 interrupt 之后
const nodeA = async (state: typeof State.State) => {
  const approved = interrupt("Approve this change?");
  if (approved) {
    await db.createAuditLog({ userId: state.userId, action: "approved" });
  }
  return { approved };
};

// 坏：Insert 在每次恢复时创建重复！
const nodeA = async (state: typeof State.State) => {
  await db.createAuditLog({  // 恢复时再次运行！
    userId: state.userId,
    action: "pending_approval",
  });
  const approved = interrupt("Approve this change?");
  return { approved };
};
```
</typescript>
</ex-idempotent-patterns>

<subgraph-interrupt-re-execution>

### 恢复时子图重新执行

当子图包含 `interrupt()` 时，恢复会重新执行**父节点**（调用子图的那个）和**子图节点**（调用 `interrupt()` 的那个）：

<python>

```python
def node_in_parent_graph(state: State):
    some_code()  # <-- 恢复时重新执行
    subgraph_result = subgraph.invoke(some_input)
    # ...

def node_in_subgraph(state: State):
    some_other_code()  # <-- 恢复时也重新执行
    result = interrupt("你的名字是什么？")
    # ...
```
</python>
</subgraph-interrupt-re-execution>

---

## Command(resume) 警告

`Command(resume=...)` 是**唯一**旨在作为 `invoke()`/`stream()` 输入的 Command 模式。不要将 `Command(update=...)` 作为输入——它会从最新检查点恢复，图会看起来卡住。多轮对话请改为传入普通字典。

---

## Fixes

<fix-checkpointer-required-for-interrupts>
<python>
中断功能需要 checkpointer。

```python
# 错误
graph = builder.compile()

# 正确
graph = builder.compile(checkpointer=InMemorySaver())
```
</python>
<typescript>
中断功能需要 checkpointer。

```typescript
// 错误
const graph = builder.compile();

// 正确
const graph = builder.compile({ checkpointer: new MemorySaver() });
```
</typescript>
</fix-checkpointer-required-for-interrupts>

<fix-resume-with-command>
<python>
使用 Command 从中断恢复（普通 dict 会重新启动图）。

```python
# 错误
graph.invoke({"resume_data": "approve"}, config)

# 正确
graph.invoke(Command(resume="approve"), config)
```
</python>
<typescript>
使用 Command 从中断恢复（普通对象会重新启动图）。

```typescript
// 错误
await graph.invoke({ resumeData: "approve" }, config);

// 正确
await graph.invoke(new Command({ resume: "approve" }), config);
```
</typescript>
</fix-resume-with-command>

<fix-v2-interrupt-detection>
<python>
使用 v2 API 时，通过 `result.interrupts` 检测中断而非 `result["__interrupt__"]`。

```python
# v2 风格（推荐）
result = graph.invoke({"input": "data"}, config, version="v2")
if result.interrupts:
    for interrupt in result.interrupts:
        print(f"中断: {interrupt.value}")

# v1 风格（向后兼容）
result = graph.invoke({"input": "data"}, config)
if "__interrupt__" in result:
    print(f"中断: {result['__interrupt__']}")
```
</python>
</fix-v2-interrupt-detection>

<boundaries>
### 不应该做的事情

- 在没有 checkpointer 的情况下使用中断——会失败
- 在没有相同 thread_id 的情况下恢复——会创建新线程而非恢复
- 将 `Command(update=...)` 作为 invoke 输入——图会看起来卡住（使用普通 dict）
- 在 `interrupt()` 前执行非幂等的副作用——恢复时会产生重复
- 假设 `interrupt()` 前的代码只运行一次——每次恢复都会重新运行
</boundaries>
