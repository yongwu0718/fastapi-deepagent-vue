# RAG 模块 API 文档

> 向量化检索增强生成（Retrieval-Augmented Generation）模块，负责将 Markdown 文档通过 Ollama 嵌入模型向量化后存入 ChromaDB，并提供文档管理、配置热重载及向量库浏览等完整功能。

---

## 1. 架构概览

```
用户请求
    │
    ▼
┌───────────────────────────────────────┐
│  api/routers/rag_pipeline.py          │  ← 路由层（13 个端点）
│  请求校验 → 错误处理 → 调用 service   │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│  api/services/rag_service.py          │  ← 业务逻辑层
│  文件处理 / 向量入库 / 删除 / 配置管理 │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│  api/markdown_rag/                    │  ← 核心引擎层
│  ├─ rag_setting.py    配置加载/热重载  │
│  └─ save_VectorStore.py               │
│     ├─ MarkdownLoader                 │
│     ├─ MarkdownSplitter  (二级分割)    │
│     └─ VectorStoreCreator (ChromaDB)  │
└───────────────────────────────────────┘
    │                    │
    ▼                    ▼
┌──────────┐    ┌──────────────────────┐
│ rag_     │    │  Ollama Embedding    │
│ config.  │    │  (my-qwen3-embed)    │
│ yaml     │    └──────────────────────┘
└──────────┘
```

### 核心依赖

| 组件 | 技术选型 |
|------|----------|
| 嵌入模型 | Ollama Embeddings (`my-qwen3-embed:latest`) |
| 向量库 | ChromaDB (LangChain Chroma 封装 + 原生 PersistentClient) |
| 索引算法 | HNSW (cosine 距离) |
| 文档分割 | ExperimentalMarkdownSyntaxTextSplitter + RecursiveCharacterTextSplitter 二级分割 |
| 配置管理 | `rag_config.yaml`，支持运行时热重载 |
| 支持格式 | 仅 `.md` (Markdown) |

---

## 2. 配置文件 (`rag_config.yaml`)

配置文件位于 `backend/api/markdown_rag/rag_config.yaml`，通过 `GET/PUT /api/rag/config` 读写。

### 2.1 完整结构

```yaml
embedding:
  model: my-qwen3-embed:latest          # Ollama 嵌入模型名称
  base_url: http://localhost:11434       # Ollama 服务地址

rag:
  splitter:
    headers: ['#', '##', '###']          # 用于切分的标题层级
    return_each_line: false              # 是否逐行返回
    strip_headers: false                 # 是否剥离标题行
    enable_char_split: false             # 是否启用二级字符切分
    chunk_size: 1000                     # 字符切分最大 chunk 大小 (100-10000)
    chunk_overlap: 200                   # 字符切分重叠区间 (0-2000)

  hnsw:
    space: cosine                        # 距离度量: cosine / l2 / ip
    ef_construction: 200                 # 构建时搜索深度 (10-2000)
    max_neighbors: 32                    # 最大邻居数 (4-256)
    ef_search: 200                       # 查询时搜索深度 (10-2000)
    num_threads: 4                       # 构建线程数 (1-64)
    batch_size: 100                      # 批量入库大小 (1-10000)
    sync_threshold: 1000                 # 同步阈值 (1-100000)
    resize_factor: 1.2                   # 扩容因子 (1.0-5.0)

  processing:
    preview_output_dir: preview          # 分块预览输出目录
    enable_interactive: true             # CLI 模式下是否交互确认

  collection:
    name: sunzi                          # Chroma 集合名称 (3-63字符, 字母/数字/._-)
    memory_name: memory                  # 记忆集合名称
    persist_directory: data/chroma_db    # 向量库持久化目录
```

---

## 3. API 端点

### 3.1 文档处理

---

#### `POST /api/rag/process` — 路径模式入库

通过本地文件绝对路径批量处理 `.md` 文件，完成分块、分割、（可选）向量化入库。

