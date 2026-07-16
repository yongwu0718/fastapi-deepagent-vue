# Markdown 消息

> 将 LLM 响应渲染为丰富、带格式的 Markdown，并提供完善的流式支持

LLM 会自然地生成带 Markdown 格式的文本，包括标题、列表、代码块、表格和内联格式。如果将这些内容以纯文本形式渲染，就浪费了模型所提供的结构。本模式将向你展示如何在所有主流前端框架中，实时解析并渲染从 Agent 流式传输而来的 Markdown。

## Markdown 渲染的工作原理

渲染流程分为三个步骤：

1. **receive：** 当新 token 到达时，`useStream` 会将流式文本累积到每条 AI 消息的 `msg.text` 中，并响应式地更新。
2. **parse：** 一个 Markdown 解析器将原始文本转换为 HTML（或 React 元素树）。每次更新都会执行解析，但对于聊天长度的内容（5 KB 消息耗时 < 5 ms）来说足够快。
3. **render：** 解析后的输出被渲染到 DOM 中。React 使用虚拟 DOM diff；Vue 和 Svelte 则使用 `v-html` / `{@html}` 配合经过净化的 HTML。

## 设置 useStream

Markdown 模式使用一个简单的聊天 Agent，无需特殊配置。使用你的 Agent URL 和 assistantId 直接连接 `useStream`。

定义一个与 Agent 状态结构相匹配的 TypeScript 接口，并将其作为类型参数传递给 `useStream`，以便对状态值进行类型安全的访问。在下面的示例中，请将 `typeof myAgent` 替换为你自己的接口名称：

```python
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```

```python
import { useStream } from "@langchain/react";
import { AIMessage, HumanMessage } from "@langchain/core/messages";

const AGENT_URL = "http://localhost:2024";

export function Chat() {
  const stream = useStream({
    apiUrl: AGENT_URL,
    assistantId: "simple_agent",
  });

  return (
    <div>
      {stream.messages.map((msg) => {
        if (AIMessage.isInstance(msg)) {
          return <div key={msg.id}>{msg.text}</div>;
        }
        if (HumanMessage.isInstance(msg)) {
          return <div key={msg.id}>{msg.text}</div>;
        }
      })}
    </div>
  );
}
```

## 选择 Markdown 库

每个框架都有对应的 Markdown 渲染方案：

| 框架     | 库                               | 输出                            | 原因                                                                 |
| -------- | -------------------------------- | ------------------------------- | -------------------------------------------------------------------- |
| React    | `react-markdown` + `remark-gfm`  | React 元素                      | 基于组件、虚拟 DOM diff，不使用 `dangerouslySetInnerHTML`           |
| Vue      | `marked` + `dompurify`           | 通过 `v-html` 使用经过净化的 HTML | 轻量、快速，内置 GFM                                                 |
| Svelte   | `marked` + `dompurify`           | 通过 `{@html}` 使用经过净化的 HTML | 与 Vue 相同，API 一致                                                |
| Angular  | `marked` + `dompurify`           | 通过 `[innerHTML]` 使用经过净化的 HTML | 与 Vue / Svelte 相同                                                 |

React 的 `react-markdown` 直接将 Markdown 转换为 React 元素，因此不需要对 HTML 进行净化，也不涉及 `dangerouslySetInnerHTML`。对于 Vue、Svelte 和 Angular，在渲染之前务必使用 `dompurify` 对解析后的 HTML 进行净化。

## 构建 Markdown 组件

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {children}
    </ReactMarkdown>
  );
}
```

## 净化 HTML 输出

当将解析后的 Markdown 作为原始 HTML 渲染时（`v-html`、`{@html}`、`[innerHTML]`），必须对输出进行净化，以防止跨站脚本攻击（XSS）。LLM 的响应可能包含任意文本，其中可能包括会被 Markdown 解析器转换成可执行 HTML 的标记内容。

使用 `dompurify` 来移除危险元素：

```ts
import DOMPurify from "dompurify";

const safeHtml = DOMPurify.sanitize(rawHtml);
```

DOMPurify 会移除 `<script>` 标签、`onclick` 属性、`javascript:` 链接以及其他 XSS 攻击载体，同时保留安全的 Markdown 输出，如标题、列表、代码块、表格和链接。

React 的 `react-markdown` 不需要 `dompurify`，因为它直接生成 React 元素，不涉及原始 HTML 的注入。

## 流式传输的注意事项

`useStream` 会在每个 token 到达时响应式地更新 `msg.text`。Markdown 组件会在每次更新时重新解析。对于典型的聊天消息，这样的性能是可以接受的：

* `marked` 的解析速度约为 1 MB/s。一条 5 KB 的消息耗时 < 5 ms。
* `react-markdown` + remark 流水线对聊天长度的内容同样快速。
* 浏览器的布局引擎能够高效地处理 DOM 更新。

对于非常长的响应（> 50 KB），可以考虑以下优化：

* **节流渲染：** 使用 `requestAnimationFrame` 将更新控制在每秒 60 帧，而不是在每个 token 上都重新渲染。
* **增量解析：** 只解析新增的内容并追加到已渲染的缓冲区中（高级技巧，通常聊天 UI 不需要）。

对于大多数聊天应用来说，每次更新时重新解析完整消息的简单方法已经足够。只有在遇到长消息导致滚动卡顿或掉帧时，才需要优化。

## 为 Markdown 内容添加样式

通过为 `.markdown-content` 类应用样式来控制渲染 Markdown 的外观。以下是一些核心样式：

```css
.markdown-content p {
  margin: 0.4em 0;
}

.markdown-content ul,
.markdown-content ol {
  margin: 0.4em 0;
  padding-left: 1.4em;
}

.markdown-content pre {
  overflow-x: auto;
  border-radius: 0.375rem;
  background: rgba(0, 0, 0, 0.05);
  padding: 0.5rem;
  font-size: 0.75rem;
}

.markdown-content code {
  border-radius: 0.25rem;
  background: rgba(0, 0, 0, 0.08);
  padding: 0.125rem 0.25rem;
  font-size: 0.75rem;
}

.markdown-content blockquote {
  margin: 0.4em 0;
  padding-left: 0.75em;
  border-left: 3px solid currentColor;
  opacity: 0.8;
}

.markdown-content table {
  border-collapse: collapse;
  margin: 0.4em 0;
}

.markdown-content th,
.markdown-content td {
  border: 1px solid #e5e7eb;
  padding: 0.25em 0.5em;
}
```

为聊天气泡保持紧凑的 Markdown 样式。聊天消息通常比博客文章小，因此应该使用比典型正文样式更紧凑的边距和稍小的字体尺寸。

## 最佳实践

* **始终净化：** 当使用 `v-html`、`{@html}` 或 `[innerHTML]` 时，务必将解析后的输出通过 `dompurify` 净化。永远不要信任由 LLM 输出内容经 Markdown 解析器生成的原始 HTML。
* **启用 GFM：** GitHub Flavored Markdown 提供了表格、删除线、任务列表和自动链接。LLM 通常会使用这些特性。
* **处理空内容：** 在解析之前检查空字符串，避免渲染出空的容器。
* **使用 `breaks: true`：** 启用换行转换，使 LLM 输出中的单个换行符渲染为 `<br>` 而不是被忽略。LLM 经常使用单个换行符进行视觉分隔。
* **针对聊天上下文设计样式：** 使用适合聊天气泡的紧凑边距和尺寸，而不是全宽的文章布局。
* **用丰富内容测试：** 验证标题、嵌套列表、含有长行的代码块、宽表格以及引用块的渲染效果，以发现溢出或布局问题。