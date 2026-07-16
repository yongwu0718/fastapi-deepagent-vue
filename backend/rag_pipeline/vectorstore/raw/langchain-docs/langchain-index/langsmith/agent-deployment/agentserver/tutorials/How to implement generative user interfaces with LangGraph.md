# 如何利用 LangGraph 实现生成式用户界面

**前置要求**

- LangSmith
- Agent Server
- `useStream()` React Hook

生成式用户界面（Generative UI）允许代理超越文本，生成丰富的用户界面。这使得创建更具交互性和上下文感知能力的应用成为可能，界面会根据对话流程和 AI 响应动态调整。

LangSmith 支持将您的 React 组件与 graph 代码放在一起。这样您可以专注于为 graph 构建特定的 UI 组件，同时轻松接入现有聊天界面（如 Agent Chat），并仅在需要时加载代码。

## 教程

### 1. 定义并配置 UI 组件

首先，创建您的第一个 UI 组件。对于每个组件，您需要提供一个唯一标识符，以便在 graph 代码中引用该组件。

```tsx
const WeatherComponent = (props: { city: string }) => {
  return Weather for {props.city};
};

export default {
  weather: WeatherComponent,
};
```

接下来，在 `langgraph.json` 配置文件中定义您的 UI 组件：

```json
{
  "node_version": "20",
  "graphs": {
    "agent": "./src/agent/index.ts:graph"
  },
  "ui": {
    "agent": "./src/agent/ui.tsx"
  }
}
```

`ui` 部分指向将被 graphs 使用的 UI 组件。默认情况下，我们建议使用与 graph 名称相同的键，但您也可以随意拆分组件，更多详情请参阅自定义 UI 组件的命名空间。

LangSmith 将自动打包您的 UI 组件代码和样式，并将其作为外部资源提供，这些资源可以通过 `LoadExternalComponent` 组件加载。像 `react` 和 `react-dom` 这样的依赖项将被自动排除在打包文件之外。

CSS 和 Tailwind 4.x 也开箱即用，因此您可以在 UI 组件中自由使用 Tailwind 类以及 `shadcn/ui`。

```tsx
import "./styles.css";

const WeatherComponent = (props: { city: string }) => {
  return Weather for {props.city};
};

export default {
  weather: WeatherComponent,
};
```

```css
@import "tailwindcss";
```

### 2. 在 graph 中发送 UI 组件

```python
import uuid
from typing import Annotated, Sequence, TypedDict

from langchain.messages import AIMessage
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer, push_ui_message

class AgentState(TypedDict):  # noqa: D101
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

async def weather(state: AgentState):
    class WeatherOutput(TypedDict):
        city: str

    weather: WeatherOutput = (
        await ChatOpenAI(model="gpt-5.4-mini")
        .with_structured_output(WeatherOutput)
        .with_config({"tags": ["nostream"]})
        .ainvoke(state["messages"])
    )

    message = AIMessage(
        id=str(uuid.uuid4()),
        content=f"Here's the weather for {weather['city']}",
    )

    # Emit UI elements associated with the message
    push_ui_message("weather", weather, message=message)
    return {"messages": [message]}

workflow = StateGraph(AgentState)
workflow.add_node(weather)
workflow.add_edge("__start__", "weather")
graph = workflow.compile()
```

### 3. 在 React 应用中处理 UI 元素

在客户端，您可以使用 `useStream()` 和 `LoadExternalComponent` 来显示 UI 元素。

```tsx
"use client";

import { useStream } from "@langchain/langgraph-sdk/react";
import { LoadExternalComponent } from "@langchain/langgraph-sdk/react-ui";

export default function Page() {
  const { thread, values } = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "agent",
  });

  return (
    
      {thread.messages.map((message) => (
        
          {message.content}
          {values.ui
            ?.filter((ui) => ui.metadata?.message_id === message.id)
            .map((ui) => (
              
            ))}
        
      ))}
    
  );
}
```

在幕后，`LoadExternalComponent` 将从 LangSmith 获取 UI 组件的 JS 和 CSS，并在影子 DOM 中渲染它们，从而确保与应用程序其余部分的样式隔离。

## 操作指南

### 在客户端提供自定义组件

如果您已经在客户端应用中加载了组件，可以直接提供一个组件映射，无需从 LangSmith 获取 UI 代码即可直接渲染。

```tsx
const clientComponents = {
  weather: WeatherComponent,
};

<LoadExternalComponent
  stream={thread}
  message={ui}
  components={clientComponents}
/>;
```

### 组件加载时显示加载 UI

您可以在组件加载时提供一个后备 UI 进行渲染。

```tsx
<LoadExternalComponent
  stream={thread}
  message={ui}
  fallback={Loading...}
/>
```

