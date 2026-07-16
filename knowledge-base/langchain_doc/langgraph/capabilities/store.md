# Stores

> LangGraph stores 提供跨线程的长期记忆，与每个线程的 checkpointer 持久化互补。

Stores 允许 agent 跨线程持久化信息，包括用户偏好、累积的知识以及应持续存在超过单次对话的事实。与 [checkpointers]（保存限于一个线程的完整图 state）不同，stores 保存可从任意线程访问的任意键值数据。

**Agent Server 会自动处理 stores**
当使用 [Agent Server] 时，您无需手动实现或配置 stores。API 在幕后为您处理所有存储基础设施。

[InMemoryStore] 适用于开发和测试。对于生产环境，请使用持久化 store，如 `PostgresStore`、`MongoDBStore` 或 `RedisStore`。所有实现都扩展自 [BaseStore]，后者是节点函数签名中使用的类型注解。

## Basic usage

以下代码片段独立展示了 [InMemoryStore]，不涉及 LangGraph：

```python
from langgraph.store.memory import InMemoryStore
store = InMemoryStore()
```

Memories 通过 `tuple` 划分命名空间，下例中为 `(<user_id>, "memories")`。命名空间长度可以是任意的，可表示任何内容，不必是用户特定的。

```python
user_id = "1"
namespace_for_memory = (user_id, "memories")
```

使用 `store.put` 方法将 memories 保存到 store 中的命名空间。指定如上定义的命名空间，以及 memory 的键值对：键仅是 memory 的唯一标识符 (`memory_id`)，值（一个字典）是 memory 本身。

```python
memory_id = str(uuid.uuid4())
memory = {"food_preference" : "I like pizza"}
store.put(namespace_for_memory, memory_id, memory)
```

使用 `store.search` 方法从命名空间中读取 memories，它返回指定用户的 memories 列表，最多到 `limit` 参数（默认 `10`）。在 `InMemoryStore` 中，项目按插入顺序返回，因此最新的 memory 位于列表末尾；其他后端可能以不同顺序排列 memories（参见 [Listing items in a namespace]）。

```python
memories = store.search(namespace_for_memory)
memories[-1].dict()
{'value': {'food_preference': 'I like pizza'},
 'key': '07e0caf4-1631-47b7-b15f-65515d4c1843',
 'namespace': ['1', 'memories'],
 'created_at': '2024-10-02T17:22:31.590602+00:00',
 'updated_at': '2024-10-02T17:22:31.590605+00:00'}
```

每个 memory 类型是一个 Python 类 ([`Item`])，具有特定属性。我们可以通过 `.dict` 将其转换为字典来访问。

其属性有：

* `value`: 该 memory 的值（本身是一个字典）

* `key`: 此命名空间中该 memory 的唯一键

* `namespace`: 字符串元组，此 memory 类型的命名空间

  虽然类型是 `tuple[str, ...]`，但在转换为 JSON 时可能被序列化为列表（例如 `['1', 'memories']`）。

* `created_at`: 此 memory 创建时的时间戳

* `updated_at`: 此 memory 更新时的时间戳

## Listing items in a namespace

调用 [`store.search`]（或异步的 [`store.asearch`]）且不提供 `query` 和 `filter` 时，会返回 `namespace_prefix` 下存储的项目，最多 `limit` 个。当不需要语义排序时，用它来枚举命名空间中的所有内容。

```python
# Return up to 100 items stored under ("alice", "memories").
items = store.search(("alice", "memories"), limit=100)
```

需要牢记的三种行为：

* **`namespace_prefix` 按前缀匹配，而非精确匹配。** `("alice",)` 也会返回 `("alice", "memories")`、`("alice", "preferences")` 等之下的项目。要限定在单一级别，可传递完整命名空间或在客户端按 `item.namespace` 过滤返回的项目。
* **超过 `limit` 的结果会被静默截断。** 没有溢出信号——请将 `limit` 设置得高于预期最大值，或使用 `offset` 进行分页。
* **默认排序取决于 store 后端。** `PostgresStore` 和 `AsyncPostgresStore` 返回的结果按 `updated_at` 降序排列（最近更新的在前）。`InMemoryStore` 按插入顺序返回结果（最近插入的在后）。不要依赖跨实现的特定顺序；如果顺序重要，请在客户端按 `item.updated_at` 排序。

要分页遍历大型命名空间：

```python
page_size = 50
offset = 0
while True:
    page = store.search(("alice", "memories"), limit=page_size, offset=offset)
    if not page:
        break
    for item in page:
        pass
    offset += page_size
```

要发现存在哪些命名空间（例如，在列出每个用户的 memories 之前遍历所有用户），请使用 [`store.list_namespaces`] 或 [`store.alist_namespaces`]：

