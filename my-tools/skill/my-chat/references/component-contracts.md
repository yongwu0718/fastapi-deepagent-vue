# 组件 Props/Emits 契约

> 本文档是 SKILL.md 十三章的补充，覆盖所有组件的完整 Props/Emits 定义。

---

## ChatLayout.vue

无 props（根布局组件），管理所有子组件的状态编排。

---

## ChatView.vue

```typescript
// Props
{ threadId: string | null; chatStarted: boolean; sidebarOpen: boolean; rightSidebarOpen: boolean }
// Emits
{ createThread: []; toggleSidebar: []; toggleRightSidebar: []; chatStarted: [boolean]; updateTitle: [threadId: string, title: string] }
```

---

## ChatHeader.vue

```typescript
// Props: { hasMessages: boolean; loading: boolean; sidebarOpen: boolean; rightSidebarOpen: boolean }
// Emits: { toggleSidebar: []; toggleRightSidebar: []; createThread: [] }
```

两种渲染模式：
- `!hasMessages && !loading` → 空白状态头部（仅侧边栏/右侧栏切换按钮）
- `hasMessages || loading` → 完整头部（Logo + 标题 + 新建按钮 + 侧边栏按钮）

---

## ChatMessages.vue

```typescript
// Props
{
  messages: readonly Message[]; streamingContent: string;
  streamingReasoning: string; loading: boolean; firstTokenReceived: boolean;
  showInterrupt: boolean; interruptData: unknown;
  retryingMessageIndex?: number | null; forkingMessageIndex?: number | null;
  forkEditingIndex?: number | null; forkEditingDraft?: string;
  branchMap?: Map<number, { branches: SiblingBranch[]; currentIndex: number }>;
  branchSwitchingIndex?: number | null;
}
// Emits
{ retry: [index: number]; forkEdit: [index: number]; forkCancel: [];
  forkSubmit: [{ index: number; content: string }];
  switchBranch: [msgIndex: number, targetLeafCid: string]; }
// Expose: { scrollToBottom: () => void }
```

渲染逻辑：
1. 遍历 `messages`，过滤 `role==='tool'` 和以 `do-not-render-` 开头的内容
2. `role==='user'` → 右对齐气泡；`assistant` → 左对齐 + Markdown 渲染
3. 每条 user 消息显示 🔄重试 / 🌿分支 按钮（hover 可见）
4. 多条兄弟分支时显示 `◀ 分支 N/M ▶` 切换器（始终可见的紫色 pill）
5. 流式阶段：`loading && !firstTokenReceived` → 三点动画；`isStreaming` → 流式内容 + 光标
6. 自动滚动：watch(messages + streaming*) → `$parent.scrollTo({top: scrollHeight, smooth})`

---

## ChatInput.vue

```typescript
// Props: { loading: boolean }
// Emits: { send: [content: string, contentBlocks?: ContentBlock[]]; cancel: [] }
```

逻辑：
- Enter 提交（Shift+Enter 换行），`loading` 时按钮切换为"停止"
- 集成 `useFileUpload`：上传/拖拽/粘贴 → `ContentBlock[]`
- `canSend`: `(inputText.trim().length > 0 || contentBlocks.length > 0) && !loading`

---

## ChatReason.vue

```typescript
// Props: { reasoning: string; isStreaming: boolean }
// 内部状态: isExpanded (ref)
```

显示"思考过程"折叠面板，流式输出时标题显示 spinner + "正在思考."。

---

## ApprovalCard.vue

```typescript
// Props: { actionRequests: ActionRequest[]; reviewConfigs: ReviewConfig[]; loading: boolean }
// Emits: { respond: [HITLResponse]; cancel: [] }
```

内部维护 `decisionsState` 数组，每个 action 映射一个决策（approve/reject/edit），全部决定后启用提交。

---

## RightSidebar.vue（sidebar 模块编排层）

```typescript
// Props: { isOpen: boolean }
```

内部使用 `useSidebarResize()` 管理拖拽调整宽度（248~560px），Tab 栏切换三个子组件：
- **ToolsTab.vue**：`useToolMessages()` 模块级单例 → 工具调用分组/折叠/流式展示
- **OutlineTab.vue**：`useOutlineItems()` 模块级单例 → IntersectionObserver 视口高亮
- **DetailsTab.vue**：占位

### ToolsTab.vue

无 props/emits，内部管理 `expandedGroups` / `expandedToolMessages` 折叠状态，依赖 `useToolMessages()` 全局单例。

### OutlineTab.vue

无 props/emits，内部管理 `activeOutlineId` + `IntersectionObserver`，依赖 `useOutlineItems()` 全局单例。

### DetailsTab.vue

纯占位组件，无 props/emits。

---

## Markdown.vue

```typescript
// Props: { codeBlockIdSeed?: string }
```

- 使用默认插槽接收文本 → `marked.parse()` → `DOMPurify.sanitize()` → `v-html` 渲染
- `codeBlockIdSeed`：可选，传入后会给渲染出的 `<pre>` 注入 `id="seed-0"`, `id="seed-1"` … 锚点
- 样式使用**非 scoped** 全局 class `.markdown-content`（因为 v-html 不继承 scoped）

---

## msg 对象的 `_key` 字段

每条消息在进入 `messages[]` 前都经过 `ensureMessageKey()` 处理，生成格式为 `${role}-${uuid前8位}` 的唯一 key，作为 Vue `v-for` 的 key 值，确保：
- 消息更新时 DOM 不抖动
- replay/fork 新增消息能正确识别
