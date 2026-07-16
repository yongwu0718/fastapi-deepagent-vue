# Branching chat

与 AI agent 的对话很少是线性的。您可能想要重新措辞一个问题、重新生成一个不喜欢的回复，或探索不同的对话路径而不丢失 checkpoint 历史记录。分支聊天将 LangGraph checkpoint 用作分叉点：每次编辑或重新生成都会从所选消息的父 checkpoint 提交新的运行。

<Note>
  此功能需要 [LangGraph Agent Server](../langgraph/local-server)。使用 `langgraph dev` 在本地运行您的 agent 或 [将其部署到 LangSmith](/langsmith/deployment) 以使用此模式。
</Note>

## 什么是分支聊天？

分支聊天将对话视为一个带有 checkpoint 的时间线，而非平面列表。每条消息都有指向创建该消息之前 checkpoint 的 metadata。编辑消息或重新生成回复会从该 checkpoint 提交新的运行。

关键功能：

* **编辑任意用户消息**：重写之前的提示，并从该点重新运行 agent
* **重新生成任意 AI 回复**：让 agent 为相同输入生成不同的答案
* **检查历史记录**：当需要分支时间线时，使用 LangGraph client 加载 checkpoint

## 设置 stream metadata

将 root stream 用于消息，然后在渲染每条消息的组件中读取每条消息的 checkpoint metadata。metadata 包含用于分叉的父 checkpoint ID。

  代码示例使用 `useStream<typeof myAgent>` 获得类型安全的 stream state。有关后端类型推断，请参阅 [Python](/oss/python/langchain/frontend/overview#type-inference) 或 [JavaScript](/oss/javascript/langchain/frontend/overview#type-inference)。

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

## 理解 message metadata

`useMessageMetadata(stream, messageId)` 辅助函数为单条消息返回 [MessageMetadata](https://reference.langchain.com/javascript/langchain-react/MessageMetadata)。在渲染每条消息的组件中使用它，使 metadata 的作用域限定在该消息 ID：

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

`parentCheckpointId` 是消息之前紧邻的 checkpoint。将其用作编辑和重新生成的分叉点。

## 编辑消息

要编辑用户消息并分叉对话：

1. 从消息的 metadata 获取 `parentCheckpointId`
2. 使用 `forkFrom: { checkpointId }` 提交编辑后的消息
3. agent 从该点重新运行

```ts theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
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

编辑后：

* agent 从分叉点以更新后的消息重新运行
* 原始路径在 thread 历史记录中仍然可用

## 重新生成回复

要在不更改输入的情况下重新生成 AI 回复：

1. 从 AI 消息的 metadata 获取 `parent_checkpoint`
2. 提交空输入和 `forkFrom: { checkpointId }`
3. agent 从该点生成新的回复

```ts theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
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

每次重新生成都会在该位置为 AI 消息创建新路径。

<Tip>
  重新生成对于非确定性 agent 非常有用。由于 LLM 的输出会随 temperature 变化，重新生成相同的提示通常会生成有意义的不同的回复。
</Tip>

## 分支在底层如何工作

LangGraph 将每个 state 转换持久化为一个 **checkpoint**。当您使用 `forkFrom` 提交时，后端从该点开始新的执行路径，而非追加到当前对话。结果是一个树形结构：

```
User: "What is React?"
  └─ AI: "React is a JavaScript library..." (branch A)
  └─ AI: "React is a UI framework..." (branch B, regenerated)

User: "Tell me about hooks" (branch A)
  └─ AI: "Hooks are functions..."

User: "Tell me about JSX" (edited from branch A)
  └─ AI: "JSX is a syntax extension..."
```

每条路径都保存在 checkpoint store 中。当您想要跨 checkpoint 构建单独的时间线视图时，使用 `stream.client.threads.getHistory(threadId)`。

## 最佳实践

* **在消息附近读取 metadata**：在渲染消息控件的组件中调用 `useMessageMetadata`。
* **在悬停时显示分叉控件**：编辑和重新生成按钮应在悬停时出现，以保持 UI 整洁。
* **按需刷新历史记录**：仅在渲染时间线或在分叉完成后调用 `client.threads.getHistory()`。
* **streaming 时禁用控件**：当 agent 正在主动流式传输回复时，不允许编辑或重新生成。在启用这些操作之前检查 `stream.isLoading`。
* **取消时保留编辑文本**：如果用户开始编辑后取消，将 textarea 重置为原始消息内容。
* **使用深度 checkpoint 树进行测试**：频繁编辑和重新生成的用户可能会创建许多路径。确保时间线渲染保持高性能。