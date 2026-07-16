# Generative UI（生成式 UI）

> 使用 json-render 渲染 AI 生成的用户界面

Generative UI 让 AI 能够从自然语言提示词生成完整的用户界面。AI 的输出**就是** UI，而不是在聊天气泡中渲染文本响应：表单、卡片、仪表盘等等。开发者定义哪些组件可用（即“catalog”），而 AI 将这些组件组合成一个有效的 UI 树。

此模式使用 json-render（生成式 UI 框架）来定义组件目录、使用 AI 生成 spec，并在 React、Vue、Svelte 和 Angular 中安全地渲染它们。

## 工作原理

1. **define a catalog**：声明 AI 可以使用哪些组件，并带有类型化的 props
2. **prompt the AI**：用自然语言描述您想要的 UI
3. **AI generates a spec**：一个描述组件树的 JSON 文档
4. **render safely**：json-render 的 `Renderer` 使用您的组件来渲染 spec

catalog 充当护栏：AI 只能使用您定义过的、其 props 与您的 schema 匹配的组件。输出始终是可预测且安全的。

## 定义组件 catalog

catalog 描述了 AI 被允许使用的每个组件。每个组件都有一个用于其 props 的 Zod schema，以及一个描述，AI 读取该描述以理解何时使用它：

```ts
import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/react/schema";
import { z } from "zod";

const catalog = defineCatalog(schema, {
  components: {
    Card: {
      description: "一个卡片容器，带有可选的标题和内边距",
      props: z.object({
        title: z.string().optional(),
        padding: z.enum(["sm", "md", "lg"]).optional(),
      }),
    },
    TextInput: {
      description: "一个文本输入字段，带有可选的标签和占位符",
      props: z.object({
        label: z.string().optional(),
        placeholder: z.string().optional(),
        type: z.enum(["text", "email", "password", "number", "textarea"]).optional(),
      }),
    },
    Button: {
      description: "一个可点击的按钮，带有标签和样式变体",
      props: z.object({
        label: z.string(),
        variant: z.enum(["primary", "secondary", "ghost", "link"]).optional(),
        fullWidth: z.boolean().optional(),
      }),
    },
  },
  actions: {},
});
```

保持 catalog 的聚焦。只包含 AI 在该用例中需要的组件。与“大杂烩”式的方法相比，更小的 catalog 能产生更好的结果。

## 构建组件注册表

注册表将每个 catalog 组件映射到其实际的渲染实现。使用 `defineRegistry` 可在 catalog props 和您的组件函数之间获得类型安全的绑定：

**react**
```tsx
import { defineRegistry, Renderer, JSONUIProvider } from "@json-render/react";

const { registry } = defineRegistry(catalog, {
  components: {
    Card: ({ props, children }) => (
      <div className="card">
        {props.title && <h2>{props.title}</h2>}
        {children}
      </div>
    ),
    TextInput: ({ props }) => (
      <div>
        {props.label && <label>{props.label}</label>}
        <input type={props.type ?? "text"} placeholder={props.placeholder} />
      </div>
    ),
    Button: ({ props }) => (
      <button className={`btn btn-${props.variant ?? "primary"}`}>
        {props.label}
      </button>
    ),
  },
});
```

## 连接到 agent

agent 使用 structured output 返回一个 json-render spec。使用您 agent 的 assistant ID 设置 `useStream`，然后从 AI 消息的 `tool_calls` 中提取 spec：

**react**
```tsx
import { useStream } from "@langchain/react";
import { AIMessage } from "@langchain/core/messages";

function GenerativeUI() {
  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "generative_ui",
  });

  const aiMessage = stream.messages.find(AIMessage.isInstance);
  const rawSpec = aiMessage?.tool_calls?.[0]?.args;

  // ... 过滤并渲染（参见下文的流式传输部分）
}
```
## 流式传输与渐进式渲染

在流式传输期间，spec 是逐步构建的。元素逐个到达，并且最初可能缺少 `type` 或 `props`。过滤出仅完整的元素，并将 `loading={true}` 传递给 `Renderer`，这告诉它静默跳过尚未到达的子元素。UI 逐个组件地构建起来：

```tsx
/*
 * 过滤流式传输的 spec，使其仅包含具有有效 type/props 的元素，
 * 从而在 AI 响应构建时实现渐进式渲染。将 loading={true} 传递给
 * Renderer 会告诉它静默跳过缺失的子元素。
 */
const spec = (() => {
  if (!rawSpec?.root || !rawSpec?.elements) return null;
  const rootEl = rawSpec.elements[rawSpec.root];
  if (!rootEl?.type || rootEl?.props == null) return null;

  const safeElements = {};
  for (const [key, el] of Object.entries(rawSpec.elements)) {
    if (el?.type && el?.props != null) {
      safeElements[key] = el;
    }
  }
  return { root: rawSpec.root, elements: safeElements };
})();

return (
  <>
    {spec && (
      <JSONUIProvider registry={registry}>
        <Renderer tree={spec} loading={stream.isLoading} />
      </JSONUIProvider>
    )}
  </>
);
```

需要 `JSONUIProvider` 来设置 json-render 的内部上下文提供者（状态、可见性、验证、操作）。`Renderer` 组件必须在其内部渲染。

## spec 格式

AI agent 生成一个扁平的 JSON spec，其中包含一个指向根元素的 `root` 键，以及一个包含所有组件的 `elements` 映射：

```json
{
  "root": "login-card",
  "elements": {
    "login-card": {
      "type": "Card",
      "props": { "title": "Login" },
      "children": ["login-stack"]
    },
    "login-stack": {
      "type": "Stack",
      "props": { "direction": "vertical", "gap": "md" },
      "children": ["email-input", "password-input", "submit-btn"]
    },
    "email-input": {
      "type": "TextInput",
      "props": { "label": "Email", "placeholder": "Enter your email", "type": "email" },
      "children": []
    },
    "password-input": {
      "type": "TextInput",
      "props": { "label": "Password", "placeholder": "Enter your password", "type": "password" },
      "children": []
    },
    "submit-btn": {
      "type": "Button",
      "props": { "label": "Sign In", "variant": "primary", "fullWidth": true },
      "children": []
    }
  }
}
```

每个元素通过 ID 引用其子元素，像 `TextInput` 和 `Button` 这样的叶子元素具有空的 `children` 数组。

## 最佳实践

* **使用描述性的组件描述**：AI 利用这些描述来理解何时使用每个组件。清晰的描述会带来更好的 UI 生成。
* **渲染前验证**：由于流式传输会传递部分数据，在传递给 Renderer 之前，始终检查元素是否具有有效的 `type` 和非空的 `props`。
* **为流式传输设计**：在流式传输期间传递 `loading={true}`，以便 Renderer 优雅地处理尚未到达的子元素。用户看到 UI 是实时构建的，而不是等待完整响应。
* **使用设计令牌进行样式设置**：使用 CSS 自定义属性，以便渲染的组件能自动适应浅色和深色主题。
* **用 JSONUIProvider 包装**：`Renderer` 必须位于 `JSONUIProvider` 内部，才能访问 json-render 用于状态、可见性和操作的内部上下文。