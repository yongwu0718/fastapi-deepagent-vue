# Structured output（结构化输出）

> 使用自定义 UI 组件而非纯文本来渲染结构化的 agent 响应

Structured output 让 agent 返回带类型的、机器可读的数据，而不是纯文本。您得到的不是单个字符串，而是一个结构化对象，可以将其映射到任何 UI：卡片、表格、图表、分步拆解或特定领域的渲染器。

## 什么是 structured output？

Agent 不是返回自由形式的文本响应，而是通过一个 tool call 返回符合预定义 schema 的结构化对象。这为您带来：

* **类型安全的数据**：将响应解析为已知的 TypeScript 类型
* **精确的渲染控制**：用各自独立的 UI 处理来渲染每个字段
* **一致的格式**：无论底层模型是什么，每个响应都遵循相同的结构

Agent 通过调用一个“structured output”工具来实现这一点，该工具的参数包含响应数据。该工具本身不执行任何逻辑，纯粹是返回带类型数据的载体。

## 用例

* **产品对比**：功能表格、优缺点列表、评分
* **数据分析**：包含指标、细分和亮点的摘要
* **分步指南**：带描述和代码片段的有序说明
* **食谱**：食材、步骤、时长和营养信息
* **数学和科学**：用 LaTeX 渲染的公式、分步推导
* **旅行规划**：包含日期、地点和费用估算的行程单

## 定义 schema

为 agent 返回的结构化数据定义一个 TypeScript 类型。此 schema 的结构决定了您如何渲染 UI。

以下是一个食谱助手的示例：

```ts
interface Ingredient {
  name: string;
  amount: string;
  unit: string;
}

interface RecipeStep {
  instruction: string;
  duration?: string;
}

interface Recipe {
  title: string;
  description: string;
  servings: number;
  ingredients: Ingredient[];
  steps: RecipeStep[];
  totalTime: string;
}
```

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| `title` | `string` | 食谱名称 |
| `description` | `string` | 菜肴简短描述 |
| `servings` | `number` | 用餐人数 |
| `ingredients` | `Ingredient[]` | 包含用量和单位的食材列表 |
| `steps` | `RecipeStep[]` | 有序的准备步骤 |
| `totalTime` | `string` | 预估的总准备和烹饪时间 |

您的 schema 可以是任何内容。无论形状如何，此模式的工作方式都是一样的。

## 从消息中提取 structured output

Structured output 位于最后一条 `AIMessage` 的 `tool_calls` 数组中。通过找到 AI 消息并访问第一个 tool call 的参数来提取它：

```ts
import { AIMessage } from "@langchain/core/messages";

function extractStructuredOutput<T>(messages: any[]): T | null {
  const aiMessages = messages.filter(AIMessage.isInstance);
  if (aiMessages.length === 0) return null;

  const lastAI = aiMessages[aiMessages.length - 1];
  const toolCall = lastAI.tool_calls?.[0];
  if (!toolCall) return null;

  return toolCall.args as T;
}
```

在 agent 完成流式传输之前，structured output 的 tool call 可能尚未填充 `args`。在流式传输期间，`args` 可能部分填充或为 `undefined`。在渲染之前，请务必检查其完整性。

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
import { AIMessage } from "@langchain/core/messages";

