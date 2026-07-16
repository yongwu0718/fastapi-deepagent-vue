这段代码是 LangGraph 的 SQLite 存储后端实现。面向开发者的公开接口主要集中在 `SqliteStore` 类上，同时需要用到一些操作类型和配置类。下面按接口、配置、调用方式和返回值几个方面梳理。

---

### 一、核心类：`SqliteStore`

#### 1. 构造方法
```python
SqliteStore(
    conn: sqlite3.Connection,
    *,
    deserializer: Callable[[bytes | str | orjson.Fragment], dict[str, Any]] | None = None,
    index: SqliteIndexConfig | None = None,
    ttl: TTLConfig | None = None
)
```

- **`conn`**：必须传入的 `sqlite3.Connection` 对象，推荐使用 `check_same_thread=False` + 自动提交模式。
- **`deserializer`**：可选的自定义反序列化函数，用于将数据库中存储的 JSON 字节/字符串转为 `dict`。不提供则使用内置的 `orjson.loads`。
- **`index`**：可选，向量搜索配置，类型为 `SqliteIndexConfig`（见下文）。不提供则不会启用语义搜索。
- **`ttl`**：可选，TTL 过期配置，类型为 `TTLConfig`（见下文）。

#### 2. 类方法：`from_conn_string`
```python
@classmethod
@contextmanager
def from_conn_string(
    cls,
    conn_string: str,
    *,
    index: SqliteIndexConfig | None = None,
    ttl: TTLConfig | None = None,
) -> Iterator[SqliteStore]:
```
- 通过连接字符串（如 `":memory:"` 或文件路径）快速创建上下文管理器，自动处理连接关闭。
- 参数与构造函数的 `index`、`ttl` 一致。
- **返回值**：上下文管理器，进入时获得已构造的 `SqliteStore` 实例。

#### 3. 初始化方法：`setup`
```python
def setup(self) -> None:
```
- 必须在使用前调用一次，负责创建数据表、执行 migrations、加载 `sqlite_vec` 扩展（若配置了向量搜索）。
- 无返回值，幂等（重复调用不会重复执行）。

---

### 二、数据操作：`batch` 方法

所有读写操作都通过批量接口 `batch` 执行，不支持单独调用的 `get/put/search` 方法。

```python
def batch(self, ops: Iterable[Op]) -> list[Result]:
```
- **`ops`**：可迭代对象，元素为 `Op` 类型。`Op` 是一个联合类型，包含：
  - `GetOp`：读取操作
  - `PutOp`：写入/删除操作
  - `SearchOp`：搜索操作（支持关键词 + 向量）
  - `ListNamespacesOp`：列出命名空间
- **返回值**：`list[Result]`，与输入顺序一一对应，每一项的类型取决于操作：
  - `GetOp` → `Item | None`
  - `SearchOp` → `list[SearchItem]`
  - `ListNamespacesOp` → `list[tuple[str, ...]]`（每个元素是命名空间元组）
  - `PutOp` → 对应位置为 `None`（写入无直接返回值，错误会抛异常）

#### 操作类型示例

**`GetOp`**
```python
GetOp(
    namespace: tuple[str, ...],
    key: str,
    refresh_ttl: bool = False
)
```
- 从指定命名空间读取一个键。`refresh_ttl` 设为 `True` 且开启了 TTL 刷新策略时，会更新过期时间。

**`PutOp`**
```python
PutOp(
    namespace: tuple[str, ...],
    key: str,
    value: dict | None,        # None 表示删除
    index: list[str] | bool | None = None,
    ttl: float | None = None   # 过期分钟数
)
```
- 写入（或删除）一个文档。`index` 控制向量化字段：`False` 禁用、`None` 使用全局配置、列表指定要索引的字段路径。`ttl` 指定该文档的存活时间（分钟）。

**`SearchOp`**
```python
SearchOp(
    namespace_prefix: tuple[str, ...],
    query: str | None = None,    # 向量搜索的文本
    filter: dict | None = None,  # 过滤条件
    limit: int = 10,
    offset: int = 0,
    refresh_ttl: bool = False
)
```
- 混合搜索（向量 + 属性过滤）。若不提供 `query` 则只按过滤条件和时间排序。

