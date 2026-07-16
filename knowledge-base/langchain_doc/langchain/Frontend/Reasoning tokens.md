# Reasoning tokens

> 在可折叠块中展示模型的 thinking 和 reasoning 过程

Reasoning tokens 公开了高级模型（如 OpenAI 的 o1/o3 和具有 extended thinking 功能的 Anthropic Claude）的内部思考过程。这些模型产生结构化的内容块，将 reasoning 与最终答案分开，让您能够构建展示模型*如何*得出其响应的 UI。

## 什么是 reasoning tokens？

当具有 reasoning 能力的模型处理一个提示词时，它们会生成两种不同类型的内容：

1. **Reasoning blocks**：模型的内部 chain-of-thought、问题分解以及逐步分析
2. **Text blocks**：呈现给用户的最终、精炼后的响应

这些内容作为 `AIMessage` 内带类型的内容块进行传递，可通过 `contentBlocks` 属性访问：

```ts
// Reasoning block
{ type: "reasoning", reasoning: "让我一步步思考..." }

// Text block
{ type: "text", text: "答案是 42。" }
```

并非所有模型都会产生 reasoning tokens。此模式专门适用于支持 extended thinking 或 chain-of-thought 输出的模型。标准聊天模型仅返回 text blocks。

## 用例

* **透明度**：向用户展示模型的 reasoning 过程，以建立对其答案的信任
* **调试**：检查模型的思考过程，以识别其出错的地方
* **教育工具**：通过揭示 AI 如何处理问题来教授学生解决问题的方法
* **决策支持**：让领域专家验证建议背后的 reasoning
* **质量保证**：在受监管行业中审计 reasoning 链条以确保合规

## 提取 reasoning 和 text blocks

`AIMessage` 上的 `contentBlocks` 数组包含所有按生成顺序排列的块。通过 `type` 进行过滤，以将 reasoning 与文本分开：

```ts
import { AIMessage } from "@langchain/core/messages";

function extractBlocks(msg: AIMessage) {
  const reasoningBlocks = msg.contentBlocks
    .filter((b) => b.type === "reasoning")
    .map((b) => b.reasoning);

  const textBlocks = msg.contentBlocks
    .filter((b) => b.type === "text")
    .map((b) => b.text);

  return {
    reasoning: reasoningBlocks.join(""),
    text: textBlocks.join(""),
  };
}
```

一条消息可能包含多个 reasoning blocks（例如，如果模型暂停其 reasoning、产生部分文本，然后又进一步 reasoning）。将它们连接起来即可得到完整的思考过程。

## 从 `useStream` 访问消息

定义一个与 agent 状态结构相匹配的 TypeScript 接口，并将其作为类型参数传递给 `useStream`，以便对状态值进行类型安全的访问。在下面的示例中，请将 `typeof myAgent` 替换为您自己的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```
**vue**
```tsx
<script setup lang="ts">
import { useStream } from "@langchain/vue";
import { AIMessage, HumanMessage } from "langchain";

const stream = useStream<typeof myAgent>({
  apiUrl: "http://localhost:2024",
  assistantId: "reasoning",
});
</script>

<template>
  <div class="messages">
    <template v-for="(msg, i) in stream.messages.value" :key="i">
      <HumanBubble v-if="HumanMessage.isInstance(msg)" :text="msg.text" />
      <AIResponse
        v-else-if="AIMessage.isInstance(msg)"
        :message="msg"
        :isStreaming="stream.isLoading.value && i === stream.messages.value.length - 1"
      />
    </template>
  </div>
</template>
```

## 构建 ThinkingBubble 组件

`ThinkingBubble` 将 reasoning tokens 呈现在一个视觉上截然不同的可折叠容器中。用户可以展开它以查看完整的思考过程，或将其折叠起来以专注于最终答案。

```tsx
import { useState } from "react";

