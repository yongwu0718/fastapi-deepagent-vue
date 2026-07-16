# 结构化输出 (Structured output)

结构化输出允许 agent 以特定、可预测的格式返回数据。您无需解析自然语言响应，而是获得可以直接被应用程序使用的结构化数据，形式包括 JSON 对象、Pydantic 模型或数据类。

本页面介绍使用 `create_agent` 进行 agent 结构化输出的方法。要直接在模型上（agent 外部）使用结构化输出，请参阅 Models - Structured output。

LangChain 的 `create_agent` 会自动处理结构化输出。用户设置他们期望的结构化输出 schema，当模型生成结构化数据时，该数据会被捕获、验证，并在 agent 状态的 `'structured_response'` 键中返回。

```python
def create_agent(
    ...
    response_format: Union[
        ToolStrategy[StructuredResponseT],
        ProviderStrategy[StructuredResponseT],
        type[StructuredResponseT],
        None,
    ]
```

## Response format

使用 `response_format` 来控制 agent 返回结构化数据的方式：

- **`ToolStrategy[StructuredResponseT]`**：使用 tool calling 进行结构化输出
- **`ProviderStrategy[StructuredResponseT]`**：使用 provider 原生的结构化输出
- **`type[StructuredResponseT]`**：Schema 类型 —— 根据模型能力自动选择最佳策略
- **`None`**：未显式请求结构化输出

当直接提供 schema 类型时，LangChain 会自动选择：

- 如果所选的模型和 provider 支持原生结构化输出（例如 OpenAI、Anthropic (Claude) 或 xAI (Grok)），则使用 `ProviderStrategy`。
- 对于所有其他模型，使用 `ToolStrategy`。

如果使用 `langchain>=1.1`，对原生结构化输出特性的支持会从模型的 profile 数据中动态读取。如果数据不可用，请使用其他条件或手动指定：

  ```python
  custom_profile = {
      "structured_output": True,
      # ...
  }
  model = init_chat_model("...", profile=custom_profile)
  ```

  如果指定了 tools，模型必须支持同时使用 tools 和结构化输出。

结构化响应在 agent 最终状态的 `structured_response` 键中返回。

## Provider strategy

一些模型 provider 通过其 API 原生支持结构化输出（例如 OpenAI、xAI (Grok)、Gemini、Anthropic (Claude)）。当可用时，这是最可靠的方法。

要使用此策略，请配置一个 `ProviderStrategy`：

```python
class ProviderStrategy(Generic[SchemaT]):
    schema: type[SchemaT]
    strict: bool | None = None
```

`strict` 参数需要 `langchain>=1.2`。

定义结构化输出格式的 schema。支持：

  - **Pydantic 模型**：带有字段验证的 `BaseModel` 子类。返回经过验证的 Pydantic 实例。
  - **数据类 (Dataclasses)**：带有类型注解的 Python 数据类。返回 dict。
  - **TypedDict**：类型化字典类。返回 dict。
  - **JSON Schema**：带有 JSON schema 规范的字典。返回 dict。

可选的布尔参数，用于启用严格 schema 遵循。某些 provider（例如 OpenAI 和 xAI）支持。默认为 `None`（禁用）。

当您直接将 schema 类型传递给 `create_agent.response_format` 并且模型支持原生结构化输出时，LangChain 会自动使用 `ProviderStrategy`：

