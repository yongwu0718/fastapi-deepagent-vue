# 中断

中断允许你在特定点暂停图的执行，并等待外部输入再继续。这实现了需要外部输入才能继续的人机协同模式。当中断被触发时，LangGraph 使用其持久层保存图状态，并无限期等待，直到你恢复执行。

中断通过在图节点的任意位置调用 `interrupt()` 函数来工作。该函数接受任何可 JSON 序列化的值，该值会呈现给调用者。当你准备继续时，通过使用 `Command` 重新调用图来恢复执行，该命令随后成为节点内部 `interrupt()` 调用的返回值。

与静态断点（在特定节点之前或之后暂停）不同，中断是**动态的**：它们可以放置在你代码的任何位置，并且可以根据你的应用逻辑设置条件。

* **检查点保存你的位置：** 检查点器会写入确切的图状态，以便你稍后恢复，即使处于错误状态也能恢复。
* **`thread_id` 是你的指针：** 设置 `config={"configurable": {"thread_id": ...}}` 来告诉检查点器加载哪个状态。
* **中断负载通过 `chunk["interrupts"]` 呈现：** 当使用 `version="v2"` 进行流式传输时，你传递给 `interrupt()` 的值会出现在 `values` 流部分的 `interrupts` 字段中，这样你就知道图在等待什么。

你选择的 `thread_id` 实际上就是你的持久光标。重复使用它可以恢复同一个检查点；使用一个新值则会启动一个带有空状态的全新线程。

## 使用 `interrupt` 暂停

`interrupt` 函数暂停图的执行并向调用者返回一个值。当你在节点内调用 `interrupt` 时，LangGraph 保存当前的图状态，并等待你用输入来恢复执行。

要使用 `interrupt`，你需要：

1. 一个**检查点器**来持久化图状态（在生产环境中使用持久检查点器）
2. 在你的配置中提供一个**线程 ID**，以便运行时知道从哪个状态恢复
3. 在你想要暂停的地方调用 `interrupt()`（负载必须是 JSON 可序列化的）

```python
from langgraph.types import interrupt

def approval_node(state: State):
    # 暂停并请求批准
    approved = interrupt("你批准这个操作吗？")

    # 当你恢复时，Command(resume=...) 会在此处返回该值
    return {"approved": approved}
```

当你调用 `interrupt` 时，会发生以下情况：

1. **图执行被暂停**在调用 `interrupt` 的确切位置
2. **状态被保存**使用检查点器，以便稍后可以恢复执行。在生产环境中，这应该是一个持久检查点器（例如，由数据库支持）
3. **值被返回**给调用者，位于 `__interrupt__` 下；它可以是任何 JSON 可序列化的值（字符串、对象、数组等）
4. **图无限期等待**直到你用响应恢复执行
5. **响应被传递回**节点，当你恢复时，成为 `interrupt()` 调用的返回值

## 恢复中断

中断暂停执行后，你通过再次调用图并传入一个包含恢复值的 `Command` 来恢复图。恢复值被传递回 `interrupt` 调用，允许节点使用外部输入继续执行。

"API 参考 (v2)"
```python
from langgraph.types import Command

# 初始运行 - 遇到中断并暂停
# thread_id 是持久指针（在生产环境中存储一个稳定的 ID）
config = {"configurable": {"thread_id": "thread-1"}}
result = graph.invoke({"input": "data"}, config=config, version="v2")

# result 是一个包含 .value 和 .interrupts 的 GraphOutput
# .interrupts 包含传递给 interrupt() 的负载
print(result.interrupts)
# > (Interrupt(value='你批准这个操作吗？'),)

# 使用人工的响应恢复
# 恢复负载成为节点内部 interrupt() 的返回值
graph.invoke(Command(resume=True), config=config, version="v2")
```

**关于恢复的关键点：**

