# Tool calling

> 使用丰富、类型安全的 UI 卡片展示 Agent 的工具调用

Agent 可以调用外部工具，例如天气 API、计算器、网页搜索、数据库查询等。返回的结果是原始 JSON。本模式将向你展示如何为 Agent 发出的每一个工具调用渲染结构化、类型安全的 UI 卡片，并包含加载状态和错误处理。

## 工具调用的工作原理

当 LangGraph Agent 决定需要外部数据时，它会在 AI 消息中发出一个或多个 **tool calls**。每个 tool call 包含：

* **name**：被调用的工具名称（例如 `"get_weather"`、`"calculator"`）
* **args**：传递给 tool 的结构化参数
* **id**：用于关联调用及其结果的唯一标识符

Agent 运行时执行该 tool，结果以 `ToolMessage` 的形式返回。`useStream` hook 将所有信息统一成一个可以直接渲染的 `toolCalls` 数组。

## 设置 useStream

第一步是将 `useStream` 连接到你的 Agent 后端。该 hook 返回响应式状态，其中包含一个 `toolCalls` 数组，该数组会随着 Agent 流式传输而实时更新。

定义一个与 Agent 状态结构相匹配的 TypeScript 接口，并将其作为类型参数传递给 `useStream`，以便对状态值进行类型安全的访问。在下面的示例中，请将 `typeof myAgent` 替换为你自己的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```

```tsx
import { useStream } from "@langchain/react";

const AGENT_URL = "http://localhost:2024";

export function Chat() {
  const stream = useStream({
    apiUrl: AGENT_URL,
    assistantId: "tool_calling",
  });

  return (
    <div>
      {stream.messages.map((msg) => (
        <Message key={msg.id} message={msg} toolCalls={stream.toolCalls} />
      ))}
    </div>
  );
}
```
## ToolCallWithResult 类型

`toolCalls` 数组中的每一项都是一个 `ToolCallWithResult` 对象：

```ts
interface ToolCallWithResult {
  call: {
    id: string;
    name: string;
    args: Record<string, any>;
  };
  result: ToolMessage | undefined;
  state: "pending" | "completed" | "error";
}
```

| 属性         | 描述                                                         |
| ------------ | ------------------------------------------------------------ |
| `call.id`    | 与 AI 消息中 `tool_calls` 条目相匹配的唯一 ID                |
| `call.name`  | tool 的名称（例如 `"get_weather"`）                          |
| `call.args`  | Agent 传递给 tool 的结构化参数                               |
| `result`     | `ToolMessage` 响应，在 tool 执行完成后可用                   |
| `state`      | 生命周期状态：`"pending"` 表示执行中，`"completed"` 表示成功，`"error"` 表示失败 |

## 按消息过滤 tool calls

一条 AI 消息可能触发多个 tool calls，而你的聊天界面中可能包含多条 AI 消息。为了在每条消息下方正确渲染相应的 tool 卡片，可以通过将 `call.id` 与消息的 `tool_calls` 数组进行匹配来过滤：

```tsx
function Message({
  message,
  toolCalls,
}: {
  message: AIMessage;
  toolCalls: ToolCallWithResult[];
}) {
  const messageToolCalls = toolCalls.filter((tc) =>
    message.tool_calls?.find((t) => t.id === tc.call.id)
  );

  return (
    <div>
      <div>{message.content}</div>
      {messageToolCalls.map((tc) => (
        <ToolCard key={tc.call.id} toolCall={tc} />
      ))}
    </div>
  );
}
```

## 构建专用的 tool 卡片

不是直接展示原始 JSON，而是为每个 tool 构建专用的 UI 组件。使用 `call.name` 来选择正确的卡片：

```tsx
function ToolCard({ toolCall }: { toolCall: ToolCallWithResult }) {
  if (toolCall.state === "pending") {
    return <LoadingCard name={toolCall.call.name} />;
  }

  if (toolCall.state === "error") {
    return <ErrorCard name={toolCall.call.name} error={toolCall.result} />;
  }

  switch (toolCall.call.name) {
    case "get_weather":
      return <WeatherCard args={toolCall.call.args} result={toolCall.result} />;
    case "calculator":
      return (
        <CalculatorCard args={toolCall.call.args} result={toolCall.result} />
      );
    case "web_search":
      return <WebSearchCard args={toolCall.call.args} result={toolCall.result} />;
    default:
      return <GenericCard toolCall={toolCall} />;
  }
}
```

### 天气卡片示例

```tsx
function WeatherCard({
  args,
  result,
}: {
  args: { location: string };
  result: ToolMessage;
}) {
  const data = JSON.parse(result.content as string);

  return (
    <div className="weather-card">
      <strong>{args.location}</strong>
      <span>{data.temperature}°F</span>
      <span>{data.condition}</span>
    </div>
  );
}
```

### 加载与错误状态

务必处理 pending 和 error 状态，以便给用户明确的反馈：

```tsx
function LoadingCard({ name }: { name: string }) {
  return (
    <div className="tool-card loading">
      <span>Running {name}...</span>
    </div>
  );
}