function ThinkingBubble({
  reasoning,
  isStreaming,
}: {
  reasoning: string;
  isStreaming: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const charCount = reasoning.length;
  const previewLength = 120;
  const preview =
    reasoning.length > previewLength
      ? reasoning.slice(0, previewLength) + "..."
      : reasoning;

  return (
    <div className="thinking-bubble">
      <button
        className="thinking-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="thinking-icon">
          {isStreaming ? (
            <span className="thinking-spinner" />
          ) : (
            "💭"
          )}
        </span>
        <span className="thinking-title">
          {isStreaming ? "Thinking..." : `Thought process (${charCount} chars)`}
        </span>
        <span className={`chevron ${isExpanded ? "expanded" : ""}`}>▶</span>
      </button>

      {isExpanded && (
        <div className="thinking-content">
          {reasoning}
        </div>
      )}

      {!isExpanded && !isStreaming && (
        <div className="thinking-preview">{preview}</div>
      )}
    </div>
  );
}
```

### 为 ThinkingBubble 添加样式

通过独特的视觉处理将 reasoning blocks 与常规消息区分开来：

```css
.thinking-bubble {
  background-color: #f8f5ff;
  border: 1px solid #e2d9f3;
  border-radius: 8px;
  padding: 12px;
  margin: 8px 0;
  font-size: 0.9em;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  color: #6b21a8;
  font-weight: 500;
}

.thinking-content {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e2d9f3;
  white-space: pre-wrap;
  color: #4a4a4a;
  line-height: 1.5;
}

.thinking-preview {
  margin-top: 4px;
  color: #9ca3af;
  font-style: italic;
  font-size: 0.85em;
}

.chevron {
  margin-left: auto;
  transition: transform 0.2s;
}

.chevron.expanded {
  transform: rotate(90deg);
}
```

## Reasoning 的流式传输指示器

当模型仍在生成 reasoning tokens 时，显示一个动画指示器以传达思考正在进行中：

```css
.thinking-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #e2d9f3;
  border-top-color: #6b21a8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

在流式传输期间，默认将 ThinkingBubble 保持折叠状态，并仅显示 spinner。在流式传输过程中展开可能会随着新 token 的到来而导致布局抖动。应让用户在 reasoning 阶段完成后再展开。

## 渲染完整的 AI 响应

将 `ThinkingBubble` 和标准文本气泡组合成一个单一的 `AIResponse` 组件：

```tsx
function AIResponse({
  message,
  isStreaming,
}: {
  message: AIMessage;
  isStreaming: boolean;
}) {
  const reasoningBlocks = message.contentBlocks
    .filter((b) => b.type === "reasoning")
    .map((b) => b.reasoning)
    .join("");

  const textBlocks = message.contentBlocks
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("");

  const hasReasoning = reasoningBlocks.length > 0;
  const hasText = textBlocks.length > 0;

  const isReasoningPhase = isStreaming && !hasText;
  const isTextPhase = isStreaming && hasText;

  return (
    <div className="ai-response">
      {hasReasoning && (
        <ThinkingBubble
          reasoning={reasoningBlocks}
          isStreaming={isReasoningPhase}
        />
      )}
      {hasText && (
        <div className="text-bubble">
          {textBlocks}
          {isTextPhase && <span className="cursor-blink">▊</span>}
        </div>
      )}
    </div>
  );
}
```

## 处理边缘情况

### 没有 reasoning 的消息

并非每条 AI 消息都会包含 reasoning blocks。当 `contentBlocks` 只含有 text blocks 时，渲染一个不含 ThinkingBubble 的标准消息气泡。

### 空的 reasoning blocks

一些模型会产生空的 reasoning blocks 作为占位符。应将这些过滤掉：

```ts
const meaningfulReasoning = message.contentBlocks
  .filter((b) => b.type === "reasoning" && b.reasoning.trim().length > 0);
```

### 多个 reasoning-text 循环

一条消息可以在 reasoning blocks 和 text blocks 之间交替出现。如果您需要保留这种交错排列，请按顺序迭代 `contentBlocks`，而不是按类型分组：

```ts
message.contentBlocks.forEach((block) => {
  if (block.type === "reasoning") {
    // 渲染 ThinkingBubble
  } else if (block.type === "text") {
    // 渲染文本段落
  }
});
```

## 最佳实践

* **默认折叠**：按需展示 reasoning，而非默认展示
* **显示字符数**：让用户快速了解响应中包含了多少思考
* **视觉上加以区分**：使用不同的颜色、边框或背景，使 reasoning 绝不会与实际答案混淆
* **动画过渡**：平滑的展开/折叠动画可提升感知质量
* **考虑无障碍性**：在切换按钮上使用适当的 ARIA 属性（`aria-expanded`、`aria-controls`）
* **在预览中截断**：折叠时显示 reasoning 的简短预览，以便用户决定是否展开