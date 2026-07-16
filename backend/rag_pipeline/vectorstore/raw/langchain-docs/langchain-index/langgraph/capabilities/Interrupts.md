# 中断

> 这是 LangGraph 中**中断 (Interrupt)** 机制的胖索引，覆盖动态暂停与恢复、常见工作流模式、中断规则、调试用法及最佳实践。
> 阅读本文档可一次性掌握中断的全部概念及其关联，为构建需要外部输入的人机协同 Agent 提供决策支撑。

---

## 概念全景

中断允许在图节点执行的任意位置暂停，并等待外部输入后再继续。它与静态断点（`interrupt_before` / `interrupt_after`）不同，是**动态的、可编程的**，天然适合审批、审查、交互式验证等场景。

| 维度             | 描述                                                         |
| ---------------- | ------------------------------------------------------------ |
| **触发机制**     | 在节点函数内调用 `interrupt(value)`，value 必须是 JSON 可序列化的 |
| **状态保存**     | 检查点器（checkpointer）自动保存当前图状态，支持暂停后无限等待 |
| **恢复方式**     | 使用 `Command(resume=...)` 重新调用图，恢复值将成为 `interrupt()` 的返回值 |
| **线程标识**     | `config["configurable"]["thread_id"]` 是持久光标，必须一致才能恢复同一会话 |
| **返回值位置**   | 在 `stream(version="v2")` 的 `updates` 流中，通过 `__interrupt__` 字段获取；在 `invoke(version="v2")` 中通过 `GraphOutput.interrupts` 属性获取 |
| **动态特性**     | 可放置在代码任何位置，可包含条件逻辑，允许多次中断 |

核心决策点：**在何处放置中断、传递什么信息作为中断负载、如何处理恢复值、如何保证中断顺序和幂等性**。

---

## 1. 基本使用

### 暂停执行

在节点内调用 `interrupt()` 即可暂停。需要提前配置 checkpointer 并提供 `thread_id`。

```python
def approval_node(state: State):
    approved = interrupt("你批准这个操作吗？")
    return {"approved": approved}
```

执行流程：
1. 图执行到 `interrupt` 行时挂起。
2. 当前状态通过 checkpointer 持久化。
3. 调用者收到中断负载（此处为 `"你批准这个操作吗？"`）。

### 恢复执行

使用相同的 `thread_id`，通过 `Command(resume=value)` 继续执行。`value` 会作为 `interrupt()` 的返回值，节点从**开头重新运行**（`interrupt` 之前的代码会再次执行）。

```python
# 初始调用
config = {"configurable": {"thread_id": "1"}}
graph.invoke({"input": "data"}, config=config, version="v2")
# 恢复
graph.invoke(Command(resume=True), config=config, version="v2")
```

v2 格式下，`invoke()` 返回的 `GraphOutput` 对象包含 `interrupts` 属性，可直接查看中断负载。

---

## 2. 常见模式

### 审批工作流

在关键操作前暂停，根据人工决策路由到不同节点。`interrupt` 可返回 `True`/`False` 或更复杂的结构，节点内据此返回 `Command(goto=...)`。

```python
def approval_node(state):
    decision = interrupt({"question": "...", "details": ...})
    return Command(goto="proceed" if decision else "cancel")
```

### 审查和编辑状态

将当前生成的内容通过 `interrupt` 暴露给审查者，恢复时接收编辑后的文本，直接更新状态。

```python
def review_node(state):
    edited = interrupt({"instruction": "审查并编辑", "content": state["generated_text"]})
    return {"generated_text": edited}
# 恢复时传入编辑后的文本
graph.invoke(Command(resume="改进后的内容"), config=config)
```

### 工具内的中断

在工具函数内部调用 `interrupt`，使工具在被调用时自动暂停等待批准。适用于需要在工具执行前进行人工检查的场合。

```python
@tool
def send_email(to, subject, body):
    response = interrupt({"action": "send_email", "to": to, ...})
    if response.get("action") == "approve":
        # 可覆盖原始参数
        ...
```

### 处理多个并行中断

当多个节点同时中断时，恢复时需要将每个中断 ID 映射到对应的恢复值。可通过 `resume_map` 一次性恢复所有中断。

```python
resume_map = {i.id: f"answer for {i.value}" for i in interrupted_result["__interrupt__"]}
graph.invoke(Command(resume=resume_map), config)
```

### 验证人类输入

利用循环 + `interrupt` 实现输入验证，直到满足条件才退出。