**请求体** `RAGProcessRequest`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `files` | `string[]` | ✅ | 待处理的 `.md` 文件绝对路径列表，最少 1 个 |
| `preview_dir` | `string?` | ❌ | 分块预览输出目录，不传则使用配置文件中的 `preview_output_dir` |
| `preview_only` | `boolean` | ❌ | 是否仅预览分块不入库，默认 `false` |

**请求示例**
```json
{
  "files": [
    "F:/index_rag/knowledge-base/01-概述.md",
    "F:/index_rag/knowledge-base/02-详解.md"
  ],
  "preview_dir": "preview/test",
  "preview_only": false
}
```

**响应** `RAGProcessResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_files` | `int` | 总文件数 |
| `success_count` | `int` | 成功处理数 |
| `failed_count` | `int` | 处理失败数 |
| `total_chunks` | `int` | 总入库分块数 |
| `collection_count` | `int` | 向量库当前文档块总数 |
| `split_config` | `SplitConfig` | 本次使用的分割配置 |
| `results` | `RAGProcessResult[]` | 每个文件的处理详情 |

`SplitConfig` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `headers` | `string[]` | 用于切分的标题层级，如 `["#", "##", "###"]` |
| `return_each_line` | `bool` | 是否逐行返回 |
| `strip_headers` | `bool` | 是否剥离标题行 |
| `enable_char_split` | `bool` | 是否启用二级字符切分 |
| `chunk_size` | `int` | 字符切分最大 chunk 大小 |
| `chunk_overlap` | `int` | 字符切分重叠区间大小 |
| `secondary_separators` | `string[]` | 二级字符切分的分隔符优先级 |

`RAGProcessResult` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `filename` | `string` | 文件名 |
| `file_size` | `int` | 原文件大小（字节） |
| `chunks_count` | `int` | 生成的分块数 |
| `status` | `string` | 处理状态：`success` / `error` |
| `error` | `string?` | 失败时的错误信息 |
| `chunks` | `ChunkDetail[]` | 每个 chunk 的详细信息 |

`ChunkDetail` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `index` | `int` | 分块序号（从 1 开始） |
| `content_length` | `int` | chunk 字符数 |
| `preview` | `string` | 前 120 个字符摘要 |
| `header_path` | `string?` | 标题路径，如 `"# 概述 > ## 背景"` |
| `is_char_split` | `bool` | 是否经过二级字符切分 |

**响应示例**
```json
{
  "total_files": 2,
  "success_count": 2,
  "failed_count": 0,
  "total_chunks": 45,
  "collection_count": 45,
  "split_config": {
    "headers": ["#", "##", "###"],
    "return_each_line": false,
    "strip_headers": false,
    "enable_char_split": true,
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "secondary_separators": ["\n\n", "\n", "。", "，", " ", ""]
  },
  "results": [
    {
      "filename": "01-概述.md",
      "file_size": 5230,
      "chunks_count": 12,
      "status": "success",
      "chunks": [
        {
          "index": 1,
          "content_length": 856,
          "preview": "# 概述\n\n本文档介绍项目的基本架构...",
          "header_path": "# 概述",
          "is_char_split": false
        }
      ]
    },
    {
      "filename": "02-详解.md",
      "file_size": 12840,
      "chunks_count": 33,
      "status": "success",
      "chunks": []
    }
  ]
}
```

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_PROCESS_FAILED` | 文档处理失败 |
| `RAG_VECTORSTORE_ERROR` | 向量库连接/初始化异常 |

---

#### `POST /api/rag/process/upload` — 上传模式入库

通过 multipart/form-data 上传 Markdown 文件，完成分割与（可选）入库。

**请求参数** (Query String)

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `preview_only` | `boolean` | ❌ | 仅预览分块而不入库，默认 `false` |

**请求体** (multipart/form-data)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `files` | `file[]` | ✅ | 待处理的 `.md` 文件，支持批量上传 |

**响应** 同 `RAGProcessResponse`（见上文 `POST /api/rag/process`）

**请求示例 (curl)**
```bash
curl -X POST http://localhost:8000/api/rag/process/upload \
  -F "files=@/path/to/doc1.md" \
  -F "files=@/path/to/doc2.md"
