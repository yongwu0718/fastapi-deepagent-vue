# RAG 管理模块

> 本文档描述 RAG（检索增强生成）向量库管理模块，包含文档入库管道、配置管理、数据库浏览和健康监控。

---

## 模块架构

```
rag/
├── RagManagement.vue          # 主页面外壳（Header 导航 + 健康面板 + Tab栏 + 子组件，~172 行）
├── components/
│   ├── HealthPanel.vue        # 左侧健康面板（骨架屏/错误态/数据态）
│   ├── ProcessTab.vue         # 文件处理 Tab（拖拽上传 + 路径 + 预览 + 入库）
│   ├── ConfigTab.vue          # 配置管理 Tab（rag_config.yaml 在线编辑，含集合/存储区块）
│   └── BrowseTab.vue          # 数据库浏览 Tab（集合/文档列表/单删/清空/删除集合，含展开折叠）
└── composables/
    ├── useRagManager.ts       # API 封装与全局状态（自动生成 SDK）
    ├── useRagTabs.ts          # Tab 状态 + 切换逻辑 + 配置加载回调 + 浏览自动加载
    ├── useRagConfig.ts        # 配置表单（初始化/加载/保存/序列化）
    ├── useRagProcess.ts       # 文件处理（路径解析 + 分块预览 + 确认入库 + 结果展示）
    ├── useRagBrowse.ts        # 数据库浏览（集合选择/分页文档/单删确认/清空/删除集合）
    ├── useRagHealth.ts        # 自动刷新定时器（10s 间隔 + onMounted/onUnmounted + toggle）
    └── useRagUpload.ts        # 文件上传（拖拽 + 文件选择 + 去重 + 列表管理）
```

### 依赖注入

```
RagManagement.vue (组合入口)
  ├─ useRagManager()              → rag (API + 状态)
  ├─ useRagUpload()               → uploadItems, drag/drop 事件
  ├─ useRagProcess(rag, upload)   → 依赖 uploadItems ref, parsedFiles 计算属性
  ├─ useRagConfig(rag)            → configForm + load/save
  ├─ useRagTabs(rag)              → activeTab + switchTab
  │    ├─ registerConfigLoader()  ← 注入 handleLoadConfig 回调
  │    └─ switchTab('browse')     → 自动 fetchCollections + 选中首个集合
  ├─ useRagBrowse(rag)            → 数据库操作（确认弹窗状态）
  └─ useRagHealth(rag)            → autoRefresh + start/stop/toggle 定时器
```

---

## RagManagement.vue（主页面外壳）

### 页面结构

```
┌──────────────────────────────────────────────────────────────────┐
│  Header: [← 返回聊天]    向量库管理 (RAG)    [设置管理]          │
├─────────────┬────────────────────────────────────────────────────┤
│             │  Tab: 文件处理 | 配置管理 | 数据库浏览              │
│ 左侧健康面板 │  (config 模式下 Tab 栏右侧出现 [读取] [保存] 按钮) │
│             ├────────────────────────────────────────────────────┤
│  骨架屏/     │                                                    │
│  错误态/     │           当前 Tab 子组件内容                       │
│  数据态      │                                                    │
│             │                                                    │
│  [自动刷新]  │                                                    │
│  [🔄 刷新]  │                                                    │
└─────────────┴────────────────────────────────────────────────────┘
```

### Header 导航

- **← 返回聊天**：`stopAutoRefresh()` 后 `router.push({ name: 'chat' })`
- **设置管理**：`stopAutoRefresh()` 后 `router.push({ name: 'settings' })`

### 关键交互

- **上传/路径互斥**：`watch(processFilesInput)` 清空上传列表，`watch(uploadItems)` 清空路径输入
- **Tab 切换逻辑**：切换到 `config` 时首次自动读取配置；切换到 `browse` 时自动加载集合列表并选中首个
- **子组件通信**：所有 props 单向传递，事件 emit 回到 RagManagement.vue 调用 composable 方法

