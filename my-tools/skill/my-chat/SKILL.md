---
name: my-chat
description: Knowledge of the my-chat project (LangGraph AI Agent chat frontend built with Vue 3, 
  Composition API, Vite, SSE streaming). Covers architecture, data flow, components, 
  composables, API endpoints, and design decisions. Load this skill for any task involving 
  understanding, modifying, or extending the my-chat codebase.
---

# my-chat 项目架构索引

> **用途**：快速理解项目全貌，无需全量读取源码。
> **最后更新**：2026-06-18（分支叶子检查点传递/恢复 + branchMap 去重 + pickCheckpointFromCache 修复 + sidebar import 路径修复）
>
> **详细文档**：按需读取 `references/` 子文件：
> - [data-flows.md](./references/data-flows.md) — SSE 事件/线程切换/重试/分支/HITL/大纲 详细流程
> - [component-contracts.md](./references/component-contracts.md) — 所有组件 Props/Emits 完整契约
> - [conventions.md](./references/conventions.md) — 模块单例/三层分离/错误处理/审计原则
> - [extension-guide.md](./references/extension-guide.md) — 新增 SSE chunk/API/右侧栏 Tab/消息按钮

---

## 一、项目概要

| 项目 | 说明 |
|------|------|
| 名称 | my-chat |
| 类型 | LangGraph AI Agent 对话前端 |
| 框架 | **Vue 3** + Composition API + `<script setup lang="ts">` |
| 路由 | Vue Router 4（Hash History） |
| 构建 | Vite 8 |
| 渲染 | `marked` + `DOMPurify` |
| API | `@hey-api/openapi-ts` 自动生成 SDK |
| UI | 纯自定义 CSS，无第三方 UI 库 |
| 状态管理 | Composables 模式（无 Pinia/Vuex） |
| 通信 | SSE（Server-Sent Events）流式协议 |
| 后端 | `http://localhost:8000` |

---

## 二、目录结构

```
src/
├── main.ts                              # 入口
├── App.vue                              # 根组件：<router-view /> + <ToastContainer />
├── style.css                            # 全局样式（CSS Variables）
├── router/index.ts                      # [ / → redirect, /chat/:threadId → ChatLayout ]
├── api/
│   ├── chat.ts                          # 【核心类型】Message, StreamChunk, HITL
│   └── client/                          # OpenAPI 自动生成 SDK（勿手动修改）
└── modules/
    ├── layout/
    │   └── ChatLayout.vue               # 三栏布局编排：左侧栏 + ChatView + RightSidebar
    ├── sidebar/                         # 【右侧面板模块】
    │   ├── RightSidebar.vue             # 编排层：Tab栏 + 子组件组合（~130行）
    │   ├── ToolsTab.vue                 # 工具调用 Tab（流式/分组折叠）
    │   ├── OutlineTab.vue               # 大纲 Tab（IntersectionObserver）
    │   ├── DetailsTab.vue               # 详情 Tab 占位
    │   └── useSidebarResize.ts          # 拖拽调整宽度
    ├── chat/
    │   ├── core/
    │   │   ├── ChatView.vue             # 聊天视图容器
    │   │   ├── ChatHeader.vue           # 顶部导航栏
    │   │   ├── ChatInput.vue            # 输入框（文本 + 文件上传）
    │   │   ├── ChatMessages.vue         # 消息列表（~639行，纯展现，不拆分）
    │   │   ├── ChatReason.vue           # 推理过程折叠面板
    │   │   ├── useChatState.ts          # 纯响应式状态
    │   │   ├── useChatStream.ts         # SSE 流式编排层（组装 sse/ 子模块）
    │   │   ├── useChatController.ts     # 编排层（~489行，组装 state+stream+checkpoints）
    │   │   ├── useContentNav.ts         # 用户消息大纲导航 + 模块级共享
    │   │   └── sse/
    │   │       ├── sseChunkHandler.ts   # SSE chunk 解析与状态更新
    │   │       ├── sseRequests.ts       # 统一 SSE 请求发起（消除重复）
    │   │       └── resetStreamingState.ts # 流式状态重置（消除重复）
    │   ├── tools/
    │   │   ├── ToolCallCard.vue         # 工具调用卡片
    │   │   ├── ToolMessageCard.vue      # 工具返回卡片
    │   │   └── useToolMessages.ts       # 【全局单例】工具调用共享状态
    │   ├── checkpoints/
    │   │   └── useCheckpoints.ts        # 检查点池管理（replay/fork）
    │   └── approval/
    │       └── ApprovalCard.vue         # HITL 中断审批
    ├── threads/
    │   ├── ChatSidebar.vue              # 左侧线程列表
    │   └── useChatHistory.ts            # 线程 CRUD + localStorage
    ├── upload/
    │   ├── ContentBlocksPreview.vue     # 上传文件预览
    │   └── useFileUpload.ts             # 文件上传/拖拽/粘贴
    └── shared/
        ├── AgentLogo.vue                # Agent Logo SVG
        ├── Markdown.vue                 # marked + DOMPurify 安全渲染
        ├── ScrollToBottom.vue           # 滚动到底部按钮
        ├── ToastContainer.vue           # Toast 通知容器
        ├── useToast.ts                  # 【全局单例】发布订阅 Toast
        └── useLogger.ts                 # 日志工具
```