```python
# All namespaces that start with ("alice",), truncated to two levels deep.
namespaces = store.list_namespaces(prefix=("alice",), max_depth=2)
```

## Semantic search

除了简单检索，store 还支持语义搜索，允许您根据含义而非精确匹配查找 memories。要启用此功能，请为 store 配置 embedding 模型：

```python
from langchain.embeddings import init_embeddings

store = InMemoryStore(
    index={
        "embed": init_embeddings("openai:text-embedding-3-small"),  # Embedding provider
        "dims": 1536,                              # Embedding dimensions
        "fields": ["food_preference", "$"]              # Fields to embed
    }
)
```

现在搜索时，您可以使用自然语言查询来查找相关的 memories：

```python
# Find memories about food preferences
# (This can be done after putting memories into the store)
memories = store.search(
    namespace_for_memory,
    query="What does the user like to eat?",
    limit=3  # Return top 3 matches
)
```

您可以通过配置 `fields` 参数或在存储 memories 时指定 `index` 参数，来控制对 memories 的哪些部分进行嵌入：

```python
# Store with specific fields to embed
store.put(
    namespace_for_memory,
    str(uuid.uuid4()),
    {
        "food_preference": "I love Italian cuisine",
        "context": "Discussing dinner plans"
    },
    index=["food_preference"]  # Only embed "food_preferences" field
)

# Store without embedding (still retrievable, but not searchable)
store.put(
    namespace_for_memory,
    str(uuid.uuid4()),
    {"system_info": "Last updated: 2024-01-01"},
    index=False
)
```

## Using in LangGraph

store 与 checkpointer 协同工作：checkpointer 将 state 保存到线程，如前所述，而 store 允许您存储任意信息以供 *跨* 线程访问。如下所示，用 checkpointer 和 store 编译图。

```python
from dataclasses import dataclass
from langgraph.checkpoint.memory import InMemorySaver

@dataclass
class Context:
    user_id: str

# We need this because we want to enable threads (conversations)
checkpointer = InMemorySaver()

# ... Define the graph ...

# Compile the graph with the checkpointer and store
builder = StateGraph(MessagesState, context_schema=Context)
# ... add nodes and edges ...
graph = builder.compile(checkpointer=checkpointer, store=store)
```

然后像之前一样用 `thread_id` 调用图，同时提供 `user_id`，它像之前一样用作此特定用户的 memories 命名空间。

```python
# Invoke the graph
config = {"configurable": {"thread_id": "1"}}

# First let's just say hi to the AI
for update in graph.stream(
    {"messages": [{"role": "user", "content": "hi"}]},
    config,
    stream_mode="updates",
    context=Context(user_id="1"),
):
    print(update)
```

您可以使用 `Runtime` 对象从 *任何节点* 访问 store 和 `user_id`。当您将 `Runtime` 作为参数添加到节点函数时，LangGraph 会自动注入它。您可以用它来保存 memories：

```python
from langgraph.runtime import Runtime
from dataclasses import dataclass

@dataclass
class Context:
    user_id: str

async def update_memory(state: MessagesState, runtime: Runtime[Context]):

    # Get the user id from the runtime context
    user_id = runtime.context.user_id

    # Namespace the memory
    namespace = (user_id, "memories")

    # ... Analyze conversation and create a new memory

    # Create a new memory ID
    memory_id = str(uuid.uuid4())

    # We create a new memory
    await runtime.store.aput(namespace, memory_id, {"memory": memory})

```

您也可以从任何节点访问 store，并使用 `store.search` 方法获取 memories。Memories 以对象列表的形式返回，可转换为字典。

```python
memories[-1].dict()
{'value': {'food_preference': 'I like pizza'},
 'key': '07e0caf4-1631-47b7-b15f-65515d4c1843',
 'namespace': ['1', 'memories'],
 'created_at': '2024-10-02T17:22:31.590602+00:00',
 'updated_at': '2024-10-02T17:22:31.590605+00:00'}
```

您访问 memories 并在模型调用中使用它们。

```python
from dataclasses import dataclass
from langgraph.runtime import Runtime

@dataclass
class Context:
    user_id: str

async def call_model(state: MessagesState, runtime: Runtime[Context]):
    # Get the user id from the runtime context
    user_id = runtime.context.user_id

    # Namespace the memory
    namespace = (user_id, "memories")

    # Search based on the most recent message
    memories = await runtime.store.asearch(
        namespace,
        query=state["messages"][-1].content,
        limit=3
    )
    info = "\n".join([d.value["memory"] for d in memories])

    # ... Use memories in the model call
```

