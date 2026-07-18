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

### 核心职责

| 职责 | 实现方式 |
|------|----------|
| **消息持久化** | `watch(messages)` → `cacheThreadMessages()` 存入 localStorage |
| **线程切换** | `watch(threadId)` → 取消请求 → 清空状态 → `loadThreadHistory()` |
| **自动标题** | 取第一条 user 消息前 50 字符作为线程标题 |
| **发送消息** | `sendMessage()` → 无 threadId 先 `createThread()` → `streamSend()` |
| **重试（Retry）** | `retryUserMessage(index)` → 使用 `_parentCheckpointId` 调用 `replayCheckpoint()` |
| **分支（Fork）** | 三阶段：`startForkEdit()` → `submitForkEdit()` → `forkFromCheckpoint()` |
| **分支切换（Switch）** | `switchToBranch(targetLeafCid)` → 加载分支完整历史 |
| **branchMap** | computed，按 `parentCheckpointId` 去重计算兄弟分支 |

### 暴露的公开接口

```typescript
const ctrl = useChatController(threadId, {
  onCreateThread: () => void,
  onChatStarted: (tid: string, title: string) => void,
  onUpdateTitle: (tid: string, title: string) => void,
  onToggleSidebar: () => void,
  onToggleFilePanel: () => void,
  onToggleRightSidebar: () => void,
})

// 返回
ctrl.state          // 响应式状态
ctrl.sendMessage()  // 发送消息
ctrl.cancelRequest()// 取消当前请求
ctrl.retryUserMessage(index) // 重试
ctrl.startForkEdit(index)    // 开始分支编辑
ctrl.submitForkEdit(index)   // 提交分支编辑
ctrl.cancelForkEdit()        // 取消分支编辑
ctrl.switchToBranch(leafCid) // 切换分支
ctrl.resumeChat(decisions)   // 恢复中断对话
ctrl.loadThreadHistory(tid)  // 加载历史
ctrl.moduleState              // 暴露给 RightSidebar 的状态
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

### 公开方法

| 方法 | 说明 | 后端端点 |
|------|------|------|
| `sendMessage()` | 发送用户消息 | `/chat/{thread_id}/stream` 或 `.../with-files/stream` |
| `cancelRequest()` | 取消请求 + 打包未完成内容 | — |
| `resumeChat()` | 恢复 HITL 中断 | `/chat/{thread_id}/resume` |
| `replayCheckpoint()` | 从检查点重放（重试） | `/checkpoints/{thread_id}/replay` |
| `forkFromCheckpoint()` | 从检查点分叉（分支） | `/checkpoints/{thread_id}/fork` |

### 关键实现细节

**发送消息时**：自动查找最后一条 assistant 消息的 `_leafCheckpointId`，作为 `checkpoint_id` 传递，确保新消息沿当前分支继续：

```
sendMessage()
  → 构建消息（user role + contentBlocks + rawFiles）
  → 查找最后 assistant 消息的 _leafCheckpointId
  → 有附件 → doSseFormDataRequest (multipart)
  → 无附件 → doSseRequest (JSON, body 含 checkpoint_id + rubric)
```

**取消请求时**：不仅 `abort()`，还会将 `streamingContent` + `streamingReasoning` + `pendingToolCalls` 打包为一条 assistant 消息，保留已有内容。

**重放/分叉公共逻辑** (`enterReplayMode`)：校验 threadId → 设置 loading → 重置流式状态。

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
| **`checkpoint`** | 解析 `{checkpoint_id, parent_checkpoint_id, kind}`。`kind='input'` 绑定到 user 消息；`kind='leaf'` 绑定到 assistant 消息（处理 LEAF 先于 done 到达的时序问题） |
| **`reasoning`** | 追加到 `streamingReasoning` |
| **`text`** | 追加到 `streamingContent` |
| **`tool_call`** | 按 `tool_call_id` 存入 `pendingToolCalls` Map，参数经 `parseToolArgs()` 安全解析 |
| **`tool_result`** | 更新对应 tool_call 的 `result` 字段 |
| **`interrupt`** | 设 `showInterrupt=true`，解析 `interruptData` |
| **`user`** | 忽略（不处理） |
| **`rubric`** | Loop Engineering 评估事件：根据 `type`（`rubric_evaluation_start/end`）和 `result`（`satisfied/needs_revision/failed/max_iterations_reached/grader_error`）显示 toast |
| **`done`** | 将流式内容打包为 assistant 消息 → `applyPendingLeaf()` 补绑 LEAF → 清理状态 |
| **`error`** | 设置 error 状态，清理 |

### parseToolArgs()

```typescript
// 安全解析工具参数，容错处理
parseToolArgs(args)
  → JSON.parse 成功          → 原样返回
  → JSON.parse 失败 + 数组    → { items: [...] }
  → JSON.parse 失败 + 标量    → { value: scalar }
  → 完全失败                  → { raw: rawString }
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
| `_parentCheckpointId` | user 消息 | 用于 fork（从父状态分叉） |
| `_leafCheckpointId` | assistant 消息 | 用于 sendMessage（确定当前分支继续点） |