```python
  from pydantic import BaseModel, Field
  from langchain.agents import create_agent

class ContactInfo(BaseModel):
      """联系信息。"""
      name: str = Field(description="联系人姓名")
      email: str = Field(description="联系人邮箱地址")
      phone: str = Field(description="联系人电话号码")

  agent = create_agent(
      model="gpt-5.4",
      response_format=ContactInfo  # 自动选择 ProviderStrategy
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
  })

  print(result["structured_response"])
  # ContactInfo(name='John Doe', email='john@example.com', phone='(555) 123-4567')
  ```

  ```python
  from dataclasses import dataclass
  from langchain.agents import create_agent

@dataclass
  class ContactInfo:
      """联系信息。"""
      name: str  # 联系人姓名
      email: str # 联系人邮箱地址
      phone: str # 联系人电话号码

  agent = create_agent(
      model="gpt-5.4",
      tools=tools,
      response_format=ContactInfo  # 自动选择 ProviderStrategy
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
  })

  result["structured_response"]
  # {'name': 'John Doe', 'email': 'john@example.com', 'phone': '(555) 123-4567'}
  ```

  ```python
  from typing_extensions import TypedDict
  from langchain.agents import create_agent

class ContactInfo(TypedDict):
      """联系信息。"""
      name: str  # 联系人姓名
      email: str # 联系人邮箱地址
      phone: str # 联系人电话号码

  agent = create_agent(
      model="gpt-5.4",
      tools=tools,
      response_format=ContactInfo  # 自动选择 ProviderStrategy
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
  })

  result["structured_response"]
  # {'name': 'John Doe', 'email': 'john@example.com', 'phone': '(555) 123-4567'}
  ```

  ```python
  from langchain.agents import create_agent

contact_info_schema = {
      "type": "object",
      "description": "联系信息。",
      "properties": {
          "name": {"type": "string", "description": "联系人姓名"},
          "email": {"type": "string", "description": "联系人邮箱地址"},
          "phone": {"type": "string", "description": "联系人电话号码"}
      },
      "required": ["name", "email", "phone"]
  }

  agent = create_agent(
      model="gpt-5.4",
      tools=tools,
      response_format=ProviderStrategy(contact_info_schema)
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
  })

  result["structured_response"]
  # {'name': 'John Doe', 'email': 'john@example.com', 'phone': '(555) 123-4567'}
  ```

Provider 原生的结构化输出提供了高可靠性和严格的验证，因为 provider 强制执行 schema。当可用时请使用它。

如果 provider 对您选择的模型原生支持结构化输出，那么写 `response_format=ProductReview` 在功能上等同于 `response_format=ProviderStrategy(ProductReview)`。

  无论哪种情况，如果不支持结构化输出，agent 将回退到 tool calling 策略。

## Tool calling 策略

对于不支持原生结构化输出的模型，LangChain 使用 tool calling 来实现相同的结果。这适用于所有支持 tool calling 的模型（大多数现代模型）。

要使用此策略，请配置一个 `ToolStrategy`：

```python
class ToolStrategy(Generic[SchemaT]):
    schema: type[SchemaT]
    tool_message_content: str | None
    handle_errors: Union[
        bool,
        str,
        type[Exception],
        tuple[type[Exception], ...],
        Callable[[Exception], str],
    ]
```

定义结构化输出格式的 schema。支持：

  - **Pydantic 模型**：带有字段验证的 `BaseModel` 子类。返回经过验证的 Pydantic 实例。
  - **数据类 (Dataclasses)**：带有类型注解的 Python 数据类。返回 dict。
  - **TypedDict**：类型化字典类。返回 dict。
  - **JSON Schema**：带有 JSON schema 规范的字典。返回 dict。
  - **联合类型 (Union types)**：多个 schema 选项。模型将根据上下文选择最合适的 schema。

生成结构化输出时返回的工具消息的自定义内容。
  如果未提供，默认为显示结构化响应数据的消息。

针对结构化输出验证失败的错误处理策略。默认为 `True`。

  - **`True`**：捕获所有错误，使用默认错误模板
  - **`str`**：捕获所有错误，使用此自定义消息
  - **`type[Exception]`**：仅捕获此异常类型，使用默认消息
  - **`tuple[type[Exception], ...]`**：仅捕获这些异常类型，使用默认消息
  - **`Callable[[Exception], str]`**：返回错误消息的自定义函数
  - **`False`**：不重试，让异常传播

