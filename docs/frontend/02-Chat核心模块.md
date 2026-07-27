# Chat 核心模块

> 本文档描述聊天核心模块的架构，这是前端最复杂的模块（17 个文件），涵盖 SSE 流式通信、检查点分支导航、HITL 审批、工具调用可视化等功能。

---

## 模块架构

```
chat/
├── core/                          # 核心层
│   ├── useChatController.ts       # 编排器（组合 state + stream + checkpoints）
│   ├── useChatState.ts            # 纯响应式状态管理
│   ├── useChatStream.ts           # SSE 流式通信编排
│   ├── useContentNav.ts           # 消息大纲导航
│   ├── ChatView.vue               # 顶层视图组件
│   ├── ChatHeader.vue             # 头部工具栏
│   ├── ChatMessages.vue           # 消息列表渲染
│   ├── ChatInput.vue              # 输入框 + Loop rubric
│   ├── ChatReason.vue             # 推理过程可折叠展示
│   └── sse/                       # SSE 子层
│       ├── sseChunkHandler.ts     # 10 种 chunk 事件处理器
│       ├── sseRequests.ts         # SSE 请求封装
│       └── resetStreamingState.ts # 状态重置函数
├── approval/                      # 审批层
│   └── ApprovalCard.vue           # HITL 中断审批覆盖层
├── checkpoints/                   # 检查点层
│   └── useCheckpoints.ts          # 检查点池管理与分支导航
└── tools/                         # 工具层
    ├── useToolMessages.ts         # 工具调用共享状态
    ├── ToolCallCard.vue           # 工具调用卡片
    └── ToolMessageCard.vue        # 工具消息卡片
```

### 组件层级

```
ChatView.vue (顶层视图)
  ├── ChatHeader.vue              (工具栏 + Agent Logo)
  ├── ChatMessages.vue            (消息列表)
  │     └── ChatReason.vue        (推理折叠卡片)
  ├── ChatInput.vue               (输入框 + Loop rubric 面板)
  ├── .chat-resize-handle         (拖拽缩放手柄，hover 显示)
  └── ApprovalCard.vue            (覆盖层，interrupt 时展示)
```

---

## useChatController（核心编排器）

`useChatController` 是整个聊天模块的"大脑"，它组合了三个核心子模块：

```
useChatController(threadId, callbacks)
  ├── useChatState()            → 纯响应式状态
  ├── useChatStream(state)      → SSE 流式通信
  └── useCheckpoints(threadId)  → 检查点池管理
```

### 回调接口

```typescript
interface ChatControllerCallbacks {
  createThread: () => void
  chatStarted: (started: boolean) => void
  updateTitle: (threadId: string, title: string) => void
}
```

注意：侧边栏/文件面板/右侧栏的切换事件由 `ChatView.vue` 直接通过 emit 传递，不经过 controller。

### 核心职责

| 职责 | 实现方式 |
|------|----------|
| **消息持久化** | `watch(messages)` → `cacheThreadMessages()` 存入 localStorage → 同时异步进入 `checkpoints.loadCheckpoints()` 预加载 inputs 池 |
| **线程切换** | `watch(threadId)` → 取消请求 → 清空流式状态 → `checkpoints.reset()` → `loadThreadHistory()` |
| **刷新恢复** | 历史加载后，优先用 ID（`_msgId`）绑定检查点；无 ID 时按内容匹配兜底 → 补绑 `_leafCheckpointId` 到最后的 assistant 消息 |
| **自动标题** | 取第一条 user 消息前 50 字符作为线程标题（`titleUpdated` 标记防止重复） |
| **发送消息** | `sendMessage()` → 无 threadId 先 `createThread()` → `streamSend()` |
| **重试（Retry）** | `retryUserMessage(index)` → 优先用 `_parentCheckpointId`（父检查点）+ 注入 user 消息触发重新生成；父为 null 时回退到 `_checkpointId` |
| **分支（Fork）** | 三阶段：`startForkEdit()` → 编辑草稿 → `submitForkEdit()` → 用 `_parentCheckpointId` 调用 `forkFromCheckpoint()`；内容未变则拦截 |
| **分支切换（Switch）** | `switchToBranch(targetLeafCid)` → 加载目标分支完整历史 → 补绑检查点 → 绑定叶子 → 持久化到 localStorage |
| **branchMap** | computed，按 `parentCheckpointId` 去重：同一 parent 下多条连续 user 消息只在最后一条显示分支按钮 |