```python
def get_age_node(state):
    prompt = "你的年龄是多少？"
    while True:
        answer = interrupt(prompt)
        if isinstance(answer, int) and answer > 0:
            break
        prompt = f"'{answer}' 不是有效年龄，请重新输入。"
    return {"age": answer}
```

### 流式处理中的中断

使用 `stream_mode=["messages", "updates"]` 与 `version="v2"` 结合，通过检查 `__interrupt__` 键来实时捕获中断，并动态恢复。

---

## 3. 中断规则与陷阱

### 禁止用 try/except 包裹 interrupt

`interrupt` 通过内部异常实现暂停，若被 `except Exception` 捕获，中断将失效。需要捕获时，应使用具体的异常类型，并在 `interrupt` 调用之前或之后分离错误处理。

### 保持中断调用顺序一致

节点恢复时从头重新运行，按**索引顺序**匹配恢复值。因此，不能在节点内**有条件跳过**中断，也不能使用不确定的循环次数来调用 `interrupt`。

### 只传递 JSON 可序列化的值

复杂对象（函数、类实例、某些数据类型）无法序列化，会导致错误。仅使用字符串、数字、布尔值、列表、字典等简单结构。

### interrupt 之前的副作用必须幂等

节点恢复时会重新执行 `interrupt` 之前的代码。若在该部分执行了非幂等操作（如创建记录、发送网络请求），会导致重复。应将副作用移至 `interrupt` 之后，或拆分到独立节点。

### 子图中的中断

当子图作为函数调用时，父图与子图都会从各自调用 `interrupt` 的节点开头恢复执行，需注意双方的前置逻辑是否幂等。

---

## 4. 调试用静态中断

编译时或调用时设置 `interrupt_before` / `interrupt_after`，可在指定节点执行前后暂停，用于调试而非生产人机协同。

```python
graph = builder.compile(interrupt_before=["node_a"], checkpointer=ck)
# 或调用时
graph.invoke(input, interrupt_before=["node_a"], config=config)
# 恢复时传入 None
graph.invoke(None, config=config)
```

不推荐在人机协同中使用此静态方式，应优先使用动态 `interrupt()`。

---

## 5. 关键约束与最佳实践

- **始终配置持久化的 checkpointer**：生产环境使用 `PostgresSaver`/`SqliteSaver`，避免内存存储丢失状态。
- **thread_id 即会话 ID**：保持与中断发生时一致，否则无法恢复。
- **中断负载信息足够丰富**：包含操作描述、上下文数据，以便审查者做出决策。
- **处理多个中断时，用 ID 映射而非依赖顺序**：防止顺序错乱。
- **节点逻辑尽可能简单**：将中断集中放置，前置逻辑保持幂等（如只读取、计算）。
- **避免循环内中断次数不确定**：若确实需要动态次数，改用子图或将每次中断独立到不同节点。
- **结合流式传输实现实时交互**：使用 `stream_mode=["messages", "updates"]` 和 v2 格式。

---

## 6. 与全局概念的关联

- **检查点 (Checkpointer)**：中断依赖检查点保存状态，也是短期记忆的基础设施。
- **人机协同 (Human-in-the-loop)**：中断是实现 HITL 的核心原语，`HumanInTheLoopMiddleware` 底层即基于中断构建。
- **工具 (Tools)**：工具内可直接使用 `interrupt` 实现执行前审批，与中间件级 HITL 互补。
- **流式传输 (Streaming)**：通过 `updates` 模式捕获 `__interrupt__`，实现前端与中断交互。
- **上下文工程**：中断可向用户展示状态，用户反馈可更新 State 或 Store，改变模型后续行为。
- **短期记忆 (Short-term memory)**：中断暂停时，State 被完整保存；恢复后 State 保持连续性。

---

## 链接原文

### 语义检索（聚焦查询）

- `interrupt 函数 暂停 恢复 Command resume` → 基本用法
- `Human-in-the-loop 审批 中断` → 审批模式
- `审查 编辑 状态 interrupt` → 审查编辑
- `工具 中断 send_email interrupt` → 工具内中断
- `多个 中断 并行 resume_map` → 并行中断处理
- `验证 人类 输入 循环 interrupt` → 验证循环
- `中断规则 try/except 幂等 序列化` → 三大规则
- `静态中断 interrupt_before interrupt_after` → 调试断点

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 使用 interrupt 暂停`、`### 批准或拒绝`、`### 中断规则`），可用 `read_file` 精确展开对应章节。