```python
  from pydantic import BaseModel, Field
  from typing import Literal
  from langchain.agents import create_agent
  from langchain.agents.structured_output import ToolStrategy

class ProductReview(BaseModel):
      """产品评论分析。"""
      rating: int | None = Field(description="产品评分", ge=1, le=5)
      sentiment: Literal["positive", "negative"] = Field(description="评论情感")
      key_points: list[str] = Field(description="评论关键点。小写，每个点1-3个词。")

  agent = create_agent(
      model="gpt-5.4",
      tools=tools,
      response_format=ToolStrategy(ProductReview)
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
  })
  result["structured_response"]
  # ProductReview(rating=5, sentiment='positive', key_points=['fast shipping', 'expensive'])
  ```

  ```python
  from dataclasses import dataclass
  from typing import Literal
  from langchain.agents import create_agent
  from langchain.agents.structured_output import ToolStrategy

@dataclass
  class ProductReview:
      """产品评论分析。"""
      rating: int | None  # 产品评分 (1-5)
      sentiment: Literal["positive", "negative"]  # 评论情感
      key_points: list[str]  # 评论关键点

  agent = create_agent(
      model="gpt-5.4",
      tools=tools,
      response_format=ToolStrategy(ProductReview)
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
  })
  result["structured_response"]
  # {'rating': 5, 'sentiment': 'positive', 'key_points': ['fast shipping', 'expensive']}
  ```

  ```python
  from typing import Literal
  from typing_extensions import TypedDict
  from langchain.agents import create_agent
  from langchain.agents.structured_output import ToolStrategy

class ProductReview(TypedDict):
      """产品评论分析。"""
      rating: int | None  # 产品评分 (1-5)
      sentiment: Literal["positive", "negative"]  # 评论情感
      key_points: list[str]  # 评论关键点

  agent = create_agent(
      model="gpt-5.4",
      tools=tools,
      response_format=ToolStrategy(ProductReview)
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
  })
  result["structured_response"]
  # {'rating': 5, 'sentiment': 'positive', 'key_points': ['fast shipping', 'expensive']}
  ```

  ```python
  from langchain.agents import create_agent
  from langchain.agents.structured_output import ToolStrategy

product_review_schema = {
      "type": "object",
      "description": "产品评论分析。",
      "properties": {
          "rating": {
              "type": ["integer", "null"],
              "description": "产品评分 (1-5)",
              "minimum": 1,
              "maximum": 5
          },
          "sentiment": {
              "type": "string",
              "enum": ["positive", "negative"],
              "description": "评论情感"
          },
          "key_points": {
              "type": "array",
              "items": {"type": "string"},
              "description": "评论关键点"
          }
      },
      "required": ["sentiment", "key_points"]
  }

  agent = create_agent(
      model="gpt-5.4",
      tools=tools,
      response_format=ToolStrategy(product_review_schema)
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
  })
  result["structured_response"]
  # {'rating': 5, 'sentiment': 'positive', 'key_points': ['fast shipping', 'expensive']}
  ```

  ```python
  from pydantic import BaseModel, Field
  from typing import Literal, Union
  from langchain.agents import create_agent
  from langchain.agents.structured_output import ToolStrategy

class ProductReview(BaseModel):
      """产品评论分析。"""
      rating: int | None = Field(description="产品评分", ge=1, le=5)
      sentiment: Literal["positive", "negative"] = Field(description="评论情感")
      key_points: list[str] = Field(description="评论关键点。小写，每个点1-3个词。")

  class CustomerComplaint(BaseModel):
      """关于产品或服务的客户投诉。"""
      issue_type: Literal["product", "service", "shipping", "billing"] = Field(description="问题类型")
      severity: Literal["low", "medium", "high"] = Field(description="投诉严重程度")
      description: str = Field(description="问题简短描述")

  agent = create_agent(
      model="gpt-5.4",
      tools=tools,
      response_format=ToolStrategy(Union[ProductReview, CustomerComplaint])
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
  })
  result["structured_response"]
  # ProductReview(rating=5, sentiment='positive', key_points=['fast shipping', 'expensive'])
  ```

