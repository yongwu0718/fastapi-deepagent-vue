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

核心布局组件，组装应用的四大面板：

```
┌──────────────────────────────────────────────────────────┐
│ ChatLayout.vue                                           │
│  ┌─────────┐ ┌──────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ 线程面板 │ │ 文件面板  │ │   聊天主区   │ │ 右侧详情面板│ │
│  │(可折叠)  │ │(可折叠)   │ │  ChatView  │ │RightSidebar│ │
│  │ChatSidebar│ │FileBrowser│ │  flex:1     │ │(可拖拽宽度)│ │
│  │300px     │ │(可拖拽)   │ │             │ │           │ │
│  └─────────┘ └──────────┘ └─────────────┘ └───────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Props 与生命周期

```typescript
// 接收路由参数
const route = useRoute()
const threadId = computed(() => route.params.threadId as string)
```

**挂载时：**
1. `loadThreads()` 加载线程列表
2. 监听 `shouldAutoOpenSidebar`：流式工具调用到来时自动展开右侧栏
3. 首次打开文件面板时自动 `fm.loadDirectory()`

### useFilePanelResize.ts

面板拖拽调整宽度工具：

```typescript
function useFilePanelResize(defaultWidth = 300) {
  return {
    panelWidth: Ref<number>,             // 当前面板宽度
    isResizing: Ref<boolean>,            // 拖拽中
    onResizeStart: (e: MouseEvent) => void,      // 右侧拖拽
    onResizeStartLeft: (e: MouseEvent) => void,  // 左侧拖拽
  }
}
```

**实现：**
- `mousedown` → 注册 `mousemove`/`mouseup` 全局监听
- `mousemove` → 计算新宽度（限制最小 200px）
- `mouseup` → 移除全局监听
- 拖拽时设置 `cursor: col-resize` + `userSelect: none`

---

## 二、Router（路由）

### 路由配置

```typescript
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: () => {
      // 优先恢复上次活跃线程
      const lastId = localStorage.getItem('chat_active_thread_id')
      if (lastId) return `/chat/${lastId}`
      // 否则新建线程
      return `/chat/${crypto.randomUUID()}`
    }
  },
  {
    path: '/chat/:threadId',
    name: 'chat',
    component: () => import('@/layout/ChatLayout.vue'),  // 懒加载
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/settings/SettingsView.vue'),  // 懒加载
  },
  {
    path: '/rag',
    name: 'rag',
    component: () => import('@/rag/RagManagement.vue'),  // 懒加载
  },
]

