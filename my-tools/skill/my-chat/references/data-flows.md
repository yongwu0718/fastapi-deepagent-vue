# 详细数据流

> 本文档是 SKILL.md 五章的补充，覆盖 SSE 事件处理、线程切换、重试、分支、HITL、分支切换、大纲导航的详细流程。

---

## 1. SSE 事件 → 状态变更详细流程

```
handleSseChunk(chunk: StreamChunk)
│
├── chunk.type === 'checkpoint'
│   ├── kind='input' → 从后往前找第一条 user 消息，绑定 _checkpointId + _parentCheckpointId
│   │   （首次发送时绑定；replay/fork 时消息已有则跳过）
│   └── kind='leaf' → 从后往前找最后一条 assistant 消息，绑定 _leafCheckpointId
│       （用于分支切换时加载该分支的完整历史）
│
├── chunk.type === 'reasoning'
│   └── streamingReasoning += chunk.content
│
├── chunk.type === 'text'
│   └── streamingContent += chunk.content（不区分 replay 模式，不再做内容匹配去重）
│
├── chunk.type === 'tool_call'
│   └── pendingToolCalls.set(id, {id, name, args})
│       → syncStreamingTools() → 写入 useToolMessages 单例
│       → 触发 RightSidebar 自动展开
│
├── chunk.type === 'tool_result'
│   └── 更新 pendingToolCalls 中对应工具的 result 字段
│       → syncStreamingTools() → 右侧栏实时更新
│
├── chunk.type === 'user'
│   └── replay/fork 回带的历史 user 消息
│       → 直接 return，不入列 messages（调用方已显式 push）
│       → 已移除 seenUserMessages 去重逻辑
│
├── chunk.type === 'interrupt'
│   └── loading = false, showInterrupt = true
│       → ChatView 渲染 ApprovalCard 覆盖层
│
├── chunk.type === 'done'
│   └── 将 streamingContent + streamingReasoning + toolCalls
│       打包为 assistant 消息 push 到 messages[]
│       → 清空 streaming 状态、pendingToolCalls
│       → clearStreamingToolCalls()
│       → loading = false, isReplayMode = false
│
└── chunk.type === 'error'
    └── error = chunk.content, loading = false
        → watch(error) 自动触发 toast.error()
```

---

## 2. 线程切换流程

```
URL 变化 /chat/:threadId → route.params.threadId 变化
│
├── useChatHistory (activeThreadId 同步)
│   └── router push → watch(route.params.threadId) → activeThreadId 更新
│
└── useChatController (watch threadId)
    ├── cancelRequest()         ← 取消当前 SSE 流
    ├── 重置所有状态             ← streaming*, error, pendingToolCalls, showInterrupt
    ├── messages.value = []
    ├── checkpoints.reset()
    ├── if (!newId) return      ← 路由保证 threadId 始终有效，此守卫仅用于 TypeScript 类型窄化
    │
    ├── loadThreadHistory(newId, cachedLeaf)   ← cachedLeaf = loadBranchLeaf() 恢复上次分支
    │   ├── GET /chat/{id}/get-messages-history → serverMsgs
    │   ├── loadCachedMessages(id)               → 取 localStorage 缓存
    │   ├── pickCheckpointFromCache()            → 合并 checkpoint 字段
    │   │   (user 恢复 _checkpointId/_parentCheckpointId；assistant 恢复 _leafCheckpointId)
    │   ├── cacheThreadMessages(id, merged)      → 写回 localStorage
    │   ├── 若缺检查点 → checkpoints.loadCheckpoints()
    │   │   → resolveCheckpointForMessage() 逐条匹配 → 补全 _checkpointId
    │   │   → 写回 localStorage
    │   └── 若有 cachedLeaf：补全最后 assistant 的 _leafCheckpointId（防止刷新丢失）
    │
    └── messages.value = 最终合并后的消息列表
```

---

## 3. 检查点重试（Replay）流程