```

**预览模式示例**
```bash
curl -X POST "http://localhost:8000/api/rag/process/upload?preview_only=true" \
  -F "files=@/path/to/doc1.md"
```

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_PROCESS_FAILED` | 文档处理失败 |

---

### 3.2 文档删除

---

#### `POST /api/rag/delete` — 批量删除文档

按文档 ID 从向量库中批量删除文档。

**请求体** `RAGDeleteRequest`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ids` | `string[]` | ✅ | 待删除的文档 ID 列表，最少 1 个 |

**请求示例**
```json
{
  "ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**响应** `RAGDeleteResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `deleted_count` | `int` | 成功删除的文档数 |
| `collection_count` | `int` | 向量库当前文档块总数 |
| `message` | `string` | 操作描述 |

**响应示例**
```json
{
  "deleted_count": 2,
  "collection_count": 43,
  "message": "已删除 2 个文档"
}
```

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_DELETE_FAILED` | 删除文档失败 |

---

### 3.3 健康检查

---

#### `GET /api/rag/health` — 向量库健康检查

检查向量库连接状态及基础配置信息。

**请求参数** 无

**响应** `RAGHealthResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `string` | 集合名称 |
| `collection_count` | `int` | 当前文档块总数 |
| `persist_directory` | `string` | 持久化目录路径 |
| `embedding_model` | `string` | 嵌入模型名称 |
| `embedding_base_url` | `string` | 嵌入模型服务地址 |

**响应示例**
```json
{
  "collection_name": "sunzi",
  "collection_count": 450,
  "persist_directory": "data/chroma_db",
  "embedding_model": "my-qwen3-embed:latest",
  "embedding_base_url": "http://localhost:11434"
}
```

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_VECTORSTORE_ERROR` | 向量库健康检查失败 |

---

### 3.4 配置管理

---

#### `GET /api/rag/config` — 读取 RAG 配置

读取 `rag_config.yaml` 的完整内容。

**请求参数** 无

**响应** 完整的 `RAGFullConfigModel` 结构（见 [配置文件](#2-配置文件-rag_configyaml) 章节），返回与 `PUT` 接口一致的 JSON 对象。

---

#### `PUT /api/rag/config` — 更新 RAG 配置

覆写 `rag_config.yaml` 并自动重载运行时配置。

**请求体** `RAGFullConfigModel`

完整的 rag_config.yaml 结构，字段详见 [配置文件](#2-配置文件-rag_configyaml) 章节。

**关键行为**：
- 写入 YAML 文件后自动调用 `reload_rag_config()` 热重载
- 若集合名称变更，自动重置向量库单例
- 自动重置 ChromaDB 直连客户端
- 旧集合数据保留不删除

**响应**
```json
{
  "status": "ok",
  "message": "RAG 配置已更新并生效",
  "path": "F:/index_rag/backend/api/markdown_rag/rag_config.yaml"
}
```

**错误码**

| 错误码 | 说明 |
|--------|------|
| `VALIDATION_ERROR` | 配置序列化失败（YAML 格式错误） |
| `INTERNAL_ERROR` | 配置读取/写入异常 |

---

### 3.5 ChromaDB 数据浏览

---

#### `GET /api/rag/collections` — 列出所有集合

列出 ChromaDB 中所有集合及其文档数量。

**请求参数** 无

**响应** `CollectionListResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `collections` | `CollectionInfo[]` | 集合列表 |

`CollectionInfo`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `string` | 集合名称 |
| `count` | `int` | 文档数量 |

**响应示例**
```json
{
  "collections": [
    { "name": "sunzi", "count": 450 },
    { "name": "memory", "count": 0 }
  ]
}
```

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_VECTORSTORE_ERROR` | 列出集合失败 |

---

#### `GET /api/rag/collection/{collection_name}/stats` — 集合统计

获取指定集合的统计信息：文档数、非空率、平均长度、向量维度、元数据覆盖率。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `string` | 集合名称 |

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sample_limit` | `int` | `5000` | 统计采样上限 (100-100000) |

**响应** `CollectionStatsResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `string` | 集合名称 |
| `total_count` | `int` | 总文档数 |
| `sampled_count` | `int` | 实际采样数（≤ total_count） |
| `non_empty_count` | `int` | 非空文档数 |
| `empty_count` | `int` | 空文档数 |
| `empty_rate` | `string` | 文档非空率（百分比） |
| `avg_doc_length` | `float` | 平均文档长度（字符数） |
| `vector_dimension` | `int?` | 向量维度 |
| `metadata_coverage` | `dict[]` | 元数据字段覆盖率列表 |

`metadata_coverage` 每项：

| 字段 | 类型 | 说明 |
|------|------|------|
| `field` | `string` | 元数据字段名 |
| `count` | `int` | 包含该字段的文档数 |
| `coverage` | `string` | 覆盖率百分比 |

**响应示例**
```json
{
  "collection_name": "sunzi",
  "total_count": 450,
  "sampled_count": 450,
  "non_empty_count": 448,
  "empty_count": 2,
  "empty_rate": "99.6%",
  "avg_doc_length": 856.3,
  "vector_dimension": 4096,
  "metadata_coverage": [
    { "field": "source", "count": 450, "coverage": "100.0%" },
    { "field": "Header 1", "count": 380, "coverage": "84.4%" },
    { "field": "Header 2", "count": 290, "coverage": "64.4%" }
  ]
}
```

**注意**：空集合（total_count = 0）会返回零值响应，不会报错。

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_VECTORSTORE_ERROR` | 获取集合统计失败 |

---

#### `GET /api/rag/collection/{collection_name}/documents` — 分页查询文档

分页获取集合中的文档（ID、内容、元数据）。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `string` | 集合名称 |

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | `int` | `1` | 页码 (≥1) |
| `page_size` | `int` | `20` | 每页条数 (5-500) |

**响应** `CollectionDocumentsResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `string` | 集合名称 |
| `page` | `int` | 当前页码 |
| `page_size` | `int` | 每页条数 |
| `total` | `int` | 总文档数 |
| `documents` | `CollectionDocument[]` | 当前页文档列表 |

`CollectionDocument`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `string` | 文档 ID |
| `document` | `string?` | 文档内容 |
| `metadata` | `dict?` | 元数据键值对 |

**响应示例**
```json
{
  "collection_name": "sunzi",
  "page": 1,
  "page_size": 20,
  "total": 450,
  "documents": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "document": "# 概述\n\n本文档介绍...",
      "metadata": { "source": "01-概述.md", "Header 1": "# 概述" }
    }
  ]
}
```

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_VECTORSTORE_ERROR` | 获取文档列表失败 |