### 暴露的公开接口

```typescript
const ctrl = useChatController(threadId, callbacks)

// 返回 —— 直接暴露原始响应式字段和函数，不需要 .state 中间层
ctrl.messages          // Ref<Message[]>
ctrl.loading           // Ref<boolean>
ctrl.historyLoading    // Ref<boolean>
ctrl.error             // Ref<string | null>
ctrl.localError         // Ref<string | null>（可关闭的错误）
ctrl.clearError()       // 清除本地错误
ctrl.streamingContent  // Ref<string>
ctrl.streamingReasoning// Ref<string>
ctrl.firstTokenReceived// Ref<boolean>
ctrl.showInterrupt     // Ref<boolean>
ctrl.interruptData     // Ref<unknown>
// 操作
ctrl.sendMessage(content, contentBlocks?, rawFiles?, rubric?)
ctrl.cancelRequest()    // 取消当前请求 + 打包未完成内容
ctrl.retryUserMessage(index) // 重试指定消息
ctrl.startForkEdit(index)    // 开始分支编辑
ctrl.cancelForkEdit()        // 取消分支编辑
ctrl.submitForkEdit({index, content}) // 提交分支编辑
ctrl.switchToBranch(msgIndex, leafCid) // 切换分支
ctrl.resumeChat(decisions)   // 恢复中断对话
// 分支状态
ctrl.retryingMessageIndex  // 当前重试中的消息索引
ctrl.forkingMessageIndex   // 当前分支中的消息索引
ctrl.forkEditingIndex      // 正在编辑的 fork 消息索引
ctrl.forkEditingDraft      // fork 编辑草稿
ctrl.branchSwitchingIndex  // 当前分支切换中的消息索引
ctrl.branchMap              // Map<msgIndex, { branches, currentIndex }>
ctrl.persistBranchLeaf(leafCid)
ctrl.loadBranchLeaf() → string | null
// 滚动
ctrl.showScrollButton      // 是否显示滚动到底部按钮
ctrl.handleScrollToBottom(messagesRef)
ctrl.onMessagesScroll(event)
```

---

## useChatState（状态管理）

纯响应式状态，不涉及任何 API 调用。

### 状态字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `messages` | `Ref<Message[]>` | 消息列表（初始含欢迎消息） |
| `loading` | `Ref<boolean>` | 是否正在流式通信中 |
| `historyLoading` | `Ref<boolean>` | 是否正在加载历史 |
| `error` | `Ref<string \| null>` | 错误信息 |
| `streamingContent` | `Ref<string>` | 实时累积的流式文本 |
| `streamingReasoning` | `Ref<string>` | 实时累积的推理内容 |
| `firstTokenReceived` | `Ref<boolean>` | 首个 token 是否已到达 |
| `pendingToolCalls` | `Ref<Map<string, ToolCall>>` | 流式中的工具调用（key=tool_call_id） |
| `showInterrupt` | `Ref<boolean>` | 是否显示中断 UI |
| `interruptData` | `Ref<unknown>` | 中断负载数据 |

### ensureMessageKey()

为每条消息生成唯一的 `_key`（格式：`{role}-{uuid8}`），供 Vue `v-for` key 使用，确保列表渲染性能。

### DO_NOT_RENDER_ID_PREFIX

```
DO_NOT_RENDER_ID_PREFIX = 'do-not-render-'
```

用于标记不应渲染的消息（如系统内部消息）。

---

## useChatStream（SSE 流式通信）

### 构造函数

```typescript
useChatStream(state, threadId, options?)
// options: { onReplayStart?: () => void, onReplayEnd?: () => void }
```

`onReplayStart`/`onReplayEnd` 用于重试/分支操作的开始和结束回调（目前 reserved，未在 controller 层使用）。

### 公开方法

| 方法 | 说明 | 后端端点 |
|------|------|------|
| `sendMessage()` | 发送用户消息 | `/chat/{thread_id}/stream` 或 `.../with-files/stream` |
| `cancelRequest()` | 取消请求 + 打包未完成内容 | — |
| `resumeChat()` | 恢复 HITL 中断 | `/chat/{thread_id}/resume` |
| `replayCheckpoint()` | 从检查点重放（重试），可选注入 messages | `/checkpoints/{thread_id}/replay` |
| `forkFromCheckpoint()` | 从检查点分叉（分支） | `/checkpoints/{thread_id}/fork` |

