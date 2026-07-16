# API 层

> 本文档描述前端的 API 层设计，包括手写类型定义、自动生成的类型安全客户端及其使用方式。

---

## 架构概览

API 层分为两层：

```
src/api/
├── chat.ts              # 手写：聊天相关富类型定义
├── files.ts             # 手写：文件管理类型 + 工具函数
└── client/              # 自动生成：类型安全 HTTP 客户端（@hey-api/openapi-ts）
    ├── client.gen.ts    # 全局客户端单例
    ├── index.ts         # 统一导出入口
    ├── sdk.gen.ts       # 39 个 API 函数
    ├── types.gen.ts     # 50+ 个请求/响应类型定义（2173 行）
    ├── client/          # 客户端核心实现
    │   ├── client.gen.ts    # createClient 工厂函数（fetch 封装 + 拦截器）
    │   ├── types.gen.ts     # Client / Config / RequestResult 核心类型
    │   └── utils.gen.ts     # mergeHeaders / buildUrl / createConfig
    └── core/            # 底层基础设施
        ├── auth.gen.ts              # 认证（apiKey / http bearer / basic）
        ├── bodySerializer.gen.ts    # FormData / JSON / URLSearchParams 序列化
        ├── params.gen.ts            # 参数分发（body / headers / path / query）
        ├── pathSerializer.gen.ts    # Label / Matrix / Simple / Form 风格序列化
        ├── queryKeySerializer.gen.ts# Pinia Colada 缓存 key 生成
        ├── serverSentEvents.gen.ts  # SSE 流式客户端（支持重连、指数退避）
        ├── types.gen.ts             # HttpMethod / 通用 Client / Config 接口
        └── utils.gen.ts             # URL 构建 / 请求体处理
```

---

## 手写类型层 (`chat.ts`)

### Message 与消息类型

```typescript
// 原始消息角色
type MessageRole = 'user' | 'assistant' | 'system' | 'tool'

// 多模态内容块（图片、文件附件）
interface ContentBlock {
  type: 'image' | 'file'
  mimeType: string
  data: string          // base64 编码
  metadata?: {
    filename?: string
    size?: number
    name?: string
  }
}

// 工具调用
interface ToolCall {
  id: string            // tool_call_id
  name: string          // 工具名称
  args: Record<string, unknown>
  result?: string       // 工具执行结果
}
```

### Message 核心接口

```typescript
interface Message {
  role: MessageRole
  content: string
  reasonContent?: string         // 推理过程
  contentBlocks?: ContentBlock[]  // 多模态内容
  toolCalls?: ToolCall[]          // assistant 消息的工具调用
  interrupt?: unknown             // 中断数据
  // 检查点绑定（用于分支导航）
  _checkpointId?: string          // input 检查点（用于 retry）
  _parentCheckpointId?: string    // 父检查点（用于 fork）
  _leafCheckpointId?: string      // 叶子检查点（当前分支终点）
}
```

### SSE 流事件类型

```typescript
// SSE 流返回的 chunk 事件
interface StreamChunk {
  type: 'text' | 'reasoning' | 'tool_call' | 'tool_result'
      | 'done' | 'error' | 'interrupt' | 'checkpoint'
      | 'user' | 'rubric'
  content?: string
  tool_call_id?: string
  tool_call_name?: string
  args?: string
  metadata?: Record<string, unknown>
}
```

### HITL 审批类型

```typescript
// 后端 interrupt 事件解析后的数据结构
interface ActionRequest {
  name: string
  args: Record<string, unknown>
  description?: string
}

interface ReviewConfig {
  action_name: string
  allowed_decisions: ('approve' | 'reject' | 'edit')[]
}

interface HITLRequest {
  action_requests: ActionRequest[]
  review_configs: ReviewConfig[]
}

// 用户对单个动作的决策
interface HITLDecision {
  type: 'approve' | 'reject' | 'edit'
  message?: string        // 拒绝原因
  edited_action?: Record<string, unknown>  // 编辑后的参数
}

interface HITLResponse {
  decisions: HITLDecision[]
}
```

---

## 手写类型层 (`files.ts`)

### 文件条目类型

```typescript
// 后端返回的原始数据结构
interface RawFileItem {
  name: string
  type: 'file' | 'dir'
  size?: number
  modified?: string
}

interface RawListResponse {
  path: string
  items: RawFileItem[]
}

// 标准化后的前端条目
interface FileEntry {
  name: string
  path: string
  type: 'file' | 'directory'
  size?: number
  modified?: string
  editable?: boolean
  url?: string
}
```

### 文件类型判断工具函数

