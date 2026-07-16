# Human-in-the-Loop（人机协同）

> 通过基于 interrupt 的人工审核添加审批工作流

并非每个 agent 动作都应该在无监督下运行。当 agent 即将发送邮件、删除记录、执行金融交易或任何不可逆操作时，您需要人工先审核并批准该动作。Human-in-the-Loop（HITL）模式让您的 agent 暂停执行，将待处理的动作呈现给用户，并仅在明确批准后才恢复。

## interrupt 的工作原理

LangGraph agent 支持 **interrupt**，即显式的暂停点，agent 在此将控制权交还给客户端。当 agent 遇到一个 interrupt 时：

1. Agent 停止执行并发出一个 interrupt 载荷
2. `useStream` hook 通过 `stream.interrupt` 暴露出该 interrupt
3. 您的 UI 渲染一个包含批准/拒绝/编辑选项的审核卡片
4. 用户做出决定
5. 您的代码调用 `stream.submit()` 并传入恢复命令
6. Agent 从暂停处继续执行

## 为 HITL 设置 useStream

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

const AGENT_URL = "http://localhost:2024";

const stream = useStream<typeof myAgent>({
  apiUrl: AGENT_URL,
  assistantId: "human_in_the_loop",
});

function handleRespond(response: HITLResponse) {
  stream.submit(null, { command: { resume: response } });
}
</script>

<template>
  <div>
    <Message
      v-for="msg in stream.messages.value"
      :key="msg.id"
      :message="msg"
    />
    <ApprovalCard
      v-if="stream.interrupt.value"
      :interrupt="stream.interrupt.value"
      @respond="handleRespond"
    />
  </div>
</template>
```

## interrupt 载荷

当 agent 暂停时，`stream.interrupt` 包含一个具有以下结构的 `HITLRequest`：

```ts
interface HITLRequest {
  actionRequests: ActionRequest[];
  reviewConfigs: ReviewConfig[];
}

interface ActionRequest {
  action: string;
  args: Record<string, any>;
  description?: string;
}

interface ReviewConfig {
  allowedDecisions: ("approve" | "reject" | "edit" | "respond")[];
}
```

| 属性 | 描述 |
| --- | --- |
| `actionRequests` | agent 想要执行的待处理动作数组 |
| `actionRequests[].action` | 动作名称（例如 `"send_email"`、`"delete_record"`） |
| `actionRequests[].args` | 动作的结构化参数 |
| `actionRequests[].description` | 可选，对该动作功能的人类可读描述 |
| `reviewConfigs` | 针对每个动作的配置，控制允许哪些决策 |
| `reviewConfigs[].allowedDecisions` | 要显示的按钮：`"approve"`、`"reject"`、`"edit"`、`"respond"` |

## 决策类型

HITL 模式支持四种决策类型：

### 批准 (Approve)

用户确认动作应按原样执行：

```ts
const response: HITLResponse = {
  decision: "approve",
};

stream.submit(null, { command: { resume: response } });
```

### 拒绝 (Reject)

用户拒绝该动作，并可附带一个原因：

```ts
const response: HITLResponse = {
  decision: "reject",
  reason: "邮件语气过于强硬，请修改。",
};

stream.submit(null, { command: { resume: response } });
```

当动作被拒绝后，agent 会收到拒绝原因，并可以决定如何继续。它可能会重新措辞、提出澄清问题，或完全放弃该动作。

### 编辑 (Edit)

用户在批准前修改动作的参数：

```ts
const response: HITLResponse = {
  decisions: [
    {
      type: "edit",
      editedAction: {
        name: actionRequest.name,
        args: {
          ...actionRequest.args,
          subject: "Updated subject line",
          body: "Revised email body with softer language.",
        },
      },
    },
  ],
};

stream.submit(null, { command: { resume: response } });
```

### 回复 (Respond)

用户为“询问用户”类工具提供直接回复。`message` 会成为工具结果，而工具本身不会执行：

```ts
const response: HITLResponse = {
  decision: "respond",
  message: "蓝色。",
};