### 关键实现细节

**发送消息时**：自动查找最后一条 assistant 消息的 `_leafCheckpointId`，作为 `checkpoint_id` 传递，确保新消息沿当前分支继续：

```
sendMessage()
  → 构建消息（user role + contentBlocks + rawFiles）
  → 查找最后 assistant 消息的 _leafCheckpointId
  → resetStreamingState(state) + 创建 AbortController
  → 有附件 → doSseFormDataRequest (multipart, body 含 messages + checkpoint_id)
  → 无附件 → doSseRequest (JSON, body 含 messages + checkpoint_id + rubric)
```

**取消请求时**：不仅 `abort()`，还会将 `streamingContent` + `streamingReasoning` + `pendingToolCalls` 打包为一条 assistant 消息（含 `interrupt` 标记），然后调用 `applyPendingLeaf()` 补绑 LEAF 检查点。

**恢复中断时** (`resumeChat`)：只设置 `loading=true`，保持 `showInterrupt=true`（等待首个 SSE 数据到达时才关闭），手动清除流式状态字段（不调用 `resetStreamingState`）。通过内置的 `client.sse.post()` 直接发起 SSE 请求。

**重放/分叉公共逻辑** (`enterReplayMode`)：校验 threadId → 检查 loading → 设 `isReplayMode=true` → 调 `onReplayStart` → 重置流式状态 → 创建 AbortController。

---

## SSE Chunk 处理

### 请求层 (`sseRequests.ts`)

两个统一函数：

```typescript
// JSON body → SSE
doSseRequest(url, body, onSseEvent): AsyncGenerator

// FormData/multipart → SSE
doSseFormDataRequest(url, formData, onSseEvent): AsyncGenerator
```

两者都返回 `AsyncGenerator`，在 `onSseEvent` 回调中处理每个事件。

### 事件处理器 (`sseChunkHandler.ts`)

`createSseChunkHandler()` 返回 `handleSseChunk` 和 `handleSseError`，处理 **10 种** chunk 事件：

| 事件 | 处理逻辑 |
|------|----------|
| **`checkpoint`** | 解析 `{checkpoint_id, parent_checkpoint_id, kind}`。`kind='input'` 绑定到最近的 user 消息（`_checkpointId` + `_parentCheckpointId`）；`kind='leaf'` 先尝试立即绑定到最新 assistant，同时暂存 `pendingLeafCheckpointId` 以备 done 后补绑 |
| **`reasoning`** | 追加到 `streamingReasoning`，首个非 checkpoint chunk 触发 `firstTokenReceived=true` |
| **`text`** | 追加到 `streamingContent` |
| **`tool_call`** | 按 `tool_call_id` 存入 `pendingToolCalls` Map，参数经 `parseToolArgs()` 安全解析；每次更新后同步到右侧栏（`syncStreamingTools()`） |
| **`tool_result`** | 更新对应 tool_call 的 `result` 字段，无对应项时创建新条目（id 缺失时自动生成 `tool_result_{timestamp}`） |
| **`interrupt`** | 设 `loading=false`、`showInterrupt=true`，解析 `interruptData`（优先 JSON 解析，失败回退原始字符串） |
| **`user`** | 直接忽略（return） |
| **`rubric`** | Loop Engineering 评估事件：根据 `type`（`rubric_evaluation_start/end`）和 `result`（`satisfied/needs_revision/failed/max_iterations_reached/grader_error`）显示不同级别 toast |
| **`done`** | 将 `streamingContent` + `streamingReasoning` + `pendingToolCalls` 打包为 assistant 消息 → `applyPendingLeaf()` 补绑 LEAF → 清理流式状态 → `isReplayMode=false` |
| **`error`** | 设置 error 状态，清理流式状态 → `isReplayMode=false` → `onReplayEnd?.()` |

### parseToolArgs()

```typescript
// 安全解析工具参数，容错处理
parseToolArgs(rawArgs, fallback?)
  → rawArgs 为空              → fallback || {}
  → JSON.parse 成功 + object   → 原样返回（非数组 object）
  → JSON.parse 成功 + array    → { items: [...] }
  → JSON.parse 成功 + 标量     → { value: scalar }
  → JSON.parse 失败            → { raw: rawArgs }
```

### applyPendingLeaf()