---

## 三、组件层级树

```
App.vue
  ├── router-view
  │   └── ChatLayout.vue                       [路由：/chat/:threadId]
  │       ├── ChatSidebar.vue                  [左侧：线程列表]
  │       ├── ChatView.vue                     [主内容：聊天区域]
  │       │   ├── ChatHeader.vue               [顶部：切换侧边栏 + 新建]
  │       │   ├── ChatMessages.vue             [消息列表核心]
  │       │   │   ├── ChatReason.vue           [推理过程折叠面板]
  │       │   │   └── Markdown.vue             [Markdown 渲染]
  │       │   ├── ChatInput.vue                [底部：输入框 + 上传]
  │       │   │   └── ContentBlocksPreview.vue [上传文件预览]
  │       │   ├── ApprovalCard.vue             [HITL 审批覆盖层]
  │       │   └── ScrollToBottom.vue           [滚动到底部]
  │       └── RightSidebar.vue                 [右侧详情面板]
  │           ├── ToolsTab.vue                  [工具调用]
  │           │   ├── ToolCallCard.vue
  │           │   └── ToolMessageCard.vue
  │           ├── OutlineTab.vue                [大纲导航]
  │           └── DetailsTab.vue                [详情占位]
  └── ToastContainer.vue                       [全局 Toast]
```

---

## 四、核心类型定义

```typescript
// ===== src/api/chat.ts =====
type MessageRole = 'user' | 'assistant' | 'system' | 'tool'

interface ContentBlock {
  type: 'image' | 'file'
  mimeType: string; data: string  // base64
  metadata: { name?: string; filename?: string }
}

interface ToolCall {
  id: string; name: string
  args: Record<string, unknown>
  result?: string
}

interface Message {
  role: MessageRole; content: string
  reasonContent?: string; contentBlocks?: ContentBlock[]
  toolCalls?: ToolCall[]; interrupt?: boolean
  _checkpointId?: string; _parentCheckpointId?: string | null
  _leafCheckpointId?: string | null; _key?: string
}

interface StreamChunk {
  type: 'text' | 'reasoning' | 'tool_call' | 'tool_result'
       | 'done' | 'error' | 'interrupt' | 'checkpoint' | 'user'
  content?: string; tool_call_id?: string
  tool_call_name?: string; tool_call_args?: string; done: boolean
}

// HITL 审批
interface HITLRequest { action_requests: ActionRequest[]; review_configs: ReviewConfig[] }
interface HITLResponse { decisions: HITLDecision[] }
```

---

## 五、核心数据流

### 5.1 发送消息 → 流式响应