---

## Tab 1：文件处理（ProcessTab.vue）

**「预览 → 确认」两步入库流程：**

### Step 1：选择文件（两种方式互斥）

| 方式 | 说明 |
|------|------|
| **拖拽上传** | 拖拽 `.md` 文件到上传区，或点击选择（multipart 直传）。已上传文件显示列表（文件名、大小、移除按钮） |
| **路径填写** | 填写服务器上已有的 `.md` 文件路径（每行一个）。通过 `parsedFiles` 计算属性按换行和逗号分割 |

> 两种方式互斥：通过 `watch(processFilesInput)` 和 `watch(uploadItems)` 双向清空实现。路径被填写时上传区显示"已填写路径，上传已禁用"；有上传文件时路径 textarea 禁用。

### Step 2：预览分块

点击"预览分块"按钮 → 调用 `useRagProcess.handleProcess()`：
- 有上传文件 → `rag.processUploadedFiles(uploadFiles, previewDir, previewOnly=true)`
- 有路径 → `rag.processFiles(parsedFiles, previewDir, previewOnly=true)`

后端执行分块但不写入向量库 → 返回逐文件分块详情表格：

| 列 | 说明 |
|------|------|
| # | 分块序号 |
| 标题路径 | 文档中的标题层级路径（无则为 —） |
| 内容预览 | 分块内容前若干字符（等宽字体展示） |
| 长度 | 分块字符数 |
| 类型 | `标题切分` / `二次切分`（badge 样式区分，二次切分行背景高亮） |

点击每个文件行可展开/折叠分块详情表。

### Step 3：确认入库

检查分块质量后，点击"确认入库 (N 个分块)" → `handleConfirmSave()`，根据原始输入方式调用 `processFiles` 或 `processUploadedFiles`（`previewOnly=false`），实际写入 Chroma 向量库。

### 结果展示

- **Summary**：总文件数 / 成功数（绿色）/ 失败数（红色）/ 总分块数
- **Meta**：向量库当前文档块总数
- **详情列表**：按文件展开，成功/失败状态分别着色，失败文件显示错误信息

### 分块策略（后端）

| 层级 | 切分器 | 参数 |
|------|--------|------|
| 第一级 | `ExperimentalMarkdownSyntaxTextSplitter` | 按 `#`/`##`/`###` 标题、代码块、水平线 |
| 第二级 | `RecursiveCharacterTextSplitter` | `chunk_size=1000`, `overlap=200`（可配置） |

---

## Tab 2：配置管理（ConfigTab.vue）

在线编辑 `rag_config.yaml`，保存后运行时自动重载。Tab 栏右侧有「读取」「保存」按钮。

**配置项：**

| 分类 | 配置项 | 控件类型 | 说明 |
|------|--------|----------|------|
| **嵌入模型** | `model` | text | Ollama 嵌入模型名称 |
| | `base_url` | text | Ollama 服务地址 |
| **文档分割器** | `headers` | text（逗号分隔） | 标题切分层级（`#,##,###`） |
| | `chunk_size` | number | 字符分块大小 |
| | `chunk_overlap` | number | 重叠字符数 |
| | `enable_char_split` | checkbox | 是否启用字符切分 |
| | `return_each_line` | checkbox | 逐行返回 |
| | `strip_headers` | checkbox | 剥离标题行 |
| **HNSW 索引** | `space` | select | 距离度量（cosine / l2 / ip） |
| | `ef_construction` | number | 构建时搜索深度 |
| | `max_neighbors` | number | 最大邻居数 |
| | `ef_search` | number | 查询深度 |
| | `num_threads` | number | 构建线程数 |
| | `batch_size` | number | 批处理大小 |
| | `sync_threshold` | number | 同步阈值 |
| | `resize_factor` | number（step=0.1） | 扩容因子 |
| **处理参数** | `preview_output_dir` | text | 分块预览输出目录 |
| | `enable_interactive` | checkbox | CLI 交互确认开关 |
| **集合/存储** | `name` | text | Chroma 集合名称，修改后旧集合数据保留在磁盘 |
| | `memory_name` | text | 记忆库 Chroma 集合名称 |
| | `persist_directory` | text | 向量库磁盘路径 |

