# create_agent

创建一个 agent 图，该图在一个循环中调用工具，直到满足停止条件。

有关使用 `create_agent` 的更多详细信息，请参阅 Agents 文档。

```python
create_agent(
  model: str | BaseChatModel,
  tools: Sequence[BaseTool | Callable[..., Any] | dict[str, Any]] | None = None,
  *,
  system_prompt: str | SystemMessage | None = None,
  middleware: Sequence[AgentMiddleware[StateT_co, ContextT]] = (),
  response_format: ResponseFormat[ResponseT] | type[ResponseT] | dict[str, Any] | None = None,
  state_schema: type[AgentState[ResponseT]] | None = None,
  context_schema: type[ContextT] | None = None,
  checkpointer: Checkpointer | None = None,
  store: BaseStore | None = None,
  interrupt_before: list[str] | None = None,
  interrupt_after: list[str] | None = None,
  debug: bool = False,
  name: str | None = None,
  cache: BaseCache[Any] | None = None,
  transformers: Sequence[TransformerFactory] | None = None
) -> CompiledStateGraph[AgentState[ResponseT], ContextT, _InputAgentState, _OutputAgentState[ResponseT]]
```

agent 节点使用消息列表（在应用系统提示之后）调用语言模型。如果生成的 `AIMessage` 包含 `tool_calls`，图将调用这些工具。工具节点执行工具，并将响应作为 `ToolMessage` 对象添加到消息列表中。然后 agent 节点再次调用语言模型。此过程重复进行，直到响应中不再有 `tool_calls`。然后 agent 返回完整的消息列表。

**示例：**

```python
from langchain.agents import create_agent

def check_weather(location: str) -> str:
    '''Return the weather forecast for the specified location.'''
    return f"It's always sunny in {location}"

graph = create_agent(
    model="anthropic:claude-sonnet-4-5-20250929",
    tools=[check_weather],
    system_prompt="You are a helpful assistant",
)
inputs = {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
for chunk in graph.stream(inputs, stream_mode="updates"):
    print(chunk)
```

## 参数

| 名称                 | 类型     | 描述                 |
| ------------------ | ------------- | ------------------ |
| `model`\*          | `str \| BaseChatModel`         | agent 的语言模型。可以是字符串标识符（例如 `"openai:gpt-4"`）或直接的聊天模型实例（例如 `ChatOpenAI` 或其他 LangChain 聊天模型）。有关支持的模型字符串的完整列表，请参阅 `init_chat_model`。提示：请参阅 Models 文档了解更多信息。                                                              |
| `tools`            | `Sequence[BaseTool \| Callable[..., Any] \| dict[str, Any]] \| None`     | 默认值：`None`。工具、字典或可调用对象的列表。如果为 `None` 或空列表，agent 将只包含一个模型节点，没有工具调用循环。提示：请参阅 Tools 文档了解更多信息。                                                                                                                          |
| `system_prompt`    | `str \| SystemMessage \| None`                                           | 默认值：`None`。LLM 的可选系统提示。可以是 `str`（将转换为 `SystemMessage`）或直接是 `SystemMessage` 实例。系统消息在调用模型时被添加到消息列表的开头。                                                                                                                |
| `middleware`       | `Sequence[AgentMiddleware[StateT_co, ContextT]]`                         | 默认值：`()`。应用于 agent 的中间件实例序列。中间件可以在各个阶段拦截并修改 agent 的行为。提示：请参阅 Middleware 文档了解更多信息。                                                                                                                                   |
| `response_format`  | `ResponseFormat[ResponseT] \| type[ResponseT] \| dict[str, Any] \| None` | 默认值：`None`。结构化响应的可选配置。可以是 `ToolStrategy`、`ProviderStrategy` 或 Pydantic 模型类。如果提供，agent 将在对话流程中处理结构化输出。原始模式将根据模型能力被包装到适当的策略中。提示：请参阅 Structured output 文档了解更多信息。                                                       |
| `state_schema`     | `type[AgentState[ResponseT]] \| None`                                    | 默认值：`None`。一个可选的扩展 `AgentState` 的 `TypedDict` 模式。当提供时，将使用此模式代替 `AgentState` 作为与中间件状态模式合并的基础模式。这允许用户添加自定义状态字段而无需创建自定义中间件。通常，建议通过中间件使用 `state_schema` 扩展，以使相关扩展的范围限定在相应的钩子/工具内。                                       |
| `context_schema`   | `type[ContextT] \| None`                                                 | 默认值：`None`。运行时上下文的可选模式。                                                                                                                                                                                             |
| `checkpointer`     | `Checkpointer \| None`                                                   | 默认值：`None`。可选的检查点保存器对象。用于持久化单个线程（例如单个对话）的图状态（例如作为聊天记忆）。                                                                                                                                                             |
| `store`            | `BaseStore \| None`                                                      | 默认值：`None`。可选的存储对象。用于跨多个线程（例如多个对话/用户）持久化数据。                                                                                                                                                                         |
| `interrupt_before` | `list[str] \| None`                                                      | 默认值：`None`。在执行之前要中断的节点名称的可选列表。如果您希望在采取行动之前添加用户确认或其他中断，这很有用。                                                                                                                                                         |
| `interrupt_after`  | `list[str] \| None`                                                      | 默认值：`None`。在执行之后要中断的节点名称的可选列表。如果您希望直接返回或在输出上运行额外处理，这很有用。                                                                                                                                                            |
| `debug`            | `bool`                                                                   | 默认值：`False`。是否为图执行启用详细日志记录。启用后，将在 agent 运行期间打印有关每个节点执行、状态更新和转换的详细信息。对于调试中间件行为和理解 agent 执行流程很有用。                                                                                                                     |
| `name`             | `str \| None`                                                            | 默认值：`None`。`CompiledStateGraph` 的可选名称。当将 agent 图作为子图节点添加到另一个图时，此名称将被自动使用——对于构建多 agent 系统特别有用。                                                                                                                       |
| `cache`            | `BaseCache[Any] \| None`                                                 | 默认值：`None`。可选的 `BaseCache` 实例，用于启用图执行的缓存。                                                                                                                                                                           |
| `transformers`     | `Sequence[TransformerFactory] \| None`                                   | 默认值：`None`。可选的作用域感知 `StreamTransformer` 工厂序列，除了 agent 默认值之外，还将注册到编译后的图上。每个工厂作为 `factory(scope)` 调用，因此每次调用都会接收一个新实例。编译后的图上的最终顺序为：`ToolCallTransformer`，然后是中间件通过 `AgentMiddleware.transformers` 声明的任何工厂，最后是此处提供的任何工厂。 |