const router = createRouter({
  history: createWebHashHistory(),  // Hash 模式
  routes,
})
```

### 关键设计

- **Hash 模式**：`createWebHashHistory()`，避免部署时的路径问题
- **懒加载**：所有页面组件使用动态 `import()`
- **线程恢复**：根路径自动重定向到 localStorage 中的上次活跃线程

---

## 三、Threads（对话线程管理）

### useChatHistory.ts（核心状态管理）

**模块级单例**，通过 `useChatHistory()` 获取。

#### 数据类型

```typescript
interface ChatThread {
  id: string
  title: string
  createdAt: string
  messageCount: number
}
```

#### 状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `threads` | `Ref<ChatThread[]>` | 线程列表 |
| `activeThreadId` | `Ref<string>` | 当前活跃线程 ID |
| `threadsLoading` | `Ref<boolean>` | 加载中 |

#### 路由双向同步

```
URL 变化 → watch(route.params.threadId) → activeThreadId
activeThreadId 变化 → watch(activeThreadId) → router.push()
```

#### localStorage 持久化

| Key | 值 | 说明 |
|-----|-----|------|
| `chat_active_thread_id` | 线程 ID | 活跃线程，页面刷新后恢复 |
| `chat_msgs_{threadId}` | JSON 消息数组 | 线程消息缓存，用于搜索和离线恢复 |

#### 关键方法

| 方法 | 说明 |
|------|------|
| `loadThreads()` | 从 `GET /threads` 加载，去重合并 |
| `createThread()` | 生成 UUID，创建本地线程 + 路由跳转 |
| `selectThread(id)` | 切换线程 + URL 跳转 |
| `deleteThread(id)` | 调后端删除 + 清理 localStorage + 自动切换 |
| `updateThreadTitle(id, title)` | 更新标题 |
| `loadThreadHistory(tid, checkpointId?)` | 加载历史消息，合并 checkpoint 信息 |
| `cacheThreadMessages(tid, msgs)` | 缓存消息到 localStorage |

### ChatSidebar.vue（线程列表 UI）

#### 功能

| 功能 | 说明 |
|------|------|
| **列表** | 按 `createdAt` 降序排列 |
| **搜索** | 支持正则（兜底普通字符串），搜索标题 + 缓存对话内容 |
| **新建** | 创建新线程 |
| **删除** | hover 显示删除按钮 |
| **骨架屏** | 加载中显示 20 行占位 |
| **空状态** | 无线程时显示提示 |

#### 线程条目显示

每个条目显示：
- **标题**：前 50 字符 + 省略号
- **日期**：今天 / 昨天 / N 天前
- **消息数**
- **删除按钮**：hover 时显示

---

## 四、Sidebar（右侧详情面板）

### RightSidebar.vue

三 Tab 面板容器：

```
┌─────────────────┐
│ 工具调用(3) | 大纲 | 详情 │  ← Tab 导航
├─────────────────┤
│                 │
│   当前 Tab 内容  │
│                 │
└─────────────────┘
```

- **可拖拽调整宽度**：最小 280px，最大为父容器 80%
- **Badge 计数**：工具调用数量 + 用户消息数量

### ToolsTab.vue（工具调用）

**数据来源**：`useToolMessages()` composable

| 区域 | 说明 |
|------|------|
| **流式工具调用** | 实时显示正在进行中的工具调用（spinner 动画） |
| **历史工具调用分组** | 按 assistant 消息分组，可折叠展开 |
| **Tool 消息列表** | 来自 `get-messages-history`，显示工具返回结果 |
| **操作按钮** | 展开全部 / 折叠全部 |

### OutlineTab.vue（大纲导航）

**数据来源**：`useOutlineItems()` composable（由 ChatView 传入消息列表）

- 基于 Markdown 标题层级构建文档大纲
- **IntersectionObserver**：自动高亮当前可视区域的大纲项
- 点击跳转到对应消息位置

### DetailsTab.vue（详情）

当前为空占位组件，预留扩展。

### useSidebarResize.ts

与 `useFilePanelResize` 类似，专用右侧面板拖拽调整宽度。使用 `ResizeObserver` 监听父容器大小，限制最大宽度为父容器 80%。

---

## 五、Upload（文件上传到聊天）

### useFileUpload.ts

文件上传 composable，用于聊天中的文件附件。

#### 支持的格式

| 类型 | 格式 |
|------|------|
| 图片 | JPEG / PNG / GIF / WebP |
| 文件 | PDF / DOCX |

#### ContentBlock 数据结构

```typescript
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
```

#### 上传方式

| 方式 | 实现 |
|------|------|
| **按钮选择** | `<input type="file">` 触发 |
| **粘贴** | `document.addEventListener('paste')`（图片/文件） |
| **拖拽** | `window` 级别 `dragover`/`drop` 事件 |

#### 关键特性

- 去重检测（按文件名）
- 原始 File 对象保留在 `rawFiles` 中供 FormData 使用
- `onUnmounted` 时移除全局拖拽事件

### ContentBlocksPreview.vue（上传预览）

#### 预览样式

| 类型 | 展示 |
|------|------|
| 图片 | 缩略图（max-height: 120px） |
| 文件 | 文件图标 + 文件名 |

每个块可独立删除（点击 ✕ 按钮）。
