`CodeInterpreterMiddleware` 是一个面向 AI Agent 的中间件，它在每个 LangGraph 会话中提供一个**持久化、沙箱化的 JavaScript REPL 执行环境**。Agent 可以把 JavaScript 代码当作一个工具来调用，REPL 中的变量、函数等会在同一线程的多轮对话间保持，直到线程结束或被手动回收。

下面按模块的组成、核心机制和使用要点逐层解析。

---

## 1. 模块定位与依赖

| 依赖来源 | 说明 |
|---------|------|
| `langchain_quickjs`（内部包） | 封装 QuickJS 运行时，提供 REPL 创建、代码执行、控制台捕获、PTC 桥接、快照序列化等能力。 |
| `deepagents` / `langchain.agents` | 提供 AgentMiddleware 基类、AgentState、ModelRequest/Response 等抽象。 |
| `langgraph` | 提供运行时 `get_config`，用于从当前运行上下文中提取 `thread_id`。 |

该中间件继承 `AgentMiddleware[REPLState, ContextT, ResponseT]`，通过实现 `before_agent`、`after_agent`、`wrap_model_call` 等钩子介入 Agent 的整个生命周期。

---

## 2. 自定义状态 `REPLState`

```python
class REPLState(AgentState):
    _quickjs_snapshot_payload: NotRequired[Annotated[bytes | None, PrivateStateAttr]]
```

- 在原有 `AgentState` 基础上增加了一个**私有属性** `_quickjs_snapshot_payload`，用于存储 QuickJS 运行时状态的序列化快照（字节串）。
- 这个属性的存在使得 REPL 状态可以在 Agent 的多个 Turn 之间**持久化**：某一 Turn 结束时生成快照存入状态，下一 Turn 开始时恢复。

---

## 3. 线程 ID 解析 `_resolve_thread_id`

```python
def _resolve_thread_id(fallback: str) -> str:
    try:
        config = get_config()
    except RuntimeError:
        return fallback
    thread_id = config.get("configurable", {}).get("thread_id") if config else None
    return str(thread_id) if thread_id is not None else fallback
```

- **作用**：确定当前调用属于哪个 LangGraph 线程，以便为该线程分配独立的 REPL 实例。
- **后备方案**：如果不在 LangGraph 上下文内（如单元测试或直接 `agent.invoke` 未设 `thread_id`），则回退到中间件实例创建时生成的 `_fallback_thread_id`，保证同一中间件实例内所有 `eval` 调用共享同一个 REPL，避免出现 `tools is not defined` 等错误。

---

## 4. 核心工具 `eval` 的构建

工具由 `_build_tool` 方法创建，类型为 `StructuredTool`：

- **名称**：默认为 `"eval"`，可通过 `tool_name` 自定义。
- **输入模式** `EvalSchema`：仅一个字段 `code: str`，即要执行的 JavaScript 代码。
- **描述**：向模型说明这是一个**持久沙箱 REPL**，无文件系统/网络/真实时钟，且不支持顶层 `await`（因为是同步调用，异步逻辑需在函数内部使用 `await`）。

### 同步/异步执行流程

```python
def sync_eval(runtime, code) -> ToolMessage:
    repl = registry.get(_resolve_thread_id(fallback_id))
    skills = middleware._skills_for_eval(runtime)
    return _run(lambda c: repl.eval_sync(c, skills=..., skills_backend=..., outer_runtime=runtime),
                code, runtime.tool_call_id)
```

`async_eval` 类似，区别在于调用 `repl.eval_async` 并传入外层事件循环。

- 从 `_registry` 中按线程 ID 获取（或惰性创建）REPL 实例。
- 收集需要导入的技能元数据（若配置了 `skills_backend`）。
- 执行代码，得到 `outcome`（包含结果、stdout、错误等）。
- 用 `format_outcome` 将结果格式化为字符串，并截断至 `max_result_chars` 长度，返回 `ToolMessage`。

---

## 5. 技能（Skills）支持

通过 `skills_backend: BackendProtocol | None` 参数，REPL 可以**动态导入**以 `@/skills/<name>` 路径表示的技能模块。

- 在 `_skills_for_eval` 中，从当前 `runtime.state` 的 `skills_metadata` 列表里提取元数据，构建 `{name: metadata}` 字典。
- 当 REPL 执行 `await import("@/skills/xxx")` 时，会利用 `BackendProtocol` 读取源代码并注入沙箱。
- 需要配合使用 `SkillsMiddleware` 来填充 `skills_metadata` 状态字段。

---

## 6. 程序化工具调用（PTC）

`ptc` 参数允许 **REPL 内部的 JavaScript 代码直接调用 Agent 的其他工具**，例如：

```js
const result = await tools.search("some query");
```

### 工作机制

1. **工具过滤**：在 `_prepare_for_call` 中，通过 `filter_tools_for_ptc` 根据 `ptc` 参数（允许列表）筛选当前请求中的工具，并排除 REPL 自身的 `eval` 工具以防止递归。
2. **安装桥接**：`repl.install_tools(exposed)` 在 QuickJS 上下文中创建名为 `tools.<camelCase>` 的宿主函数，每个函数接受参数并返回 `Promise<string>`。
3. **系统提示**：动态生成 PTC 的使用说明和签名，附加到发送给模型的基础系统提示中。
4. **缓存**：按暴露工具的名称集合缓存渲染好的提示文本，避免每轮重复生成。

