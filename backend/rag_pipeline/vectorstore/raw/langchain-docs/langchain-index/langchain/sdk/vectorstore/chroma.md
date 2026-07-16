按接口类别逐一解释参数如何配置、如何调用以及返回值。

---

## 一、模块级公开接口

### 1. 常量 `DEFAULT_K`
- **值**：`4`
- **说明**：默认的相似度搜索返回文档数量。在未指定 `k` 参数时使用。

---

### 2. 函数 `cosine_similarity`
```python
cosine_similarity(X: Matrix, Y: Matrix) -> np.ndarray
```
- **用途**：计算两个等宽矩阵的行间余弦相似度。
- **参数**：
  - `X`：`list[list[float]]` 或 `np.ndarray`，形状 `(n, d)`
  - `Y`：`list[list[float]]` 或 `np.ndarray`，形状 `(m, d)`
- **返回值**：`np.ndarray`，形状 `(n, m)`，其中 `[i, j]` 为 `X` 第 `i` 行与 `Y` 第 `j` 行的余弦相似度。
- **说明**：若某行范数为零，则相似度置为 `0.0`，忽略除零错误。
- **调用示例**：
```python
import numpy as np
from langchain_chroma.vectorstores import cosine_similarity

X = [[1.0, 0.0], [0.0, 1.0]]
Y = [[1.0, 0.0]]
sim = cosine_similarity(X, Y)
# sim[0,0] ≈ 1.0, sim[1,0] ≈ 0.0
```

---

### 3. 函数 `maximal_marginal_relevance`
```python
maximal_marginal_relevance(
    query_embedding: np.ndarray,
    embedding_list: list,
    lambda_mult: float = 0.5,
    k: int = 4,
) -> list[int]
```
- **用途**：最大边界相关算法，平衡查询相似度与结果多样性，返回选中的嵌入索引列表。
- **参数**：
  - `query_embedding`：`np.ndarray`，查询嵌入向量，形状 `(d,)` 或 `(1, d)`
  - `embedding_list`：候选嵌入列表，每个元素为嵌入向量（一维数组或列表）
  - `lambda_mult`：`float`，取值 0~1，`0` 表示最大多样性，`1` 表示最小多样性（默认 0.5）
  - `k`：返回的索引数量（默认 4）
- **返回值**：`list[int]`，选中的嵌入在 `embedding_list` 中的索引列表。
- **调用示例**：
```python
import numpy as np
from langchain_chroma.vectorstores import maximal_marginal_relevance

q_emb = np.array([0.2, 0.8])
candidates = [np.array([0.1, 0.9]), np.array([0.3, 0.7]), np.array([0.9, 0.1])]
selected_indices = maximal_marginal_relevance(q_emb, candidates, lambda_mult=0.5, k=2)
# 返回类似 [1, 0] 的列表
```

---

## 二、Chroma 类的公开接口

