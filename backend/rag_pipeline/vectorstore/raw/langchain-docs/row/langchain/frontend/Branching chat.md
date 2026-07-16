# 分支对话（Branching chat）

与 AI agent 的对话很少是线性的。你可能想重新表述一个问题、重新生成一个不满意的回复，或者探索不同的对话路径，同时又不想丢失 checkpoints 历史。Branching chat 利用 LangGraph checkpoints 作为分支点（fork point）：每次编辑或重新生成，都会从所选消息的 parent checkpoint 开始提交一次新的运行。

## 什么是 branching chat？

Branching chat 将对话视为一条基于 checkpoints 的时间线，而不是一个扁平的列表。每条消息都带有 metadata，指向该消息被创建前的 checkpoint。编辑一条消息或重新生成一次回复，都会从该 checkpoint 提交一次新的运行。关键能力：

- **编辑任何用户消息：** 重写之前的提示，并从该点重新运行 agent
- **重新生成任何 AI 回复：** 对同一个输入，要求 agent 给出不同的回答
- **查看历史：** 当你需要分支时间线时，使用 LangGraph 客户端加载 checkpoints

## 设置流式 metadata

使用根 stream 获取消息，然后在渲染每条消息的组件中读取每条消息的 checkpoint metadata。该 metadata 中包含要 fork 的 parent checkpoint ID。

**Vue**

```vue
<script setup lang="ts">
import { useStream } from "@langchain/vue";

const AGENT_URL = "http://localhost:2024";

const stream = useStream<typeof myAgent>({
  apiUrl: AGENT_URL,
  assistantId: "simple_agent",
});
</script>

<template>
  <div>
    <MessageWithForkControls
      v-for="msg in stream.messages.value"
      :key="msg.id"
      :stream="stream"
      :message="msg"
    />
  </div>
</template>
```

## 理解消息 metadata

`useMessageMetadata(stream, messageId)` 辅助函数会返回某条消息的 [MessageMetadata](https://reference.langchain.com/javascript/langchain-react/MessageMetadata)。请在渲染每条消息的组件中使用它，以便 metadata 的作用域始终限定在该消息 ID 上：

```ts
import type { BaseMessage } from "langchain";
import { useState } from "react";
import { useMessageMetadata, useStream } from "@langchain/react";

function Chat() {
  const stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "simple_agent",
  });

  return stream.messages.map((message) => (
    <MessageWithForkControls
      key={message.id}
      stream={stream}
      message={message}
    />
  ));
}

function MessageWithForkControls({
  stream,
  message,
}: {
  stream: ReturnType<typeof useStream>;
  message: BaseMessage;
}) {
  const metadata = useMessageMetadata(stream, message.id);
  const checkpointId = metadata?.parentCheckpointId;
  const [editedText, setEditedText] = useState(message.text);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (!checkpointId) return;

        stream.submit(
          { messages: [{ type: "human", content: editedText }] },
          { forkFrom: { checkpointId } }
        );
      }}
    >
      <textarea
        value={editedText}
        onChange={(event) => setEditedText(event.target.value)}
      />
      <button disabled={!checkpointId || editedText === message.text}>
        Submit edited branch
      </button>
    </form>
  );
}
```

`parentCheckpointId` 就是该消息之前的那个 checkpoint。将其用作编辑和重新生成时的 fork point。

## 编辑一条消息

要编辑用户消息并 fork 对话：

1. 从消息的 metadata 中获取 `parentCheckpointId`
2. 使用 `forkFrom: { checkpointId }` 提交编辑后的消息
3. agent 将从该点重新运行

```ts
function handleEdit(
  stream: ReturnType<typeof useStream>,
  originalMsg: HumanMessage,
  metadata: MessageMetadata | undefined,
  newText: string
) {
  if (!metadata?.parentCheckpointId) return;

  stream.submit(
    {
      messages: [{ type: "human", content: newText }],
    },
    { forkFrom: { checkpointId: metadata.parentCheckpointId } }
  );
}
```

编辑完成后：

- agent 会从 fork point 开始使用更新后的消息重新运行
- 原始路径在 thread 历史中仍然可用

## 重新生成一次回复

要在不改变输入的情况下重新生成 AI 回复：

1. 从该 AI 消息的 metadata 中获取 `parent_checkpoint`
2. 使用空输入并附带 `forkFrom: { checkpointId }` 进行提交
3. agent 将从该点生成一个新的回复

```ts
function handleRegenerate(
  stream: ReturnType<typeof useStream>,
  metadata: MessageMetadata | undefined
) {
  if (!metadata?.parentCheckpointId) return;

  stream.submit(undefined, {
    forkFrom: { checkpointId: metadata.parentCheckpointId },
  });
}
```

每次重新生成都会为该位置的 AI 消息创建一条新的路径。

## 底层分支是如何工作的

LangGraph 会将每一次状态变迁持久化为一个 **checkpoint**。当你使用 `forkFrom` 提交时，后端会从那个点开始一条新的执行路径，而不是追加到当前对话之后。最终形成一个树形结构：

```
User: "What is React?"
  └─ AI: "React is a JavaScript library..." (branch A)
  └─ AI: "React is a UI framework..." (branch B, regenerated)

User: "Tell me about hooks" (branch A)
  └─ AI: "Hooks are functions..."

User: "Tell me about JSX" (edited from branch A)
  └─ AI: "JSX is a syntax extension..."
```

每一条路径都被持久化在 checkpoint 存储中。当你需要基于多个 checkpoints 构建独立的时间线视图时，可使用 `stream.client.threads.getHistory(threadId)`。

## 最佳实践

- **在消息附近读取 metadata：** 在渲染消息控件的组件中调用 `useMessageMetadata`。
- **在悬停时显示 fork 控件：** 编辑和重新生成按钮应在悬停时出现，以保持 UI 整洁。
- **按需刷新历史：** 仅在渲染时间线或在 fork 完成后，调用 `client.threads.getHistory()`。
- **在 streaming 期间禁用控件：** 当 agent 正在流式输出响应时，不允许进行编辑或 regenerate。在启用这些操作前，请检查 `stream.isLoading`。
- **取消时保留编辑文本：** 如果用户开始编辑后又取消，请将 textarea 重置为原始消息内容。
- **对深层 checkpoint 树进行测试：** 频繁编辑和重新生成的用户会创建大量路径。请确保时间线渲染保持性能良好。