如果您创建新线程，只要 `user_id` 相同，您仍然可以访问相同的 memories。

```python
# Invoke the graph on a new thread
config = {"configurable": {"thread_id": "2"}}

# Let's say hi again
for update in graph.stream(
    {"messages": [{"role": "user", "content": "hi, tell me about my memories"}]},
    config,
    stream_mode="updates",
    context=Context(user_id="1"),
):
    print(update)
```

当您在本地使用 LangSmith（例如在 [Studio] 中）或 [hosted] 时，基础 store 默认可用，您无需在图编译期间指定它。但是，要启用语义搜索，您 **确实** 需要在 `langgraph.json` 文件中配置索引设置。例如：

```json
{
    ...
    "store": {
        "index": {
            "embed": "openai:text-embeddings-3-small",
            "dims": 1536,
            "fields": ["$"]
        }
    }
}
```

有关更多详细信息和配置选项，请参阅 [deployment guide]。

## Build a custom store

要使用内置实现之外的存储后端，请子类化 [BaseStore] 并实现其必需的方法。内置的 [InMemoryStore] 是最简单的参考实现。

### Base contract

所有五个异步方法都是必需的。同步对应方法（`put`、`get`、`delete`、`search`、`list_namespaces`）是可选的，但建议实现以兼容同步图执行。

| Method                                                                               | Description                                                         |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| `aput(namespace, key, value, index=None)`                                            | 存储或覆盖单个项目                                                  |
| `aget(namespace, key)`                                                               | 通过键检索单个项目；若缺失则返回 `None`                             |
| `adelete(namespace, key)`                                                            | 删除单个项目                                                        |
| `asearch(namespace_prefix, *, query=None, filter=None, limit=10, offset=0)`          | 搜索命名空间前缀下的项目；可选地通过语义查询                        |
| `alist_namespaces(*, prefix=None, suffix=None, max_depth=None, limit=100, offset=0)` | 列出匹配前缀/后缀模式的命名空间                                      |

在实现之前查找确切的签名：

```python
import inspect
from langgraph.store.base import BaseStore
print(inspect.getsource(BaseStore))
```

### Namespace design

命名空间是字符串元组，例如 `("user_id", "memories")`。Store 实现必须支持：

* **前缀匹配**：`asearch(("alice",))` 返回 `("alice",)`、`("alice", "memories")` 和任何其他子命名空间下的项目。
* **精确键查找**：`aget(("alice", "memories"), "some-key")` 必须是 O(1) 或接近 O(1)。

对于 SQL 后端，一个常见模式：

```sql
CREATE TABLE store_items (
    namespace   TEXT[] NOT NULL,
    key         TEXT NOT NULL,
    value       JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (namespace, key)
);

CREATE INDEX ON store_items USING gin(namespace);
```

### Serialization

Store 值是普通的 Python dict——不需要特殊的序列化器。直接使用 `json.dumps` / `json.loads` 或 JSONB 列进行序列化。不要存储非 JSON 可序列化的原始 Python 对象。

### Semantic search support

如果您的后端支持向量搜索，请实现 `asearch` 上的 `query` 参数：

* 接受 `query: str | None` 参数。
* 当 `query` 不为 `None` 时，对其进行嵌入，并按余弦相似度对结果进行排序。
* 当提供 `query` 时，结果中的每个 `Item` 应包含一个 `score` 字段。

如果您的后端不支持向量搜索，则在传入 `query` 时引发 `NotImplementedError`。

### Testing

目前没有针对自定义 stores 的一致性测试套件。以 [InMemoryStore] 作为参考进行测试：

```python
import pytest
from langgraph.store.memory import InMemoryStore
from your_module import YourStore

@pytest.fixture
async def store():
    async with YourStore.create() as s:
        yield s

@pytest.fixture
def reference():
    return InMemoryStore()

async def test_put_and_get(store, reference):
    ns = ("test", "ns")
    for s in [store, reference]:
        await s.aput(ns, "k1", {"val": 1})
        item = await s.aget(ns, "k1")
        assert item is not None
        assert item.value == {"val": 1}

async def test_delete(store, reference):
    ns = ("test", "ns")
    for s in [store, reference]:
        await s.aput(ns, "k1", {"val": 1})
        await s.adelete(ns, "k1")
        assert await s.aget(ns, "k1") is None

async def test_search_prefix(store, reference):
    for s in [store, reference]:
        await s.aput(("user", "memories"), "m1", {"text": "likes pizza"})
        results = await s.asearch(("user",))
        assert any(r.key == "m1" for r in results)
```

### Next steps

* [Add a custom store to Agent Server] — 部署您的实现
* [Checkpointers] — 线程范围的 state 持久化