* 恢复时必须使用中断发生时的**相同线程 ID**
* 传递给 `Command(resume=...)` 的值成为 `interrupt` 调用的返回值
* 恢复时，节点会从调用 `interrupt` 的节点的开头重新开始，因此 `interrupt` 之前的任何代码都会再次运行
* 你可以传递任何 JSON 可序列化的值作为恢复值

`Command(resume=...)` 是**唯一**旨在作为 `invoke()`/`stream()` 输入的 `Command` 模式。其他 `Command` 参数（`update`、`goto`、`graph`）是为从节点函数返回而设计的。不要将 `Command(update=...)` 作为输入来继续多轮对话——请改为传递普通的输入字典。

## 常见模式

中断解锁的关键功能是能够暂停执行并等待外部输入。这对于各种用例都很有用，包括：

* 审批工作流：在执行关键操作（API 调用、数据库更改、金融交易）之前暂停
* 处理多个中断：在单次调用中恢复多个中断时，将中断 ID 与恢复值配对
* 审查和编辑：让人类在继续之前审查和修改 LLM 输出或工具调用
* 中断工具调用：在执行工具调用之前暂停，以便在执行前审查和编辑工具调用
* 验证人类输入：在进行下一步之前暂停以验证人类输入

### 使用人机协同（HITL）中断进行流式传输

在构建具有人机协同工作流的交互式代理时，你可以同时流式传输消息块和节点更新，以在处理中断时提供实时反馈。

使用多种流模式（`"messages"` 和 `"updates"`）并设置 `subgraphs=True`（如果存在子图）来：

* 实时流式传输 AI 生成的响应
* 检测图何时遇到中断
* 处理用户输入并无缝恢复执行

```python
async for chunk in graph.astream(
    initial_input,
    stream_mode=["messages", "updates"],
    subgraphs=True,
    config=config,
    version="v2",
):
    if chunk["type"] == "messages":
        # 处理流式消息内容
        msg, _ = chunk["data"]
        if isinstance(msg, AIMessageChunk) and msg.content:
            display_streaming_content(msg.content)

    elif chunk["type"] == "updates":
        # 检查更新数据中的中断
        if "__interrupt__" in chunk["data"]:
            interrupt_info = chunk["data"]["__interrupt__"][0].value
            user_response = get_user_input(interrupt_info)
            initial_input = Command(resume=user_response)
            break
        else:
            current_node = list(chunk["data"].keys())[0]
```

* **`version="v2"`**：所有块都是带有 `type`、`ns` 和 `data` 键的 `StreamPart` 字典
* **`chunk["type"]`**：根据流模式（`"messages"`、`"updates"` 等）缩小范围以进行类型推断
* **`chunk["ns"]`**：标识源图（根图为空元组，子图为已填充）
* **`subgraphs=True`**：在嵌套图中检测中断所必需
* **`Command(resume=...)`**：使用用户提供的数据恢复图执行

### 处理多个中断

当并行分支同时中断时（例如，扇出到多个节点，每个节点都调用 `interrupt()`），你可能需要在单次调用中恢复多个中断。
在单次调用中恢复多个中断时，将每个中断 ID 映射到其恢复值。
这确保每个响应在运行时与正确的中断配对。

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

# 步骤 1：调用 - 两个并行节点都遇到 interrupt() 并暂停
interrupted_result = graph.invoke({"vals": []}, config)
print(interrupted_result)
"""
{
    'vals': [],
    '__interrupt__': [
        Interrupt(value='question_a', id='bd4f3183600f2c41dddafbf8f0f7be7b'),
        Interrupt(value='question_b', id='29963e3d3585f0cef025dd0f14323f55')
    ]
}
"""

# 步骤 2：一次性恢复所有待处理的中断
resume_map = {
    i.id: f"answer for {i.value}"
    for i in interrupted_result["__interrupt__"]
}
result = graph.invoke(Command(resume=resume_map), config)

print("最终状态:", result)
#> 最终状态: {'vals': ['a:answer for question_a', 'b:answer for question_b']}
```

### 批准或拒绝

中断最常见的用途之一是在关键操作之前暂停并请求批准。例如，你可能希望请求人类批准 API 调用、数据库更改或任何其他重要决策。

```python
from typing import Literal
from langgraph.types import interrupt, Command

