# RAG 管理模块

> 本文档描述 RAG（检索增强生成）向量库管理模块，包含文档入库管道、配置管理、数据库浏览和健康监控。

---

## 模块架构

```
rag/
├── RagManagement.vue          # 主页面外壳（Header + Tab栏 + 子组件组合，~170 行）
├── components/
│   ├── HealthPanel.vue        # 左侧健康面板
│   ├── ProcessTab.vue         # 文件处理 Tab（拖拽上传 + 路径 + 预览 + 入库）
│   ├── ConfigTab.vue          # 配置管理 Tab（rag_config.yaml 在线编辑）
│   └── BrowseTab.vue          # 数据库浏览 Tab（集合/统计/文档列表/批量操作）
└── composables/
    ├── useRagManager.ts       # API 封装与全局状态（自动生成 SDK）
    ├── useRagTabs.ts          # Tab 状态 + 切换逻辑 + 配置加载回调
    ├── useRagConfig.ts        # 配置表单（初始化/加载/保存/序列化）
    ├── useRagProcess.ts       # 文件处理（分块预览 + 确认入库 + 结果展示）
    ├── useRagBrowse.ts        # 数据库浏览（集合选择/统计/分页文档/删除操作）
    ├── useRagHealth.ts        # 自动刷新定时器（10s 间隔 + onMounted/onUnmounted）
    └── useRagUpload.ts        # 文件上传（拖拽 + 文件选择 + 列表管理）
```

### 依赖注入

```
RagManagement.vue (组合入口)
  ├─ useRagManager()              → rag (API + 状态)
  ├─ useRagUpload()               → uploadItems, drag/drop 事件
  ├─ useRagProcess(rag, upload)   → 依赖 uploadItems ref
  ├─ useRagConfig(rag)            → configForm + load/save
  ├─ useRagTabs(rag)              → activeTab + switchTab
  │    └─ registerConfigLoader()  ← 注入 handleLoadConfig 回调
  ├─ useRagBrowse(rag)            → 数据库操作
  └─ useRagHealth(rag)            → autoRefresh + 定时器
```

---

## RagManagement.vue（主页面外壳）

### 布局

```
┌─────────────┬──────────────────────────────────────────┐
│             │  Tab: 文件处理 | 配置管理 | 数据库浏览       │
│ 左侧健康面板 ├──────────────────────────────────────────┤
│             │                                           │
│ 集合名称      │         当前 Tab 子组件内容                │
│ 文档块数      │                                           │
│ 嵌入模型      │                                           │
│ 嵌入服务地址  │                                           │
│ 持久化目录    │                                           │
│             │                                           │
│ 自动刷新 10s │                                           │
└─────────────┴──────────────────────────────────────────┘
```

### 三大 Tab

---

### Tab 1：文件处理（ProcessTab.vue）

**「预览 → 确认」两步入库流程：**

#### Step 1：选择文件（两种方式互斥）

| 方式 | 说明 |
|------|------|
| **拖拽上传** | 拖拽 `.md` 文件到上传区，或点击选择（multipart 直传） |
| **路径填写** | 填写服务器上已有的 `.md` 文件路径（每行一个） |

> 两种方式互斥：通过 `watch(processFilesInput)` 和 `watch(uploadItems)` 双向清空实现。

#### Step 2：预览分块

点击"预览分块"按钮 → 后端执行分块但不写入向量库 → 返回逐文件分块详情表格：

| 列 | 说明 |
|------|------|
| 索引 | 分块序号 |
| 标题路径 | 文档中的标题层级路径 |
| 内容预览 | 分块内容前若干字符 |
| 长度 | 分块字符数 |
| 切分类型 | 标题切分 / 二次切分 |

#### Step 3：确认入库

检查分块质量后，点击"确认入库" → 实际写入 Chroma 向量库。

#### 结果展示

- 总文件数 / 成功数 / 失败数 / 总分块数
- 向量库文档块总数（入库后更新）

#### 分块策略（后端）

| 层级 | 切分器 | 参数 |
|------|--------|------|
| 第一级 | `ExperimentalMarkdownSyntaxTextSplitter` | 按 `#`/`##`/`###` 标题、代码块、水平线 |
| 第二级 | `RecursiveCharacterTextSplitter` | `chunk_size=1000`, `overlap=200`（可配置） |

---

### Tab 2：配置管理（ConfigTab.vue）

在线编辑 `rag_config.yaml`，保存后运行时自动重载。Tab 栏右侧有「读取」「保存」按钮。

**配置项：**

