---
name: deep-agents-memory
description: "INVOKE THIS SKILL when your Deep Agent needs memory, persistence, or filesystem access. Covers agent-scoped vs user-scoped memory, StateBackend (ephemeral), StoreBackend (persistent), FilesystemBackend, CompositeBackend, and FilesystemMiddleware."
---

<overview>
Deep Agents 使用可插拔后端进行文件操作和记忆：

**短期记忆（StateBackend）**: 单个线程内持久，线程结束即丢失
**长期记忆（StoreBackend）**: 跨线程和会话持久
**混合存储（CompositeBackend）**: 将不同路径路由到不同后端
**本地开发（FilesystemBackend）**: 直接磁盘访问，配合 virtual_mode 安全使用

FilesystemMiddleware 提供工具：`ls`、`read_file`、`write_file`、`edit_file`、`glob`、`grep`
</overview>

<backend-selection>

| 场景 | 后端 | 原因 |
|------|------|------|
| 临时工作文件 | StateBackend | 默认，无需配置 |
| 本地开发 CLI | FilesystemBackend | 直接磁盘访问 |
| 跨会话记忆 | StoreBackend | 跨线程持久化 |
| 混合存储 | CompositeBackend | 混合临时 + 持久 |

</backend-selection>

---

## 记忆作用域

<memory-scoping>
Deep Agents 支持两种常见的记忆作用域模式：

### Agent 作用域记忆（Agent-scoped）

让 agent 拥有自己的持久身份，在所有用户间共享。后端命名空间设为 `(assistant_id,)`，意味着此 agent 的所有对话都读写同一个记忆文件。

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/memories/AGENTS.md"],
    skills=["/skills/"],
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(
                namespace=lambda rt: (rt.server_info.assistant_id,),
            ),
            "/skills/": StoreBackend(
                namespace=lambda rt: (rt.server_info.assistant_id,),
            ),
        },
    ),
)
```

访问 `rt.server_info` 需要 `deepagents>=0.5.0`。旧版从 `get_config()["metadata"]["assistant_id"]` 获取。

### User 作用域记忆（User-scoped）

按用户隔离记忆，每个用户看到自己独立的记忆文件。将 `user_id` 加入命名空间：

```python
backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/memories/": StoreBackend(
            namespace=lambda rt: (rt.server_info.user_id,),
        ),
    },
)
```
</memory-scoping>

<ex-default-state-backend>
<python>
默认 StateBackend 在线程内临时存储文件。

```python
from deepagents import create_deep_agent

agent = create_deep_agent()  # 默认：StateBackend
result = agent.invoke({
    "messages": [{"role": "user", "content": "把笔记写入 /draft.txt"}]
}, config={"configurable": {"thread_id": "thread-1"}})
# /draft.txt 在线程结束时会丢失
```
</python>
<typescript>
默认 StateBackend 在线程内临时存储文件。

```typescript
import { createDeepAgent } from "deepagents";

const agent = await createDeepAgent();  // 默认：StateBackend
const result = await agent.invoke({
  messages: [{ role: "user", content: "把笔记写入 /draft.txt" }]
}, { configurable: { thread_id: "thread-1" } });
// /draft.txt 在线程结束时会丢失
```
</typescript>
</ex-default-state-backend>

<ex-composite-backend-for-hybrid>
<python>
配置 CompositeBackend 将路径路由到不同的存储后端。

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

composite_backend = lambda rt: CompositeBackend(
    default=StateBackend(rt),
    routes={"/memories/": StoreBackend(rt)}
)

agent = create_deep_agent(backend=composite_backend, store=store)

# /draft.txt -> 临时存储（StateBackend）
# /memories/user-prefs.txt -> 持久存储（StoreBackend）
```
</python>
<typescript>
配置 CompositeBackend 将路径路由到不同的存储后端。

```typescript
import { createDeepAgent, CompositeBackend, StateBackend, StoreBackend } from "deepagents";
import { InMemoryStore } from "@langchain/langgraph";

const store = new InMemoryStore();

const agent = await createDeepAgent({
  backend: (config) => new CompositeBackend(
    new StateBackend(config),
    { "/memories/": new StoreBackend(config) }
  ),
  store
});
```
</typescript>
</ex-composite-backend-for-hybrid>

