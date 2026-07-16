# Join & rejoin streams（加入与重新加入流）

> 断开与重新连接到正在运行的 agent stream

Join and rejoin 允许您在不停止 agent 的情况下断开与正在运行的 agent stream 的连接，然后再重新连接到它。Agent 在客户端离开时继续在服务器端执行，而您可以准确地在中断的地方继续接收 stream。

此功能需要 LangGraph Agent Server。使用 `langgraph dev` 在本地运行您的 agent，或将其部署到 LangSmith 以使用此模式。

## 为什么需要 join & rejoin？

传统的 streaming API 会将客户端和服务器紧密耦合：如果客户端断开连接，stream 就会丢失。Join and rejoin 打破了这种耦合，从而支持几种重要的模式：

* **网络中断**：在基站或 Wi-Fi 网络之间切换的移动用户可以无缝恢复
* **页面导航**：用户离开聊天页面后稍后返回，而不会丢失进度
* **移动端后台化**：被操作系统挂起的应用可以在回到前台时重新加入 stream
* **长时间运行的任务**：agent 执行持续数分钟的操作（研究、代码生成、数据分析），而用户无需保持页面打开
* **多设备切换**：在手机上开始对话，在桌面上重新加入

## 核心概念

join/rejoin 模式涉及三个关键机制：

| 方法 / 选项 | 用途 |
| --- | --- |
| `stream.stop()` | 断开客户端与 stream 的连接，而不停止 agent |
| `stream.joinStream(runId)` | 通过其 run ID 重新连接到现有的 stream |
| `onDisconnect: "continue"` | 提交选项，告知服务器在客户端断开后继续运行 |
| `streamResumable: true` | 提交选项，使 stream 能够在以后被重新加入 |

`stream.stop()` 与取消运行有着根本性的不同。停止操作仅断开**客户端**。Agent 在服务器端继续处理。要真正取消 agent 的执行，您需要使用 interrupt 或 cancel 机制。

## 设置 `useStream`

关键的设置步骤是从 `onCreated` 回调中捕获 `run_id`，以便稍后可以重新加入。

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
import { useState } from "react";

function Chat() {
  const [savedRunId, setSavedRunId] = useState(null);

  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "join_rejoin",
    onCreated(run) {
      setSavedRunId(run.run_id);
    },
  });

  const isConnected = stream.isLoading;

  return (
    <div>
      <MessageList messages={stream.messages} />
      <ConnectionStatus connected={isConnected} />
      <ChatControls
        stream={stream}
        savedRunId={savedRunId}
        isConnected={isConnected}
      />
    </div>
  );
}
```
## 使用可恢复的选项进行提交

当您提交消息时，请传递 `onDisconnect: "continue"` 和 `streamResumable: true` 来启用 join/rejoin 流程：

```ts
stream.submit(
  { messages: [{ type: "human", content: text }] },
  {
    onDisconnect: "continue",
    streamResumable: true,
  }
);
```

| 选项 | 默认值 | 描述 |
| --- | --- | --- |
| `onDisconnect` | `"cancel"` | 客户端断开连接时发生的情况。`"continue"` 使 agent 继续运行；`"cancel"` 则停止它。 |
| `streamResumable` | `false` | 当为 `true` 时，服务器保留 stream 状态，以便客户端稍后可以重新加入。 |

请务必同时使用这两个选项。在没有 `streamResumable: true` 的情况下设置 `onDisconnect: "continue"` 意味着 agent 会继续运行，但您无法重新加入 stream 以查看其输出。

## 断开与 stream 的连接

调用 `stream.stop()` 来断开客户端连接。Agent 在服务器端继续处理。

```ts
stream.stop();
```

调用 `stop()` 后：

* `stream.isLoading` 变为 `false`
* 消息列表会保留在断开点之前收到的所有消息
* Agent 在服务器上继续运行
* 在重新加入之前不会收到任何新消息

## 重新加入一个 stream

使用保存的 run ID 调用 `stream.joinStream(runId)` 来重新连接：

```ts
stream.joinStream(savedRunId);
```

重新加入后：

* `stream.isLoading` 再次变为 `true`
* 在断开连接期间生成的任何消息都会被传递
* 新的 streaming 消息会实时恢复
* 如果 agent 已经完成，您会立即收到最终状态

## 构建连接状态指示器

一个视觉指示器可帮助用户了解他们是否正在主动从 agent 接收更新。

```tsx
function ConnectionStatus({ connected }: { connected: boolean }) {
  return (
    <div className="connection-status">
      <span
        className={`status-dot ${connected ? "connected" : "disconnected"}`}
      />
      <span>
        {connected ? "Connected" : "Disconnected"}
      </span>
    </div>
  );
}
```

使用绿色/红色圆点设置指示器样式：

```css
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
}