### 1. 构造函数 `__init__`
```python
Chroma(
    collection_name: str = "langchain",
    embedding_function: Embeddings | None = None,
    persist_directory: str | None = None,
    host: str | None = None,
    port: int | None = None,
    headers: dict[str, str] | None = None,
    chroma_cloud_api_key: str | None = None,
    tenant: str | None = None,
    database: str | None = None,
    client_settings: chromadb.config.Settings | None = None,
    collection_metadata: dict | None = None,
    collection_configuration: CreateCollectionConfiguration | None = None,
    client: chromadb.ClientAPI | None = None,
    relevance_score_fn: Callable[[float], float] | None = None,
    create_collection_if_not_exists: bool = True,
    *,
    ssl: bool = False,
)
```
- **用途**：初始化 Chroma 向量存储，并连接到本地或远程 Chroma 实例。
- **参数说明**（连接方式只能选一种）：
  - **索引与嵌入**：
    - `collection_name`：集合名称，默认 `"langchain"`。
    - `embedding_function`：嵌入模型实例，需实现 `Embeddings` 接口（如 `OpenAIEmbeddings()`）。若不提供，查询时只能使用原始文本或预计算嵌入。
    - `collection_metadata`：创建集合时附加的元数据。
    - `collection_configuration`：索引配置（如设置 `hnsw` 空间距离度量）。
  - **客户端连接**（三选一，不可混用）：
    - `persist_directory`：本地持久化目录 → 自动创建 `PersistentClient`。
    - `host`：远程 Chroma 服务器地址 → 创建 `HttpClient`，需配合 `port`（默认 8000）、`ssl`、`headers`。
    - `chroma_cloud_api_key`：Chroma Cloud API 密钥 → 创建 `CloudClient`，此时必须提供 `tenant` 和 `database`。
    - 若以上三者均为 `None`，则创建一个内存模式客户端（`Client()`）。
    - 也可直接传入 `client` 参数（一个已配置的 Chroma 客户端），此时忽略以上连接参数。
  - **其他连接参数**：
    - `port`：远程服务器的端口，默认 `8000`。
    - `ssl`：是否使用 SSL，默认 `False`。
    - `headers`：HTTP 头字典。
    - `tenant`：租户 ID，Chroma Cloud 必填，本地服务器默认为 `"default_tenant"`。
    - `database`：数据库名称，Chroma Cloud 必填，本地默认为 `"default_database"`。
    - `client_settings`：`Settings` 实例，用于微调客户端行为。
  - **其他**：
    - `relevance_score_fn`：自定义距离→相似度得分转换函数，若提供则覆盖自动选择的函数。
    - `create_collection_if_not_exists`：若为 `True`（默认），集合不存在时自动创建；否则必须已存在，会调用 `get_collection`。
- **调用示例**：
```python
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

vector_store = Chroma(
    collection_name="my_collection",
    embedding_function=OpenAIEmbeddings(),
    persist_directory="./chroma_db"
)
```

---

### 2. 属性 `embeddings`
```python
@property
embeddings -> Embeddings | None
```
- **用途**：返回初始化时传入的嵌入函数对象。
- **返回值**：`Embeddings` 实例或 `None`。

---

### 3. 静态方法 `encode_image`
```python
@staticmethod
encode_image(uri: str) -> str
```
- **用途**：读取图像文件并转换为 Base64 编码字符串。
- **参数**：`uri`（`str`）—— 图像文件路径。
- **返回值**：`str`，Base64 编码的图像数据。
- **调用示例**：
```python
b64_img = Chroma.encode_image("/path/to/image.jpg")
```

---

### 4. 方法 `fork`
```python
fork(new_name: str) -> Chroma
```
- **用途**：复制当前集合（包括其数据）到一个新名称的集合，返回一个新的 `Chroma` 实例。
- **参数**：`new_name`（`str`）—— 新集合名称。
- **返回值**：`Chroma` 实例，指向新创建的集合。
- **调用示例**：
```python
new_store = vector_store.fork("my_collection_copy")
```

---

### 5. 方法 `add_texts`
```python
add_texts(
    texts: Iterable[str],
    metadatas: list[dict] | None = None,
    ids: list[str] | None = None,
    **kwargs: Any,
) -> list[str]
```
- **用途**：将文本列表存入向量库，自动调用嵌入函数生成向量（若提供）。
- **参数**：
  - `texts`：待添加的文本列表。
  - `metadatas`：可选的元数据列表，与 `texts` 等长。若部分为空字典，会自动分批插入（避免元数据验证错误）。
  - `ids`：可选的 ID 列表；若未提供则自动生成 UUID。若列表中某元素为 `None`，该项也会自动生成 UUID。
  - `**kwargs`：额外关键字参数（保留）。
- **返回值**：`list[str]`，实际使用的 ID 列表（可能包含生成的 UUID）。
- **调用示例**：
```python
ids = vector_store.add_texts(
    texts=["hello", "world"],
    metadatas=[{"source": "a"}, {}],
    ids=["1", "2"]
)
# ids 为 ["1", "2"]
```

---