```
用户点击「🔄 重试」按钮
│
├── ChatMessages.vue → emit('retry', index)
├── ChatView.vue → ctrl.retryUserMessage(index)
│
└── useChatController.retryUserMessage(index)
    ├── 校验：threadId 存在、msg.role === 'user'、有 _checkpointId、不在 loading
    ├── retryingMessageIndex = index  (UI 显示 loading 态)
    └── replayCheckpoint(checkpointId, checkpointNs)
        │
        └── useChatStream.replayCheckpoint()
            1. isReplayMode = true  ← 标记（仅用于日志/状态重置，不再做消息过滤）
            2. 重置所有流式状态（但不追加 user 消息）
            3. doReplayRequest() → POST /checkpoints/{id}/replay (SSE)
            4. SSE 事件 → handleSseChunk（共用同一套处理逻辑）
               - checkpoint 事件：消息已有 _checkpointId，跳过
               - user 事件：直接 return（不入列）
               - text 事件：直接拼接（不再做内容匹配）
               - done：push assistant，退出 replay 模式
```

---

## 4. 分支（Fork）流程

```
用户点击「🌿 分支」按钮
│
├── ChatMessages.vue → emit('forkEdit', index)
├── ChatView.vue → ctrl.startForkEdit(index)
│   └── forkEditingIndex = index, forkEditingDraft = msg.content
│       → ChatMessages 中该条消息替换为内联编辑 textarea
│
├── 用户编辑内容 → 点击「✅ 创建分支」
│
├── ChatMessages.vue → emit('forkSubmit', {index, content})
├── ChatView.vue → ctrl.submitForkEdit({index, content})
│
└── useChatController.submitForkEdit()
    ├── 校验：与重试相同 + 内容确实已修改（与原文不同）
    ├── forkingMessageIndex = index
    └── forkFromCheckpoint(checkpointId, {
          values: {
            messages: [{
              type: 'human', role: 'human', content: trimmed
            }]
          }
        })
        │
        └── useChatStream.forkFromCheckpoint()
            1. isReplayMode = true（共用同一套前置逻辑）
            2. 重置流式状态
            3. doForkRequest() → POST /checkpoints/{id}/fork (SSE)
            4. SSE 事件 → handleSseChunk（共用同一套处理）
```

---

## 5. HITL 中断审批流程

```
SSE 收到 chunk.type === 'interrupt'
│
├── loading = false, showInterrupt = true
├── interruptData = parsed JSON (HITLRequest)
│
├── ChatView.vue
│   ├── v-if="showInterrupt && parsedInterrupt"
│   └── 渲染 ApprovalCard（覆盖层，z-index: 50）
│       ├── 展示 action_requests（名称、参数、描述）
│       ├── 展示 review_configs（允许的决策列表）
│       ├── 用户对每个 action 选择：批准/拒绝/编辑
│       ├── 拒绝：可选填拒绝原因
│       ├── 编辑：展示 JSON 编辑器
│       └── 提交 → emit('respond', {decisions: HITLDecision[]})
│
├── ChatView.onResume(decisions)
│
└── useChatStream.resumeChat(decisions)
    1. loading = true, 保持 showInterrupt = true（卡片显示"提交中…"）
    2. 重置 streaming 状态
    3. POST /chat/{id}/resume (SSE)
    4. onSseEvent 首次收到数据时 → showInterrupt = false（隐藏审批卡片）
    5. 复用 handleSseChunk 处理后续流
    6. 流自然结束或出错 → 安全兜底重置 loading
```

---

## 6. 分支切换（Branch Switch）流程