```
ChatInput.vue → emit('send', content, contentBlocks)
  │
  └── ChatView.vue → useChatController.sendMessage()
        └── useChatStream.sendMessage()
             ├── 追加 user msg 到 messages[]
             ├── 重置流式状态（resetStreamingState）
             ├── 查找最后一条 assistant 消息的 _leafCheckpointId（分支场景）
             │     └── 若存在 → 传入 ChatRequest.checkpoint_id，确保后端沿当前分支继续
             ├── 构建 ChatRequest（仅含新 user 消息 + 可选 checkpoint_id）
             └── doSseRequest() → POST /chat/{id}/stream (SSE)
                  └── 事件循环 → handleSseChunk(chunk)
```

> 详细 SSE 事件处理、线程切换、Replay/Fork/Branch Switch/HITL/大纲流程 → [references/data-flows.md](./references/data-flows.md)

---

## 六、状态管理全景

### 6.1 Composable 分层

```
ChatLayout.vue
  ├── useChatHistory() ── 线程列表 & activeThreadId
  ├── useToolMessages() ─ 右侧栏共享状态
  │
  └── ChatView.vue
        └── useChatController(threadId, callbacks)     ← 编排层
              ├── useChatState() . 状态层
              ├── useChatStream(state, tid) . 通信层（组装 sse/）
              ├── useCheckpoints(tid) . 检查点
              └── useContentNav(msgs, sc) . 大纲同步

RightSidebar.vue
  ├── useSidebarResize() ── 拖拽调整宽度
  ├── useToolMessages() ── 工具调用数据
  └── useOutlineItems() ── 大纲数据
```

### 6.2 Composable 职责表

| Composable | 文件 | 范围 | 关键字段 |
|------------|------|:--:|----------|
| `useChatState()` | `chat/core/useChatState.ts` | 实例 | `messages, loading, streamingContent, streamingReasoning, pendingToolCalls, showInterrupt.` |
| `useChatStream()` | `chat/core/useChatStream.ts` | 实例 | `isReplayMode, abortController` |
| `useChatController()` | `chat/core/useChatController.ts` | 实例 | `localError, retryingMessageIndex, forkingMessageIndex, forkEditingIndex, branchMap, showScrollButton.` |
| `useChatHistory()` | `threads/useChatHistory.ts` | 实例 | `threads, activeThreadId` |
| `useCheckpoints()` | `chat/checkpoints/useCheckpoints.ts` | 实例 | `checkpoints, loaded` |
| `useToolMessages()` | `chat/tools/useToolMessages.ts` | **全局单例** | `_toolCallGroups, _streamingToolCalls` |
| `useFileUpload()` | `upload/useFileUpload.ts` | 实例 | `contentBlocks, dragOver` |
| `useToast()` | `shared/useToast.ts` | **全局单例** | 模块顶级 `toasts[]` + 发布订阅 |
| `useContentNav()` | `chat/core/useContentNav.ts` | 实例→全局 | `navItems, _outlineItems` |
| `useOutlineItems()` | `chat/core/useContentNav.ts` | **全局单例** | `outlineItems`（只读） |
| `useSidebarResize()` | `sidebar/useSidebarResize.ts` | 实例 | `sidebarWidth, isResizing` |

### 6.3 localStorage 持久化

| Key | 内容 | 位置 |
|-----|------|------|
| `chat_active_thread_id` | 当前活跃线程 UUID | `useChatHistory` |
| `chat_msgs_{threadId}` | 消息数组 JSON（含 checkpoint） | `cacheThreadMessages/loadCachedMessages` |
| `chat_branch_leaf_{threadId}` | 当前分支叶子检查点 ID | `useChatController` |

---

## 七、API 端点

| 端点 | 方法 | 协议 | 说明 | 调用 |
|------|------|------|------|------|
| `/chat/{id}/stream` | POST | **SSE** | 发送消息流式返回（分支场景携带 `checkpoint_id`） | `useChatStream` |
| `/chat/{id}/resume` | POST | **SSE** | 恢复中断对话 | `useChatStream.resumeChat` |
| `/chat/{id}/get-messages-history` | GET | JSON | 获取历史（支持 `?checkpoint_id=leaf`） | `loadThreadHistory` |
| `/chat/{id}/delete-messages-history` | DELETE | JSON | 删除会话历史 | `useChatHistory.deleteThread` |
| `/threads` | GET | JSON | 列出所有线程 | `useChatHistory.loadThreads` |
| `/checkpoints/{id}/inputs` | GET | JSON | 输入检查点列表 | `useCheckpoints.loadCheckpoints` |
| `/checkpoints/{id}/replay` | POST | **SSE** | 检查点重放 | `useChatStream.doReplayRequest` |
| `/checkpoints/{id}/fork` | POST | **SSE** | 检查点分叉 | `useChatStream.doForkRequest` |