.status-dot.connected {
  background-color: #22c55e;
  box-shadow: 0 0 4px #22c55e;
}

.status-dot.disconnected {
  background-color: #ef4444;
  box-shadow: 0 0 4px #ef4444;
}
```

## 断开连接和重新连接控件

提供明确的断开和重新连接按钮，以便用户拥有完全的控制权：

```tsx
function ChatControls({ stream, savedRunId, isConnected }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    stream.submit(
      { messages: [{ type: "human", content: input.trim() }] },
      { onDisconnect: "continue", streamResumable: true }
    );
    setInput("");
  };

  return (
    <div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="输入消息..."
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
      />
      <button onClick={handleSend}>发送</button>

      {isConnected ? (
        <button onClick={() => stream.stop()} className="disconnect-btn">
          断开连接
        </button>
      ) : (
        savedRunId && (
          <button
            onClick={() => stream.joinStream(savedRunId)}
            className="rejoin-btn"
          >
            重新加入 stream
          </button>
        )
      )}
    </div>
  );
}
```

## 持久化 run ID

对于跨会话重新加入（例如，用户关闭浏览器后稍后返回），将 run ID 持久化到存储中：

```ts
const stream = useStream({
  apiUrl: "http://localhost:2024",
  assistantId: "join_rejoin",
  onCreated(run) {
    localStorage.setItem("activeRunId", run.run_id);
  },
});

// 页面加载时，检查是否有活动运行
const existingRunId = localStorage.getItem("activeRunId");
if (existingRunId) {
  stream.joinStream(existingRunId);
}
```

持久化的 run ID 应在运行完成时清理。监听 stream 完成并移除存储的 ID，以避免尝试重新加入已完成的运行。

## 错误处理

如果运行已过期、已被删除或服务器已重启，重新加入可能会失败。优雅地处理这些情况：

```ts
try {
  stream.joinStream(savedRunId);
} catch (error) {
  console.error("重新加入 stream 失败:", error);
  // 清除过时的 run ID 并通知用户
  setSavedRunId(null);
  localStorage.removeItem("activeRunId");
}
```

## 完整示例

```tsx
function JoinRejoinChat() {
  const [savedRunId, setSavedRunId] = useState(null);
  const [input, setInput] = useState("");

  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "join_rejoin",
    onCreated(run) {
      setSavedRunId(run.run_id);
    },
  });

  const isConnected = stream.isLoading;

  const handleSend = () => {
    if (!input.trim()) return;
    stream.submit(
      { messages: [{ type: "human", content: input.trim() }] },
      { onDisconnect: "continue", streamResumable: true }
    );
    setInput("");
  };

  return (
    <div className="chat-container">
      <h1>Join & Rejoin 演示</h1>

      <ConnectionStatus connected={isConnected} />

      <div className="messages">
        {stream.messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入消息..."
        />
        <button type="submit">发送</button>
      </form>

      <div className="controls">
        {isConnected ? (
          <button onClick={() => stream.stop()}>
            断开连接
          </button>
        ) : (
          savedRunId && (
            <button onClick={() => stream.joinStream(savedRunId)}>
              重新加入 stream
            </button>
          )
        )}
      </div>
    </div>
  );
}
```

## 最佳实践

* **始终保存 run ID**：没有它，重新加入是不可能的。同时使用组件状态和持久化存储以提高弹性。
* **显示清晰的连接状态**：用户应始终知道他们是在接收实时更新还是查看快照。
* **在可见性更改时自动重新加入**：使用 Page Visibility API 在用户返回标签页时自动重新加入。
* **设置合理的超时**：如果重新加入尝试花费太长时间，则回退到获取 thread 历史记录。
* **清理已完成的运行**：当 agent 完成时移除持久化的 run ID，以避免过时的重新加入尝试。