### 自定义工具消息内容

`tool_message_content` 参数允许您自定义生成结构化输出时出现在对话历史中的消息：

```python
from pydantic import BaseModel, Field
from typing import Literal
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class MeetingAction(BaseModel):
    """从会议记录中提取的行动项。"""
    task: str = Field(description="需要完成的具体任务")
    assignee: str = Field(description="负责该任务的人员")
    priority: Literal["low", "medium", "high"] = Field(description="优先级")

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    response_format=ToolStrategy(
        schema=MeetingAction,
        tool_message_content="行动项已捕获并添加到会议记录！"
    )
)

agent.invoke({
    "messages": [{"role": "user", "content": "From our meeting: Sarah needs to update the project timeline as soon as possible"}]
})
```

```
================================ Human Message =================================

From our meeting: Sarah needs to update the project timeline as soon as possible
================================== Ai Message ==================================
Tool Calls:
  MeetingAction (call_1)
 Call ID: call_1
  Args:
    task: Update the project timeline
    assignee: Sarah
    priority: high
================================= Tool Message =================================
Name: MeetingAction

行动项已捕获并添加到会议记录！
```

如果没有 `tool_message_content`，我们最终的 `ToolMessage` 将是：

```
================================= Tool Message =================================
Name: MeetingAction

Returning structured response: {'task': 'update the project timeline', 'assignee': 'Sarah', 'priority': 'high'}
```

### 错误处理

模型在通过 tool calling 生成结构化输出时可能会出错。LangChain 提供智能重试机制来自动处理这些错误。

#### 多个结构化输出错误

当模型错误地调用了多个结构化输出工具时，agent 会在 `ToolMessage` 中提供错误反馈，并提示模型重试：

```python
from pydantic import BaseModel, Field
from typing import Union
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class ContactInfo(BaseModel):
    name: str = Field(description="联系人姓名")
    email: str = Field(description="邮箱地址")

class EventDetails(BaseModel):
    event_name: str = Field(description="活动名称")
    date: str = Field(description="活动日期")

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    response_format=ToolStrategy(Union[ContactInfo, EventDetails])  # 默认: handle_errors=True
)

agent.invoke({
    "messages": [{"role": "user", "content": "Extract info: John Doe (john@email.com) is organizing Tech Conference on March 15th"}]
})
```

```
================================ Human Message =================================

Extract info: John Doe (john@email.com) is organizing Tech Conference on March 15th
None
================================== Ai Message ==================================
Tool Calls:
  ContactInfo (call_1)
 Call ID: call_1
  Args:
    name: John Doe
    email: john@email.com
  EventDetails (call_2)
 Call ID: call_2
  Args:
    event_name: Tech Conference
    date: March 15th
================================= Tool Message =================================
Name: ContactInfo

Error: Model incorrectly returned multiple structured responses (ContactInfo, EventDetails) when only one is expected.
 Please fix your mistakes.
================================= Tool Message =================================
Name: EventDetails

Error: Model incorrectly returned multiple structured responses (ContactInfo, EventDetails) when only one is expected.
 Please fix your mistakes.
================================== Ai Message ==================================
Tool Calls:
  ContactInfo (call_3)
 Call ID: call_3
  Args:
    name: John Doe
    email: john@email.com
================================= Tool Message =================================
Name: ContactInfo

Returning structured response: {'name': 'John Doe', 'email': 'john@email.com'}
```

#### Schema 验证错误

当结构化输出与预期 schema 不匹配时，agent 会提供具体的错误反馈：

```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class ProductRating(BaseModel):
    rating: int | None = Field(description="1-5 的评分", ge=1, le=5)
    comment: str = Field(description="评论内容")

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    response_format=ToolStrategy(ProductRating),  # 默认: handle_errors=True
    system_prompt="You are a helpful assistant that parses product reviews. Do not make any field or value up."
)

agent.invoke({
    "messages": [{"role": "user", "content": "Parse this: Amazing product, 10/10!"}]
})
```

