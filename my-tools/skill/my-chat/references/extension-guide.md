# 扩展功能实践指南

> 本文档是 SKILL.md 十七章的补充，覆盖常见扩展操作的步骤清单。

---

## 添加新的 SSE chunk 类型

假设后端新增 `chunk.type === 'citation'`（引用文献）：

1. **类型**（`api/chat.ts`）：在 `StreamChunk.type` 联合类型中加 `'citation'`
2. **状态**（`useChatState.ts`）：加 `streamingCitations` ref
3. **处理**（`chat/core/sse/sseChunkHandler.ts`）：在 `handleSseChunk` 中加 `if (chunk.type === 'citation')` 分支
4. **展示**（`ChatMessages.vue`）：在流式区域渲染 citation 内容
5. **done 时打包**：在 `done` 分支中将 citation 写入 assistant 消息的扩展字段

---

## 添加新的 API 端点

1. 后端 OpenAPI 规范更新后，重新生成 SDK（`src/api/client/`）
2. 在对应 Composable 中调用生成的 SDK 函数
3. 遵循三层分离：state → stream/API → controller

---

## 新增一个右侧面板 Tab

1. 在 `sidebar/` 下新建 `NewTab.vue` 组件
2. 在 `sidebar/RightSidebar.vue` 的 `tabs` 数组中加 `{ id: 'newtab', label: '新标签' }`
3. 在 `<div class="right-sidebar-body">` 中加 `<NewTab v-if="activeTab === 'newtab'" />`
4. 如需共享数据，创建新的模块级单例 Composable（参考 `useToolMessages`）

---

## 添加新的消息操作按钮

1. 在 `ChatMessages.vue` 的操作按钮区（`.message-actions`）加按钮
2. 通过 emit 向 `ChatView.vue` 传递事件
3. `ChatView.vue` 通过 `useChatController` 调用具体逻辑
4. 如需 loading 态，在 `useChatController` 中加 `ref<number | null>` 跟踪
