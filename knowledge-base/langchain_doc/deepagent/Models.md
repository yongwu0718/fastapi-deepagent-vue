# 模型

Deep Agents 可与任何支持工具调用的 LangChain 聊天模型配合使用。
## 支持的模型

使用 `provider:model` 格式指定模型（例如 `google_genai:gemini-3.1-pro-preview`、`openai:gpt-5.4` 或 `anthropic:claude-sonnet-4-6`）。提供商前缀用于选择 LangChain 集成，冒号后的部分会作为模型标识符传递给该提供商。有效的提供商字符串请参见 `init_chat_model` 的 `model_provider` 参数。提供商特定的配置请参见聊天模型集成。

模型标识符必须符合提供商期望的格式。有些提供商使用像 `gpt-5.4` 这样简单的名称；其他提供商则使用命名空间 ID 或部署路径，例如 `zai-org/GLM-5.1`，因此完整的 Deep Agents 字符串应为 `baseten:zai-org/GLM-5.1`。请查阅提供商的模型目录或集成文档以获取当前标识符。

### 建议的模型

这些模型在 Deep Agents 评估套件中表现良好，该套件测试基本的代理操作。通过这些评估是必要的，但不足以在更长、更复杂的任务中取得出色表现。

| 提供商                                                  | 模型                                                                                                                                    |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Google                                                  | `gemini-3.1-pro-preview`, `gemini-3-flash-preview`                                                                                      |
| OpenAI                                                  | `gpt-5.4`, `gpt-4o`, `gpt-5.4`, `o4-mini`, `gpt-5.2-codex`, `gpt-4o-mini`, `o3`                                                         |
| Anthropic                                               | `claude-opus-4-6`, `claude-opus-4-5`, `claude-sonnet-4-6`, `claude-sonnet-4`, `claude-sonnet-4-5`, `claude-haiku-4-5`, `claude-opus-4-1` |
| 开放权重模型                                            | `GLM-5`, `Kimi-K2.5`, `MiniMax-M2.5`, `qwen3.5-397B-A17B`, `devstral-2-123B`                                                            |

开放权重模型可通过 Baseten、Fireworks、OpenRouter 和 Ollama 等提供商获取。

### 模型评估

Deep Agents 评估套件测试了以下流行模型：

| 模型                                          |          文件操作 |          检索 |        工具使用 |          记忆 |          对话 |          摘要 |
| :------------------------------------------- | ---------------: | ------------: | --------------: | ------------: | ------------: | ------------: |
| google\_genai:gemini-3.1-pro-preview         |         **100%** |      **100%** |            25% |           54% |           48% |           80% |
| openai:gpt-5.4                               |         **100%** |      **100%** |            18% |           51% |           38% |      **100%** |
| openai:gpt-5.5                               |             92%  |      **100%** |            20% |           64% |       **52%** |           80% |
| anthropic:claude-opus-4-6                    |             92%  |      **100%** |            26% |       **69%** |           22% |      **100%** |
| anthropic:claude-opus-4-7                    |         **100%** |      **100%** |            18% |           —    |       **52%** |      **100%** |
| baseten:moonshotai/Kimi-K2.6                 |         **100%** |      **100%** |            20% |           —    |           —    |           60% |
| baseten:zai-org/GLM-5                        |             92%  |      **100%** |        **87%** |           44% |           29% |           60% |
| ollama:minimax-m2.7:cloud                    |             92%  |           90% |            82% |           38% |           29% |           60% |
| openrouter:deepseek/deepseek-v4-pro          |         **100%** |      **100%** |            25% |           —    |           —    |           80% |
| openrouter:minimax/minimax-m2.7              |             92%  |      **100%** |            20% |           —    |           —    |           60% |
| openrouter:nvidia/nemotron-3-super-120b-a12b |              0%  |            0% |             0% |            0% |            0% |            0% |
| openrouter:z-ai/glm-5.1                      |             92%  |      **100%** |            25% |           —    |           33% |           80% |

更多信息请参见评估运行。

## 配置模型参数

可以将 `provider:model` 格式的模型字符串传递给 `create_deep_agent`，或者传递一个已配置好的模型实例以获得完全控制权。在底层，模型字符串会通过 `init_chat_model` 进行解析。

要配置模型特定的参数，请使用 `init_chat_model` 或直接实例化提供商模型类：

```python
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

model = init_chat_model(
    model="google_genai:gemini-3.1-pro-preview",
    thinking_level="medium",
)
agent = create_deep_agent(model=model)
```

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from deepagents import create_deep_agent

model = ChatGoogleGenerativeAI(
    model="gemini-3.1-pro-preview",
    thinking_level="medium",
)
agent = create_deep_agent(model=model)
```

可用参数因提供商而异。提供商特定的配置选项请参见聊天模型集成页面。

### 提供商配置文件 (ProviderProfile)

`ProviderProfile` 封装了一些初始化参数，这些参数会在你创建深度代理并提供 `provider:model` 字符串时生效。当你通过 `init_chat_model` 传入一个预配置好的模型时，它不会生效。

你可以在两个层级注册，两者可以共存：

- **提供商级别** — 一个裸的提供商键名，例如 `"openai"`，会应用到来自 `openai` 提供商的每一个模型。
- **模型级别** — 一个 `provider:model` 组合键名，例如 `"openai:gpt-5.4"`，只会应用到该特定模型，并且会与任何匹配的提供商级别配置合并。

```python
from deepagents import ProviderProfile, register_provider_profile

# 提供商级别的默认设置：每个 openai 模型的 temperature 都设为 0。
register_provider_profile(
    "openai",
    ProviderProfile(init_kwargs={"temperature": 0}),
)

# 模型级别的覆盖：gpt-5.4 额外获得特定的推理强度设置。
# 会继承上面提供商级别配置中的 temperature=0。
register_provider_profile(
    "openai:gpt-5.4",
    ProviderProfile(init_kwargs={"reasoning_effort": "medium"}),
)
```

完整的字段列表、合并语义和插件打包请参见配置文件。

要塑造**代理**在模型构建完成后的行为，请使用框架配置文件 (harness profile)。

## 在运行时选择模型

如果你的应用程序允许用户选择模型（例如通过界面中的下拉菜单），可以使用中间件在运行时切换模型，而无需重新构建代理。

将用户的模型选择通过运行时上下文传递，然后使用一个 `wrap_model_call` 中间件，通过 `@wrap_model_call` 装饰器在每次调用时覆盖模型：

```python
from dataclasses import dataclass
from langchain.chat_models import init_chat_model
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from deepagents import create_deep_agent
from typing import Callable

@dataclass
class Context:
    model: str

@wrap_model_call
def configurable_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    model_name = request.runtime.context.model
    model = init_chat_model(model_name)
    return handler(request.override(model=model))

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    middleware=[configurable_model],
    context_schema=Context,
)

# 使用用户选择的模型进行调用
result = agent.invoke(
    {"messages": [{"role": "user", "content": "你好！"}]},
    context=Context(model="openai:gpt-5.4"),
)
```

有关更多动态模型模式（例如根据对话复杂度或成本优化进行路由），请参见 LangChain 代理指南中的动态模型。

## 了解更多

- LangChain 中的模型：聊天模型功能，包括工具调用、结构化输出和多模态