def approval_node(state: State) -> Command[Literal["proceed", "cancel"]]:
    # 暂停执行；负载出现在 result["__interrupt__"] 下
    is_approved = interrupt({
        "question": "你想继续这个操作吗？",
        "details": state["action_details"]
    })

    # 根据响应进行路由
    if is_approved:
        return Command(goto="proceed")  # 在提供恢复负载后运行
    else:
        return Command(goto="cancel")
```

恢复图时，传递 `True` 表示批准，`False` 表示拒绝：

```python
# 批准
graph.invoke(Command(resume=True), config=config)

# 拒绝
graph.invoke(Command(resume=False), config=config)
```

 "API 参考 (v2)"
```python
from typing import Literal, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

class ApprovalState(TypedDict):
	action_details: str
	status: Optional[Literal["pending", "approved", "rejected"]]

def approval_node(state: ApprovalState) -> Command[Literal["proceed", "cancel"]]:
	# 暴露详细信息，以便调用者可以在 UI 中渲染它们
	decision = interrupt({
		"question": "批准这个操作吗？",
		"details": state["action_details"],
	})

	# 恢复后路由到适当的节点
	return Command(goto="proceed" if decision else "cancel")

def proceed_node(state: ApprovalState):
	return {"status": "approved"}

def cancel_node(state: ApprovalState):
	return {"status": "rejected"}

builder = StateGraph(ApprovalState)
builder.add_node("approval", approval_node)
builder.add_node("proceed", proceed_node)
builder.add_node("cancel", cancel_node)
builder.add_edge(START, "approval")
builder.add_edge("proceed", END)
builder.add_edge("cancel", END)

# 在生产环境中使用更持久的检查点器
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "approval-123"}}
initial = graph.invoke(
	{"action_details": "转账 $500", "status": "pending"},
	config=config,
)
print(initial["__interrupt__"])  # -> [Interrupt(value={'question': ..., 'details': ...})]

# 使用决策恢复；True 路由到 proceed，False 路由到 cancel
resumed = graph.invoke(Command(resume=True), config=config)
print(resumed["status"])  # -> "approved"
```

### 审查和编辑状态

有时，你可能希望让人类在继续之前审查和编辑图状态的一部分。这对于纠正 LLM、添加缺失信息或进行调整非常有用。

```python
from langgraph.types import interrupt

def review_node(state: State):
    # 暂停并显示当前内容以供审查（出现在 result["__interrupt__"] 中）
    edited_content = interrupt({
        "instruction": "审查并编辑此内容",
        "content": state["generated_text"]
    })

    # 使用编辑后的版本更新状态
    return {"generated_text": edited_content}
```

恢复时，提供编辑后的内容：

```python
graph.invoke(
    Command(resume="已编辑和改进的文本"),  # 该值成为 interrupt() 的返回值
    config=config
)
```

"API 参考 (v2)"
```python
import sqlite3
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

class ReviewState(TypedDict):
	generated_text: str

def review_node(state: ReviewState):
	# 请求审查员编辑生成的内容
	updated = interrupt({
		"instruction": "审查并编辑此内容",
		"content": state["generated_text"],
	})
	return {"generated_text": updated}

builder = StateGraph(ReviewState)
builder.add_node("review", review_node)
builder.add_edge(START, "review")
builder.add_edge("review", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "review-42"}}
initial = graph.invoke({"generated_text": "初稿"}, config=config)
print(initial["__interrupt__"])  # -> [Interrupt(value={'instruction': ..., 'content': ...})]

# 使用审查员的编辑后文本恢复
final_state = graph.invoke(
	Command(resume="审查后改进的草稿"),
	config=config,
)
print(final_state["generated_text"])  # -> "审查后改进的草稿"
```

### 工具中的中断

你也可以将中断直接放置在工具函数内部。这使得工具本身在被调用时暂停以等待批准，并允许在执行前对工具调用进行人工审查和编辑。

首先，定义一个使用 `interrupt` 的工具：

```python
from langchain.tools import tool
from langgraph.types import interrupt