### 配置序列化

- **加载**：`handleLoadConfig()` → `rag.fetchConfig()` → `applyConfigToForm()` 将 API 返回数据映射到表单
- **保存**：`handleSaveConfig()` → `buildConfigPayload()` 序列化表单 → `rag.saveConfig()`
- **空值处理**：空字符串转为 `undefined` 再提交

---

## Tab 3：数据库浏览（BrowseTab.vue）

直接在浏览器中查看和管理 ChromaDB 数据。

**功能：**

| 区域 | 功能 |
|------|------|
| **集合选择** | 下拉框列出所有 Collection（含文档数），支持手动刷新。切换集合自动重新加载文档列表 |
| **文档列表** | 分页表格（6列：展开、#、文档ID、内容预览前300字、元数据JSON、操作），支持文档内容展开/折叠 |
| **单文档删除** | 每行 `✕` 按钮，点击后显示确认/取消，二次确认后删除 |
| **清空集合** | 点击后显示警告文案与确认/取消按钮，确认后清空集合内所有文档 |
| **删除集合** | 点击后显示警告文案与确认/取消按钮，确认后永久删除集合 |

> **注：** 源码中已移除「统计面板」和「批量删除」功能，当前仅保留上述功能。

### 文档展开/折叠

- 每行首列有 ▶ 按钮，点击展开该文档的完整内容（`expandedDocIds` Set 追踪）
- 展开行横跨 6 列，最大高度 360px 可滚动
- 切换集合或翻页时自动收起所有展开行
- ▶ 图标展开时旋转 90° 并变蓝

### 交互保护

- 操作加载中（`browseActionLoading`）时所有按钮禁用
- 删除/清空/删除集合均为二级确认，防止误操作

---

## 左侧健康面板（HealthPanel.vue）

实时展示向量库状态，三种显示模式：

### 骨架屏（首次加载）

当 `healthLoading` 为 true 且 `health` 为 null 时，显示 5 行占位骨架条（脉冲动画）。

### 错误态

当 `healthError` 非空时，显示红色错误面板。

### 数据态

正常显示健康信息：

| 信息 | 来源 |
|------|------|
| 集合名称 (`collection_name`) | `GET /api/rag/health` |
| 文档块数 (`collection_count`) | `GET /api/rag/health`（蓝色高亮加粗） |
| 嵌入模型 (`embedding_model`) | `GET /api/rag/health` |
| 嵌入服务 (`embedding_base_url`) | `GET /api/rag/health`（等宽字体） |
| 持久化目录 (`persist_directory`) | `GET /api/rag/health`（等宽字体） |

### 刷新控制

- 默认开启自动刷新（10s 间隔），`onMounted` 时启动
- [自动刷新] 复选框控制 `autoRefresh` 状态，toggle 启停定时器
- 手动 [🔄 刷新] 按钮（独立于自动定时器）
- `onUnmounted` 时自动停止定时器

---

## useRagManager（API 封装与状态管理）

### 文件处理 API

```typescript
fetchHealth(): Promise<RagHealthResponse>
processFiles(files: string[], previewDir?: string | null, previewOnly?: boolean)
processUploadedFiles(files: File[], previewDir?: string | null, previewOnly?: boolean)
confirmSave(pathFiles: string[], uploadFiles: File[], previewDir: string | null)
deleteByIds(ids: string[]): Promise<RagDeleteResponse>
```

### 配置管理 API

```typescript
fetchConfig(): Promise<RagFullConfigModel>
saveConfig(model: RagFullConfigModel): Promise<void>
```