<ex-cross-session-memory>
<python>
/memories/ 路径下的文件通过 StoreBackend 路由跨线程持久化。

```python
# 使用上例的 CompositeBackend
config1 = {"configurable": {"thread_id": "thread-1"}}
agent.invoke({"messages": [{"role": "user", "content": "保存到 /memories/style.txt"}]}, config=config1)

config2 = {"configurable": {"thread_id": "thread-2"}}
agent.invoke({"messages": [{"role": "user", "content": "读取 /memories/style.txt"}]}, config=config2)
# 线程 2 可以读取线程 1 保存的文件
```
</python>
<typescript>
/memories/ 路径下的文件通过 StoreBackend 路由跨线程持久化。

```typescript
const config1 = { configurable: { thread_id: "thread-1" } };
await agent.invoke({ messages: [{ role: "user", content: "保存到 /memories/style.txt" }] }, config1);

const config2 = { configurable: { thread_id: "thread-2" } };
await agent.invoke({ messages: [{ role: "user", content: "读取 /memories/style.txt" }] }, config2);
// 线程 2 可以读取线程 1 保存的文件
```
</typescript>
</ex-cross-session-memory>

<ex-agent-scoped-memory-full>
<python>
完整的 agent 作用域记忆示例：填充初始记忆、跨两个线程调用 agent 并观察它记住并更新所学内容。

```python
from langchain_core.utils.uuid import uuid7
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()  # 部署到 LangSmith 时使用平台存储

# 填充记忆文件
store.put(
    ("my-agent",),
    "/memories/AGENTS.md",
    create_file_data("""## 回复风格
- 保持回复简洁
- 在可能的情况下使用代码示例
"""),
)

# 填充技能
store.put(
    ("my-agent",),
    "/skills/langgraph-docs/SKILL.md",
    create_file_data("""---
name: langgraph-docs
description: 获取相关的 LangGraph 文档以提供准确指导。
---

# langgraph-docs
使用 fetch_url 工具读取文档。"""),
)

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/memories/AGENTS.md"],
    skills=["/skills/"],
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/memories/": StoreBackend(namespace=lambda rt: ("my-agent",)),
            "/skills/": StoreBackend(namespace=lambda rt: ("my-agent",)),
        },
    ),
    store=store,
)
```
</python>
</ex-agent-scoped-memory-full>

<ex-filesystem-backend-local-dev>
<python>
在本地开发中使用 FilesystemBackend 实现真实的磁盘访问，配合人机协同。

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),  # 限制访问范围
    interrupt_on={"write_file": True, "edit_file": True},
    checkpointer=MemorySaver()
)
```
</python>
<typescript>
在本地开发中使用 FilesystemBackend 实现真实的磁盘访问，配合人机协同。

```typescript
import { createDeepAgent, FilesystemBackend } from "deepagents";
import { MemorySaver } from "@langchain/langgraph";

const agent = await createDeepAgent({
  backend: new FilesystemBackend({ rootDir: ".", virtualMode: true }),
  interruptOn: { write_file: true, edit_file: true },
  checkpointer: new MemorySaver()
});
```
</typescript>

**安全警告：绝不在 Web 服务器中使用 FilesystemBackend —— 使用 StateBackend 或沙箱代替。**
</ex-filesystem-backend-local-dev>

<ex-store-in-custom-tools>
<python>
在自定义工具中直接访问 store 进行长期记忆操作。

```python
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore

@tool
def get_user_preference(key: str, runtime: ToolRuntime) -> str:
    """从长期存储中获取用户偏好。"""
    store = runtime.store
    result = store.get(("user_prefs",), key)
    return str(result.value) if result else "Not found"

@tool
def save_user_preference(key: str, value: str, runtime: ToolRuntime) -> str:
    """将用户偏好保存到长期存储。"""
    store = runtime.store
    store.put(("user_prefs",), key, {"value": value})
    return f"已保存 {key}={value}"

store = InMemoryStore()