stream.submit(null, { command: { resume: response } });
```

当工具被设计为用于收集人工输入的占位符时（例如一个 `ask_user` 工具，提示 agent 从用户那里收集信息），请使用 `respond`。

## 构建 ApprovalCard

以下是一个完整的审批卡片组件，它处理了所有四种决策类型：

```tsx
function ApprovalCard({
  interrupt,
  onRespond,
}: {
  interrupt: { value: HITLRequest };
  onRespond: (response: HITLResponse) => void;
}) {
  const request = interrupt.value;
  const [editedArgs, setEditedArgs] = useState(
    request.actionRequests[0]?.args ?? {}
  );
  const [rejectReason, setRejectReason] = useState("");
  const [respondMessage, setRespondMessage] = useState("");
  const [mode, setMode] = useState("review");

  const action = request.actionRequests[0];
  const config = request.reviewConfigs[0];

  if (!action || !config) return null;

  return (
    <div className="rounded border p-4">
      <h3 className="text-lg font-bold">需要审核操作</h3>
      <p className="text-sm text-gray-600">
        {action.description ?? `Agent 想要执行：${action.action}`}
      </p>

      <pre className="my-2 rounded bg-gray-100 p-2 text-xs">
        {JSON.stringify(action.args, null, 2)}
      </pre>

      {mode === "review" && (
        <div className="flex gap-2">
          {config.allowedDecisions.includes("approve") && (
            <button
              className="rounded bg-green-600 px-4 py-2 text-white"
              onClick={() => onRespond({ decision: "approve" })}
            >
              批准
            </button>
          )}
          {config.allowedDecisions.includes("reject") && (
            <button
              className="rounded bg-red-600 px-4 py-2 text-white"
              onClick={() => setMode("reject")}
            >
              拒绝
            </button>
          )}
          {config.allowedDecisions.includes("edit") && (
            <button
              className="rounded bg-blue-600 px-4 py-2 text-white"
              onClick={() => setMode("edit")}
            >
              编辑
            </button>
          )}
          {config.allowedDecisions.includes("respond") && (
            <button
              className="rounded bg-purple-600 px-4 py-2 text-white"
              onClick={() => setMode("respond")}
            >
              回复
            </button>
          )}
        </div>
      )}

      {mode === "reject" && (
        <div className="mt-2">
          <textarea
            className="w-full rounded border p-2"
            placeholder="拒绝原因..."
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
          <button
            className="mt-2 rounded bg-red-600 px-4 py-2 text-white"
            onClick={() =>
              onRespond({ decision: "reject", reason: rejectReason })
            }
          >
            确认拒绝
          </button>
        </div>
      )}

      {mode === "edit" && (
        <div className="mt-2">
          <textarea
            className="w-full rounded border p-2 font-mono text-sm"
            value={JSON.stringify(editedArgs, null, 2)}
            onChange={(e) => {
              try {
                setEditedArgs(JSON.parse(e.target.value));
              } catch {
                // 编辑时允许无效 JSON
              }
            }}
          />
          <button
            className="mt-2 rounded bg-blue-600 px-4 py-2 text-white"
            onClick={() =>
              onRespond({ decision: "edit", args: editedArgs })
            }
          >
            提交修改
          </button>
        </div>
      )}

      {mode === "respond" && (
        <div className="mt-2">
          <textarea
            className="w-full rounded border p-2"
            placeholder="您的回复..."
            value={respondMessage}
            onChange={(e) => setRespondMessage(e.target.value)}
          />
          <button
            className="mt-2 rounded bg-purple-600 px-4 py-2 text-white"
            onClick={() =>
              onRespond({ decision: "respond", message: respondMessage })
            }
          >
            发送回复
          </button>
        </div>
      )}
    </div>
  );
}
```

## 恢复流程

用户做出决定后，完整的循环如下所示：

1. 调用 `stream.submit(null, { command: { resume: hitlResponse } })`
2. `useStream` hook 将恢复命令发送到 LangGraph 后端
3. Agent 收到 `HITLResponse` 并继续执行。HITL 响应可能是以下之一：
   * `"approve"`：agent 继续执行下一个动作
   * `"reject"`：agent 收到拒绝理由并决定下一步
   * `"edit"`：agent 使用编辑后的参数运行工具
   * `"respond"`：人工回复直接作为工具结果返回，而不执行工具
4. 当 agent 恢复流式传输时，`interrupt` 属性重置为 `null`

您可以在单个 agent 运行中串联多个 HITL 检查点。例如，一个 agent 可能会先请求搜索批准，然后在发送包含结果的邮件前再次请求批准。每个 interrupt 都是独立处理的。

## 常见用例

| 用例 | 动作 | 审核配置 |
| --- | --- | --- |
| 邮件发送 | `send_email` | `["approve", "reject", "edit"]` |
| 数据库写入 | `update_record` | `["approve", "reject"]` |
| 金融交易 | `transfer_funds` | `["approve", "reject"]` |
| 文件删除 | `delete_files` | `["approve", "reject"]` |
| 对外部服务的 API 调用 | `call_api` | `["approve", "reject", "edit"]` |
| 收集用户输入 | `ask_user` | `["respond"]` |

## 处理多个待处理动作

当 agent 想要一次执行多个动作时，一个 interrupt 可能包含多个 `actionRequests`。为每个动作渲染一个卡片，并在恢复前收集所有决策：

```tsx
function MultiActionReview({
  interrupt,
  onRespond,
}: {
  interrupt: { value: HITLRequest };
  onRespond: (responses: HITLResponse[]) => void;
}) {
  const [decisions, setDecisions] = useState<Record<number, HITLResponse>>({});
  const request = interrupt.value;

  const allDecided =
    Object.keys(decisions).length === request.actionRequests.length;

  return (
    <div>
      {request.actionRequests.map((action, i) => (
        <SingleActionCard
          key={i}
          action={action}
          config={request.reviewConfigs[i]}
          onDecide={(response) =>
            setDecisions((prev) => ({ ...prev, [i]: response }))
          }
        />
      ))}
      {allDecided && (
        <button
          className="rounded bg-green-600 px-4 py-2 text-white"
          onClick={() =>
            onRespond(
              request.actionRequests.map((_, i) => decisions[i])
            )
          }
        >
          提交所有决策
        </button>
      )}
    </div>
  );
}
```

## 最佳实践

在实现 HITL 工作流时，请牢记以下准则：

* **提供清晰的上下文**。始终显示 agent 想做什么以及*为什么*。包含动作描述和完整参数。
* **让批准成为最简单的路径**。如果动作看起来正确，批准应该只需点击一次。将多步骤流程留给拒绝/编辑。
* **验证编辑后的参数**。当用户编辑动作参数时，在发送之前验证 JSON 结构。对于格式错误的输入显示内联错误。
* **持久化 interrupt 状态**。如果用户刷新页面，interrupt 应该仍然可见。`useStream` 通过线程的检查点处理此问题。
* **记录所有决策**。为了审计追踪，记录每一次批准/拒绝/编辑决策，包括时间戳和做出决定的用户。
* **合理设置超时**。长时间运行的 agent 不应该无限期地阻塞在人工审核上。考虑显示 agent 已等待了多长时间。