---

## 八、SSE 通信机制

### 8.1 子模块结构（`core/sse/`）

| 子模块 | 职责 |
|--------|------|
| `sseRequests.ts` | 统一 `doSseRequest()`，消除 stream/replay/fork 三处重复 |
| `sseChunkHandler.ts` | `createSseChunkHandler()` chunk 解析 + `parseToolArgs()` |
| `resetStreamingState.ts` | 流式状态重置，消除 4 处重复 |

### 8.2 底层实现

```
client.sse.post({url, path, body, signal, onSseEvent, onSseError})
  ├── fetch + ReadableStream + TextDecoderStream
  ├── 自动重连：指数退避（max 30s）
  ├── AbortController 请求取消
  └── 返回 AsyncGenerator<{event?, data, id?}>
```

### 8.3 四类 SSE 端点差异

| 端点 | 请求体 | 特殊处理 |
|------|--------|----------|
| `/stream` | `{messages: [{role:'user', content}], checkpoint_id?: string}` | 仅发送新 user 消息；分支场景携带最后 assistant 的 _leafCheckpointId |
| `/replay` | `{thread_id, checkpoint_id, messages?}` | replay 模式 + 可选注入 messages 触发再生 |
| `/fork` | `{thread_id, checkpoint_id, values}` | replay 模式 + 修改 values |
| `/resume` | `{decisions: HITLDecision[]}` | 首次数据时隐藏中断卡片 |

---

## 九、路由与初始化

```typescript
// router/index.ts
const routes = [
  { path: '/', redirect: () => /* localStorage 恢复或新建 UUID */ },
  { path: '/chat/:threadId', component: () => import('@/modules/layout/ChatLayout.vue') },
]
```

初始化链路：
```
main.ts → createApp → mount
  └── 路由 / → redirect → /chat/{uuid}
        └── ChatLayout.vue
              ├── useChatHistory() → activeThreadId 从 route.params 初始化
              └── ChatView.vue → useChatController(threadIdRef)
                    └── watch(threadId, immediate: true) → loadThreadHistory(newId)
```

---

## 十、关键设计决策

### 10.1 为什么只发送新 user 消息？
LangGraph checkpoint 已维护完整历史。全量发送会导致 `_messages_delta_reducer` 因缺 ID 重复追加。

### 10.2 检查点三层绑定
1. **SSE 实时**（`handleSseChunk` type='checkpoint'）→ 最准确
   - `kind='input'`：绑定 `_checkpointId` + `_parentCheckpointId` 到 user 消息
   - `kind='leaf'`：绑定 `_leafCheckpointId` 到 assistant 消息
2. **localStorage 恢复**（`pickCheckpointFromCache`）→ 刷新恢复
   - `pickFromCandidate` 按位置+角色+内容匹配，user 消息恢复 `_checkpointId/_parentCheckpointId`，assistant 消息恢复 `_leafCheckpointId`（不再要求 `_checkpointId` 存在）
3. **/inputs 兜底**（`resolveCheckpointForMessage`）→ 缓存缺失，按4级匹配策略补全

### 10.3 分支对话继续：sendMessage 传递 checkpoint_id
- 发送消息前查找最后一条 assistant 消息的 `_leafCheckpointId`
- 若存在 → 传入 `ChatRequest.checkpoint_id`，后端 `config["configurable"]["checkpoint_id"]` 设置后 LangGraph 从该检查点继续
- 无分支时 `_leafCheckpointId` 也可能存在（SSE 总会发 kind='leaf'），传入无副作用
- 解决 fork 后发送新消息走到错误分支的问题

