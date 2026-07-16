`langgraph.store.base` 模块定义了持久化键值存储的抽象接口和数据类型。所有具体的 Store 实现（如 `SqliteStore`、`InMemoryStore`）都继承 `BaseStore` 并遵循这里的接口约定。

下面是该模块的完整公开接口清单，按类别梳理参数与返回值。

---

### 1. 核心抽象类 `BaseStore`

这是所有 Store 实现的基类，定义了同步/异步的操作集合。**实际使用时，你调用的是子类实例（如 `SqliteStore`）继承的这些方法。**

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get(namespace, key, *, refresh_ttl=None)` | `namespace: tuple[str, ...]`<br>`key: str`<br>`refresh_ttl: bool \| None = None` | `Item \| None` | 检索单个键值。`refresh_ttl` 控制是否刷新过期时间（`None` 则使用 store 配置的默认值）。 |
| `search(namespace_prefix, /, *, query=None, filter=None, limit=10, offset=0, refresh_ttl=None)` | `namespace_prefix: tuple[str, ...]`<br>`query: str \| None` 语义搜索文本<br>`filter: dict \| None` 属性过滤条件<br>`limit: int`<br>`offset: int`<br>`refresh_ttl: bool \| None` | `list[SearchItem]` | 混合搜索（向量 + 属性过滤）。返回带相关度分数的条目列表。 |
| `put(namespace, key, value, index=None, *, ttl=NOT_PROVIDED)` | `namespace: tuple[str, ...]`<br>`key: str`<br>`value: dict` 要存储的数据<br>`index: False \| list[str] \| None` 索引控制<br>`ttl: float \| None \| NotProvided` 存活分钟数 | `None` | 写入或更新条目。`index=False` 禁用索引；`index=["field"]` 指定索引字段；`ttl` 为 `None` 表示永不过期。 |
| `delete(namespace, key)` | `namespace: tuple[str, ...]`<br>`key: str` | `None` | 删除条目。 |
| `list_namespaces(*, prefix=None, suffix=None, max_depth=None, limit=100, offset=0)` | `prefix: NamespacePath \| None` 前缀匹配<br>`suffix: NamespacePath \| None` 后缀匹配<br>`max_depth: int \| None` 最大层级深度<br>`limit: int`<br>`offset: int` | `list[tuple[str, ...]]` | 列出命名空间，可限定前缀/后缀和深度。 |
| `batch(ops)` | `ops: Iterable[Op]` 操作列表（可混合多种操作） | `list[Result]` | 批量执行，结果顺序与输入对应。 |
| `aget(...)`, `asearch(...)`, `aput(...)`, `adelete(...)`, `alist_namespaces(...)`, `abatch(...)` | 参数与同步版本相同 | 返回相应类型的 awaitable | 异步版本。**注意：`SqliteStore` 不支持异步方法，需使用 `AsyncSqliteStore`。** |

---

### 2. 操作类（用于 `batch` 或底层构造）

#### `GetOp(NamedTuple)`
| 字段 | 类型 | 说明 |
|------|------|------|
| `namespace` | `tuple[str, ...]` | 命名空间路径 |
| `key` | `str` | 键 |
| `refresh_ttl` | `bool` (默认 `True`) | 是否刷新 TTL |

#### `PutOp(NamedTuple)`
| 字段 | 类型 | 说明 |
|------|------|------|
| `namespace` | `tuple[str, ...]` | 命名空间 |
| `key` | `str` | 键 |
| `value` | `dict \| None` | 要存储的字典；`None` 表示删除 |
| `index` | `False \| list[str] \| None` | 索引字段列表，`False` 不索引，`None` 使用默认 |
| `ttl` | `float \| None` | TTL（分钟），`None` 不过期 |

#### `SearchOp(NamedTuple)`
| 字段 | 类型 | 说明 |
|------|------|------|
| `namespace_prefix` | `tuple[str, ...]` | 搜索范围前缀 |
| `filter` | `dict \| None` | 过滤条件（支持 `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`） |
| `limit` | `int` (默认 10) | 返回数量上限 |
| `offset` | `int` (默认 0) | 跳过条数 |
| `query` | `str \| None` | 自然语言查询（用于向量搜索） |
| `refresh_ttl` | `bool` (默认 `True`) | 是否刷新 TTL |

#### `ListNamespacesOp(NamedTuple)`
| 字段 | 类型 | 说明 |
|------|------|------|
| `match_conditions` | `tuple[MatchCondition, ...] \| None` | 命名空间匹配条件（前缀/后缀） |
| `max_depth` | `int \| None` | 返回的最大层级深度 |
| `limit` | `int` (默认 100) | 返回数量上限 |
| `offset` | `int` (默认 0) | 跳过条数 |

#### `MatchCondition(NamedTuple)`
用于定义命名空间匹配规则。
| 字段 | 类型 | 说明 |
|------|------|------|
| `match_type` | `NamespaceMatchType` (`"prefix"` 或 `"suffix"`) | 匹配方式 |
| `path` | `NamespacePath` (`tuple[str \| "*", ...]`) | 命名空间路径模式，支持通配符 `"*"` |

---

### 3. 数据实体类

#### `Item`
存储条目及元数据。
| 属性 | 类型 | 说明 |
|------|------|------|
| `namespace` | `tuple[str, ...]` | 命名空间 |
| `key` | `str` | 键 |
| `value` | `dict[str, Any]` | 存储的数据 |
| `created_at` | `datetime` | 创建时间 |
| `updated_at` | `datetime` | 最后更新时间 |

#### `SearchItem(Item)`
继承 `Item`，增加一个属性。
| 属性 | 类型 | 说明 |
|------|------|------|
| `score` | `float \| None` | 相关度分数（仅向量搜索时有效） |

---

### 4. 配置字典类型

#### `TTLConfig(TypedDict)`（全部可选）
| 键 | 类型 | 说明 |
|----|------|------|
| `refresh_on_read` | `bool` | 读取时是否刷新 TTL（默认 `True`） |
| `default_ttl` | `float \| None` | 默认 TTL（分钟），`None` 不过期 |
| `sweep_interval_minutes` | `int \| None` | 自动清理过期条目的间隔（分钟），`None` 不自动清理 |

#### `IndexConfig(TypedDict)`
用于配置向量索引。
| 键 | 类型 | 说明 |
|----|------|------|
| `dims` | `int`（必需） | 嵌入向量维度 |
| `embed` | `Embeddings`、函数或字符串（必需） | 嵌入模型或函数 |
| `fields` | `list[str] \| None` | 要索引的字段路径，默认 `["$"]` 表示整个文档 |

---

### 5. 类型别名

| 别名 | 定义 | 说明 |
|------|------|------|
| `Op` | `GetOp \| SearchOp \| PutOp \| ListNamespacesOp` | 所有操作类型的联合 |
| `Result` | `Item \| list[Item] \| list[SearchItem] \| list[tuple[str, ...]] \| None` | `batch` 返回值的联合类型 |
| `NamespacePath` | `tuple[str \| Literal["*"], ...]` | 命名空间路径，可含通配符 |
| `NamespaceMatchType` | `Literal["prefix", "suffix"]` | 命名空间匹配方式 |

---

### 6. 异常类

- **`InvalidNamespaceError(ValueError)`**：当命名空间不符合规则时抛出（如包含空字符串、点号，或顶层为 `"langgraph"`）。

---

### 7. 辅助函数

| 函数 | 签名 | 作用 |
|------|------|------|
| `ensure_embeddings(embed)` | `embed: Embeddings \| EmbeddingsFunc \| AEmbeddingsFunc \| str` → `Embeddings` | 将多种嵌入表示统一为 `Embeddings` 实例 |
| `tokenize_path(path: str)` | `path: str` → `list[str]` | 将 JSON 路径字符串（如 `"a.b[*].c"`）解析为 token 列表 |
| `get_text_at_path(value, path)` | `value: dict`, `path: list[str]` → `list[str]` | 从文档中按路径提取文本（用于生成嵌入向量） |

---

### 8. 哨兵值

- **`NOT_PROVIDED`**：`NotProvided` 类的唯一实例，用于区分“未传递参数”与“参数值为 `None`”。  
- **`NotProvided`**：哨兵类，其布尔值为 `False`。

---

以上即为 `langgraph.store.base` 模块的完整公开接口。实际开发中，你通常通过 Store 实例的 **`get`/`put`/`search`/`list_namespaces`** 等便利方法操作数据，它们内部会自动构造对应的 `Op` 并调用 `batch`。