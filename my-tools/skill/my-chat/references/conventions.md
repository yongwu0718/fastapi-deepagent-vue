# 关键约定与模式

> 本文档是 SKILL.md 十五章的补充，覆盖项目中的所有约定、模式和设计原则。

---

## DO_NOT_RENDER 前缀

```typescript
// useChatState.ts
export const DO_NOT_RENDER_ID_PREFIX = 'do-not-render-'
```

在 `ChatMessages.vue` 中，`v-if` 过滤 `msg.content?.startsWith(DO_NOT_RENDER_ID_PREFIX)` 的消息。用于标记不展示的系统消息（如 LangGraph 内部 state 变更记录）。

---

## 模块级单例模式

`useToolMessages()` 和 `useToast()` 的共享状态定义在**模块顶层**（不在函数体内），因此所有调用方共享同一份响应式引用：

```typescript
// useToolMessages.ts - 模块顶层 ref，所有组件共享
const _toolCallGroups = ref<ToolCallGroup[]>([])
const _streamingToolCalls = ref<ToolCall[]>([])

// 函数体内只做导出，不创建新实例
export function useToolMessages() {
  return { toolCallGroups: _toolCallGroups, . }
}
```

---

## Composables 三层分离模式

```
useChatState()      → 纯状态定义（ref/computed），无副作用
useChatStream()     → SSE 编排层（组装 sse/ 子模块），接受 state 引用
useChatController() → 编排层（组装上述两者 + checkpoints + 线程历史）
```

**SSE 子模块化**：`useChatStream` 内部的 chunk 处理、请求发起、状态重置已拆分到 `core/sse/` 三个独立文件，消除 stream/replay/fork/resume 四处的重复代码。

**RightSidebar 模块化**：右侧面板从 `layout/` 独立为 `sidebar/` feature 模块，拆分为 5 个文件（RightSidebar + 3 个 Tab 组件 + 1 个 composable），每个子组件职责单一。

**扩展新功能时的标准做法**：新建 Composable 放在对应 feature 目录下，通过 useChatController 注入。例如添加"消息搜索"功能：
1. 新建 `chat/search/useMessageSearch.ts`
2. 在 `useChatController` 中组装
3. 通过 `ChatView.vue` 透传 props/emits

---

## 错误处理模式

- SSE 流错误 → `state.error` → `watch(error)` → `toast.error()`
- 操作校验失败 → `toast.warning()` 直接调用（如"只能重试用户消息"）
- 同步错误 → `state.error` 状态 + UI 内嵌错误栏（ChatView 中的 `.chat-error`）
- `lastErrorMsg` 闭包变量：防止同一错误重复 toast

---

## 模块职责审计原则

拆分/新增模块时遵循以下原则：
- **单向依赖**：`shared/` / `api/` → feature modules → controller → layout
- **全局单例**仅限于跨模块共享状态（`useToolMessages`、`useToast`、`useOutlineItems`）
- **ChatMessages.vue 不拆分**：纯展现组件，12 props + 6 emits 直接透传优于 props-drilling
- **useChatController 保持编排层角色**：不按功能域拆分，重试/分支/切换共用同一依赖链

---

## 自动生成的 SDK 层

`src/api/client/` 整个目录由 `@hey-api/openapi-ts` 从后端 OpenAPI 规范自动生成。
**不应手动修改**。如果后端 API 变更，需要重新运行 SDK 生成命令。

客户端实例在 `client.gen.ts` 中：
```typescript
export const client = createClient({ baseUrl: 'http://localhost:8000' })
```
