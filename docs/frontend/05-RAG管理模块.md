# RAG 管理模块

> 本文档描述 RAG（检索增强生成）向量库管理模块，包含文档入库管道、文档删除、配置管理和健康监控。

---

## 模块架构

```
rag/
├── RagManagement.vue   # RAG 管理主页面（3 Tab + 健康面板）
└── useRagManager.ts    # RAG API 封装与状态管理
```

---

## RagManagement.vue（RAG 管理主页面）

### 布局

```
┌─────────────┬──────────────────────────────────────────┐
│             │  Tab: 文件处理 | 文档删除 | 配置管理        │
│ 左侧健康面板 ├──────────────────────────────────────────┤
│             │                                           │
│ 集合名称      │         当前 Tab 内容区域                 │
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

### Tab 1：文件处理

**「预览 → 确认」两步入库流程：**

#### Step 1：选择文件（两种方式互斥）

| 方式 | 说明 |
|------|------|
| **拖拽上传** | 拖拽 `.md` 文件到上传区，或点击选择（multipart 直传） |
| **路径填写** | 填写服务器上已有的 `.md` 文件路径（每行一个） |

> 两种方式互斥：使用拖拽上传时自动清空路径输入，填写路径时自动清空上传文件。

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

- 总文件数
- 成功/失败数
- 总分块数
- 向量库文档块总数（入库后更新）

#### 分块策略（后端）

| 层级 | 切分器 | 参数 |
|------|--------|------|
| 第一级 | `ExperimentalMarkdownSyntaxTextSplitter` | 按 `#`/`##`/`###` 标题、代码块、水平线 |
| 第二级 | `RecursiveCharacterTextSplitter` | `chunk_size=1000`, `overlap=200`（可配置） |

---

### Tab 2：文档删除

- 文档 ID 列表输入（每行一个）
- 批量删除向量库文档
- 删除结果展示

---

### Tab 3：配置管理

在线编辑 `rag_config.yaml`，保存后运行时自动重载。

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

### 左侧健康面板

实时展示向量库状态：

| 信息 | 来源 |
|------|------|
| 集合名称 | `GET /api/rag/health` |
| 文档块数 | `GET /api/rag/health` |
| 嵌入模型 | 配置 |
| 嵌入服务地址 | 配置 |
| 持久化目录 | 配置 |

支持每 10 秒自动刷新，也可手动刷新。

---

## useRagManager（RAG 状态管理）

### API 封装

```typescript
// 健康检查
fetchHealth(): Promise<RagHealthResponse>

// 按路径处理（JSON body）
processFiles(files: string[], previewDir?: string, previewOnly?: boolean)

// 上传文件处理（multipart FormData）
processUploadedFiles(files: File[], previewDir?: string, previewOnly?: boolean)

// 确认入库
confirmSave(pathFiles: string[], uploadFiles: File[], previewDir: string)

// 按 ID 删除
deleteByIds(ids: string[]): Promise<RagProcessResponse>

// 配置读写
fetchConfig(): Promise<RagFullConfigModel>
saveConfig(model: RagFullConfigModel): Promise<void>
```

### 状态字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `health` | `Ref<RagHealthResponse \| null>` | 健康检查结果 |
| `processResult` | `Ref<RagProcessResponse \| null>` | 处理/入库结果 |
| `loading` | `Ref<boolean>` | 加载中 |
| `config` | `Ref<RagFullConfigModel \| null>` | 当前 RAG 配置 |
| `configLoading` | `Ref<boolean>` | 配置加载中 |
| `autoRefresh` | `Ref<boolean>` | 自动刷新开关 |

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
```