```typescript
getFileExtension(name: string): string          // 提取扩展名
isBinaryFile(name: string): boolean             // 是否二进制
isPreviewableImage(name: string): boolean       // 是否可 <img> 预览
isIframePreviewable(name: string): boolean      // 是否可 <iframe> 预览（PDF）

// 数据标准化
normalizeEntry(raw: RawFileItem, basePath: string): FileEntry
normalizeListResponse(raw: RawListResponse): { path: string; entries: FileEntry[] }
normalizeReadResponse(raw: RawReadResponse): FileReadResponse
```

---

## 自动生成层

### 全局客户端单例 (`client.gen.ts`)

```typescript
import { createClient } from './client/client.gen'

const client = createClient({
  baseUrl: 'http://localhost:8000',
})
```

所有 SDK 函数默认使用此单例，也可按需传入自定义 options。

### SDK 函数调用模式

每个端点对应一个导出的 async 函数，支持两种调用模式：

```typescript
// 模式 1：抛异常（throwOnError: true）
const data = await getInputCheckpointsCheckpointsThreadIdInputsGet({
  path: { thread_id: 'xxx' }
})

// 模式 2：不抛异常，返回 { data, error, request, response }
const { data, error } = await getInputCheckpointsCheckpointsThreadIdInputsGet({
  path: { thread_id: 'xxx' },
  throwOnError: false  // 默认不抛异常
})
```

### 端点总览（39 个函数）

#### 聊天（8 个端点）

| 函数名 | 方法 | URL | 说明 |
|--------|------|-----|------|
| `chatEndpointChatThreadIdPost` | POST | `/chat/{thread_id}` | 非流式聊天 |
| `chatStreamChatThreadIdStreamPost` | POST | `/chat/{thread_id}/stream` | 流式聊天（SSE） |
| `resumeChatEndpointChatThreadIdResumePost` | POST | `/chat/{thread_id}/resume` | 恢复 HITL 中断 |
| `chatWithFilesEndpointChatThreadIdWithFilesPost` | POST | `/chat/{thread_id}/with-files` | 带文件非流式聊天 |
| `chatWithFilesStreamEndpointChatThreadIdWithFilesStreamPost` | POST | `/chat/{thread_id}/with-files/stream` | 带文件流式聊天 |
| `getMessagesHistoryChatThreadIdGetMessagesHistoryGet` | GET | `/chat/{thread_id}/get-messages-history` | 获取历史（支持 checkpoint_id） |
| `deleteMessagesHistoryChatThreadIdDeleteMessagesHistoryDelete` | DELETE | `/chat/{thread_id}/delete-messages-history` | 删除历史消息 |
| `listThreadsEndpointThreadsGet` | GET | `/threads` | 列出所有线程 |

#### 检查点（3 个端点）

| 函数名 | 方法 | URL | 说明 |
|--------|------|-----|------|
| `getInputCheckpointsCheckpointsThreadIdInputsGet` | GET | `/checkpoints/{thread_id}/inputs` | 获取 input 检查点（分页） |
| `replayCheckpointCheckpointsThreadIdReplayPost` | POST | `/checkpoints/{thread_id}/replay` | 从检查点重放（SSE） |
| `forkCheckpointCheckpointsThreadIdForkPost` | POST | `/checkpoints/{thread_id}/fork` | 从检查点分叉（SSE） |

#### 文件管理（11 个端点）

| 函数名 | 方法 | URL | 说明 |
|--------|------|-----|------|
| `listDirectoryEndpointApiFilesListGet` | GET | `/api/files/list` | 列出目录 |
| `getFileEndpointApiFilesFileGet` | GET | `/api/files/file` | 读取文件（二进制） |
| `readFileEndpointApiFilesReadGet` | GET | `/api/files/read` | 读取文件（JSON） |
| `searchFilesEndpointApiFilesSearchGet` | GET | `/api/files/search` | 搜索文件 |
| `createFileEndpointApiFilesCreateFilePost` | POST | `/api/files/create-file` | 创建文件 |
| `createDirectoryEndpointApiFilesCreateDirectoryPost` | POST | `/api/files/create-directory` | 创建目录 |
| `uploadFileEndpointApiFilesUploadPost` | POST | `/api/files/upload` | 上传文件（multipart） |
| `renameEndpointApiFilesRenamePut` | PUT | `/api/files/rename` | 重命名 |
| `moveEndpointApiFilesMovePut` | PUT | `/api/files/move` | 移动文件 |
| `modifyFileEndpointApiFilesModifyPut` | PUT | `/api/files/modify` | 修改内容 |
| `deleteEndpointApiFilesDeleteDelete` | DELETE | `/api/files/delete` | 删除 |

#### 设置（5 个端点）