function RecipeChat() {
  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "recipe_assistant",
  });

  const recipe = extractStructuredOutput<Recipe>(stream.messages);

  return (
    <div>
      {!recipe && !stream.isLoading && (
        <InputForm
          onSubmit={(text) =>
            stream.submit({ messages: [{ type: "human", content: text }] })
          }
        />
      )}
      {stream.isLoading && <LoadingSpinner />}
      {recipe && <RecipeCard recipe={recipe} />}
    </div>
  );
}
```
## 渲染结构化数据

一旦有了类型化对象，就可以构建一个组件，将每个字段映射到合适的 UI 元素。这是该模式的核心：将结构化数据转变为专门构建的界面。

```tsx
function RecipeCard({ recipe }: { recipe: Recipe }) {
  return (
    <div className="recipe-card">
      <h2>{recipe.title}</h2>
      <p>{recipe.description}</p>
      <div className="meta">
        <span>{recipe.servings} 份</span>
        <span>{recipe.totalTime}</span>
      </div>

      <h3>食材</h3>
      <ul>
        {recipe.ingredients.map((ing, i) => (
          <li key={i}>
            {ing.amount} {ing.unit} {ing.name}
          </li>
        ))}
      </ul>

      <h3>步骤</h3>
      {recipe.steps.map((step, i) => (
        <div key={i} className="step">
          <strong>步骤 {i + 1}</strong>
          <p>{step.instruction}</p>
          {step.duration && (
            <span className="duration">{step.duration}</span>
          )}
        </div>
      ))}
    </div>
  );
}
```

相同的方法适用于任何领域。将每个字段映射到最能代表它的 UI 元素：

| 数据类型 | 渲染策略 |
| --- | --- |
| 纯文本 | 段落、标题、列表项 |
| 数字/指标 | 统计卡片、进度条、徽章 |
| 数组 | 列表、表格、网格 |
| 嵌套对象 | 嵌套卡片、手风琴式区域 |
| Markdown | Markdown 渲染器（如 `react-markdown`） |
| LaTeX/数学 | KaTeX 或 MathJax |
| 日期/时间 | 格式化时间戳、相对时间 |
| URL | 链接、嵌入式预览 |

## 处理部分流式数据

在流式传输期间，tool call 的参数可能是不完整的 JSON。在提取逻辑中对此进行防护：

```ts
function extractStructuredOutput<T>(
  messages: any[],
  requiredFields: string[] = [],
): T | null {
  const aiMessages = messages.filter(AIMessage.isInstance);
  if (aiMessages.length === 0) return null;

  const lastAI = aiMessages[aiMessages.length - 1];
  const toolCall = lastAI.tool_calls?.[0];
  if (!toolCall?.args) return null;

  const args = toolCall.args as Record<string, any>;
  const hasRequired = requiredFields.every(
    (field) => args[field] !== undefined
  );

  if (requiredFields.length > 0 && !hasRequired) return null;
  return args as T;
}
```

使用 `requiredFields` 参数，等待关键字段填充完毕后再渲染：

```ts
const recipe = extractStructuredOutput<Recipe>(stream.messages, [
  "title",
  "ingredients",
  "steps",
]);
```

## 在流式传输期间渐进式渲染

与其等待完整的 structured output，不如在字段到达时即时渲染。这会在 agent 仍在生成时给用户即时反馈：

```tsx
function ProgressiveRecipeCard({ messages }: { messages: any[] }) {
  const partial = extractStructuredOutput<Partial<Recipe>>(messages);
  if (!partial) return null;

  return (
    <div className="recipe-card">
      {partial.title && <h2>{partial.title}</h2>}
      {partial.description && <p>{partial.description}</p>}

      {partial.ingredients && partial.ingredients.length > 0 && (
        <div>
          <h3>食材</h3>
          <ul>
            {partial.ingredients.map((ing, i) => (
              <li key={i}>
                {ing.amount} {ing.unit} {ing.name}
              </li>
            ))}
          </ul>
        </div>
      )}

      {partial.steps && partial.steps.length > 0 && (
        <div>
          <h3>步骤</h3>
          {partial.steps.map((step, i) => (
            <div key={i} className="step">
              <strong>步骤 {i + 1}</strong>
              <p>{step.instruction}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

当 schema 具有自然的自上而下顺序时，渐进式渲染效果很好：先是标题，然后是描述，然后是详细信息。Agent 通常按 schema 顺序生成字段，因此 UI 会自然地逐步填充。

## 重置和重新提交

为了让用户在查看结果后提交新查询，添加一个启动新 thread 的按钮：

```tsx
{recipe && (
  <button onClick={() => stream.switchThread(null)}>
    重新开始
  </button>
)}
```

这会清除当前对话并让用户开始新的交互。

## 最佳实践

* **渲染前验证**：由于流式传输可能提供部分数据，在渲染之前务必检查所需字段是否存在
* **使用通用的提取函数**：用类型和必填字段参数化您的提取逻辑，使其能够跨不同 schema 工作
* **渐进式渲染**：在字段到达时即时显示，而不是等待完整对象，以便用户获得即时反馈
* **提供后备表示形式**：如果某个字段支持富渲染（LaTeX、Markdown、图表），还应在 schema 中包含纯文本等效项作为后备
* **尽可能保持 schema 扁平**：深度嵌套的 schema 更难渐进式渲染，并且在部分流式传输期间更容易出错
* **将 UI 与数据匹配**：选择最能代表每个字段类型的渲染策略（数组用表格，嵌套对象用卡片，状态字段用徽章）