agent = create_agent(
    model="gpt-4.1",
    tools=[get_user_preference, save_user_preference],
    store=store
)
```
</python>
</ex-store-in-custom-tools>

<boundaries>
### Agent 可以配置的内容

- 后端类型和配置
- CompositeBackend 的路由规则
- FilesystemBackend 的根目录
- 文件操作的人机协同审批
- 记忆作用域（agent 级别或 user 级别）
- 初始记忆文件内容

### Agent 不能配置的内容

- 工具名称（ls、read_file、write_file、edit_file、glob、grep）
- 在 virtual_mode 限制之外访问文件
- 在没有正确后端设置的情况下访问跨线程文件
</boundaries>

<fix-storebackend-requires-store>
<python>
StoreBackend 需要 store 实例。

```python
# 错误
agent = create_deep_agent(backend=lambda rt: StoreBackend(rt))

# 正确
agent = create_deep_agent(backend=lambda rt: StoreBackend(rt), store=InMemoryStore())
```
</python>
<typescript>
StoreBackend 需要 store 实例。

```typescript
// 错误
const agent = await createDeepAgent({ backend: (c) => new StoreBackend(c) });

// 正确
const agent = await createDeepAgent({ backend: (c) => new StoreBackend(c), store: new InMemoryStore() });
```
</typescript>
</fix-storebackend-requires-store>

<fix-statebackend-files-dont-persist>
<python>
StateBackend 文件是线程作用域的 —— 使用相同 thread_id 或 StoreBackend 进行跨线程访问。

```python
# 错误：线程 2 无法读取线程 1 的文件
agent.invoke({"messages": [...]}, config={"configurable": {"thread_id": "thread-1"}})  # 写入
agent.invoke({"messages": [...]}, config={"configurable": {"thread_id": "thread-2"}})  # 文件未找到！
```
</python>
<typescript>
StateBackend 文件是线程作用域的 —— 使用相同 thread_id 或 StoreBackend 进行跨线程访问。

```typescript
// 错误：线程 2 无法读取线程 1 的文件
await agent.invoke({ messages: [...] }, { configurable: { thread_id: "thread-1" } });
await agent.invoke({ messages: [...] }, { configurable: { thread_id: "thread-2" } });
```
</typescript>
</fix-statebackend-files-dont-persist>

<fix-path-prefix-for-persistence>
<python>
路径必须匹配 CompositeBackend 的路由前缀才能持久化。

```python
# 路由 = {"/memories/": StoreBackend(rt)}:
agent.invoke(...)  # /prefs.txt -> 临时存储（不匹配任何路由）
agent.invoke(...)  # /memories/prefs.txt -> 持久存储（匹配路由）
```
</python>
<typescript>
路径必须匹配 CompositeBackend 的路由前缀才能持久化。

```typescript
// 路由 = { "/memories/": StoreBackend }:
await agent.invoke(...);  // /prefs.txt -> 临时存储
await agent.invoke(...);  // /memories/prefs.txt -> 持久存储
```
</typescript>
</fix-path-prefix-for-persistence>

<fix-production-store>
<python>
生产环境使用 PostgresStore（InMemoryStore 重启后丢失）。

```python
# 错误                              # 正确
store = InMemoryStore()             store = PostgresStore(connection_string="postgresql://...")
```
</python>
<typescript>
生产环境使用 PostgresStore（InMemoryStore 重启后丢失）。

```typescript
// 错误                                    // 正确
const store = new InMemoryStore();         const store = new PostgresStore({ connectionString: "..." });
```
</typescript>
</fix-production-store>

<fix-filesystem-backend-needs-virtual-mode>
<python>
启用 virtual_mode=True 以限制路径访问（防止 ../ 和 ~/ 转义）。

```python
backend = FilesystemBackend(root_dir="/project", virtual_mode=True)  # 安全
```
</python>
</fix-filesystem-backend-needs-virtual-mode>

<fix-longest-prefix-match>
<python>
CompositeBackend 按最长前缀优先匹配。

```python
routes = {"/mem/": StoreBackend(rt), "/mem/temp/": StateBackend(rt)}
# /mem/file.txt -> StoreBackend, /mem/temp/file.txt -> StateBackend（更长匹配）
```
</python>
</fix-longest-prefix-match>