解决 SSE 事件乱序问题：LEAF checkpoint 可能在 `done` 之前到达，暂存 ID；`done` 后补绑到最新的 assistant 消息。

### 流式状态重置 (`resetStreamingState.ts`)

被 `sendMessage`、`resumeChat`、`replayCheckpoint`、`forkFromCheckpoint` 共享调用：

```typescript
loading = true
error = null
streamingContent = ''
streamingReasoning = ''
firstTokenReceived = false
pendingToolCalls = new Map()
showInterrupt = false
interruptData = null
```

---

## useCheckpoints（检查点管理）

### 数据源

```
GET /checkpoints/{thread_id}/inputs?limit=200&offset=0
```

### 检查点信息提取

| 方法 | 说明 |
|------|------|
| `extractCheckpointId(summary)` | 优先通过 `config.configurable.checkpoint_id` 获取；失败时用正则 `/checkpoint_id"\s*:\s*"([^"]+)"/` 兜底 |
| `extractCheckpointNs(summary)` | 从 `config.configurable.checkpoint_ns` 提取，无值返回空字符串 |

### 绑定策略（双级优先级）

**一级：ID 精确匹配**（权威 O(1) 绑定）
`buildIdMap()` 构建 `trigger_message_id → {checkpointId, parentCheckpointId}` 字典。通过消息的 `_msgId`（LangChain 消息 ID）直接查找，跳过内容匹配。

**二级：内容模糊匹配**（旧消息兜底）
`matchByContent()` 仅在没有 `_msgId` 的旧消息时使用，四级优先级：
1. normalize 后**完全相等**
2. 消息以 **input_preview** 开头（preview 被截断）
3. **input_preview** 以消息开头（消息被截断）
4. 双向包含兜底

`resolveCheckpoint(msgId, userMessage)` 综合以上两级：先查 idMap，未命中时回退内容匹配。

### 核心概念

```
消息链:  user → assistant → user → assistant → ...
          │        │           │        │
    _checkpointId    │    _checkpointId    │
_parentCheckpointId  │ _parentCheckpointId │
               _leafCheckpointId      _leafCheckpointId
```

| 字段 | 绑定消息 | 用途 |
|------|----------|------|
| `_checkpointId` | user 消息 | 用于 retry（从该检查点重放） |
| `_parentCheckpointId` | user 消息 | 用于 fork（从父状态分叉）；根 input 的父检查点为 `null`，也绑定以标识无前驱 |
| `_leafCheckpointId` | assistant 消息 | 用于 sendMessage（确定当前分支继续点） |

### 兄弟分支

`getSiblingBranches(parentCheckpointId)` 按 `parent_checkpoint_id` 分组：
- 过滤掉 `source === 'fork'` 的检查点（排除 fork 来源）
- 排序：`source === 'input'` 的优先排在前面
- 仅当兄弟数 > 1 时返回列表，UI 才显示分支切换器

### 分支叶子持久化

```typescript
localStorage key: `chat_branch_leaf_{threadId}`
```

SSE 流结束后自动持久化，线程切换时恢复，确保刷新后回到同一分支。

### branchMap（computed）

按 `parentCheckpointId` 去重：同一 parent 下的多条连续 user 消息，只在最后一条（实际分叉点）显示分支按钮。前面的消息是顺序执行链。

### 重置

`reset()` 清空 checkpoints、loaded、lastMatched、error 状态，在线程切换时调用。

---

## useContentNav（消息大纲导航）

### 架构

采用**模块级共享状态**模式，避免 prop drilling：

```typescript
// 模块级 shallowRef，供外部组件（如 RightSidebar）直接读取
const _outlineItems = shallowRef<readonly NavItem[]>([])

// 导出读取钩子
export function useOutlineItems() {
  return { outlineItems: _outlineItems }
}
```

`useContentNav(messages, streamingContent)` 内部通过 `watch(navItems, ...)` 将 computed 结果同步到 `_outlineItems`。

### 功能

| 功能 | 说明 |
|------|------|
| **大纲提取** | computed 从 messages 中提取所有 role='user' 的消息，生成 `{ messageIndex, preview, anchorId }` 条目 |
| **内容截断** | 消息内容超过 40 字符截断为前 37 字符 + "…" |
| **导航跳转** | `scrollToNavItem(anchorId)` → `document.getElementById` + `scrollIntoView` |
| **共享状态** | 通过 `useOutlineItems()` 同步到模块级 `_outlineItems` |

