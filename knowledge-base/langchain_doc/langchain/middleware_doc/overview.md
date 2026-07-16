
在 `create_agent` 中，中间件节点是通过遍历 `middleware` 参数，为每个中间件实例的 **四个生命周期钩子** 按需创建并注册到 `StateGraph` 的。具体定义方式如下：

---

### 1. 钩子节点的添加条件

每个中间件类 `AgentMiddleware` 提供了四种钩子方法：

- `before_agent` / `abefore_agent`
- `before_model` / `abefore_model`
- `after_model` / `aafter_model`
- `after_agent` / `aafter_agent`

判断是否添加节点的依据是：**中间件子类是否重写了默认基类方法**。  
比较方式：

```python
m.__class__.before_agent is not AgentMiddleware.before_agent
or m.__class__.abefore_agent is not AgentMiddleware.abefore_agent
```

只要同步版本或异步版本**任意一个**被重写，就会为该中间件的该钩子创建一个节点。

---

### 2. 节点的运行时实现：`RunnableCallable`

为了同时支持同步和异步执行模式，节点的运行体不是直接传递方法，而是包装进 `RunnableCallable`：

```python
sync_before_agent = (
    m.before_agent
    if m.__class__.before_agent is not AgentMiddleware.before_agent
    else None
)
async_before_agent = (
    m.abefore_agent
    if m.__class__.abefore_agent is not AgentMiddleware.abefore_agent
    else None
)
before_agent_node = RunnableCallable(sync_before_agent, async_before_agent, trace=False)
```

- **如果只重写了同步方法**，则 `sync_xxx` 为实际方法，`async_xxx` 为 `None`；反之亦然。
- `RunnableCallable` 接受两个可选的可调用对象，分别对应 `invoke`（同步）和 `ainvoke`（异步），从而让图在运行时根据上下文自动选择执行路径，避免签名冲突。
- `trace=False` 表示该节点不参与单独的 tracing。

---

### 3. 节点的命名与注册

使用 `graph.add_node()` 注册节点时：

```python
graph.add_node(
    f"{m.name}.before_agent", before_agent_node, input_schema=resolved_state_schema
)
```

- **节点 id**：`{中间件实例名称}.{钩子名}`，例如 `"my_middleware.before_model"`。
- **输入模式**：统一使用合并后的 `resolved_state_schema`（即所有中间件的状态模式与基础 `AgentState` 合并后的最终状态类型），保证所有中间件节点能够访问全量状态字段。

---

### 总结流程

1. 遍历每个中间件实例 `m`。
2. 对四个生命周期钩子逐个检查是否被重写（同步或异步）。
3. 若重写，则提取重写的方法，未重写的设为 `None`。
4. 用 `RunnableCallable(sync_fn, async_fn, trace=False)` 创建节点可运行体。
5. 以 `"{m.name}.{hook}"` 为节点名、`resolved_state_schema` 为输入模式，调用 `graph.add_node()` 注册。

这样设计保证了中间件可以灵活地只实现它关心的生命周期阶段，并在图中以独立节点的形式串联到模型调用前后，实现拦截和修改行为。