### 自定义 UI 组件的命名空间

默认情况下，`LoadExternalComponent` 将使用 `useStream()` 钩子中的 `assistantId` 来获取 UI 组件的代码。您可以通过向 `LoadExternalComponent` 组件提供 `namespace` 属性来自定义这一点。

```tsx
<LoadExternalComponent
  stream={thread}
  message={ui}
  namespace="custom-namespace"
/>
```

```json
{
  "ui": {
    "custom-namespace": "./src/agent/ui.tsx"
  }
}
```

### 从 UI 组件访问并与 thread 状态交互

您可以通过使用 `useStreamContext` 钩子在 UI 组件内部访问 thread 状态。

```tsx
import { useStreamContext } from "@langchain/langgraph-sdk/react-ui";

const WeatherComponent = (props: { city: string }) => {
  const { thread, submit } = useStreamContext();
  return (
    <>
      <div>Weather for {props.city}</div>

      <button
        onClick={() => {
          const newMessage = {
            type: "human",
            content: `What's the weather in ${props.city}?`,
          };

          submit({ messages: [newMessage] });
        }}
      >
        Retry
      </button>
    </>
  );
};
```

### 向客户端组件传递额外上下文

您可以通过向 `LoadExternalComponent` 组件提供 `meta` 属性，向客户端组件传递额外上下文。

```tsx
<LoadExternalComponent stream={thread} message={ui} meta={{ userId: "123" }} />
```

然后，您可以在 UI 组件中使用 `useStreamContext` 钩子访问 `meta` 属性。

```tsx
import { useStreamContext } from "@langchain/langgraph-sdk/react-ui";

const WeatherComponent = (props: { city: string }) => {
  const { meta } = useStreamContext<
    { city: string },
    { MetaType: { userId?: string } }
  >();

  return (
    <div>
      Weather for {props.city} (user: {meta?.userId})
    </div>
  );
};
```

### 从服务器流式传输 UI 消息

您可以使用 `useStream()` 钩子的 `onCustomEvent` 回调，在节点执行完成之前流式传输 UI 消息。这对于在 LLM 生成响应时更新 UI 组件特别有用。

```tsx
import { uiMessageReducer } from "@langchain/langgraph-sdk/react-ui";

const { thread, submit } = useStream({
  apiUrl: "http://localhost:2024",
  assistantId: "agent",
  onCustomEvent: (event, options) => {
    options.mutate((prev) => {
      const ui = uiMessageReducer(prev.ui ?? [], event);
      return { ...prev, ui };
    });
  },
});
```

然后，您可以通过调用 `ui.push()` / `push_ui_message()` 并传入与要更新的 UI 消息相同的 ID 来向 UI 组件推送更新。

```python
from typing import Annotated, Sequence, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain.messages import AIMessage, AIMessageChunk, BaseMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, push_ui_message, ui_message_reducer

class AgentState(TypedDict):  # noqa: D101
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

class CreateTextDocument(TypedDict):
    """Prepare a document heading for the user."""

    title: str

async def writer_node(state: AgentState):
    model = ChatAnthropic(model="claude-sonnet-4-6")
    message: AIMessage = await model.bind_tools(
        tools=[CreateTextDocument],
        tool_choice={"type": "tool", "name": "CreateTextDocument"},
    ).ainvoke(state["messages"])

    tool_call = next(
        (x["args"] for x in message.tool_calls if x["name"] == "CreateTextDocument"),
        None,
    )

    if tool_call:
        ui_message = push_ui_message("writer", tool_call, message=message)
        ui_message_id = ui_message["id"]

        # We're already streaming the LLM response to the client through UI messages
        # so we don't need to stream it again to the `messages` stream mode.
        content_stream = model.with_config({"tags": ["nostream"]}).astream(
            f"Create a document with the title: {tool_call['title']}"
        )

        content: AIMessageChunk | None = None
        async for chunk in content_stream:
            content = content + chunk if content else chunk

            push_ui_message(
                "writer",
                {"content": content.text()},
                id=ui_message_id,
                message=message,
                # Use `merge=True` to merge props with the existing UI message
                merge=True,
            )

    return {"messages": [message]}
```
### 从状态中移除 UI 消息

类似于可以通过追加 `RemoveMessage` 来从状态中移除消息，您可以通过调用 `remove_ui_message` / `ui.delete` 并传入 UI 消息的 ID 来从状态中移除 UI 消息。

```python
from langgraph.graph.ui import push_ui_message, delete_ui_message

# push message
message = push_ui_message("weather", {"city": "London"})

# remove said message
delete_ui_message(message["id"])
```

## 了解更多

- JS/TS SDK 参考