@tool
def send_email(to: str, subject: str, body: str):
    """向收件人发送电子邮件。"""

    # 发送前暂停；负载出现在 result["__interrupt__"] 中
    response = interrupt({
        "action": "send_email",
        "to": to,
        "subject": subject,
        "body": body,
        "message": "批准发送此电子邮件吗？"
    })

    if response.get("action") == "approve":
        # 恢复值可以在执行前覆盖输入
        final_to = response.get("to", to)
        final_subject = response.get("subject", subject)
        final_body = response.get("body", body)
        return f"电子邮件已发送至 {final_to}，主题为 '{final_subject}'"
    return "用户取消了电子邮件"
```

当你希望批准逻辑与工具本身共存，使其可在图的不同部分重用时，这种方法很有用。LLM 可以自然地调用该工具，并且每当工具被调用时，中断都会暂停执行，允许你批准、编辑或取消该操作。

 "API 参考 (v2)"
```python
import sqlite3
from typing import TypedDict

from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

class AgentState(TypedDict):
	messages: list[dict]

@tool
def send_email(to: str, subject: str, body: str):
	"""向收件人发送电子邮件。"""

	# 发送前暂停；负载出现在 result["__interrupt__"] 中
	response = interrupt({
		"action": "send_email",
		"to": to,
		"subject": subject,
		"body": body,
		"message": "批准发送此电子邮件吗？",
	})

	if response.get("action") == "approve":
		final_to = response.get("to", to)
		final_subject = response.get("subject", subject)
		final_body = response.get("body", body)

		# 实际发送电子邮件（你的实现在此处）
		print(f"[send_email] to={final_to} subject={final_subject} body={final_body}")
		return f"电子邮件已发送至 {final_to}"

	return "用户取消了电子邮件"

model = ChatAnthropic(model="claude-sonnet-4-6").bind_tools([send_email])

def agent_node(state: AgentState):
	# LLM 可能决定调用该工具；中断在发送前暂停
	result = model.invoke(state["messages"])
	return {"messages": state["messages"] + [result]}

builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_edge(START, "agent")
builder.add_edge("agent", END)

checkpointer = SqliteSaver(sqlite3.connect("tool-approval.db"))
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "email-workflow"}}
initial = graph.invoke(
	{
		"messages": [
			{"role": "user", "content": "向 alice@example.com 发送关于会议的电子邮件"}
		]
	},
	config=config,
)
print(initial["__interrupt__"])  # -> [Interrupt(value={'action': 'send_email', ...})]

# 使用批准和可选编辑的参数恢复
resumed = graph.invoke(
	Command(resume={"action": "approve", "subject": "更新后的主题"}),
	config=config,
)
print(resumed["messages"][-1])  # -> send_email 返回的工具结果
```

### 验证人类输入

有时你需要验证来自人类的输入，如果无效则再次询问。你可以使用循环中的多个 `interrupt` 调用来实现这一点。

```python
from langgraph.types import interrupt

def get_age_node(state: State):
    prompt = "你的年龄是多少？"

    while True:
        answer = interrupt(prompt)  # 负载出现在 result["__interrupt__"] 中

        # 验证输入
        if isinstance(answer, int) and answer > 0:
            # 有效输入 - 继续
            break
        else:
            # 无效输入 - 使用更具体的提示再次询问
            prompt = f"'{answer}' 不是有效的年龄。请输入一个正数。"

    return {"age": answer}
```

每次你使用无效输入恢复图时，它都会以更清晰的消息再次询问。一旦提供了有效输入，节点就会完成，图继续执行。

"API 参考 (v2)"
```python
import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

class FormState(TypedDict):
	age: int | None