**安全警告**：PTC 调用会绕过正常的 `ToolNode` 路径，因此不支持 `interrupt_on` 等人机交互（HITL）审批机制。调用次数受 `max_ptc_calls` 限制，超出会抛出 `PTCCallBudgetExceeded`，防止无限循环。

---

## 7. 生命周期钩子与状态快照

### before_agent / abefore_agent（每次 Turn 开始前）

```python
def before_agent(self, state, runtime) -> dict | None:
    if not self._snapshot_between_turns:
        return None
    payload = state.get("_quickjs_snapshot_payload")
    if payload is None: return None
    repl = self._registry.get(thread_id)
    repl.restore_snapshot(payload, inject_globals=True)
    # 恢复失败则返回 {"_quickjs_snapshot_payload": None} 清除损坏数据
```

- 若开启 `snapshot_between_turns` 且状态中存在快照，则将其反序列化并注入到当前线程的 REPL，恢复上一轮结束时的完整 JavaScript 状态（全局变量、函数、模块等）。

### after_agent / aafter_agent（每次 Turn 结束后）

```python
def after_agent(self, state, runtime) -> dict | None:
    if not self._snapshot_between_turns:
        self._registry.evict(thread_id)   # 不保存快照，直接释放资源
        return None
    repl = self._registry.get_if_exists(thread_id)
    if repl is None: return None
    payload = repl.create_snapshot()
    # 检查快照大小，超限则丢弃
    update = self._snapshot_update(payload=payload, thread_id=thread_id)
    self._registry.evict(thread_id)
    return update
```

- 开启快照时，序列化当前 REPL 状态，通过 `_snapshot_update` 检查大小（不能超过 `max_snapshot_bytes`），超限则警告并返回 `None`，否则更新状态中的 `_quickjs_snapshot_payload`。
- 最后调用 `evict` 将 REPL 从注册表中移除，**释放 QuickJS 运行时所占内存**（但序列化快照已保存在状态中，下一轮可恢复）。

### wrap_model_call / awrap_model_call

每次模型被调用前，将系统提示（基础 REPL 说明 + 可选的 PTC 提示）注入到请求的 `SystemMessage` 中，让模型知道 `eval` 工具的存在及使用方法。

---

## 8. 初始化参数详解

| 参数 | 默认值 | 作用 |
|------|--------|------|
| `memory_limit` | 64 MiB | QuickJS 堆内存总量限制。 |
| `timeout` | 5 秒 | 单次 `eval` 调用最大执行时间（挂钟时间）。 |
| `max_ptc_calls` | 256 | PTC 桥接调用次数上限，`None` 禁用预算（有 DoS 风险）。 |
| `tool_name` | `"eval"` | 暴露给模型的工具名称。 |
| `max_result_chars` | 4000 | 执行结果和控制台输出各自的最大字符数，超出截断。 |
| `capture_console` | `True` | 是否捕获 `console.log/warn/error` 并返回给模型。 |
| `ptc` | `None` | PTC 配置，可为工具名字符串列表、`BaseTool` 实例或混合。 |
| `skills_backend` | `None` | 实现 `BackendProtocol` 的后端，用于读取技能源代码。 |
| `snapshot_between_turns` | `True` | 是否在 Agent Turn 之间保存/恢复 REPL 状态。 |
| `max_snapshot_bytes` | 等于 `memory_limit` | 快照序列化字节数上限，超限则丢弃快照（状态重置）。 |

---

## 9. 资源管理与清理

- `_Registry` 内部管理 QuickJS 的 worker 和运行时，提供 `get`、`get_if_exists`、`evict`、`close` 等方法。
- 每次 Turn 结束后立即 `evict`，确保空闲的 REPL 不会长期占用内存。
- `__del__` 方法中调用 `self._registry.close()` 做**尽力清理**，在解释器关闭或 GC 回收时释放底层 QuickJS 资源，并捕获所有异常以免影响正常退出。

---

## 10. 总结：数据流与应用模式

一个典型的使用场景如下：

1. 创建 Agent 时加入该中间件：  
   ```python
   agent = create_deep_agent(
       model="...",
       middleware=[CodeInterpreterMiddleware(ptc=["search"], skills_backend=backend)],
   )
   ```
2. Agent 第一轮思考 → 模型看到 `eval` 工具及 PTC 提示 → 可能调用 `eval("let x = 1; x + 1")`。
3. 返回 `ToolMessage` 包含结果 `2`，模型继续推理。
4. 该轮结束后，REPL 状态被序列化并存入状态，REPL 实例被回收。
5. 下一轮开始前，从状态恢复 REPL 到同样的 QuickJS 上下文，之前定义的变量 `x` 仍然存在。
6. 若 REPL 内部代码调用了 `tools.search(...)`，请求会被桥接到 Agent 的 `search` 工具（PTC），执行结果以 Promise 形式返回。

该设计实现了 **代码执行、工具组合、跨轮持久化** 的统一抽象，同时通过内存限制、超时、调用预算等手段保证了安全性，非常适合需要多步计算、数据处理或复杂逻辑编排的 Agent 应用。