### 6. 方法 `add_images`
```python
add_images(
    uris: list[str],
    metadatas: list[dict] | None = None,
    ids: list[str] | None = None,
) -> list[str]
```
- **用途**：将图像文件（通过 URI）编码为 Base64 并存入向量库，需嵌入函数支持 `embed_image` 方法。
- **参数**：同 `add_texts`，但 `uris` 为图像文件路径列表。
- **返回值**：`list[str]`，使用的 ID 列表。
- **注意**：如果嵌入函数没有 `embed_image` 方法，则跳过生成向量，只存储 Base64 文本。
- **调用示例**：
```python
ids = vector_store.add_images(
    uris=["img1.jpg", "img2.png"],
    metadatas=[{"tag": "cat"}, {"tag": "dog"}]
)
```

---

### 7. 方法 `hybrid_search`
```python
hybrid_search(search: Search) -> list[Document]
```
- **用途**：执行 Chroma 原生混合搜索（支持全文搜索、向量搜索、重排序等）。
- **参数**：`search`（`chromadb.Search`）—— 已配置好的搜索对象。
- **返回值**：`list[Document]`，匹配的文档列表。
- **调用示例**：
```python
from chromadb import Search, K, Knn, Rrf

hybrid_rank = Rrf(
    ranks=[
        Knn(query="some text", return_rank=True, limit=300),
        Knn(query="some text", key="sparse_embedding")
    ],
    weights=[2.0, 1.0],
    k=60
)
search = (Search()
    .where((K("language") == "en") & (K("year") >= 2020))
    .rank(hybrid_rank)
    .limit(10)
    .select(K.DOCUMENT, K.SCORE, "title", "year")
)
docs = vector_store.hybrid_search(search)
```

---

### 8. 相似度搜索方法

#### `similarity_search`
```python
similarity_search(
    query: str,
    k: int = 4,
    filter: dict[str, str] | None = None,
    **kwargs,
) -> list[Document]
```
- **用途**：根据查询文本返回最相似的 `k` 个文档（不含分数）。
- **参数**：
  - `query`：查询字符串。
  - `k`：返回数量，默认 4。
  - `filter`：元数据过滤字典，如 `{"color": "red"}`。
- **返回值**：`list[Document]`。

#### `similarity_search_with_score`
```python
similarity_search_with_score(
    query: str,
    k: int = 4,
    filter: dict[str, str] | None = None,
    where_document: dict[str, str] | None = None,
    **kwargs,
) -> list[tuple[Document, float]]
```
- **用途**：返回文档及距离（距离越小越相似）。
- **返回值**：`list[tuple[Document, float]]`。

#### `similarity_search_with_vectors`
```python
similarity_search_with_vectors(
    query: str,
    k: int = 4,
    filter: dict[str, str] | None = None,
    where_document: dict[str, str] | None = None,
    **kwargs,
) -> list[tuple[Document, np.ndarray]]
```
- **用途**：返回文档及其对应的嵌入向量。
- **返回值**：`list[tuple[Document, np.ndarray]]`。

#### `similarity_search_by_vector`
```python
similarity_search_by_vector(
    embedding: list[float],
    k: int = 4,
    filter: dict[str, str] | None = None,
    where_document: dict[str, str] | None = None,
    **kwargs,
) -> list[Document]
```
- **用途**：直接传入查询向量进行搜索，返回文档列表。
- **参数**：`embedding`——向量列表。

#### `similarity_search_by_vector_with_relevance_scores`
```python
similarity_search_by_vector_with_relevance_scores(
    embedding: list[float],
    k: int = 4,
    filter: dict[str, str] | None = None,
    where_document: dict[str, str] | None = None,
    **kwargs,
) -> list[tuple[Document, float]]
```
- **用途**：直接传入向量，返回文档及其距离分数。

**调用示例**：
```python
# 文本搜索
docs = vector_store.similarity_search("hello", k=2, filter={"year": "2021"})

# 带分数
docs_with_scores = vector_store.similarity_search_with_score("hello", k=2)
for doc, score in docs_with_scores:
    print(score, doc.page_content)

# 向量搜索
emb = embedding_model.embed_query("hello")
docs = vector_store.similarity_search_by_vector(emb, k=2)
```

---