def get_age_node(state: FormState):
	prompt = "你的年龄是多少？"

	while True:
		answer = interrupt(prompt)  # 负载出现在 result["__interrupt__"] 中

		if isinstance(answer, int) and answer > 0:
			return {"age": answer}

		prompt = f"'{answer}' 不是有效的年龄。请输入一个正数。"

builder = StateGraph(FormState)
builder.add_node("collect_age", get_age_node)
builder.add_edge(START, "collect_age")
builder.add_edge("collect_age", END)

checkpointer = SqliteSaver(sqlite3.connect("forms.db"))
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "form-1"}}
first = graph.invoke({"age": None}, config=config)
print(first["__interrupt__"])  # -> [Interrupt(value='你的年龄是多少？', ...)]

# 提供无效数据；节点重新提示
retry = graph.invoke(Command(resume="三十"), config=config)
print(retry["__interrupt__"])  # -> [Interrupt(value="'三十' 不是有效的年龄...", ...)]

# 提供有效数据；循环退出并更新状态
final = graph.invoke(Command(resume=30), config=config)
print(final["age"])  # -> 30
```

## 中断规则

当你在节点中调用 `interrupt` 时，LangGraph 通过引发一个异常来暂停执行，该异常通知运行时暂停。此异常沿调用栈向上传播，并被运行时捕获，运行时通知图保存当前状态并等待外部输入。

当执行恢复时（在你提供请求的输入后），运行时会**从头开始重新启动整个节点**——它不会从调用 `interrupt` 的确切行恢复。这意味着在 `interrupt` 之前运行的任何代码都将再次执行。因此，在使用中断时，需要遵循一些重要的规则，以确保它们按预期工作。

**不要将 `interrupt` 调用包裹在 try/except 中**

`interrupt` 在调用点暂停执行的方式是抛出一个特殊异常。如果你将 `interrupt` 调用包裹在 try/except 块中，你将捕获此异常，并且中断将不会传递回图。

* ✅ 将 `interrupt` 调用与容易出错的代码分开
* ✅ 在 try/except 块中使用特定的异常类型

"API 参考 (v2)"
```python
def node_a(state: State):
	# ✅ 好：先中断，然后分别处理
	# 错误条件
	interrupt("你叫什么名字？")
	try:
		fetch_data()  # 这可能会失败
	except Exception as e:
		print(e)
	return state
```

 "API 参考 (v2)"
```python
def node_a(state: State):
	# ✅ 好：捕获特定的异常类型
	# 不会捕获中断异常
	try:
		name = interrupt("你叫什么名字？")
		fetch_data()  # 这可能会失败
	except NetworkException as e:
		print(e)
	return state
```

* 🔴 不要将 `interrupt` 调用包裹在裸 try/except 块中

```python
def node_a(state: State):
    # ❌ 不好：将 interrupt 包裹在裸 try/except 中
    # 会捕获中断异常
    try:
        interrupt("你叫什么名字？")
    except Exception as e:
        print(e)
    return state
```

**不要对节点内的 `interrupt` 调用重新排序**

在单个节点中使用多个中断很常见，但是如果不小心处理，可能会导致意外行为。

当节点包含多个中断调用时，LangGraph 会保留一个特定于执行该节点的任务的恢复值列表。每当执行恢复时，它都会从节点的开头开始。对于遇到的每个中断，LangGraph 检查任务的恢复列表中是否存在匹配的值。匹配是**严格基于索引**的，因此节点内中断调用的顺序很重要。

* ✅ 保持节点执行中的 `interrupt` 调用一致

```python
def node_a(state: State):
    # ✅ 好：每次中断调用都以相同的顺序发生
    name = interrupt("你叫什么名字？")
    age = interrupt("你的年龄是多少？")
    city = interrupt("你来自哪个城市？")

    return {
        "name": name,
        "age": age,
        "city": city
    }