```
同 parent_checkpoint_id 下有 ≥2 个 input 检查点 → 兄弟分支
  │
  ├── 后端 /inputs 端点返回每个 input 的 leaf_checkpoint_id
  │   （_compute_leaf_for_inputs 沿 parent_config 链追溯叶子节点）
  │
  ├── 前端 useCheckpoints.getSiblingBranches(parentCid)
  │   └── 按 parent_checkpoint_id 分组，过滤 source='fork'（重试用）
  │       └── siblings.length > 1 才返回（≤1 无分支可选）
  │
  ├── useChatController.branchMap (computed) 【去重】
  │   └── 按 _parentCheckpointId 去重：同一父检查点只保留最后一条 user 消息
  │       → 要求 msg._checkpointId 存在（排除 fork 分支消息，其 checkpoint 被 SKIP）
  │       └── Map<msgIndex, { branches[], currentIndex }> — 只有分叉点有入口
  │
用户点击 ◀▶ 切换分支
  │
  ├── ChatMessages.vue → emit('switchBranch', msgIndex, targetLeafCid)
  ├── ChatView.vue → ctrl.switchToBranch(msgIndex, targetLeafCid)
  │
  └── useChatController.switchToBranch()
      1. loadThreadHistory(tid, targetLeafCid)
         → GET /chat/{id}/get-messages-history?checkpoint_id=leaf
         → 后端 graph.aget_state({checkpoint_id: leaf}) 读取该分支完整 messages
      2. 替换 messages[] 为新分支的完整历史
      3. loadCheckpoints() → resolveCheckpointForMessage() 补全 _checkpointId
      4. 设置最后 assistant 的 _leafCheckpointId = targetLeafCid（防止刷新丢失）
      5. persistBranchLeaf(leafCid) → localStorage
      6. toast.success('已切换分支')
  │
刷新恢复
  ├── loadBranchLeaf() 读取 localStorage 的叶子 ID
  ├── loadThreadHistory(tid, cachedLeaf) → 恢复到上次查看的分支
  └── 若 cachedLeaf 存在且最后 assistant 缺 _leafCheckpointId → 补全并缓存

叶子持久化（正常对话流）
  └── messages watcher → 最后一条 assistant 的 _leafCheckpointId → persistBranchLeaf()
```

---

## 7. 分支对话继续（sendMessage 传递 checkpoint_id）

```
用户发送新消息（在分支上下文中）
  │
  └── useChatStream.sendMessage()
      ├── 追加 user msg 到 messages[]
      ├── 从后往前查找最后一条 assistant 的 _leafCheckpointId
      ├── 若存在 → 传入 body.checkpoint_id
      └── POST /chat/{id}/stream → body: { messages, checkpoint_id? }
          └── 后端 stream_chat: config["configurable"]["checkpoint_id"] = checkpoint_id
              → LangGraph 从指定检查点状态继续执行（而非默认最新状态）
              → 确保 fork 后新消息沿当前分支继续，不走错分支
```

> **关键**：`_leafCheckpointId` 是前端字段，后端 `get-messages-history` 不返回。
> 刷新后需要从 `pickCheckpointFromCache`、`loadBranchLeaf()`、`cachedLeaf` 兜底逐层恢复，
> 否则 sendMessage 无法找到当前分支的叶子检查点，后端将使用默认状态走错分支。

---

## 8. 用户消息大纲导航

```
ChatView.vue
  └── useContentNav(ctrl.messages, ctrl.streamingContent)
        ├── computed: navItems = 提取所有 user 消息
        │     └── { messageIndex, preview(40字符截断), anchorId: "msg-nav-{index}" }
        ├── watch(navItems) → 同步到模块级 _outlineItems (shallowRef)
        └── hasContent = computed(navItems.length > 0)

ChatMessages.vue
  └── 每条消息容器添加 :id="`msg-nav-${index}`" 锚点

sidebar/OutlineTab.vue（大纲 Tab）
  ├── useOutlineItems() → 读取模块级 outlineItems
  ├── IntersectionObserver → 高亮当前视口消息 (activeOutlineId)
  ├── 点击条目 → document.getElementById(anchorId).scrollIntoView()
  └── Tab badge 显示条目总数
```