### 匹配策略

`matchCheckpointByContent()` 按四级优先级匹配 user 消息到检查点：

1. **完全相等**（normalize 后）
2. 消息以 **preview** 开头（preview 为前 80 字符截断）
3. **preview** 以消息开头（消息被截断）
4. 双向包含兜底

### 兄弟分支

`getSiblingBranches()` 按 `parent_checkpoint_id` 分组，找出同 parent 下的所有 input 检查点（排除 fork 来源），排序后返回 `SiblingBranch[]`。仅当兄弟数 > 1 时 UI 才显示分支切换器。

### 分支叶子持久化

```typescript
localStorage key: `chat_branch_leaf_{threadId}`
```

SSE 流结束后自动持久化，线程切换时恢复，确保刷新后回到同一分支。

### branchMap（computed）

按 `parentCheckpointId` 去重：同一 parent 下的多条连续 user 消息，只在最后一条（实际分叉点）显示分支按钮。前面的消息是顺序执行链。

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

| 状态 | 说明 |
|------|------|
| `_toolCallGroups` | 按消息分组的 assistant toolCalls |
| `_toolMessages` | tool 角色消息条目（就近匹配） |
| `_streamingToolCalls` | 流式期间的实时工具调用 |
| `_shouldAutoOpenSidebar` | 流式工具调用到来时自动触发右侧栏展开 |

---

## HITL 审批流程

### 触发路径

```
后端 interrupt chunk
  → sseChunkHandler: showInterrupt=true, 解析 interruptData
  → ChatView.parsedInterrupt: HITLRequest
  → 渲染 ApprovalCard.vue 覆盖层
```

### ApprovalCard 功能

- 展示 `action_requests` 列表（每项含 name、description、args）
- 三种决策：**批准 (approve)** / **拒绝 (reject)** / **编辑 (edit)**
- `review_configs` 可限制可选决策
- 拒绝时可填写原因；编辑时可修改 JSON 参数
- "全部批准"快捷按钮
- 提交 → `ctrl.resumeChat(HITLResponse)` → `POST /chat/{thread_id}/resume`
- 取消 → 直接关闭 `showInterrupt`

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

```html
<ChatHeader ... />
<ChatMessages ... />
<ChatInput ... />
<ApprovalCard v-if="showInterrupt" ... />
<div class="chat-resize-handle" />  <!-- 拖拽缩放手柄，仅消息区可见 -->
```

**computed**：
- `parsedInterrupt`：将 `interruptData` 解析为 `HITLRequest`
- `contentNav`：消息大纲（共享到 RightSidebar）

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
- **空白状态**：仅工具栏按钮（侧边栏切换、文件面板切换、设置）
- **聊天中**：完整导航栏 + AgentLogo + 新建对话按钮，始终保持全宽

### ChatInput.vue

输入框组件，包含：
- 文件上传（图片/PDF/DOCX）
- **Loop 模式**：点击左下角"Loop"按钮展开 rubric 条件输入框
- 拖入文件路径支持
- 发送和取消按钮
- 宽度通过 `var(--chat-max-width, 48rem)` 与消息列表同步，随拖拽缩放联动

### ChatReason.vue

可折叠的推理过程展示：
- 流式中有 spinner 动画
- 完成后显示字符数和折叠/展开按钮

### ChatMessages.vue

消息列表渲染核心：
- 过滤 tool 角色和不渲染前缀的消息
- 长消息折叠（500 字符阈值）
- 复制、重试、分支按钮
- 分支切换器（多分支导航）
- Fork 内联编辑器
- 空状态欢迎页
- 宽度通过 `var(--chat-max-width, 48rem)` 居中，随拖拽缩放联动
- assistant 消息通过共享组件 `<Markdown>` 渲染（支持 Mermaid 图表、代码块复制）

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

### Pose 事件（Vue emit）

| 来源 | 事件 | 处理方 |
|------|------|--------|
| `ChatInput` | `send(content, contentBlocks, rawFiles, rubric)` | `ChatView` → `ctrl.sendMessage()` |
| `ChatInput` | `cancel` | `ChatView` → `ctrl.cancelRequest()` |
| `ChatMessages` | `retry(index)` | `ChatView` → `ctrl.retryUserMessage()` |
| `ChatMessages` | `forkEdit(index)` | `ChatView` → `ctrl.startForkEdit()` |
| `ChatMessages` | `forkSubmit({index, content})` | `ChatView` → `ctrl.submitForkEdit()` |
| `ChatMessages` | `switchBranch(msgIndex, leafCid)` | `ChatView` → `ctrl.switchToBranch()` |
| `ApprovalCard` | `respond(HITLResponse)` | `ChatView` → `ctrl.resumeChat()` |
| `ChatHeader` | 侧边栏/面板切换 | `ChatView` → emit 到 `ChatLayout` |
