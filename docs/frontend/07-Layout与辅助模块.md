# Layout 与辅助模块

> 本文档描述布局系统及辅助模块：主布局（ChatLayout）、路由、线程管理、右侧边栏、文件上传。

---

## 模块组成

```
layout/         # 主布局（2 个文件）
router/         # 路由配置（1 个文件）
threads/        # 对话线程管理（2 个文件）
sidebar/        # 右侧详情面板（5 个文件）
upload/         # 文件上传（2 个文件）
```

---

## 一、Layout（主布局）

### ChatLayout.vue

核心布局组件，组装应用的四大面板 + 嵌套拖拽手柄：

```
┌──────────────────────────────────────────────────────────────┐
│ ChatLayout.vue                                               │
│  ┌───────────┐ ┌────────────┐ ┌───────────┐ ┌─────────────┐ │
│  │ 线程面板   │ │ 文件面板    │ │ 聊天主区   │ │ 右侧详情面板 │ │
│  │(可折叠)    │ │(可折叠)     │ │ ChatView  │ │ RightSidebar│ │
│  │ChatSidebar │ │FileBrowser  │ │ flex:1    │ │(可拖拽宽度)  │ │
│  │◆可拖拽宽度 │ │◆左右双拖拽   │ │           │ │             │ │
│  │默认 300px  │ │默认 480px   │ │           │ │             │ │
│  └───────────┘ └────────────┘ └───────────┘ └─────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

每个面板都有独立的拖拽手柄（`◆` 标记处）。

### 面板开关状态

ChatLayout 管理 4 个核心状态：

| 状态 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sidebarOpen` | `Ref<boolean>` | `true` | 左侧线程面板是否展开 |
| `filePanelOpen` | `Ref<boolean>` | `localStorage 恢复` | 文件面板是否展开，持久化到 `chat_file_panel_open` |
| `rightSidebarOpen` | `Ref<boolean>` | `false` | 右侧详情面板是否展开 |
| `chatStarted` | `Ref<boolean>` | `false` | 当前线程对话是否已开始 |

**初始化逻辑：**
- 线程面板默认展开
- 文件面板从 localStorage 恢复上次状态（打开/关闭持久化）
- 右侧面板默认关闭，由流式工具调用自动打开
- `chatStarted` 由 ChatView 通过事件向上通知

### ChatView Props 与 Events

ChatLayout 向 ChatView 传递 5 个 props，接收 6 个 events：

| Props | 类型 | 说明 |
|-------|------|------|
| `threadId` | `string \| null` | 当前活跃线程 ID |
| `chatStarted` | `boolean` | 对话是否已开始 |
| `sidebarOpen` | `boolean` | 线程面板状态 |
| `filePanelOpen` | `boolean` | 文件面板状态 |
| `rightSidebarOpen` | `boolean` | 右侧面板状态 |

| Events | 参数 | 说明 |
|--------|------|------|
| `create-thread` | - | 创建新线程 |
| `toggle-sidebar` | - | 切换线程面板 |
| `toggle-file-panel` | - | 切换文件面板 |
| `toggle-right-sidebar` | - | 切换右侧面板 |
| `chat-started` | `boolean` | 通知对话开始状态 |
| `update-title` | `(threadId, title)` | 更新线程标题 |

### 挂载生命周期

1. `loadThreads()` 加载线程列表
2. 监听 `shouldAutoOpenSidebar`：流式工具调用到来时自动展开右侧栏（通过 `consumeAutoOpenSidebar()` 消费标记）
3. 文件面板初始化：先用 `fm.restoreState()` 尝试恢复上次目录状态，失败则 `fm.loadDirectory()` 加载根目录

### useFilePanelResize.ts

面板拖拽调整宽度工具，文件面板和线程面板共用：

```typescript
function useFilePanelResize(initialWidth?: number) {
  return {
    panelWidth: Ref<number>,                     // 当前面板宽度
    isResizing: Ref<boolean>,                    // 拖拽中
    rootRef: Ref<HTMLElement | null>,            // 面板 DOM 引用
    onResizeStart: (e: MouseEvent) => void,      // 右侧拖拽（向右拉宽）
    onResizeStartLeft: (e: MouseEvent) => void,  // 左侧拖拽（向左拉宽）
  }
}
```

**默认值：** `DEFAULT_WIDTH = 480`，线程面板传入 300。