```
================================ Human Message =================================

Parse this: Amazing product, 10/10!
================================== Ai Message ==================================
Tool Calls:
  ProductRating (call_1)
 Call ID: call_1
  Args:
    rating: 10
    comment: Amazing product
================================= Tool Message =================================
Name: ProductRating

Error: Failed to parse structured output for tool 'ProductRating': 1 validation error for ProductRating.rating
  Input should be less than or equal to 5 [type=less_than_equal, input_value=10, input_type=int].
 Please fix your mistakes.
================================== Ai Message ==================================
Tool Calls:
  ProductRating (call_2)
 Call ID: call_2
  Args:
    rating: 5
    comment: Amazing product
================================= Tool Message =================================
Name: ProductRating

Returning structured response: {'rating': 5, 'comment': 'Amazing product'}
```

#### 错误处理策略

您可以使用 `handle_errors` 参数自定义错误的处理方式：

**自定义错误消息：**

```python
ToolStrategy(
    schema=ProductRating,
    handle_errors="请提供 1-5 之间的有效评分并包含评论。"
)
```

如果 `handle_errors` 是字符串，agent 将*始终*提示模型使用固定的工具消息重试：

```
================================= Tool Message =================================
Name: ProductRating

请提供 1-5 之间的有效评分并包含评论。
```

**仅处理特定异常：**

```python
ToolStrategy(
    schema=ProductRating,
    handle_errors=ValueError  # 仅在 ValueError 时重试，其他异常抛出
)
```

如果 `handle_errors` 是异常类型，agent 仅在引发的异常是指定类型时才重试（使用默认错误消息）。在所有其他情况下，异常将被抛出。

**处理多种异常类型：**

```python
ToolStrategy(
    schema=ProductRating,
    handle_errors=(ValueError, TypeError)  # 在 ValueError 和 TypeError 时重试
)
```

如果 `handle_errors` 是异常元组，agent 仅在引发的异常是其中一种指定类型时才重试（使用默认错误消息）。在所有其他情况下，异常将被抛出。

**自定义错误处理函数：**

```python

from langchain.agents.structured_output import StructuredOutputValidationError
from langchain.agents.structured_output import MultipleStructuredOutputsError

def custom_error_handler(error: Exception) -> str:
    if isinstance(error, StructuredOutputValidationError):
        return "格式有问题，请重试。"
    elif isinstance(error, MultipleStructuredOutputsError):
        return "返回了多个结构化输出。请选择最相关的一个。"
    else:
        return f"错误: {str(error)}"

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    response_format=ToolStrategy(
                        schema=Union[ContactInfo, EventDetails],
                        handle_errors=custom_error_handler
                    )  # 默认: handle_errors=True
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract info: John Doe (john@email.com) is organizing Tech Conference on March 15th"}]
})

for msg in result['messages']:
    # 如果消息实际是 ToolMessage 对象（不是 dict），检查其类名
    if type(msg).__name__ == "ToolMessage":
        print(msg.content)
    # 如果消息是字典或您需要后备方案
    elif isinstance(msg, dict) and msg.get('tool_call_id'):
        print(msg['content'])

```

在 `StructuredOutputValidationError` 时：

```
================================= Tool Message =================================
Name: ToolStrategy

格式有问题，请重试。
```

在 `MultipleStructuredOutputsError` 时：

```
================================= Tool Message =================================
Name: ToolStrategy

返回了多个结构化输出。请选择最相关的一个。
```

在其他错误时：

```
================================= Tool Message =================================
Name: ToolStrategy

错误: <异常信息>
```

**无错误处理：**

```python
response_format = ToolStrategy(
    schema=ProductRating,
    handle_errors=False  # 抛出所有异常
)
```