| 分类 | 配置项 | 说明 |
|------|--------|------|
| **嵌入模型** | embedding model | 嵌入模型名称 |
| | base_url | 嵌入服务地址 |
| **文档分割器** | headers | 标题切分层级（`#`/`##`/`###`） |
| | chunk_size | 字符分块大小 |
| | chunk_overlap | 重叠字符数 |
| | character_split | 是否启用字符切分 |
| **HNSW 索引** | space | 距离度量（cosine/ip/l2） |
| | ef_construction | 构建时搜索深度 |
| | max_neighbors | 最大邻居数 |
| | ef_search | 搜索时搜索深度 |
| | batch_size | 批处理大小 |
| | num_threads | 线程数 |
| | resize_factor | 扩展因子 |
| | sync_threshold | 同步阈值 |
| **处理参数** | preview_output_dir | 分块预览输出目录 |
| | cli_interactive | CLI 交互确认开关 |

---

### Tab 3：数据库浏览（BrowseTab.vue）

直接在浏览器中查看和管理 ChromaDB 数据，替代了旧的「文档删除」Tab。

**功能：**

| 区域 | 功能 |
|------|------|
| **集合选择** | 下拉框列出所有 Collection（含文档数），支持手动刷新 |
| **统计面板** | 总文档数、采样文档数、非空率、平均长度、向量维度、空文档数、元数据字段覆盖率 |
| **文档列表** | 分页表格（序号、ID、内容预览、元数据 tags），每行末尾 `✕` 删除按钮 |
| **批量删除** | 文本区输入 ID 列表，批量删除 |
| **清空集合** | 二级确认后清空所有文档 |
| **删除集合** | 二级确认后永久删除集合 |

依赖后端 6 个新增 REST 端点（见后端 API 文档）。

---

### 左侧健康面板（HealthPanel.vue）

实时展示向量库状态：

| 信息 | 来源 |
|------|------|
| 集合名称 | `GET /api/rag/health` |
| 文档块数 | `GET /api/rag/health` |
| 嵌入模型 | 配置 |
| 嵌入服务地址 | 配置 |
| 持久化目录 | 配置 |

支持每 10 秒自动刷新，也可手动刷新。使用 `onMounted` / `onUnmounted` 管理定时器生命周期。

---

## useRagManager（API 封装与状态管理）

### 文件处理 API

```typescript
fetchHealth(): Promise<RagHealthResponse>
processFiles(files: string[], previewDir?: string, previewOnly?: boolean)
processUploadedFiles(files: File[], previewDir?: string, previewOnly?: boolean)
confirmSave(pathFiles: string[], uploadFiles: File[], previewDir: string)
deleteByIds(ids: string[]): Promise<RagProcessResponse>
```

### 配置管理 API

```typescript
fetchConfig(): Promise<RagFullConfigModel>
saveConfig(model: RagFullConfigModel): Promise<void>
```

### 数据库浏览 API

```typescript
fetchCollections(): Promise<CollectionListResponse>
fetchCollectionStats(name: string, limit?: number): Promise<CollectionStatsResponse>
fetchDocuments(name: string, page: number, pageSize: number): Promise<CollectionDocumentsResponse>
selectCollection(name: string)      // 同时加载统计 + 文档
deleteDocsFromCollection(name: string, ids: string[]): Promise<DeleteDocsResponse>
clearCollectionAction(name: string): Promise<ClearCollectionResponse>
deleteCollectionAction(name: string): Promise<DeleteCollectionResponse>
```

### 状态字段（新增数据库浏览状态）

| 字段 | 类型 | 说明 |
|------|------|------|
| `health` | `Ref<RagHealthResponse \| null>` | 健康检查结果 |
| `processResult` | `Ref<RagProcessResponse \| null>` | 处理/入库结果 |
| `config` | `Ref<RagFullConfigModel \| null>` | 当前 RAG 配置 |
| `configLoading` | `Ref<boolean>` | 配置加载中 |
| `collections` | `Ref<CollectionListResponse \| null>` | 集合列表 |
| `selectedCollection` | `Ref<string>` | 当前选中的集合名 |
| `collectionStats` | `Ref<CollectionStatsResponse \| null>` | 集合统计信息 |
| `documents` | `Ref<CollectionDocumentsResponse \| null>` | 分页文档列表 |
| `browsePage` / `browsePageSize` | `Ref<number>` | 文档分页参数 |

---

## 数据流

```
用户操作                   前端                        后端
───────                   ──────                      ──────
选择文件                  上传/填写路径                  接收文件/路径
点击"预览分块"            processFiles/UploadedFiles   分块（不写入向量库）
                          (previewOnly=true)
查看分块表格              渲染分块结果
点击"确认入库"            confirmSave()               写入 Chroma 向量库
查看入库结果              渲染成功/失败统计

选择集合                  fetchCollections()           GET /api/rag/collections
点击集合名                selectCollection()           GET stats + GET documents
点击行删除按钮            deleteDocsFromCollection()   POST collection/{name}/delete-docs
点击清空集合              clearCollectionAction()     POST collection/{name}/clear
点击删除集合              deleteCollectionAction()     DELETE collection/{name}
```