**`ListNamespacesOp`**
```python
ListNamespacesOp(
    match_conditions: list[MatchCondition] | None = None,
    max_depth: int | None = None,
    limit: int = 100,
    offset: int = 0
)
```
- 列出所有命名空间，支持前缀/后缀匹配和层级深度控制。

---

### 三、配置类

#### 1. `SqliteIndexConfig`
用于设置向量嵌入。常用字段：
```python
SqliteIndexConfig(
    dims: int,           # 向量维度（如 OpenAI 的 1536）
    embed: Embeddings,   # LangChain Embeddings 实例，需实现 embed_documents/embed_query
    fields: list[str] | None = None,  # 默认索引的字段路径列表，默认 ["$"] 代表整个文档
    distance_type: str = "cosine",    # 相似度算法："cosine", "l2", "inner_product"
    text_fields: ...                  # 内部使用，同上 fields
)
```
- 实际构建时，你通常传入 `dims`、`embed`、`fields`（或 `text_fields`）即可。

#### 2. `TTLConfig`
TTL 过期配置：
```python
TTLConfig(
    refresh_on_read: bool = False,        # 读取时是否刷新过期时间
    sweep_interval_minutes: float = 5,    # 自动清理间隔（分钟）
)
```
- 可在构造 `SqliteStore` 时传入 `ttl=TTLConfig(...)`，然后调用 `start_ttl_sweeper()` 启动后台清理线程。

---

### 四、TTL 管理方法

```python
def sweep_ttl(self) -> int:
```
- 手动触发一次过期清理，返回删除的条目数。

```python
def start_ttl_sweeper(self, sweep_interval_minutes: int | None = None) -> concurrent.futures.Future[None]:
```
- 启动后台线程定期清理过期数据。返回一个 `Future`，可用来等待或取消。间隔可在参数或 `ttl_config` 中指定。

```python
def stop_ttl_sweeper(self, timeout: float | None = None) -> bool:
```
- 停止后台清理线程，返回是否成功停止。

---

### 五、异步接口

```python
async def abatch(self, ops: Iterable[Op]) -> list[Result]:
    raise NotImplementedError("... AsyncSqliteStore ...")
```
- 同步版本的 `SqliteStore` 不支持 `abatch`，需使用 `langgraph.store.sqlite.aio.AsyncSqliteStore`。

---

### 六、返回的实体类

- **`Item`**：包含 `key`, `namespace`, `value` (dict), `created_at`, `updated_at`。
- **`SearchItem`**：继承类似字段，额外有 `score: float | None`（仅向量搜索时有效）。
- **`Result`**：在 `batch` 返回中为以上类型或 `None`。

---

### 典型调用流程

```python
from langgraph.store.sqlite import SqliteStore
import sqlite3

conn = sqlite3.connect(":memory:", check_same_thread=False)
store = SqliteStore(conn)
store.setup()

# 写入一条数据
store.batch([
    PutOp(("users", "123"), "prefs", {"theme": "dark"})
])

# 读取
results = store.batch([
    GetOp(("users", "123"), "prefs")
])
item = results[0]  # Item 或 None

# 搜索（需提前配置 index）
results = store.batch([
    SearchOp(("docs",), query="Python guide", limit=5)
])
items = results[0]  # list[SearchItem]

# 列出命名空间
results = store.batch([
    ListNamespacesOp(max_depth=1)
])
namespaces = results[0]  # list[tuple[str,...]]
```

如果需要向量搜索，构造时需传入 `index`，并在 `setup` 前完成。使用 `from_conn_string` 更简洁：

```python
with SqliteStore.from_conn_string(
    ":memory:",
    index={"dims": 1536, "embed": my_embeddings, "fields": ["text"]},
    ttl={"refresh_on_read": True, "sweep_interval_minutes": 10}
) as store:
    store.setup()
    # 开始操作 ...
```

以上即为该模块暴露给开发者的主要公开接口、参数配置和调用方式。