```

* 🔴 不要有条件地跳过节点内的 `interrupt` 调用
* 🔴 不要使用跨执行不确定的逻辑来循环 `interrupt` 调用

"API 参考 (v2)"
```python
def node_a(state: State):
	# ❌ 不好：有条件地跳过中断会改变顺序
	name = interrupt("你叫什么名字？")

	# 在第一次运行时，这可能会跳过中断
	# 在恢复时，它可能不会跳过——导致索引不匹配
	if state.get("needs_age"):
		age = interrupt("你的年龄是多少？")

	city = interrupt("你来自哪个城市？")

	return {"name": name, "city": city}
```

 "API 参考 (v2)"
```python
def node_a(state: State):
	# ❌ 不好：基于非确定性数据进行循环
	# 中断的次数在每次执行之间会发生变化
	results = []
	for item in state.get("dynamic_list", []):  # 列表可能在每次运行之间发生变化
		result = interrupt(f"批准 {item} 吗？")
		results.append(result)

	return {"results": results}
```

**不要在 `interrupt` 调用中返回复杂值**

根据使用的检查点器，复杂值可能无法序列化（例如，你不能序列化函数）。为了使你的图适应任何部署，最佳实践是只使用可以合理序列化的值。

* ✅ 将简单的、JSON 可序列化的类型传递给 `interrupt`
* ✅ 传递具有简单值的字典/对象

 "API 参考 (v2)"
```python
def node_a(state: State):
	# ✅ 好：传递可序列化的简单类型
	name = interrupt("你叫什么名字？")
	count = interrupt(42)
	approved = interrupt(True)

	return {"name": name, "count": count, "approved": approved}
```

"API 参考 (v2)"
```python
def node_a(state: State):
	# ✅ 好：传递具有简单值的字典
	response = interrupt({
		"question": "输入用户详细信息",
		"fields": ["name", "email", "age"],
		"current_values": state.get("user", {})
	})

	return {"user": response}
```

* 🔴 不要将函数、类实例或其他复杂对象传递给 `interrupt`

"API 参考 (v2)"
```python
def validate_input(value):
	return len(value) > 0

def node_a(state: State):
	# ❌ 不好：将函数传递给 interrupt
	# 该函数无法序列化
	response = interrupt({
		"question": "你叫什么名字？",
		"validator": validate_input  # 这将失败
	})
	return {"name": response}
```

"API 参考 (v2)"
```python
class DataProcessor:
	def __init__(self, config):
		self.config = config

def node_a(state: State):
	processor = DataProcessor({"mode": "strict"})

	# ❌ 不好：将类实例传递给 interrupt
	# 该实例无法序列化
	response = interrupt({
		"question": "输入要处理的数据",
		"processor": processor  # 这将失败
	})
	return {"result": response}
```

** `interrupt` 之前调用的副作用必须是幂等的**

因为中断通过重新运行它们被调用的节点来工作，所以在 `interrupt` 之前调用的副作用应该（理想情况下）是幂等的。作为背景，幂等性意味着同一个操作可以被多次应用，而不会改变初始执行之后的结果。

例如，你可能在节点中有一个 API 调用来更新记录。如果在进行该调用之后调用了 `interrupt`，那么当节点恢复时，它将被多次重新运行，可能会覆盖初始更新或创建重复记录。

* ✅ 在 `interrupt` 之前使用幂等操作
* ✅ 将副作用放在 `interrupt` 调用之后
* ✅ 在可能的情况下，将副作用分离到单独的节点中

 "API 参考 (v2)"
```python
def node_a(state: State):
	# ✅ 好：使用幂等的 upsert 操作
	# 多次运行将具有相同的结果
	db.upsert_user(
		user_id=state["user_id"],
		status="pending_approval"
	)

	approved = interrupt("批准此更改吗？")

	return {"approved": approved}
```

 "API 参考 (v2)"
```python
def node_a(state: State):
	# ✅ 好：将副作用放在中断之后
	# 这确保它仅在收到批准后运行一次
	approved = interrupt("批准此更改吗？")

	if approved:
		db.create_audit_log(
			user_id=state["user_id"],
			action="approved"
		)

	return {"approved": approved}