| 函数名 | 方法 | URL | 说明 |
|--------|------|-----|------|
| `readModelConfigEndpointSettingsModelConfigReadGet` | GET | `/settings/model-config/read` | 读取模型配置 |
| `writeModelConfigEndpointSettingsModelConfigWritePut` | PUT | `/settings/model-config/write` | 覆写模型配置 |
| `getSkillsSettingsSkillsGet` | GET | `/settings/skills` | 获取技能启用状态 |
| `updateSkillsSettingsSkillsPut` | PUT | `/settings/skills` | 更新技能并重建 Graph |
| `rebuildSettingsRebuildPost` | POST | `/settings/rebuild` | 重新编译 LangGraph |

#### Memory & Skill 文件管理（10 个端点）

与文件管理功能镜像，端点前缀为 `/settings/memory-and-skill/`，需要 `type: 'memory' | 'skills'` 查询参数。

#### RAG 管理（6 个端点）

| 函数名 | 方法 | URL | 说明 |
|--------|------|-----|------|
| `processRagEndpointApiRagProcessPost` | POST | `/api/rag/process` | 按路径处理 .md 文档入库 |
| `processUploadEndpointApiRagProcessUploadPost` | POST | `/api/rag/process/upload` | 上传 .md 文件入库 |
| `deleteRagEndpointApiRagDeletePost` | POST | `/api/rag/delete` | 按 ID 删除向量库文档 |
| `healthRagEndpointApiRagHealthGet` | GET | `/api/rag/health` | 向量库健康检查 |
| `getRagConfigEndpointApiRagConfigGet` | GET | `/api/rag/config` | 读取 RAG 配置 |
| `updateRagConfigEndpointApiRagConfigPut` | PUT | `/api/rag/config` | 覆写 RAG 配置 |

---

## 类型定义总览 (`types.gen.ts`)

包含 **50+ 个类型/接口**，主要分类：

### 请求体类型

| 类型 | 说明 |
|------|------|
| `ChatRequest` | 聊天请求：messages + checkpoint_id + rubric |
| `ChatResponse` | 聊天响应 |
| `MessageResponse` | 消息响应 |
| `ResumeRequest` | 恢复中断请求 |
| `CreateFileRequest` | 创建文件请求 |
| `RagProcessRequest` | RAG 处理请求 |
| `RagDeleteRequest` | RAG 删除请求 |
| `RagFullConfigModel` | RAG 完整配置 |
| `SkillsUpdateRequest` | 技能更新请求 |

### 多部分表单类型（multipart FormData）

| 类型 | 说明 |
|------|------|
| `BodyChatWithFilesEndpointChatThreadIdWithFilesPost` | 聊天文件附件 |
| `BodyUploadFileEndpointApiFilesUploadPost` | 文件上传 |
| `BodyProcessUploadEndpointApiRagProcessUploadPost` | RAG 文件上传 |

### 端点数据类型

每个端点有对应的 `XxxData`、`XxxErrors`（422 ValidationError）、`XxxResponses` 类型。

---

## 客户端核心实现

### `createClient` 工厂函数

```
createClient(config)
  ├── 所有 HTTP 方法：get / post / put / delete / patch / head / options
  ├── SSE 方法：sse.get / sse.post / ... (用于流式请求)
  ├── request()：底层通用请求方法
  ├── buildUrl()：构建完整 URL
  └── interceptors：请求/响应/错误三阶段拦截器中间件
```

**请求流程：**
1. `beforeRequest`：合并配置 → 认证参数注入 → 参数校验 → body 序列化
2. 构造 `Request` 对象（URL + headers + body + method）
3. 请求拦截器（`interceptors.request`）
4. `fetch()` 执行
5. 响应拦截器（`interceptors.response`）
6. 解析响应体（根据 `Content-Type` 自动选 `json/blob/text/formData/stream`）
7. 错误拦截器（`interceptors.error`）

### SSE 客户端 (`core/serverSentEvents.gen.ts`)

`createSseClient()` 提供完整的 SSE 流式客户端：

- **事件解析**：解析 `data:` / `event:` / `id:` / `retry:` 字段
- **自动重连**：连接断开时自动重连
- **指数退避**：重连间隔按指数增长
- **Last-Event-ID**：传递最后收到的事件 ID

---

## 使用示例

```typescript
import {
  chatStreamChatThreadIdStreamPost,
  getInputCheckpointsCheckpointsThreadIdInputsGet,
  type ChatRequest,
  type CheckpointSummary,
} from '@/api/client'

// 流式聊天
const generator = chatStreamChatThreadIdStreamPost({
  path: { thread_id: 'xxx' },
  body: {
    messages: [{ role: 'user', content: '你好' }],
    rubric: undefined  // 可选：Loop Engineering 条件
  },
  onSseEvent: (event) => {
    console.log('SSE event:', event.type, event.data)
  }
})

// 获取检查点
const { data } = await getInputCheckpointsCheckpointsThreadIdInputsGet({
  path: { thread_id: 'xxx' },
  query: { limit: 200, offset: 0 }
})
if (data) {
  const checkpoints: CheckpointSummary[] = data.items
}
```