**实现细节：**
- `mousedown` → 注册 `mousemove`/`mouseup` 全局监听
- **10px 防抖死区** (`DRAG_DEADZONE`)：避免轻微触碰就改变宽度
- 右侧拖拽：`startWidth + delta`（向右拉宽）
- 左侧拖拽：`startWidth - delta`（向左拉宽）
- 最小宽度无硬限制（允许到 `0`）
- `mouseup` → 移除全局监听，恢复 `cursor` 和 `userSelect`
- 拖拽时设置 `cursor: col-resize` + `userSelect: none`

---

## 二、Router（路由）

### 路由常量

```typescript
const LS_ACTIVE_THREAD_KEY = 'chat_active_thread_id'
```

### 路由配置

```typescript
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: () => {
      try {
        const lastId = localStorage.getItem(LS_ACTIVE_THREAD_KEY)
        if (lastId) return { path: `/chat/${lastId}`, replace: true }
      } catch { /* localStorage 不可用 */ }
      return { path: `/chat/${crypto.randomUUID()}`, replace: true }
    },
  },
  {
    path: '/chat/:threadId',
    name: 'chat',
    component: () => import('@/layout/ChatLayout.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/settings/SettingsView.vue'),
  },
  {
    path: '/rag',
    name: 'rag',
    component: () => import('@/rag/RagManagement.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})
```

### 关键设计

- **Hash 模式**：`createWebHashHistory()`，避免部署时的路径问题
- **懒加载**：所有页面组件使用动态 `import()`
- **线程恢复**：根路径自动重定向到 localStorage 中的上次活跃线程，失败则新建 UUID 线程
- **防御性编码**：localStorage 访问使用 `try/catch`，避免隐私模式下的异常
- **`replace: true`**：重定向不产生历史记录

---

## 三、Threads（对话线程管理）

### 模块结构

`useChatHistory.ts` 包含两类导出：
- **模块级独立函数**：`loadThreadHistory()`、`cacheThreadMessages()`，可直接导入使用
- **Composable**：`useChatHistory()`，在 setup 中调用

### 模块级函数

#### loadThreadHistory()

```typescript
async function loadThreadHistory(
  tid: string,
  checkpointId?: string | null,
): Promise<{ messages: Message[]; headCheckpointId: string | null }>
```

**工作流程：**
1. 先尝试从后端 `GET /messages-history/{thread_id}` 加载
2. 如果传入 `checkpointId`，则加载该分支的历史
3. 从后端返回的消息中合并 localStorage 缓存的 checkpoint 元数据（`_checkpointId`、`_parentCheckpointId`、`_leafCheckpointId`）
4. 匹配策略：优先 `_msgId` 精确匹配 → 位置索引匹配 → 角色+内容兜底匹配
5. 消息通过 `mergeConsecutiveReasoningMessages` 合并连续的推理消息
6. 加载成功后用 `cacheThreadMessages()` 更新 localStorage 缓存
7. **后端不可用时降级**：返回 localStorage 缓存的离线消息
8. 返回 `{ messages, headCheckpointId }`

#### cacheThreadMessages()

```typescript
function cacheThreadMessages(tid: string, msgs: Message[]): void
```

将消息数组缓存到 localStorage（key: `chat_msgs_{threadId}`），用于搜索和离线恢复。

### useChatHistory()（核心状态管理）

#### 数据类型

```typescript
interface ChatThread {
  id: string                    // UUID，同时作为后端 thread_id
  title: string
  createdAt: string
  messageCount: number
}
```

#### 状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `threads` | `Readonly<Ref<ChatThread[]>>` | 线程列表（readonly 封装） |
| `activeThreadId` | `Readonly<Ref<string \| null>>` | 当前活跃线程 ID |
| `threadsLoading` | `Readonly<Ref<boolean>>` | 加载中 |

> 所有返回的 ref 均通过 `readonly()` 封装，防止外部直接修改。

#### 路由双向同步

```
URL 变化 → watch(route.params.threadId) → activeThreadId
activeThreadId 变化 → watch(activeThreadId) → localStorage 持久化
```

注意：`activeThreadId` 变化后由 `createThread()`/`selectThread()`/`deleteThread()` 主动调用 `router.push()`，不存在 `activeThreadId → URL` 的自动同步 watch。

#### localStorage 持久化

| Key | 值 | 说明 |
|-----|-----|------|
| `chat_active_thread_id` | 线程 ID | 活跃线程，页面刷新后恢复 |
| `chat_msgs_{threadId}` | JSON 消息数组 | 线程消息缓存，用于搜索和离线恢复 |

