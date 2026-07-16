# Message queues（消息队列）

> 将多条消息排入队列，并在 agent 顺序处理时管理它们

Message queuing 允许用户连续快速发送多条消息，而无需等待 agent 完成当前消息的处理。每条消息都在服务器端入队并按顺序处理，让您对 pending 队列拥有完全的可见性和控制力。

此功能需要 LangGraph Agent Server。使用 `langgraph dev` 在本地运行您的 agent，或将其部署到 LangSmith 以使用此模式。

## 为什么需要 message queues？

在典型的聊天界面中，用户必须等待 agent 完成响应后才能发送另一条消息。这在以下几种场景中会造成阻碍：

* **批量提问**：用户希望一次性提出五个相关问题，而不是等待每个答案
* **连续追问**：在 agent 仍在工作时提交澄清或补充上下文
* **自动化测试序列**：以编程方式发送一系列提示词来验证 agent 行为
* **数据录入工作流**：逐一输入结构化数据以进行处理

Message queuing 通过立即接受所有提交并按顺序处理它们来解决这个问题。

## 工作原理

在底层，LangGraph 使用 `multitaskStrategy: "enqueue"` 来管理并发提交。当 agent 正在处理时提交一条消息，该消息会被添加到服务器端队列中。当前运行完成后，下一条排队消息会被自动拾取。

`useStream` hook 暴露了一个 `queue` 属性，提供对 pending 消息的实时可见性：

| 属性 | 类型 | 描述 |
| --- | --- | --- |
| `queue.entries` | `QueueEntry[]` | 所有 pending 队列条目的数组 |
| `queue.size` | `number` | 当前队列中的条目数量 |
| `queue.cancel(id)` | `(id: string) => Promise` | 通过 ID 取消特定的排队条目 |
| `queue.clear()` | `() => Promise` | 取消所有排队条目 |

每个 `QueueEntry` 对象包含：

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| `id` | `string` | 此队列条目的唯一标识符 |
| `values` | `object` | 提交的输入值（包括消息） |
| `options` | `object` | 随提交传递的任何附加选项 |
| `createdAt` | `string` | 条目创建的 ISO 时间戳 |

## 设置 `useStream`

定义一个与 agent 状态结构相匹配的 TypeScript 接口，并将其作为类型参数传递给 `useStream`，以便对状态值进行类型安全的访问。在下面的示例中，请将 `typeof myAgent` 替换为您自己的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```
**react**
```tsx
import { useStream } from "@langchain/react";

function Chat() {
  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "message_queue",
  });

  const handleSubmit = (text: string) => {
    stream.submit({
      messages: [{ type: "human", content: text }],
    });
  };

  // 访问队列状态
  const pendingCount = stream.queue.size;
  const entries = stream.queue.entries;

  return (
    <div>
      <MessageList messages={stream.messages} />
      {pendingCount > 0 && (
        <QueueList entries={entries} queue={stream.queue} />
      )}
      <InputForm onSubmit={handleSubmit} />
    </div>
  );
}
```
## 显示队列

构建一个 `QueueList` 组件，显示每条 pending 消息并附带取消按钮。这使用户能够看到正在等待的内容，并能够移除不再需要的条目。

```tsx
function QueueList({ entries, queue }) {
  return (
    <div className="queue-panel">
      <h3>排队消息 ({entries.length})</h3>
      <button onClick={() => queue.clear()}>清除全部</button>

      {entries.map((entry) => {
        const text = entry.values?.messages?.[0]?.content ?? "未知";
        return (
          <div key={entry.id} className="queue-item">
            <span className="queue-preview">{text}</span>
            <span className="queue-time">
              {new Date(entry.createdAt).toLocaleTimeString()}
            </span>
            <button
              className="queue-cancel"
              onClick={() => queue.cancel(entry.id)}
            >
              取消
            </button>
          </div>
        );
      })}
    </div>
  );
}
```

显示每条排队消息的前几个字符作为预览，以便用户能够快速识别要取消的条目，而无需阅读完整消息。

## 取消排队消息

您有两个级别的取消操作：

### 取消单个条目

通过其 ID 从队列中移除特定消息。Agent 将跳过它并移至下一个条目。

```ts
await queue.cancel(entryId);
```

### 清空整个队列

一次性移除所有 pending 消息。当用户更改上下文或想要重新开始时很有用。

```ts
await queue.clear();
```

取消队列条目仅影响**尚未开始处理**的消息。如果 agent 已在处理某条消息，从队列中取消它不会产生任何效果。使用 `stream.stop()` 来中断当前运行。

## 使用 `onCreated` 链接后续提交

`onCreated` 回调会在新运行创建时触发，为您提供一个以编程方式提交后续消息的钩子。这对于构建多步骤工作流非常有用，其中下一个问题依赖于前一个提交被接受。

```ts
stream.submit(
  { messages: [{ type: "human", content: "什么是量子计算？" }] },
  {
    onCreated(run) {
      console.log("Run created:", run.run_id);
      // 链接一个后续问题
      stream.submit({
        messages: [{ type: "human", content: "给我一个简单的类比。" }],
      });
    },
  }
);
```

这种模式会自然地填充队列。第一条消息立即开始处理，而后续消息则排在其后。

## 启动新 thread

当用户想要开始一个全新的对话时，使用 `switchThread(null)` 创建一个新 thread。这会清除当前消息历史和队列。

**react**
```tsx
function NewThreadButton() {
  const stream = useStream({ /* ... */ });

  return (
    <button onClick={() => stream.switchThread(null)}>
      新对话
    </button>
  );
}
```
## 完整示例

综合以上，这是一个具备队列管理功能的完整聊天组件：

```tsx
function QueueChat() {
  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "message_queue",
  });

  const [input, setInput] = useState("");

  const handleSubmit = () => {
    if (!input.trim()) return;
    stream.submit({
      messages: [{ type: "human", content: input.trim() }],
    });
    setInput("");
  };

  return (
    <div className="chat-container">
      <h1>Queue Chat</h1>
      <button onClick={() => stream.switchThread(null)}>新 thread</button>

      <div className="messages">
        {stream.messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {stream.isLoading && <LoadingIndicator />}
      </div>

      {stream.queue.size > 0 && (
        <div className="queue-sidebar">
          <h3>排队中 ({stream.queue.size})</h3>
          <button onClick={() => stream.queue.clear()}>清除全部</button>
          {stream.queue.entries.map((entry) => (
            <div key={entry.id} className="queue-item">
              <span>{entry.values?.messages?.[0]?.content}</span>
              <button onClick={() => stream.queue.cancel(entry.id)}>×</button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入消息（您可以发送多条！）"
        />
        <button type="submit">发送</button>
      </form>
    </div>
  );
}
```

## 最佳实践

* **限制队列大小**：虽然客户端对队列大小没有硬性限制，但要注意过大的队列可能会降低用户体验。考虑当队列超过合理阈值（例如 10 条）时显示警告。
* **显示队列位置**：为每个排队项编号，以便用户了解处理顺序。
* **保持输入焦点**：提交后保持输入字段聚焦，以便用户可以立即输入下一条消息。
* **动画过渡**：当条目从队列面板移入消息列表开始处理时，平滑地移动它们。
* **优雅地处理错误**：如果排队消息失败，请显示错误而不阻塞后续队列条目。
* **对快速提交进行防抖**：对于自动化或以编程方式进行的提交，在消息之间添加小延迟以避免压垮服务器。