### 数据库浏览 API

```typescript
fetchCollections(): Promise<CollectionListResponse>
fetchCollectionStats(collectionName: string, sampleLimit?: number): Promise<CollectionStatsResponse>
fetchDocuments(collectionName: string, page: number, pageSize: number): Promise<CollectionDocumentsResponse>
selectCollection(name: string)      // 同时加载该集合分页文档
deleteDocsFromCollection(collectionName: string, ids: string[]): Promise<DeleteDocsResponse>
clearCollectionAction(collectionName: string): Promise<ClearCollectionResponse>
deleteCollectionAction(collectionName: string): Promise<DeleteCollectionResponse>
```

### 返回状态字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `health` | `Ref<RagHealthResponse \| null>` | 健康检查结果 |
| `healthLoading` | `Ref<boolean>` | 健康检查加载中（HealthPanel 骨架屏用） |
| `healthError` | `Ref<string>` | 健康检查错误信息（HealthPanel 错误态用） |
| `processResult` | `Ref<RagProcessResponse \| null>` | 处理/入库结果 |
| `processing` | `Ref<boolean>` | 处理中（按钮 disabled 用） |
| `deleteResult` | `Ref<RagDeleteResponse \| null>` | 按ID删除结果 |
| `deleting` | `Ref<boolean>` | 删除中 |
| `config` | `Ref<RagFullConfigModel \| null>` | 当前 RAG 配置 |
| `configLoading` | `Ref<boolean>` | 配置加载中 |
| `configSaving` | `Ref<boolean>` | 配置保存中（保存按钮 disabled 用） |
| `configLoaded` | `Ref<boolean>` | 配置是否已加载（避免重复请求） |
| `collections` | `Ref<CollectionListResponse \| null>` | 集合列表 |
| `collectionsLoading` | `Ref<boolean>` | 集合列表加载中 |
| `selectedCollection` | `Ref<string>` | 当前选中的集合名 |
| `collectionStats` | `Ref<CollectionStatsResponse \| null>` | 集合统计信息 |
| `statsLoading` | `Ref<boolean>` | 统计加载中 |
| `documents` | `Ref<CollectionDocumentsResponse \| null>` | 分页文档列表 |
| `docsLoading` | `Ref<boolean>` | 文档列表加载中 |
| `browsePage` | `Ref<number>` | 当前页码（默认 1） |
| `browsePageSize` | `Ref<number>` | 每页大小（默认 20） |
| `browseActionLoading` | `Ref<boolean>` | 数据库操作执行中（统一禁用按钮用） |

---

## 数据流

```
用户操作                   前端                            后端
───────                   ──────                          ──────
选择文件/拖拽上传          uploadItems / processFilesInput   接收文件/路径
点击"预览分块"            processFiles / processUploadedFiles  分块（不写入向量库）
                          (previewOnly=true)
查看分块表格              渲染分块结果（含展开/折叠）
点击"确认入库"            confirmSave()                   写入 Chroma 向量库
查看入库结果              渲染成功/失败统计                  返回 collection_count

读取配置                  fetchConfig()                   GET /api/rag/config
编辑表单并保存            saveConfig()                    PUT /api/rag/config

选择集合                  fetchCollections()              GET /api/rag/collections
点击集合名                selectCollection()              GET collection/{name}/documents
翻页                      fetchDocuments()                GET collection/{name}/documents?page=&page_size=
点击文档 ▶ 展开           expandedDocIds.add()            纯前端状态
点击行 ✕ → 确认           deleteDocsFromCollection()      POST collection/{name}/delete-docs
点击清空 → 确认           clearCollectionAction()         POST collection/{name}/clear
点击删除集合 → 确认       deleteCollectionAction()        DELETE collection/{name}

页面挂载                  fetchHealth() + startAutoRefresh  GET /api/rag/health（每10s）
页面卸载                  stopAutoRefresh()
```