function ErrorCard({ name, error }: { name: string; error?: ToolMessage }) {
  return (
    <div className="tool-card error">
      <span>Error in {name}</span>
      <div className="error-detail">
        {error?.content ?? "Tool execution failed"}
      </div>
    </div>
  );
}
```

## 类型安全的 tool 参数

如果你的 tool 使用结构化 schema 定义，可以使用 `ToolCallFromTool` 工具类型来获得完全类型化的 `args`：

```ts
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const getWeather = tool(async ({ location }) => { /* ... */ }, {
  name: "get_weather",
  description: "Get the current weather for a location",
  schema: z.object({
    location: z.string().describe("City name"),
  }),
});

type WeatherToolCall = ToolCallFromTool<typeof getWeather>;
// WeatherToolCall.call.args 现在是 { location: string }
```

使用 `ToolCallFromTool` 可以在编译时提供安全保证。如果 tool schema 发生变化，你的 UI 组件会立即提示类型错误。

## 在流式文本中内联渲染 tool calls

Tool calls 通常会与流式文本交错出现。`useStream` hook 会使 `toolCalls` 与流保持同步，因此一旦 Agent 发出调用（在 tool 完成执行之前），pending 卡片就会立即显示。

这意味着用户会看到：

1. AI 的文本实时流入
2. 当 tool call 发出时立即显示一个加载卡片
3. 当 tool 完成后，卡片更新为显示结果

Tool calls 会在原地更新。同一个 `call.id` 会从 `"pending"` 过渡到 `"completed"`（或 `"error"`），因此你的 UI 会使用新状态重新渲染同一个组件。

## 处理多个并发 tool calls

Agent 可以并行调用多个 tool。`toolCalls` 数组中会同时包含多个 `state: "pending"` 的条目。每个调用会独立完成，因此你的 UI 应该优雅地处理部分完成的情况：

```tsx
function ToolCallList({ toolCalls }: { toolCalls: ToolCallWithResult[] }) {
  const pending = toolCalls.filter((tc) => tc.state === "pending");
  const completed = toolCalls.filter((tc) => tc.state === "completed");

  return (
    <div>
      {completed.map((tc) => (
        <ToolCard key={tc.call.id} toolCall={tc} />
      ))}
      {pending.map((tc) => (
        <ToolCard key={tc.call.id} toolCall={tc} />
      ))}
    </div>
  );
}
```

## 最佳实践

在构建 tool 调用 UI 时，请遵循以下准则：

* **始终处理全部三种状态**：`pending`、`completed` 和 `error`。用户不应该看到空白的卡片。
* **安全地解析结果**。Tool 结果以字符串形式到达。将 `JSON.parse()` 包裹在 try/catch 中，并在解析失败时显示备用内容。
* **提供通用的备用卡片**。并非每个 tool 都需要定制卡片。对于未知的 tool 名称，可以渲染一个可折叠的 JSON 视图。
* **在加载期间展示 tool 名称和参数**。用户希望在结果到达之前就知道 Agent 正在做什么。
* **保持卡片紧凑**。Tool 卡片与聊天消息内联显示。避免使用过大的 widget 挤占对话空间。