---

## 工具调用可视化

### 数据流

```
SSE tool_call/tool_result chunk
  → sseChunkHandler → state.pendingToolCalls (Map)
  → syncStreamingTools() → useToolMessages._streamingToolCalls
  → RightSidebar → ToolsTab 实时展示

done 事件
  → pendingToolCalls 打包到 assistant.toolCalls
  → syncToolCalls() → 遍历 messages，分组到 toolCallGroups / toolMessages
  → RightSidebar → ToolsTab 展示历史
```

### 三个组件

| 组件 | 说明 |
|------|------|
| `ToolCallCard.vue` | 展示单个 ToolCall（可折叠，紫色左边框，显示参数 JSON 和结果） |
| `ToolMessageCard.vue` | 展示 tool 角色消息的返回内容（绿色左边框） |
| `ToolsTab.vue` | 右侧栏消费 `useToolMessages()` 状态，分组展示 |

### useToolMessages 共享状态

| 状态/方法 | 说明 |
|------|------|
| `toolCallGroups` | 按消息分组的 assistant toolCalls（模块级 `ref`，跨组件共享） |
| `toolMessages` | tool 角色消息条目列表（就近匹配 assistant toolCalls 的 name/id） |
| `streamingToolCalls` | 流式期间的实时工具调用列表 |
| `toolCallCount` | 工具调用总数（assistant toolCalls + tool 消息 + 流式） |
| `shouldAutoOpenSidebar` | 流式工具调用到来时自动设为 `true`（watcher 监听 `streamingToolCalls`） |
| `syncToolCalls(messages)` | 从完整消息列表中提取 toolCalls 分组和 tool 消息条目 |
| `setStreamingToolCalls(calls)` | SSE 收到 tool_call/tool_result 时更新实时列表 |
| `clearStreamingToolCalls()` | 流结束时清空实时列表 |
| `consumeAutoOpenSidebar()` | 消费自动展开信号（调用后重置为 false，返回值指示是否应展开） |

---

## HITL 审批流程

### 触发路径

```
后端 interrupt chunk
  → sseChunkHandler: loading=false, showInterrupt=true, 解析 interruptData
  → ChatView.parsedInterrupt: HITLRequest
  → 渲染 ApprovalCard.vue 覆盖层（overlay + backdrop-filter 模糊背景）
```

### ApprovalCard 功能

- 展示 `action_requests` 列表（每项含 name、description、args）
- 三种决策：**批准 (approve)** / **拒绝 (reject)** / **编辑 (edit)**
- `review_configs` 通过 `allowed_decisions` 限制每项可选决策
- 拒绝时可填写原因（`message`）；编辑时可修改 JSON 参数（`edited_action`）
- "全部批准"快捷按钮
- 提交 → `ctrl.resumeChat(HITLResponse)` → `POST /chat/{thread_id}/resume`（保持 `showInterrupt=true` 直到首个 SSE 数据到达）
- 取消 → 直接关闭 `showInterrupt=false`，`interruptData=null`

---

## 分支导航 UI

### 重试按钮

每条 user 消息旁显示"重试"按钮，点击调用 `retryUserMessage(index)`：
- 使用 `_parentCheckpointId` 或 `_checkpointId` 调用 `replayCheckpoint()`
- 从父状态重新执行，相当于"换一种回答"

### Fork 内联编辑器

点击"分叉"按钮 → `startForkEdit(index)`：
- 消息内容变为可编辑 textarea
- 修改后点击"发送" → `submitForkEdit(index)` → `forkFromCheckpoint()`
- 或点击"取消"放弃编辑

### 分支切换器 (`.branch-switcher`)

多分支消息显示 `◀ 分支 2/5 ▶` 导航：
- 点击左右箭头切换分支
- 自动加载目标分支的完整历史
- 补全 checkpoint 绑定

---

## 关键组件

### ChatView.vue

顶层视图，组合所有子组件，桥接 props/emit 到 controller：

**Props**：`threadId`、`chatStarted`、`sidebarOpen`、`filePanelOpen`、`rightSidebarOpen`

**Emits**：`createThread`、`toggleSidebar`、`toggleFilePanel`、`toggleRightSidebar`、`chatStarted`、`updateTitle`

