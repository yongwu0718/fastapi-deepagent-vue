# Time travel（时间旅行）

> 检查、导航并从对话历史中的任何 checkpoint 恢复执行

LangGraph agent 中的每次状态更改都会创建一个 **checkpoint**，即该时刻 agent 状态的完整快照。Time travel 允许您检查任何 checkpoint，查看 agent 持有的确切状态，并**从该点恢复执行**以探索替代路径。它集调试器、撤销按钮和审计日志于一体。

## checkpoint 的工作原理

LangGraph 在每次节点执行后持久化 agent 状态。每个持久化状态都是一个 `ThreadState` 对象，它捕获了：

* **checkpoint**：标识此特定快照的元数据（ID、时间戳）
* **values**：此时完整的 agent 状态（消息、自定义键）
* **tasks**：计划接下来运行的图节点
* **next**：执行计划中即将到来的节点名称

这创建了一个线性时间线，记录了 agent 做出的每一个决策、调用的每一个工具以及产生的每一个响应。您的 UI 可以渲染此时间线并让用户跳转到任何点。

## 设置 useStream

通过向 `useStream` 传递 `fetchStateHistory: true` 来启用 checkpoint 历史记录。这告诉 hook 加载当前 thread 的完整 checkpoint 时间线。

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
import { ref, watch } from "vue";

const AGENT_URL = "http://localhost:2024";
const threadId = ref<string | null>(null);
const history = ref<ThreadState[]>([]);

const stream = useStream<typeof myAgent>({
  apiUrl: AGENT_URL,
  assistantId: "time_travel",
  threadId,
  onThreadId: (id) => (threadId.value = id),
});

watch(
  [threadId, stream.isLoading],
  async ([id, isLoading]) => {
    if (isLoading) return;
    history.value = id
      ? ((await stream.client.threads.getHistory(id)) as ThreadState[])
      : [];
  },
  { immediate: true },
);

function resumeFrom(cp: ThreadState) {
  stream.submit({}, {
    forkFrom: { checkpointId: cp.checkpoint.checkpoint_id },
  });
}
</script>

<template>
  <div class="flex h-screen">
    <ChatPanel :messages="stream.messages.value" />
    <TimelineSidebar :history="history" @select="resumeFrom" />
  </div>