### 10.4 叶子检查点恢复链路（页面刷新场景）
- `_leafCheckpointId` 是前端字段，后端 `get-messages-history` 不返回
- 三层恢复：
  1. `pickCheckpointFromCache` 从 localStorage 缓存恢复（位置+内容匹配）
  2. `loadBranchLeaf()` 读取持久化的 `chat_branch_leaf_{threadId}`
  3. `switchToBranch` 中显式设置 `_leafCheckpointId = targetLeafCheckpointId` 到最后一条 assistant
- 刷新时 `watch(threadId)` 在加载历史后用 `cachedLeaf` 兜底恢复缺失的 `_leafCheckpointId`

### 10.5 branchMap 去重：同一父检查点只在最后一条消息显示分支
- 同一 `_parentCheckpointId` 下多条连续 user 消息（如"你好"→"我是小明"）都在同一分支链上
- `branchMap` 按 `_parentCheckpointId` 去重：`lastByParent.set(parentCid, msgIdx)` 只保留最后出现的消息
- 额外要求 `msg._checkpointId` 存在：排除 fork 分支消息（replay 模式下其 checkpoint 被 SKIP 绑定）
- 保证分支按钮只出现在实际分叉点（如"我是小明"），不会出现在前置消息（如"你好"）

### 10.6 模块职责原则
- **单向依赖**：`shared/api` → features → controller → layout
- **ChatMessages.vue 不拆分**：纯展现，12 props 直传优于 props-drilling
- **useChatController 不按功能拆分**：重试/分支/切换共用依赖链
- **全局单例**仅限 `useToolMessages` / `useToast` / `useOutlineItems`

---

## 十一、文件关联速查

| 要修改的功能 | 涉及文件 |
|-------------|---------|
| SSE chunk 解析 | `chat/core/sse/sseChunkHandler.ts` |
| SSE 请求发起 | `chat/core/sse/sseRequests.ts` |
| 流式编排 | `chat/core/useChatStream.ts` + `useChatState.ts` |
| 发送消息/重试/分支 | `chat/core/useChatController.ts` |
| 检查点管理 | `chat/checkpoints/useCheckpoints.ts` |
| 线程管理 | `threads/useChatHistory.ts` |
| 工具调用展示 | `chat/tools/useToolMessages.ts` → `sidebar/ToolsTab.vue` |
| 大纲导航 | `chat/core/useContentNav.ts` → `sidebar/OutlineTab.vue` |
| 右侧面板 | `sidebar/RightSidebar.vue` + `useSidebarResize.ts` |
| HITL 审批 | `chat/approval/ApprovalCard.vue` |
| 消息列表 UI | `chat/core/ChatMessages.vue` |
| 类型定义 | `api/chat.ts` |
| 全局通知 | `shared/useToast.ts` |

---

## 十二、项目运行

```bash
cd f:/index_rag/API-agent/my-chat
npm install
npm run dev        # 开发服务器
npm run build      # vue-tsc + vite build
npm run type-check # 仅类型检查
```

**依赖**：vue ^3.5, vue-router ^4.6, marked ^18, dompurify ^3.4, vite ^8, typescript ~5.8

**CSS 变量主题**：`--bg, --text, --text-h, --border, --accent(#aa3bff), --code-bg`

---

## 十三、扩展指南

> 详细步骤见 [references/extension-guide.md](./references/extension-guide.md)

| 需求 | 关键步骤 |
|------|---------|
| 新增 SSE chunk 类型 | `api/chat.ts` 加类型 → `sseChunkHandler.ts` 加分支 → `useChatState.ts` 加状态 → `ChatMessages.vue` 渲染 |
| 新增 API 端点 | 后端更新 OpenAPI → 重新生成 SDK → Composable 调用 |
| 新增右侧栏 Tab | `sidebar/` 下新建 `NewTab.vue` → `RightSidebar.vue` 注册 |
| 新增消息操作按钮 | `ChatMessages.vue` 加按钮 → emit → `ChatView` → `useChatController` |