---

#### `POST /api/rag/collection/{collection_name}/delete-docs` — 批量删除集合内文档

从指定集合中按 ID 批量删除文档。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `string` | 集合名称 |

**请求体** `DeleteDocsRequest`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ids` | `string[]` | ✅ | 待删除的文档 ID 列表 |

**请求示例**
```json
{
  "ids": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

**响应** `DeleteDocsResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `deleted_count` | `int` | 成功删除的文档数 |
| `message` | `string` | 操作描述 |

**响应示例**
```json
{
  "deleted_count": 1,
  "message": "已从 sunzi 删除 1 个文档"
}
```

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_DELETE_FAILED` | 删除文档失败 |

---

#### `POST /api/rag/collection/{collection_name}/clear` — 清空集合

清空指定集合中的所有文档数据，集合本身保留。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `string` | 集合名称 |

**响应** `ClearCollectionResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `deleted_count` | `int` | 清除的文档数 |
| `collection_name` | `string` | 集合名称 |
| `message` | `string` | 操作描述 |

**响应示例**
```json
{
  "deleted_count": 450,
  "collection_name": "sunzi",
  "message": "集合 sunzi 已清空，共删除 450 条数据"
}
```

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_DELETE_FAILED` | 清空集合失败 |

---

#### `DELETE /api/rag/collection/{collection_name}` — 删除整个集合

永久删除整个 ChromaDB 集合。若删除的是当前 RAG 使用的集合，向量库单例将自动重置。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `string` | 集合名称 |

**响应** `DeleteCollectionResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `collection_name` | `string` | 已删除的集合名称 |
| `message` | `string` | 操作描述 |

**响应示例**
```json
{
  "collection_name": "temp_collection",
  "message": "集合 temp_collection 已永久删除"
}
```

**注意**：若删除的是当前 RAG 配置中的集合并后续调用处理接口，向量库单例将自动重新初始化。

**错误码**

| 错误码 | 说明 |
|--------|------|
| `RAG_DELETE_FAILED` | 删除集合失败 |

---

## 4. 端点总览

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rag/process` | 路径模式批量入库 |
| `POST` | `/api/rag/process/upload` | 上传模式批量入库 |
| `POST` | `/api/rag/delete` | 批量删除文档 |
| `GET` | `/api/rag/health` | 向量库健康检查 |
| `GET` | `/api/rag/config` | 读取 RAG 配置 |
| `PUT` | `/api/rag/config` | 更新 RAG 配置（热重载） |
| `GET` | `/api/rag/collections` | 列出所有集合 |
| `GET` | `/api/rag/collection/{name}/stats` | 集合统计信息 |
| `GET` | `/api/rag/collection/{name}/documents` | 分页查询集合文档 |
| `POST` | `/api/rag/collection/{name}/delete-docs` | 集合内批量删除文档 |
| `POST` | `/api/rag/collection/{name}/clear` | 清空集合 |
| `DELETE` | `/api/rag/collection/{name}` | 删除整个集合 |

---

## 5. Schema 模型速查表

### 5.1 请求模型

| 类名 | 用途 | 关键字段 |
|------|------|----------|
| `RAGProcessRequest` | 路径模式入库请求 | `files`, `preview_dir`, `preview_only` |
| `RAGDeleteRequest` | 批量删除请求 | `ids` |
| `DeleteDocsRequest` | 集合内删除请求 | `ids` |
| `RAGFullConfigModel` | 完整配置写入 | `embedding`, `rag` |

### 5.2 响应模型

| 类名 | 用途 | 关键字段 |
|------|------|----------|
| `RAGProcessResponse` | 入库响应 | `total_files`, `success_count`, `failed_count`, `total_chunks`, `collection_count`, `split_config`, `results` |
| `RAGProcessResult` | 单文件处理结果 | `filename`, `chunks_count`, `status`, `chunks` |
| `SplitConfig` | 分割配置信息 | `headers`, `chunk_size`, `chunk_overlap`, `enable_char_split` |
| `ChunkDetail` | 单个 chunk 详情 | `index`, `content_length`, `preview`, `header_path`, `is_char_split` |
| `RAGDeleteResponse` | 删除响应 | `deleted_count`, `collection_count`, `message` |
| `RAGHealthResponse` | 健康检查响应 | `collection_name`, `collection_count`, `embedding_model` |
| `CollectionListResponse` | 集合列表 | `collections` |
| `CollectionInfo` | 集合信息 | `name`, `count` |
| `CollectionStatsResponse` | 集合统计 | `total_count`, `sampled_count`, `avg_doc_length`, `vector_dimension`, `metadata_coverage` |
| `CollectionDocumentsResponse` | 文档分页 | `page`, `page_size`, `total`, `documents` |
| `CollectionDocument` | 文档项 | `id`, `document`, `metadata` |
| `DeleteDocsResponse` | 集合内删除响应 | `deleted_count`, `message` |
| `ClearCollectionResponse` | 清空集合响应 | `deleted_count`, `collection_name`, `message` |
| `DeleteCollectionResponse` | 删除集合响应 | `collection_name`, `message` |

### 5.3 配置子模型

| 类名 | 用途 | 关键字段 |
|------|------|----------|
| `RAGEmbeddingConfig` | 嵌入模型配置 | `model`, `base_url` |
| `RAGSplitterConfig` | 分割器配置 | `headers`, `chunk_size`, `chunk_overlap`, `enable_char_split` |
| `RAGHNSWConfig` | HNSW 索引参数 | `space`, `ef_construction`, `max_neighbors`, `batch_size` |
| `RAGProcessingConfig` | 处理参数配置 | `preview_output_dir`, `enable_interactive` |
| `RAGCollectionConfig` | 集合/存储配置 | `name`, `persist_directory` |
| `RAGPipelineSection` | rag 段聚合 | `splitter`, `hnsw`, `processing`, `collection` |
| `RAGFullConfigModel` | 完整配置模型 | `embedding`, `rag` |

---

## 6. 核心业务逻辑

### 6.1 文档分割流程（二级分割）

```
原始 Markdown 文本
    │
    ▼
ExperimentalMarkdownSyntaxTextSplitter  ← 一级：按标题层级切分
    │  (基于 headers: ["#", "##", "###"])
    │  (保留块元数据: Header 1, Header 2, Header 3)
    ▼
┌─ enable_char_split = false ─→ 直接返回 chunks
│
└─ enable_char_split = true ──→ RecursiveCharacterTextSplitter ← 二级：按字符长度二次切分
                                   │  (chunk_size + chunk_overlap)
                                   │  (separators: \n\n, \n, 。, ，, 空格)
                                   │  (自动继承父块的元数据)
                                   ▼
                              最终 chunks
```

### 6.2 ChunkDetail 构建逻辑

- `header_path`：从 metadata 的 `Header 1`~`Header N` 按 `" > "` 拼接
- `is_char_split`：当启用二级切分且 chunk 长度 ≤ `chunk_size` 时标记为 `true`
- `preview`：自动截断为 120 字符

### 6.3 向量库单例模式

- `_get_vectorstore()` — LangChain Chroma 封装，用于入库/删除/健康检查
- `_get_chroma_client()` — ChromaDB 原生 PersistentClient，用于数据浏览
- 单例在以下场景自动重置：
  - 配置更新后集合名称变更
  - 删除的集合恰好是当前使用的集合
  - 配置更新后持久化目录变更

### 6.4 配置热重载

`PUT /api/rag/config` 调用链：

```
接收 JSON → Pydantic 校验 → 序列化为 YAML → 写入文件
    → rag_setting.reload_rag_config() 重载模块变量
    → 对比新旧 collection_name / persist_directory
    → 必要时重置向量库单例
    → 返回成功响应
```

### 6.5 预览模式

- `preview_only=true` 时仅执行分块 + 生成预览文件，不写入 ChromaDB
- 预览文件格式：`.md` 文件，包含每块序号、字符数、标题路径、内容
- 预览输出目录由请求参数或配置文件的 `preview_output_dir` 决定

### 6.6 文件处理错误策略

单个文件处理失败**不影响其他文件**，`_process_batch` 采用逐文件 try/except：

| 异常类型 | status | error 消息 |
|----------|--------|------------|
| `UnicodeDecodeError` | `error` | "文件编码不是合法的 UTF-8" |
| `ValueError` | `error` | 具体错误信息（不支持格式/空内容等） |
| 其他异常 | `error` | "处理过程中发生未知错误" |

---

## 7. 错误码汇总

| 错误码 | HTTP 状态码 | 使用场景 |
|--------|------------|----------|
| `RAG_PROCESS_FAILED` | 500 | 文档处理失败（路径/上传模式） |
| `RAG_DELETE_FAILED` | 500 | 删除文档/清空集合/删除集合失败 |
| `RAG_VECTORSTORE_ERROR` | 500 | 向量库初始化/连接/健康检查失败 |
| `RAG_FILE_NOT_FOUND` | 404 | RAG 配置文件不存在或为空 |
| `VALIDATION_ERROR` | 400 | 请求参数校验失败（Pydantic） / YAML 序列化失败 |
| `INTERNAL_ERROR` | 500 | 配置文件读写异常 |
