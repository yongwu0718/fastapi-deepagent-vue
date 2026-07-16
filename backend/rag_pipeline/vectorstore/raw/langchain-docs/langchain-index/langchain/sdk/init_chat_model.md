# init_chat_model

使用统一接口从任何支持的 provider 初始化一个聊天模型。

两种主要用例：

- **固定模型** – 预先指定模型，获得一个可直接使用的聊天模型。
- **可配置模型** – 选择在运行时通过 config 指定参数（包括模型名称）。无需更改代码即可轻松切换模型/provider。

**安装要求**
需要安装所选模型 provider 的集成包。

请参见下面的 `model_provider` 参数了解具体的包名称（例如 `pip install langchain-openai`）。

有关可用作 `**kwargs` 的受支持模型参数，请参阅 provider 集成的 API 参考。

```python
init_chat_model(
  model: str | None = None,
  *,
  model_provider: str | None = None,
  configurable_fields: Literal['any'] | list[str] | tuple[str, ...] | None = None,
  config_prefix: str | None = None,
  **kwargs: Any = {}
) -> BaseChatModel | _ConfigurableModel
```

## 初始化一个不可配置的模型

```python
# pip install langchain langchain-openai

from langchain.chat_models import init_chat_model

gpt_5 = init_chat_model("openai:gpt-5.5", temperature=0)
gpt_5.invoke("what's your name")
```

## 部分可配置模型（无默认值）

```python
# pip install langchain langchain-openai

from langchain.chat_models import init_chat_model

# (如果没有指定模型，不需要设置 configurable=True)
configurable_model = init_chat_model(temperature=0)

# 使用 GPT-5.5 生成响应
configurable_model.invoke(
    "what's your name",
    config={"configurable": {"model": "gpt-5.5"}},
)
```

## 完全可配置模型（带默认值）

```python
# pip install langchain langchain-openai langchain-anthropic

from langchain.chat_models import init_chat_model

configurable_model_with_default = init_chat_model(
    "openai:gpt-5.5",
    configurable_fields="any",  # 这允许我们在运行时配置 temperature、max_tokens 等其他参数。
    config_prefix="foo",
    temperature=0,
)

configurable_model_with_default.invoke("what's your name")
# GPT-5.5 响应，temperature=0（如默认设置）

# 通过 config 在运行时覆盖模型和 temperature。
# 注意 config 键上使用了 "foo_" 前缀，这与我们初始化模型时设置的 config_prefix 匹配。
configurable_model_with_default.invoke(
    "what's your name",
    config={
        "configurable": {
            "foo_model": "anthropic:claude-opus-4-7",
            "foo_temperature": 0.6,
        }
    },
)
```

## 绑定工具到可配置模型

您可以像使用普通模型一样，在可配置模型上调用任何聊天模型的声明式方法：

```python
# pip install langchain langchain-openai langchain-anthropic

from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

class GetWeather(BaseModel):
    '''Get the current weather in a given location'''

    location: str = Field(..., description="The city and state, e.g. San Francisco, CA")

class GetPopulation(BaseModel):
    '''Get the current population in a given location'''

    location: str = Field(..., description="The city and state, e.g. San Francisco, CA")

configurable_model = init_chat_model(
    "gpt-5.5", configurable_fields=("model", "model_provider"), temperature=0
)

configurable_model_with_tools = configurable_model.bind_tools(
    [
        GetWeather,
        GetPopulation,
    ]
)
configurable_model_with_tools.invoke(
    "Which city is hotter today and which is bigger: LA or NY?"
)
# 使用 GPT-5.5

configurable_model_with_tools.invoke(
    "Which city is hotter today and which is bigger: LA or NY?",
    config={"configurable": {"model": "claude-opus-4-7"}},
)
# 使用 Opus 4.7
```

## 参数