```html
<ChatHeader ... />
<ChatMessages ... />
<ChatInput ... />
<ApprovalCard v-if="showInterrupt && parsedInterrupt" ... />
<div class="chat-resize-handle" />  <!-- 拖拽缩放手柄，仅消息区可见 -->
```

**computed**：
- `parsedInterrupt`：将 `interruptData` 解析为 `HITLRequest`，失败返回 null
- 大纲通过 `useContentNav(ctrl.messages, ctrl.streamingContent)` 同步到模块级共享状态（供 RightSidebar 读取）

**对话宽度自由缩放**：

ChatView 通过注入 CSS 变量 `--chat-max-width` 控制消息列表和输入框的最大宽度，并在右侧边缘提供拖拽手柄：

| 状态/字段 | 说明 |
|-----------|------|
| `chatMaxWidth` (ref) | 当前宽度值（如 `"48rem"`），从 localStorage 恢复 |
| `isDragging` (ref) | 是否正在拖拽中 |
| `startDrag()` | mousedown 时注册全局 mousemove/mouseup 监听 |
| `onDrag()` | 按鼠标距 `.chat-view` 左边缘距离计算新宽度（范围 24rem ~ 容器宽度） |
| `stopDrag()` | 移除全局监听，将宽度写入 `localStorage`（key: `chat_max_width`） |

拖拽手柄默认透明隐藏，hover `.chat-content` 时显示紫色竖条，拖拽中高亮放大。`ChatMessages.vue`、`ChatInput.vue` 的 `.chat-messages` / `.chat-input` 通过 `max-width: var(--chat-max-width, 48rem)` 响应宽度变化。`ChatHeader` 保持全宽不跟随缩放。

### ChatHeader.vue

双模式：
- **空白状态**：侧边栏切换、文件面板切换、**RAG 向量库管理**、设置、右侧详情面板切换
- **聊天中**：完整导航栏 + AgentLogo + "Agent Chat" 标题（点击可新建对话）+ 新建对话按钮（+ 图标），始终保持全宽

### ChatInput.vue

**Props**：仅接收 `loading: boolean`

**Emits**：`send(content, contentBlocks?, rawFiles?, rubric?)`、`cancel()`

输入框组件，包含：
- 文件上传（图片 JPEG/PNG/GIF/WebP + PDF/DOCX），通过 `useFileUpload()` composable 管理
- **Loop 模式**：点击左下角"Loop"按钮展开 rubric 条件输入框（最多 10 轮迭代评估）
- 文件拖入（`dragOver` 遮罩提示）
- 文件路径拖入（从右侧文件浏览器拖拽，在光标处插入路径文本）
- 发送（📤）和停止（⏹ 带旋转动画）按钮；Enter 发送，Shift+Enter 换行
- **ContentBlocksPreview** 文件预览组件（可移除单个附件）
- 宽度通过 `var(--chat-max-width, 48rem)` 与消息列表同步，随拖拽缩放联动

### ChatReason.vue

**Props**：`reasoning: string`、`isStreaming: boolean`

可折叠的推理过程展示：
- 流式中显示 spinner 动画 + "正在思考." 文本
- 完成后显示 "思考过程（N 字符）" + 💭 图标
- ▶ 箭头旋转动画（展开时 90°），紫色左边框，等宽字体 pre 显示
- 最大高度 300px 可滚动

### ChatMessages.vue

消息列表渲染核心：

**显示层处理**：
- 过滤：跳过 `DO_NOT_RENDER_ID_PREFIX` 前缀、tool 角色消息
- 合并：`mergeConsecutiveReasoningMessages(messages, skipTool=true)` 将连续纯推理 assistant 消息合并为一条（不影响原始 messages 索引用于 retry/fork）

**功能**：
- 长消息折叠（500 字符阈值，展开/收起按钮）
- 复制消息（`navigator.clipboard.writeText`，2 秒绿色反馈）
- 重试按钮（🔄 重试）
- 分支按钮（🌿 分支）
- Fork 内联编辑器（textarea 编辑 → ✅ 创建分支 / ✖ 取消）
- 分支切换器（◀ 分支 N/M ▶）
- 多模态内容块展示（图片 base64 渲染 / 文件附件图标）
- 中断提示（无审批负载时显示"对话已中断"）
- 空状态欢迎页
- 宽度通过 `var(--chat-max-width, 48rem)` 居中，随拖拽缩放联动
- assistant 消息通过共享组件 `<Markdown>` 渲染（支持 Mermaid 图表、代码块复制）