```

"API 参考 (v2)"
```python
def approval_node(state: State):
	# ✅ 好：在此节点中仅处理中断
	approved = interrupt("批准此更改吗？")

	return {"approved": approved}

def notification_node(state: State):
	# ✅ 好：副作用发生在单独的节点中
	# 这在批准后运行，因此只执行一次
	if (state.approved):
		send_notification(
			user_id=state["user_id"],
			status="approved"
		)

	return state
```

* 🔴 不要在 `interrupt` 之前执行非幂等操作
* 🔴 不要在不检查记录是否存在的情况下创建新记录

 "API 参考 (v2)"
```python
def node_a(state: State):
	# ❌ 不好：在 interrupt 之前创建新记录
	# 这将在每次恢复时创建重复记录
	audit_id = db.create_audit_log({
		"user_id": state["user_id"],
		"action": "pending_approval",
		"timestamp": datetime.now()
	})

	approved = interrupt("批准此更改吗？")

	return {"approved": approved, "audit_id": audit_id}
```

 "API 参考 (v2)"
```python
def node_a(state: State):
	# ❌ 不好：在 interrupt 之前追加到列表
	# 这将在每次恢复时添加重复条目
	db.append_to_history(state["user_id"], "approval_requested")

	approved = interrupt("批准此更改吗？")

	return {"approved": approved}
```

## 与作为函数调用的子图一起使用

当在节点中调用子图时，父图将从调用子图的节点和触发 `interrupt` 的节点的**开头**恢复执行。同样，**子图**也将从调用 `interrupt` 的节点的开头恢复。

```python
def node_in_parent_graph(state: State):
    some_code()  # <-- 这将在恢复时重新执行
    # 作为函数调用子图。
    # 子图中包含一个 `interrupt` 调用。
    subgraph_result = subgraph.invoke(some_input)
    # ...

def node_in_subgraph(state: State):
    some_other_code()  # <-- 这也将在恢复时重新执行
    result = interrupt("你叫什么名字？")
    # ...
```

## 使用中断进行调试

要调试和测试图，你可以使用静态中断作为断点，一次一个节点地单步调试图的执行。静态中断在定义的节点执行之前或之后触发。你可以在编译图时通过指定 `interrupt_before` 和 `interrupt_after` 来设置它们。

对于人机协同工作流，**不**推荐使用静态中断。请改用 `interrupt` 函数。

 "编译时"
```python
graph = builder.compile(
	interrupt_before=["node_a"],  
	interrupt_after=["node_b", "node_c"],  
	checkpointer=checkpointer,
)

# 将线程 ID 传递给图
config = {
	"configurable": {
		"thread_id": "some_thread"
	}
}

# 运行图直到断点
graph.invoke(inputs, config=config)  

# 恢复图
graph.invoke(None, config=config)  
```

1. 断点在 `compile` 时设置。
2. `interrupt_before` 指定在执行节点之前应暂停执行的节点。
3. `interrupt_after` 指定在执行节点之后应暂停执行的节点。
4. 需要检查点器才能启用断点。
5. 图运行直到遇到第一个断点。
6. 通过为输入传递 `None` 来恢复图。这将运行图直到遇到下一个断点。

 "调用时"
```python
config = {
	"configurable": {
		"thread_id": "some_thread"
	}
}

# 运行图直到断点
graph.invoke(
	inputs,
	interrupt_before=["node_a"],  
	interrupt_after=["node_b", "node_c"],  
	config=config,
)

# 恢复图
graph.invoke(None, config=config)  
```

1. `graph.invoke` 使用 `interrupt_before` 和 `interrupt_after` 参数调用。这是一个运行时配置，可以针对每次调用进行更改。
2. `interrupt_before` 指定在执行节点之前应暂停执行的节点。
3. `interrupt_after` 指定在执行节点之后应暂停执行的节点。
4. 图运行直到遇到第一个断点。
5. 通过为输入传递 `None` 来恢复图。这将运行图直到遇到下一个断点。