### 9. 图像相似度搜索

#### `similarity_search_by_image`
```python
similarity_search_by_image(
    uri: str,
    k: int = 4,
    filter: dict[str, str] | None = None,
    **kwargs,
) -> list[Document]
```
- **用途**：根据图像 URI 搜索最相似的已存储图像（要求嵌入函数支持 `embed_image`）。
- **参数**：`uri`——图像文件路径。
- **返回值**：`list[Document]`，页面内容为 Base64 编码图像。

#### `similarity_search_by_image_with_relevance_score`
```python
similarity_search_by_image_with_relevance_score(
    uri: str,
    k: int = 4,
    filter: dict[str, str] | None = None,
    **kwargs,
) -> list[tuple[Document, float]]
```
- **返回值**：`list[tuple[Document, float]]`，文档和距离分数。

**调用示例**：
```python
# 前提：嵌入函数支持 embed_image
docs = vector_store.similarity_search_by_image("query_img.jpg", k=5)
```

---

### 10. 最大边界相关（MMR）搜索

#### `max_marginal_relevance_search`
```python
max_marginal_relevance_search(
    query: str,
    k: int = 4,
    fetch_k: int = 20,
    lambda_mult: float = 0.5,
    filter: dict[str, str] | None = None,
    where_document: dict[str, str] | None = None,
    **kwargs,
) -> list[Document]
```
- **用途**：基于文本查询进行 MMR 搜索，平衡相关性与多样性。
- **参数**：
  - `k`：最终返回的文档数。
  - `fetch_k`：先获取的候选文档数（从中挑选）。
  - `lambda_mult`：多样性控制参数（0~1），0 为最大多样性。
  - `filter` / `where_document`：过滤条件。
- **返回值**：`list[Document]`。

#### `max_marginal_relevance_search_by_vector`
```python
max_marginal_relevance_search_by_vector(
    embedding: list[float],
    k: int = 4,
    fetch_k: int = 20,
    lambda_mult: float = 0.5,
    filter: dict[str, str] | None = None,
    where_document: dict[str, str] | None = None,
    **kwargs,
) -> list[Document]
```
- **用途**：直接传入向量进行 MMR 搜索。
- **调用示例**：
```python
docs = vector_store.max_marginal_relevance_search(
    "machine learning", k=3, fetch_k=10, lambda_mult=0.7
)
```

---

### 11. 集合管理方法

#### `delete_collection`
```python
delete_collection() -> None
```
- **用途**：删除当前集合，之后 `_chroma_collection` 置为 `None`。

#### `reset_collection`
```python
reset_collection() -> None
```
- **用途**：先删除集合再重新创建（清空数据）。

#### `delete`
```python
delete(ids: list[str] | None = None, **kwargs) -> None
```
- **用途**：根据 ID 列表删除文档。
- **调用示例**：
```python
vector_store.delete(ids=["1", "2"])
```

---

### 12. 文档读取方法

#### `get`
```python
get(
    ids: str | list[str] | None = None,
    where: Where | None = None,
    limit: int | None = None,
    offset: int | None = None,
    where_document: WhereDocument | None = None,
    include: list[str] | None = None,
) -> dict[str, Any]
```
- **用途**：从集合中获取文档，支持多种过滤条件。
- **参数**：
  - `ids`：要获取的 ID 或 ID 列表。
  - `where`：元数据过滤器（如 `{"$and": [{"color": "red"}, {"price": 4.20}]}`）。
  - `limit`：返回数量上限。
  - `offset`：分页偏移。
  - `where_document`：内容过滤器（如 `{"$contains": "hello"}`）。
  - `include`：包含的字段列表，默认 `["metadatas", "documents"]`，可追加 `"embeddings"`。
- **返回值**：字典，包含 `"ids"`, `"embeddings"`（若请求）, `"metadatas"`, `"documents"`。
- **调用示例**：
```python
data = vector_store.get(
    where={"source": "web"},
    limit=10,
    include=["metadatas", "documents"]
)
# data["ids"], data["documents"], data["metadatas"]
```