</template>
```

## ThreadState 对象

`history` 数组中的每个条目都是一个 `ThreadState`，代表时间线中的一个 checkpoint：

```ts
interface ThreadState {
  checkpoint: {
    checkpoint_id: string;
    checkpoint_ns: string;
  };
  values: Record<string, any>;
  tasks: Array<{
    id: string;
    name: string;
    interrupts?: unknown[];
  }>;
  next: string[];
}
```

| 属性 | 描述 |
| --- | --- |
| `checkpoint` | 标识此快照。将其传递给 `submit` 以从此处恢复 |
| `values` | 此时完整的 agent 状态，包括 `messages` 和任何自定义状态键 |
| `tasks` | 在此 checkpoint 运行的图节点，包括其名称和任何 interrupt |
| `next` | 计划在此 checkpoint 之后执行的节点名称 |

## 构建 checkpoint 时间线

时间线侧边栏将每个 checkpoint 显示为一个可点击的条目。每个条目显示运行的节点以及此时存在的消息数量：

```tsx
function TimelineSidebar({
  history,
  onSelect,
}: {
  history: ThreadState[];
  onSelect: (cp: ThreadState) => void;
}) {
  return (
    <div className="timeline-sidebar">
      <h3>Checkpoint 时间线</h3>
      <div className="timeline-entries">
        {history.map((cp, i) => {
          const taskName = cp.tasks?.[0]?.name ?? "unknown";
          const msgCount = (cp.values?.messages as unknown[])?.length ?? 0;

          return (
            <button
              key={cp.checkpoint.checkpoint_id}
              onClick={() => onSelect(cp)}
              className="w-full rounded-lg border bg-white p-3 text-left
                         hover:border-blue-400 hover:shadow-sm transition-all"
            >
              <div className="flex items-center gap-2">
                <span className="checkpoint-index">#{i + 1}</span>
                <span className="checkpoint-task">{taskName}</span>
              </div>
              <div className="text-xs text-gray-500">
                {msgCount} 条消息{msgCount !== 1 ? "" : ""}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

## 检查 checkpoint 状态

点击一个 checkpoint 应显示该点的完整状态。JSON 查看器为开发者提供了 agent 知道什么以及决定了什么的完全可见性：

```tsx
function CheckpointInspector({ checkpoint }: { checkpoint: ThreadState }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="checkpoint-inspector">
      <h4>Checkpoint {checkpoint.checkpoint.checkpoint_id.slice(0, 8)}...</h4>
      <div className="meta">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-blue-600 hover:underline"
        >
          {expanded ? "折叠" : "展开"} 状态
        </button>
        <div>
          <strong>节点：</strong>
          {checkpoint.tasks?.[0]?.name ?? "—"}
        </div>
        <div>
          <strong>下一个：</strong>
          {checkpoint.next?.join(", ") || "—"}
        </div>
        <div>
          <strong>消息：</strong>
          {(checkpoint.values?.messages as unknown[])?.length ?? 0}
        </div>
      </div>
      {expanded && (
        <pre className="state-json">
          {JSON.stringify(checkpoint.values, null, 2)}
        </pre>
      )}
    </div>
  );
}
```

对于生产环境 UI，请考虑使用带有可折叠节点的适当 JSON 查看器组件，而不是原始的 `JSON.stringify`。像 `react-json-view` 或 `react-json-tree` 这样的库可以为用户提供更好的探索体验。

## 从 checkpoint 恢复

Time travel 的核心是能够**从任何先前的 checkpoint 恢复执行**。当用户选择一个 checkpoint 时，使用 `null` 输入调用 `submit` 并传递 checkpoint 引用：

```ts
stream.submit(null, { checkpoint: selectedCheckpoint.checkpoint });
```

这告诉 LangGraph：

1. 回滚到所选 checkpoint 的状态
2. 从该点向前重新执行图
3. 将新结果流式传输到客户端

所选 checkpoint 之后的现有消息将被新的执行路径替换。这有效地在对话时间线中创建了一个**分支**。

从 checkpoint 恢复并不会删除原始时间线。先前的 checkpoint 在历史记录中仍然可用。这意味着用户始终可以返回并尝试不同的路径，而不会丢失任何先前的工作。

## SplitView 布局

Time travel 最适合采用分割布局，左侧是主聊天区，右侧是时间线：

```tsx
function TimeTravelLayout() {
  const stream = useStream({
    apiUrl: AGENT_URL,
    assistantId: "time_travel",
    fetchStateHistory: true,
  });

  const [selectedCheckpoint, setSelectedCheckpoint] =
    useState<ThreadState | null>(null);

  const history = stream.history ?? [];

  return (
    <div className="split-layout">
      {/* 主聊天区域 */}
      <div className="chat-area">
        <div className="messages">
          {stream.messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
        </div>
        <ChatInput
          onSubmit={(text) =>
            stream.submit({ messages: [{ type: "human", content: text }] })
          }
          isLoading={stream.isLoading}
        />
      </div>

      {/* 时间线侧边栏 */}
      <div className="timeline-panel">
        <TimelineSidebar
          history={history}
          selected={selectedCheckpoint}
          onSelect={setSelectedCheckpoint}
          onResume={(cp) =>
            stream.submit(null, { checkpoint: cp.checkpoint })
          }
        />
        {selectedCheckpoint && (
          <CheckpointInspector checkpoint={selectedCheckpoint} />
        )}
      </div>
    </div>
  );
}
```

## 提取 checkpoint 元数据

将原始 checkpoint 数据转换为时间线中显示友好的条目：

```ts
function formatCheckpoints(history: ThreadState[]) {
  return history.map((cp, index) => ({
    index,
    id: cp.checkpoint?.checkpoint_id,
    taskName: cp.tasks?.[0]?.name ?? "unknown",
    messageCount: (cp.values?.messages as unknown[])?.length ?? 0,
    hasInterrupts: cp.tasks?.some((t) => t.interrupts?.length) ?? false,
    nextNodes: cp.next ?? [],
  }));
}
```

这使得使用有意义的标签而不是原始 ID 来渲染时间线条目变得容易。

## 用例

Time travel 在许多场景中都非常宝贵：

* **调试 agent 行为**：逐步跟踪 agent 的决策，以理解它为什么选择特定路径
* **撤销操作**：如果 agent 走错了方向，可以从较早的 checkpoint 恢复并重试
* **探索替代方案**：从对话中途的 checkpoint 分叉，看看不同的输入如何改变结果
* **审计**：审查 agent 操作的完整历史，用于合规、质量保证或事后分析
* **教学**：逐步演示 agent 的执行过程，以解释多步骤推理的工作原理

Time travel 在与 human-in-the-loop 模式结合使用时尤其强大。如果人工审核者在 interrupt 时拒绝了 agent 的操作，他们可以从操作执行前的 checkpoint 恢复并提供纠正性输入。

## 在时间线中处理 interrupt

包含 interrupt（human-in-the-loop 暂停）的 checkpoint 需要特殊的视觉处理。它们代表 agent 停止并等待人工输入的时刻：

```tsx
function TimelineEntry({
  checkpoint,
  index,
}: {
  checkpoint: ThreadState;
  index: number;
}) {
  const hasInterrupt = checkpoint.tasks?.some(
    (t) => t.interrupts && t.interrupts.length > 0
  );

  return (
    <div
      className={`rounded-lg border p-3 ${
        hasInterrupt
          ? "border-amber-300 bg-amber-50"
          : "border-gray-200 bg-white"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="checkpoint-index">#{index + 1}</span>
        {hasInterrupt && (
          <span className="interrupt-badge">
            Interrupt
          </span>
        )}
      </div>
      <div className="checkpoint-task">
        {checkpoint.tasks?.[0]?.name ?? "—"}
      </div>
    </div>
  );
}
```

## 最佳实践

* **懒加载历史记录**：对于包含数百个 checkpoint 的 thread，进行分页或仅加载最近的 N 个条目，以保持 UI 响应灵敏。
* **显示有意义的标签**：显示节点名称和消息计数，而不是原始 checkpoint ID。用户需要的是上下文，而不是 UUID。
* **恢复前确认**：从旧 checkpoint 恢复会替换当前的执行路径。显示确认对话框，以免用户意外丢失当前对话状态。
* **高亮当前 checkpoint**：在视觉上明确哪个 checkpoint 对应于对话的当前状态。
* **支持键盘导航**：高级用户会希望使用箭头键逐步浏览 checkpoint。向时间线添加键盘处理程序，以获得流畅的调试体验。
* **比较 checkpoint 之间的状态差异**：对于高级用户，显示两个连续 checkpoint 之间发生的变化可以揭示 agent 的状态在每一步是如何演变的。