| 名称                  | 类型                                                                   | 描述                                                                                                                                                                                                                                                       |
| --------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `model`               | `str \| None`                                                          | 默认值：`None`。<br>要使用的模型名称，带有 provider 前缀 — 例如 `'openai:gpt-5.5'`。<br>也接受裸模型名称（例如 `'claude-opus-4-7'`）；我们将尝试使用下面的映射从前缀推断 provider。推断是尽力而为的，不保证成功，因此尽可能优先使用带前缀的形式。<br>优先使用固定的模型 ID，而不是移动的别名（例如 `'claude-haiku-4-5-20251001'` 而不是 `'claude-haiku-4-5'`），这样当别名在上游被重新指向时，行为不会漂移。<br>按前缀推断的 provider（不区分大小写）：<br>`gpt-... ｜ o1... ｜ o3...` -> `openai`<br>`claude...` -> `anthropic`<br>`amazon.... ｜ anthropic.... ｜ meta....` -> `bedrock`<br>`gemini...` -> `google_vertexai`（下一个主要版本中默认值会更改；传递 `model_provider` 以锁定）<br>`command...` -> `cohere`<br>`accounts/fireworks...` -> `fireworks`<br>`mistral... ｜ mixtral...` -> `mistralai`<br>`deepseek...` -> `deepseek`<br>`grok...` -> `xai`<br>`sonar...` -> `perplexity`<br>`solar...` -> `upstage`<br>`chatgpt... ｜ text-davinci...` -> `openai`（旧版）|
| `model_provider`      | `str \| None`                                                          | 默认值：`None`。<br>模型的 provider，单独传递，而不是作为模型的前缀。<br>等效于前缀形式 — 例如 `model='claude-sonnet-4-5'`, `model_provider='anthropic'` 的行为与 `model='anthropic:claude-sonnet-4-5'` 相同。<br>对于大多数用法，优先使用模型上的前缀形式。在以下情况下使用此关键字参数：<br>- provider 是动态的（从配置或环境变量中读取），否则您将不得不拼接字符串。<br>- 您希望 `model` 和 `model_provider` 在运行时通过 `configurable_fields` 独立可互换（例如，将相同的模型名称路由到不同的主机）。<br>支持的值及其所需的集成包：<br>`openai` -> `langchain-openai`<br>`anthropic` -> `langchain-anthropic`<br>`azure_openai` -> `langchain-openai`<br>`azure_ai` -> `langchain-azure-ai`<br>`google_vertexai` -> `langchain-google-vertexai`<br>`google_genai` -> `langchain-google-genai`<br>`anthropic_bedrock` -> `langchain-aws`<br>`bedrock` -> `langchain-aws`<br>`bedrock_converse` -> `langchain-aws`<br>`cohere` -> `langchain-cohere`<br>`fireworks` -> `langchain-fireworks`<br>`together` -> `langchain-together`<br>`mistralai` -> `langchain-mistralai`<br>`huggingface` -> `langchain-huggingface`<br>`groq` -> `langchain-groq`<br>`ollama` -> `langchain-ollama`<br>`google_anthropic_vertex` -> `langchain-google-vertexai`<br>`deepseek` -> `langchain-deepseek`<br>`ibm` -> `langchain-ibm`<br>`nvidia` -> `langchain-nvidia-ai-endpoints`<br>`xai` -> `langchain-xai`<br>`openrouter` -> `langchain-openrouter`<br>`perplexity` -> `langchain-perplexity`<br>`upstage` -> `langchain-upstage`<br>`baseten` -> `langchain-baseten`<br>`litellm` -> `langchain-litellm` |
| `configurable_fields` | `Literal['any'] \| list[str] \| tuple[str, ...] \| None`               | 默认值：`None`。<br>哪些模型参数在运行时是可配置的：<br>- `None`：没有可配置字段（即固定模型）。<br>- `'any'`：所有字段都是可配置的。请参阅下面的安全说明。<br>- `list[str] \| Tuple[str, ...]`：指定的字段是可配置的。<br>如果指定了 `config_prefix`，则假定字段名称中已去除了该前缀。<br>如果指定了 `model`，则默认为 `None`。<br>如果未指定 `model`，则默认为 `("model", "model_provider")`。<br>**安全说明**<br>设置 `configurable_fields="any"` 意味着 `api_key`、`base_url` 等字段可以在运行时被更改，可能将模型请求重定向到不同的服务/用户。请确保如果您接受不受信任的配置，请显式枚举 `configurable_fields=(...)`。 |
| `config_prefix`       | `str \| None`                                                          | 默认值：`None`。<br>配置键的可选前缀。<br>当您在同一个应用程序中有多个可配置模型时很有用。<br>如果 `config_prefix` 是非空字符串，则模型将在运行时通过 `config["configurable"]["{config_prefix}_{param}"]` 键进行配置。请参见下面的示例。<br>如果 `config_prefix` 是空字符串，则模型将通过 `config["configurable"]["{param}"]` 进行配置。 |
| `**kwargs`            | `Any`                                                                  | 默认值：`{}`。<br>其他特定于模型的关键字参数，将传递给底层聊天模型的 `__init__` 方法。常见参数包括：<br>- `temperature`：模型温度，用于控制随机性。<br>- `max_tokens`：最大输出 token 数。<br>- `timeout`：等待响应的最大时间（秒）。<br>- `max_retries`：失败请求的最大重试次数。<br>- `base_url`：自定义 API 端点 URL。<br>- `rate_limiter`：一个 `BaseRateLimiter` 实例，用于控制请求速率。<br>有关所有可用参数，请参阅特定模型 provider 的集成参考。 |