#### `get_by_ids`
```python
get_by_ids(ids: Sequence[str], /) -> list[Document]
```
- **用途**：通过 ID 列表批量获取文档（仅位置参数）。
- **参数**：`ids`——ID 序列。
- **返回值**：`list[Document]`，顺序可能与输入不同，ID 缺失的不报错。
- **调用示例**：
```python
docs = vector_store.get_by_ids(["id1", "id2"])
```

---

### 13. 文档更新方法

#### `update_document`
```python
update_document(document_id: str, document: Document) -> None
```
- **用途**：更新单个文档（实际上是调用 `update_documents`）。

#### `update_documents`
```python
update_documents(ids: list[str], documents: list[Document]) -> None
```
- **用途**：批量更新文档内容和元数据，自动重新计算嵌入向量（需要嵌入函数）。
- **参数**：
  - `ids`：要更新的文档 ID 列表。
  - `documents`：新的 `Document` 对象列表，与 ID 一一对应。
- **调用示例**：
```python
updated_doc = Document(page_content="new content", metadata={"key": "val"})
vector_store.update_documents(ids=["1"], documents=[updated_doc])
```

---

### 14. 类方法 `from_texts`
```python
@classmethod
from_texts(
    cls,
    texts: list[str],
    embedding: Embeddings | None = None,
    metadatas: list[dict] | None = None,
    ids: list[str] | None = None,
    collection_name: str = "langchain",
    persist_directory: str | None = None,
    host: str | None = None,
    port: int | None = None,
    headers: dict[str, str] | None = None,
    chroma_cloud_api_key: str | None = None,
    tenant: str | None = None,
    database: str | None = None,
    client_settings: Settings | None = None,
    client: ClientAPI | None = None,
    collection_metadata: dict | None = None,
    collection_configuration: CreateCollectionConfiguration | None = None,
    *,
    ssl: bool = False,
    **kwargs,
) -> Chroma
```
- **用途**：一次性创建集合并添加文本，返回初始化好的 `Chroma` 实例。
- **参数**：除构造函数的参数外，增加了 `texts`、`metadatas`、`ids`，直接用于添加数据。
- **返回值**：`Chroma` 实例。

---

### 15. 类方法 `from_documents`
```python
@classmethod
from_documents(
    cls,
    documents: list[Document],
    embedding: Embeddings | None = None,
    ids: list[str] | None = None,
    collection_name: str = "langchain",
    persist_directory: str | None = None,
    host: str | None = None,
    port: int | None = None,
    headers: dict[str, str] | None = None,
    chroma_cloud_api_key: str | None = None,
    tenant: str | None = None,
    database: str | None = None,
    client_settings: Settings | None = None,
    client: ClientAPI | None = None,
    collection_metadata: dict | None = None,
    collection_configuration: CreateCollectionConfiguration | None = None,
    *,
    ssl: bool = False,
    **kwargs,
) -> Chroma
```
- **用途**：从 `Document` 列表创建向量存储，自动提取文本和元数据。
- **参数**：与 `from_texts` 类似，但接收 `documents` 而非 `texts`；若 `ids` 未提供，会使用 `Document.id`，若无则生成 UUID。
- **返回值**：`Chroma` 实例。
- **调用示例**：
```python
from langchain_core.documents import Document

docs = [Document(page_content="foo", metadata={"a": 1}), Document(page_content="bar")]
vector_store = Chroma.from_documents(
    documents=docs,
    embedding=OpenAIEmbeddings(),
    persist_directory="./db"
)
```

---

## 三、内部支持说明（非公开接口，仅供参考）
- `_results_to_docs`、`_results_to_docs_and_scores`、`_results_to_docs_and_vectors`：将 Chroma 查询结果转换为 LangChain 文档格式。
- `__query_collection`：底层查询方法，支持文本或向量查询，公开方法均基于它实现。
- `_select_relevance_score_fn`：根据集合的距离度量自动选择相似度转换函数（`cosine` → `1 - distance`，`l2` → 距离本身，`ip` → 取反内积）。若构造函数提供了 `relevance_score_fn` 则优先使用。

---