**Props**：接收 controller 的所有响应式状态（messages、streaming、重试/分支/编辑状态、branchMap 等），通过 emit 向上传递用户操作。
**defineExpose**：暴露 `scrollToBottom()` 供父组件调用。

---

## 共享组件：Markdown.vue

位于 `frontend/src/shared/Markdown.vue`，FilePreview 和 ChatMessages 共用。

### 依赖

| 库 | 说明 |
|----|------|
| `marked` | Markdown → HTML 解析 |
| `DOMPurify` | XSS 安全过滤 |
| `mermaid` | 图表渲染（flowchart、sequence 等） |

### Mermaid 配置

```typescript
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: {
    curve: 'step',          // 直角正交连线
    rankSpacing: 100,       // 层级间距
    nodeSpacing: 90,        // 节点间距
    useMaxWidth: false,     // 不限制宽度
  },
})
```

### 渲染流程

```
slots.default → 提取文本
  → marked.parse()
  → extractMermaidBlocks()    // 提取 ```mermaid → 占位 div
  → DOMPurify.sanitize()
  → mermaid.render() 异步      // 逐个渲染为 SVG
  → addCodeCopyButtons()      // <pre> 包裹 .code-block-wrapper + 复制按钮
  → html.value
```

- 使用 `ref` + `watch` 异步模式适配 mermaid.render() 的 Promise
- `decodeHtmlEntities()` 解码 marked 的 HTML 转义

### 代码块复制

hover 代码块右上角「复制」按钮 → `navigator.clipboard.writeText()` → 绿色「已复制」2 秒恢复。

### Mermaid 图表

- 渲染为 SVG，hover 右上角「源码」按钮复制原始 mermaid 代码
- 对话系统中无缩放/平移工具栏（仅文件预览有）
- 渲染失败显示红色错误提示

### Props

| 字段 | 类型 | 说明 |
|------|------|------|
| `codeBlockIdSeed` | `string?` | 代码块锚点 ID 前缀，用于右侧栏内容导航 |

---

## 事件通信总结

### Props / Emits 流转

```
ChatView.vue (props: threadId, chatStarted, sidebarOpen, filePanelOpen, rightSidebarOpen)
  ├── ChatHeader.vue ← props: hasMessages, loading, sidebarOpen, filePanelOpen, rightSidebarOpen
  │     → emit: toggleSidebar, toggleFilePanel, toggleRightSidebar, createThread
  ├── ChatMessages.vue ← props: messages + 所有 streaming/重试/分支/编辑状态
  │     → emit: retry(index), forkEdit(index), forkCancel(), forkSubmit({index, content}), switchBranch(msgIndex, leafCid)
  ├── ChatInput.vue ← props: loading
  │     → emit: send(content, contentBlocks?, rawFiles?, rubric?), cancel()
  └── ApprovalCard.vue ← props: actionRequests, reviewConfigs, loading
        → emit: respond(HITLResponse), cancel()
```

### Vue emit 事件表

| 来源 | 事件 | 处理方 |
|------|------|--------|
| `ChatInput` | `send(content, contentBlocks, rawFiles, rubric)` | `ChatView` → `ctrl.sendMessage()` |
| `ChatInput` | `cancel` | `ChatView` → `ctrl.cancelRequest()` |
| `ChatMessages` | `retry(index)` | `ChatView` → `ctrl.retryUserMessage()` |
| `ChatMessages` | `forkEdit(index)` | `ChatView` → `ctrl.startForkEdit()` |
| `ChatMessages` | `forkCancel()` | `ChatView` → `ctrl.cancelForkEdit()` |
| `ChatMessages` | `forkSubmit({index, content})` | `ChatView` → `ctrl.submitForkEdit()` |
| `ChatMessages` | `switchBranch(msgIndex, leafCid)` | `ChatView` → `ctrl.switchToBranch()` |
| `ApprovalCard` | `respond(HITLResponse)` | `ChatView` → `ctrl.resumeChat()` |
| `ApprovalCard` | `cancel` | `ChatView` → `ctrl.showInterrupt=false` |
| `ChatHeader` | `toggleSidebar / toggleFilePanel / toggleRightSidebar` | `ChatView` → emit 到 `ChatLayout` |
| `ChatHeader` | `createThread` | `ChatView` → emit 到 `ChatLayout` |