#### 关键方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `loadThreads()` | `() => Promise<void>` | 从 `GET /threads` 加载，与本地列表去重合并 |
| `createThread()` | `() => string` | 生成 UUID → 插到列表头部 → 路由跳转 → **返回新线程 ID** |
| `selectThread(id)` | `(id: string) => void` | 相同 ID 忽略，否则更新状态 + `router.push()` |
| `deleteThread(id)` | `(id: string) => Promise<void>` | 调后端删除 + 清理 localStorage 缓存 + 自动切到下一个线程 |
| `updateThreadTitle(id, title)` | `(id: string, title: string) => void` | 更新线程标题 |

#### 线程标题默认值

从后端加载的服务器线程，默认标题为：
```
对话 · {UUID 前 6 位}
```
点击加载后，标题会自动更新为第一条用户消息内容。

### ChatSidebar.vue（线程列表 UI）

#### 组件签名

```typescript
const props = defineProps<{
  threads: readonly ChatThread[]
  activeThreadId: string | null
  threadsLoading?: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  create: []
  delete: [id: string]
  toggle: []
}>()
```

#### 功能明细

| 功能 | 说明 |
|------|------|
| **列表** | 按 `createdAt` 降序排列 |
| **搜索** | 支持正则（兜底普通字符串忽略大小写），搜索标题 + 缓存对话内容 |
| **搜索清除** | 输入内容时显示 ✕ 清除按钮 |
| **新建** | 底部常驻"新建对话"按钮 |
| **删除** | hover 时显示 ✕ 按钮 |
| **骨架屏** | 加载中显示 20 行占位（CSS pulse 动画） |
| **空状态** | 无线程时显示"暂无对话历史"；搜索无结果时显示"未找到匹配的对话" |
| **键盘支持** | Enter / Space 触发选中 |
| **标题** | 头部显示 "Thread History" |

#### 线程条目显示

每个条目显示：
- **标题**：来自 `thread.title` 或兜底 "新对话"
- **日期**：`formatDate()` 函数 —— 今天 / 昨天 / N 天前（< 7 天）/ 本地日期格式
- **删除按钮**：hover 时 `opacity: 0 → 1` 显示

---

## 四、Sidebar（右侧详情面板）

### RightSidebar.vue

三 Tab 面板容器，标题"详情面板"：

```
┌─────────────────┐
│ 详情面板          │  ← 头部标题
├─────────────────┤
│ 工具调用(3) | 大纲 | 详情 │  ← Tab 导航（tools → outline → details）
├─────────────────┤
│                 │
│   当前 Tab 内容  │
│                 │
└─────────────────┘
```

**Props：**
| Prop | 类型 | 说明 |
|------|------|------|
| `isOpen` | `boolean` | 面板是否展开 |

**Tab 定义：**
```typescript
type TabId = 'tools' | 'details' | 'outline'
// 渲染顺序：工具调用 → 大纲 → 详情
```

**Badge 计数：**
- 工具调用：来自 `useToolMessages().toolCallCount`
- 大纲：来自 `useOutlineItems().outlineItems.length`，仅当 > 0 时显示

### ToolsTab.vue（工具调用）

**数据来源**：`useToolMessages()` composable

| 区域 | 说明 |
|------|------|
| **流式工具调用** | 标题 "⏳ 流式工具调用"，紫色虚线边框，显示实时 ToolCallCard |
| **展开/折叠全部** | 一键操作，统一控制工具调用分组和工具消息分组 |
| **工具调用分组** | 按 assistant 消息分组，紫色左边框，可折叠展开，折叠标题显示工具名称和消息摘要 |
| **工具返回分隔线** | 当两者都存在时，显示 "工具返回" 分隔线 |
| **工具消息列表** | 来自 `get-messages-history` 的 tool 角色消息，绿色左边框，可折叠展开，预览 40 字符截断 |

**折叠标签示例：**
```
🔧 3 个工具调用 · "用户消息摘要"   ▶
🔧 search_documents              ▶
✅ tool_name → 返回内容前40字…    ▶
```

### OutlineTab.vue（大纲导航）

**数据来源**：`useOutlineItems()` composable

- 基于 Markdown 标题层级构建文档大纲
- **IntersectionObserver**（`rootMargin: '-20% 0px -50% 0px'`, `threshold: 0`）：自动高亮当前可视区域的大纲项
- 点击 `scrollIntoView({ behavior: 'smooth', block: 'center' })` 跳转
- `onMounted` / `watch(outlineItems, deep)` 时重建 observer
- `onUnmounted` 时 `disconnect()` 清理
- 空状态："暂无用户消息"

### DetailsTab.vue（详情）

占位组件，显示图标 + "此处可展示附加信息"，预留扩展。

### useSidebarResize.ts

右侧面板专用拖拽调整宽度：

```typescript
function useSidebarResize() {
  return {
    sidebarWidth: Ref<number>,                // 当前宽度
    isResizing: Ref<boolean>,                 // 拖拽中
    rootRef: Ref<HTMLElement | null>,         // 面板 DOM 引用
    onResizeStart: (e: MouseEvent) => void,   // 拖拽开始
  }
}
```

**常量：** `MIN_WIDTH = 280`, `MAX_INITIAL_WIDTH = 480`

**实现：**
- `onMounted` 时通过 `ResizeObserver` 监听父容器，限制最大宽度为父容器 80%
- 向左拖拽（`startX - e.clientX`）拓宽面板
- 拖拽时 `Math.min(maxWidth, Math.max(MIN_WIDTH, startWidth + delta))` 双重限制
- `onUnmounted` 时 `disconnect()` 清理 ResizeObserver

---

## 五、Upload（文件上传到聊天）

### useFileUpload.ts

文件上传 composable，用于聊天中的文件附件。

#### 支持的格式

`SUPPORTED_FILE_TYPES` 常量：

| 类型 | MIME Type |
|------|-----------|
| 图片 | `image/jpeg`, `image/png`, `image/gif`, `image/webp` |
| 文件 | `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (DOCX) |

#### ContentBlock 数据结构

```typescript
interface ContentBlock {
  type: 'image' | 'file'
  mimeType: string
  data: string          // base64 编码（不含 data:...;base64, 前缀）
  metadata: {
    name?: string       // 图片时使用
    filename?: string   // 文件时使用
  }
}
```

#### 上传方式

| 方式 | 实现 |
|------|------|
| **按钮选择** | `handleFileUpload()` 监听 `<input type="file">` 的 `change` 事件 |
| **粘贴** | `handlePaste()` 监听 `document paste` 事件（图片/文件） |
| **拖拽** | `window` 级别 `dragenter`/`dragleave`/`dragover`/`drop` 事件 |

#### 关键特性

- **去重检测**：`isDuplicate()` 按文件名比较
- **Toast 通知**：不支持类型 → `toast.error()`；重复文件 → `toast.warning()`
- **原始 File 对象**：保留在 `rawFiles` 中供 FormData 附件端点使用，与 `contentBlocks` 索引一一对应
- **全局拖拽防重复注册**：`eventsAttached` 标记，确保多次调用 `useFileUpload()` 不会重复绑定事件
- **拖拽嵌套防抖**：`dragCounter` 计数器处理子元素间的 `dragenter`/`dragleave` 事件冒泡
- **拖拽视觉反馈**：`dragOver` 状态用于显示拖拽覆盖层
- **onUnmounted 清理**：移除所有全局拖拽事件 + 重置 `eventsAttached`
- **paste 事件中 `e.preventDefault()`**：仅在确认是支持的文件类型后才调用

#### 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| `contentBlocks` | `Readonly<Ref<ContentBlock[]>>` | 当前内容块列表 |
| `rawFiles` | `Readonly<Ref<File[]>>` | 原始 File 对象（与 contentBlocks 索引对应） |
| `dragOver` | `Readonly<Ref<boolean>>` | 是否有文件拖拽悬停 |
| `handleFileUpload` | `(e: Event) => Promise<void>` | 文件选择处理 |
| `handlePaste` | `(e: ClipboardEvent) => Promise<void>` | 粘贴处理 |
| `removeBlock` | `(idx: number) => void` | 删除指定内容块 |
| `resetBlocks` | `() => void` | 清空所有内容块 |

### ContentBlocksPreview.vue（上传预览）

#### Component Props/Events

```typescript
defineProps<{
  blocks: readonly ContentBlock[]
}>()

const emit = defineEmits<{
  remove: [index: number]
}>()
```

#### 预览样式

| 类型 | 展示 |
|------|------|
| 图片 | 缩略图 **56×56px**，`object-fit: cover` |
| 文件 | 文件图标 + 文件名（max-width: 140px 溢出省略） |

每个块可独立删除：hover 时显示圆形半透明删除按钮（`⌀20px`），hover 删除按钮变为红色 (`rgba(220,38,38,0.8)`)。
