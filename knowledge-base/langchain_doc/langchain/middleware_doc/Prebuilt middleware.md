```markdown
# 预构建中间件 (Prebuilt middleware)

> 用于常见 agent 用例的预构建中间件

LangChain 和 Deep Agents 为常见用例提供了预构建的中间件。每个中间件均可用于生产环境，并可根据您的特定需求进行配置。

## 与 Provider 无关的中间件 (Provider-agnostic middleware)

以下中间件适用于任何 LLM provider：

| 中间件 (Middleware)                               | 描述 (Description)                                                                  |
| --------------------------------------- | ---------------------------------------------------------------------------- |
| Summarization         | 当接近 token 限制时自动总结对话历史。  |
| Human-in-the-loop | 暂停执行以进行人工审批 tool calls。                            |
| Model call limit   | 限制模型调用次数以防止过度成本。                  |
| Tool call limit     | 通过限制调用次数来控制工具执行。                              |
| Model fallback       | 当主模型失败时自动回退到备选模型。             |
| PII detection         | 检测并处理个人身份信息 (PII)。                 |
| To-do list               | 为 agent 配备任务规划和跟踪能力。                   |
| LLM tool selector | 在调用主模型之前使用 LLM 选择相关工具。               |
| Tool retry               | 使用指数退避自动重试失败的工具调用。              |
| Model retry             | 使用指数退避自动重试失败的模型调用。             |
| LLM tool emulator | 使用 LLM 模拟工具执行以用于测试目的。                    |
| Context editing     | 通过修剪或清除工具使用来管理对话上下文。               |
| Shell tool               | 向 agent 暴露持久的 shell 会话以执行命令。               |
| File search             | 提供对文件系统文件的 Glob 和 Grep 搜索工具。                    |
| Filesystem    | 为 agent 提供用于存储上下文和长期记忆的文件系统。 |
| Subagent                   | 添加生成子 agent 的能力。                                          |

### Summarization

当接近 token 限制时自动总结对话历史，保留最近的消息同时压缩较旧的上下文。总结在以下场景中很有用：

* 超出上下文窗口的长时间对话。
* 具有大量历史记录的多轮对话。
* 需要保留完整对话上下文的应用程序。

**API 参考：** `SummarizationMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[your_weather_tool, your_calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("tokens", 4000),
            keep=("messages", 20),
        ),
    ],
)
```

`trigger` 和 `keep` 的 `fraction` 条件（如下所示）依赖于聊天模型的 profile 数据（如果使用 `langchain>=1.1`）。如果数据不可用，请使用其他条件或手动指定：

    ```python
    from langchain.chat_models import init_chat_model

    custom_profile = {
        "max_input_tokens": 100_000,
        # ...
    }
    model = init_chat_model("gpt-5.4", profile=custom_profile)
    ```

`model`  
用于生成摘要的模型。可以是模型标识符字符串（例如 `'openai:gpt-5.4-mini'`）或 `BaseChatModel` 实例。有关更多信息，请参阅 `init_chat_model`。

`trigger`  
触发总结的条件。可以是：

    * 单个 `ContextSize` 元组（必须满足指定条件）
    * 一个 `ContextSize` 元组列表（必须满足任一条件 - OR 逻辑）

    条件应为以下之一：

    * `fraction` (float)：模型上下文大小的一部分 (0-1)
    * `tokens` (int)：绝对 token 计数
    * `messages` (int)：消息计数

    必须指定至少一个条件。如果未提供，总结将不会自动触发。

    有关更多信息，请参阅 `ContextSize` 的 API 参考。

`keep`  
总结后要保留的上下文量。精确指定以下之一：

    * `fraction` (float)：要保留的模型上下文大小的比例 (0-1)
    * `tokens` (int)：要保留的绝对 token 计数
    * `messages` (int)：要保留的最近消息数

    有关更多信息，请参阅 `ContextSize` 的 API 参考。

`token_counter`  
自定义 token 计数函数。默认为基于字符的计数。

`summary_prompt`  
用于总结的自定义提示模板。如果未指定，则使用内置模板。模板应包含 `{messages}` 占位符，对话历史将插入其中。

`max_summary_tokens`  
生成摘要时要包含的最大 token 数。消息将在总结前被修剪以适应此限制。

`prompt`（已弃用）  
**已弃用：** 请使用 `summary_prompt` 来提供完整提示。

`token_threshold`（已弃用）  
**已弃用：** 请改用 `trigger: ("tokens", value)`。触发总结的 token 阈值。

`keep_messages`（已弃用）  
**已弃用：** 请改用 `keep: ("messages", value)`。要保留的最近消息。

总结中间件会监控消息的 token 计数，并在达到阈值时自动总结较旧的消息。

  **触发条件 (Trigger conditions)** 控制总结何时运行：

  * 单个条件对象（必须满足指定条件）
  * 条件数组（必须满足任一条件 - OR 逻辑）
  * 每个条件可以使用 `fraction`（模型上下文大小的比例）、`tokens`（绝对计数）或 `messages`（消息计数）

  **保留条件 (Keep condition)** 控制要保留多少上下文（精确指定一个）：

  * `fraction` - 要保留的模型上下文大小的比例
  * `tokens` - 要保留的绝对 token 计数
  * `messages` - 要保留的最近消息数

  ```python
  from langchain.agents import create_agent
  from langchain.agents.middleware import SummarizationMiddleware

# 单一条件：如果 tokens >= 4000 则触发
  agent = create_agent(
      model="gpt-5.4",
      tools=[your_weather_tool, your_calculator_tool],
      middleware=[
          SummarizationMiddleware(
              model="gpt-5.4-mini",
              trigger=("tokens", 4000),
              keep=("messages", 20),
          ),
      ],
  )

  # 多个条件：如果 token 数 >= 3000 或消息数 >= 6，则触发
  agent2 = create_agent(
      model="gpt-5.4",
      tools=[your_weather_tool, your_calculator_tool],
      middleware=[
          SummarizationMiddleware(
              model="gpt-5.4-mini",
              trigger=[
                  ("tokens", 3000),
                  ("messages", 6),
              ],
              keep=("messages", 20),
          ),
      ],
  )

  # 使用分数限制
  agent3 = create_agent(
      model="gpt-5.4",
      tools=[your_weather_tool, your_calculator_tool],
      middleware=[
          SummarizationMiddleware(
              model="gpt-5.4-mini",
              trigger=("fraction", 0.8),
              keep=("fraction", 0.3),
          ),
      ],
  )
  ```

### Human-in-the-loop

在执行前暂停 agent 执行，以便人工审批、编辑或拒绝 tool calls。人机交互在以下场景中很有用：

* 需要人工批准的高风险操作（例如数据库写入、金融交易）。
* 需要强制人工监督的合规工作流。
* 需要人工反馈来指导 agent 的长时间对话。

**API 参考：** `HumanInTheLoopMiddleware`

人机交互中间件需要一个 checkpointer 来维护中断之间的状态。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

def your_read_email_tool(email_id: str) -> str:
    """通过 ID 读取电子邮件的模拟函数。"""
    return f"Email content for ID: {email_id}"

def your_send_email_tool(recipient: str, subject: str, body: str) -> str:
    """发送电子邮件的模拟函数。"""
    return f"Email sent to {recipient} with subject '{subject}'"

agent = create_agent(
    model="gpt-5.4",
    tools=[your_read_email_tool, your_send_email_tool],
    checkpointer=InMemorySaver(),
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "your_send_email_tool": {
                    "allowed_decisions": ["approve", "edit", "reject"],
                },
                "your_read_email_tool": False,
            }
        ),
    ],
)
```

有关完整示例、配置选项和集成模式，请参阅 Human-in-the-loop 文档。

观看此视频指南，了解人机交互中间件的行为。

### Model call limit

限制模型调用次数以防止无限循环或过度成本。模型调用限制在以下场景中很有用：

* 防止失控的 agent 进行过多 API 调用。
* 对生产部署实施成本控制。
* 在特定调用预算内测试 agent 行为。

**API 参考：** `ModelCallLimitMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-5.4",
    checkpointer=InMemorySaver(),  # 线程限制所需
    tools=[],
    middleware=[
        ModelCallLimitMiddleware(
            thread_limit=10,
            run_limit=5,
            exit_behavior="end",
        ),
    ],
)
```

观看此视频指南，了解模型调用限制中间件的行为。

`thread_limit`  
在一个线程中所有运行的最大模型调用次数。默认为无限制。

`run_limit`  
单次调用的最大模型调用次数。默认为无限制。

`exit_behavior`  
达到限制时的行为。选项：`'end'`（优雅终止）或 `'error'`（引发异常）

### Tool call limit

通过限制 tool calls 的次数来控制 agent 执行，可以是全局所有工具的限制，也可以是特定工具的限制。工具调用限制在以下场景中很有用：

* 防止过多调用昂贵的外部 API。
* 限制网络搜索或数据库查询。
* 对特定工具的使用实施速率限制。
* 防止 agent 陷入失控循环。

**API 参考：** `ToolCallLimitMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, database_tool],
    middleware=[
        # 全局限制
        ToolCallLimitMiddleware(thread_limit=20, run_limit=10),
        # 工具特定限制
        ToolCallLimitMiddleware(
            tool_name="search",
            thread_limit=5,
            run_limit=3,
        ),
    ],
)
```

观看此视频指南，了解工具调用限制中间件的行为。

`tool_name`  
要限制的特定工具的名称。如果未提供，则限制适用于**所有全局工具**。

`thread_limit`  
在一个线程（对话）的所有运行中最大工具调用次数。在具有相同线程 ID 的多次调用中持续存在。需要 checkpointer 来维护状态。`None` 表示无线程限制。

`run_limit`  
单次调用（一条用户消息 → 响应周期）的最大工具调用次数。随每条新用户消息重置。`None` 表示无运行限制。

    **注意：** 必须至少指定 `thread_limit` 或 `run_limit` 中的一个。

`exit_behavior`  
达到限制时的行为：

    * `'continue'`（默认）- 用错误消息阻止超出的工具调用，让其他工具和模型继续。模型根据错误消息决定何时结束。
    * `'error'` - 引发 `ToolCallLimitExceededError` 异常，立即停止执行
    * `'end'` - 立即停止执行，并为超出的工具调用返回 `ToolMessage` 和 AI 消息。仅在限制单个工具时有效；如果其他工具有待处理的调用，则引发 `NotImplementedError`。

使用以下方式指定限制：

  * **线程限制 (Thread limit)** - 在一个对话的所有运行中最大调用次数（需要 checkpointer）
  * **运行限制 (Run limit)** - 单次调用的最大调用次数（每轮重置）

  退出行为 (Exit behaviors)：

  * `'continue'`（默认）- 用错误消息阻止超出的调用，agent 继续
  * `'error'` - 立即引发异常
  * `'end'` - 使用 ToolMessage + AI 消息停止（仅限单工具场景）

  ```python
  from langchain.agents import create_agent
  from langchain.agents.middleware import ToolCallLimitMiddleware

global_limiter = ToolCallLimitMiddleware(thread_limit=20, run_limit=10)
  search_limiter = ToolCallLimitMiddleware(tool_name="search", thread_limit=5, run_limit=3)
  database_limiter = ToolCallLimitMiddleware(tool_name="query_database", thread_limit=10)
  strict_limiter = ToolCallLimitMiddleware(tool_name="scrape_webpage", run_limit=2, exit_behavior="error")

  agent = create_agent(
      model="gpt-5.4",
      tools=[search_tool, database_tool, scraper_tool],
      middleware=[global_limiter, search_limiter, database_limiter, strict_limiter],
  )
  ```

### Model fallback

当主模型失败时自动回退到备选模型。模型回退在以下场景中很有用：

* 构建能够处理模型中断的弹性 agent。
* 通过回退到更便宜的模型进行成本优化。
* 跨 OpenAI、Anthropic 等的 Provider 冗余。

**API 参考：** `ModelFallbackMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        ModelFallbackMiddleware(
            "gpt-5.4-mini",
            "claude-3-5-sonnet-20241022",
        ),
    ],
)
```

观看此视频指南，了解模型回退中间件的行为。

`fallback_model`  
当主模型失败时首先尝试的备选模型。可以是模型标识符字符串（例如 `'openai:gpt-5.4-mini'`）或 `BaseChatModel` 实例。

`additional_fallbacks`  
如果之前的模型失败，按顺序尝试的附加备选模型

### PII detection

使用可配置策略检测并处理对话中的个人身份信息 (PII)。PII 检测在以下场景中很有用：

* 具有合规要求的医疗保健和金融应用程序。
* 需要清理日志的客户服务 agent。
* 任何处理敏感用户数据的应用程序。

**API 参考：** `PIIMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
    ],
)
```

#### 自定义 PII 类型

您可以通过提供 `detector` 参数来创建自定义 PII 类型。这使您能够检测超出内置类型的特定于您的用例的模式。

**创建自定义检测器的三种方法：**

1.  **正则表达式模式字符串** - 简单模式匹配

2.  **自定义函数** - 带有验证的复杂检测逻辑

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
import re

# 方法 1：正则表达式模式字符串
agent1 = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{32}",
            strategy="block",
        ),
    ],
)

# 方法 2：编译后的正则表达式模式
agent2 = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        PIIMiddleware(
            "phone_number",
            detector=re.compile(r"\+?\d{1,3}[\s.-]?\d{3,4}[\s.-]?\d{4}"),
            strategy="mask",
        ),
    ],
)

# 方法 3：自定义检测器函数
def detect_ssn(content: str) -> list[dict[str, str | int]]:
    """检测并验证 SSN。

    返回包含 'text'、'start' 和 'end' 键的字典列表。
    """
    import re
    matches = []
    pattern = r"\d{3}-\d{2}-\d{4}"
    for match in re.finditer(pattern, content):
        ssn = match.group(0)
        # 验证：前三位数字不应是 000、666 或 900-999
        first_three = int(ssn[:3])
        if first_three not in [0, 666] and not (900 <= first_three <= 999):
            matches.append({
                "text": ssn,
                "start": match.start(),
                "end": match.end(),
            })
    return matches

agent3 = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        PIIMiddleware(
            "ssn",
            detector=detect_ssn,
            strategy="hash",
        ),
    ],
)
```

**自定义检测器函数签名：**

检测器函数必须接受一个字符串 (content) 并返回匹配项：

返回一个字典列表，包含 `text`、`start` 和 `end` 键：

```python
def detector(content: str) -> list[dict[str, str | int]]:
    return [
        {"text": "matched_text", "start": 0, "end": 12},
        # ... 更多匹配项
    ]
```

对于自定义检测器：

  * 对简单模式使用正则表达式字符串
  * 当需要标志（例如，不区分大小写匹配）时使用 RegExp 对象
  * 当需要超出模式匹配的验证逻辑时使用自定义函数
  * 自定义函数让您完全控制检测逻辑，可以实现复杂的验证规则

`pii_type`  
要检测的 PII 类型。可以是内置类型（`email`、`credit_card`、`ip`、`mac_address`、`url`）或自定义类型名称。

`strategy`  
如何处理检测到的 PII。选项：

    * `'block'` - 检测到时引发异常
    * `'redact'` - 替换为 `[REDACTED_{PII_TYPE}]`
    * `'mask'` - 部分遮盖（例如 `****-****-****-1234`）
    * `'hash'` - 替换为确定性哈希

`detector`  
自定义检测器函数或正则表达式模式。如果未提供，则使用 PII 类型的内置检测器。

`apply_to_input`  
检查模型调用前的用户消息

`apply_to_output`  
检查模型调用后的 AI 消息

`apply_to_tool`  
检查执行后的工具结果消息

### To-do list

为 agent 配备任务规划和跟踪能力，以处理复杂的多步骤任务。待办事项列表在以下场景中很有用：

* 需要跨多个工具协调的复杂多步骤任务。
* 需要进度可见性的长时间运行操作。

此中间件自动为 agent 提供 `write_todos` 工具和系统提示，以指导有效的任务规划。

**API 参考：** `TodoListMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[read_file, write_file, run_tests],
    middleware=[TodoListMiddleware()],
)
```

观看此视频指南，了解待办事项列表中间件的行为。

`system_prompt`  
用于指导待办事项使用的自定义系统提示。如果未指定，则使用内置提示。

`tool_description`  
`write_todos` 工具的自定义描述。如果未指定，则使用内置描述。

### LLM tool selector

使用 LLM 智能选择相关工具，然后再调用主模型。LLM 工具选择器在以下场景中很有用：

* 具有许多工具 (10+) 的 agent，其中大多数与每个查询无关。
* 通过过滤不相关的工具来减少 token 使用量。
* 提高模型聚焦和准确性。

此中间件使用结构化输出询问 LLM 哪些工具与当前查询最相关。结构化输出 schema 定义了可用的工具名称和描述。模型 provider 通常会在后台将此结构化输出信息添加到系统提示中。

**API 参考：** `LLMToolSelectorMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolSelectorMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[tool1, tool2, tool3, tool4, tool5, ...],
    middleware=[
        LLMToolSelectorMiddleware(
            model="gpt-5.4-mini",
            max_tools=3,
            always_include=["search"],
        ),
    ],
)
```

`model`  
用于工具选择的模型。可以是模型标识符字符串（例如 `'openai:gpt-5.4-mini'`）或 `BaseChatModel` 实例。有关更多信息，请参阅 `init_chat_model`。

    默认为 agent 的主模型。

`prompt_instructions`  
用于选择模型的说明。如果未指定，则使用内置提示。

`max_tools`  
要选择的最大工具数量。如果模型选择了更多，则只使用前 `max_tools` 个。如果未指定，则无限制。

`always_include`  
无论选择如何都始终包含的工具名称。这些不计入 `max_tools` 限制。

### Tool retry

使用可配置的指数退避自动重试失败的工具调用。工具重试在以下场景中很有用：

* 处理外部 API 调用中的瞬时故障。
* 提高依赖网络的工具的可靠性。
* 构建能够优雅处理临时错误的弹性 agent。

**API 参考：** `ToolRetryMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, database_tool],
    middleware=[
        ToolRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
        ),
    ],
)
```

`max_retries`  
初始调用之后的最大重试次数（默认情况下总共 3 次尝试）

`tools`  
要对其应用重试逻辑的工具或工具名称的可选列表。如果为 `None`，则适用于所有工具。

`retry_on`  
要么是要重试的异常类型的元组，要么是一个可调用对象，该对象接受一个异常并在应重试时返回 `True`。

`on_failure`  
当所有重试都耗尽时的行为。选项：

    * `'return_message'` - 返回带有错误详细信息的 `ToolMessage`（允许 LLM 处理失败）
    * `'raise'` - 重新引发异常（停止 agent 执行）
    * 自定义可调用对象 - 接受异常并返回 `ToolMessage` 内容字符串的函数

`backoff_factor`  
指数退避的乘数。每次重试等待 `initial_delay * (backoff_factor ** retry_number)` 秒。设置为 `0.0` 表示恒定延迟。

`initial_delay`  
第一次重试前的初始延迟（秒）

`max_delay`  
重试之间的最大延迟（秒）（限制指数退避增长）

`jitter`  
是否添加随机抖动（`±25%`）以避免惊群效应

中间件使用指数退避自动重试失败的工具调用。

  **关键配置：**

  * `max_retries` - 重试次数（默认值：2）
  * `backoff_factor` - 指数退避的乘数（默认值：2.0）
  * `initial_delay` - 起始延迟（秒）（默认值：1.0）
  * `max_delay` - 延迟增长的上限（默认值：60.0）
  * `jitter` - 添加随机变化（默认值：True）

  **失败处理 (Failure handling)：**

  * `on_failure='return_message'` - 返回错误消息
  * `on_failure='raise'` - 重新引发异常
  * 自定义函数 - 返回错误消息的函数

  ```python
  from langchain.agents import create_agent
  from langchain.agents.middleware import ToolRetryMiddleware

agent = create_agent(
      model="gpt-5.4",
      tools=[search_tool, database_tool, api_tool],
      middleware=[
          ToolRetryMiddleware(
              max_retries=3,
              backoff_factor=2.0,
              initial_delay=1.0,
              max_delay=60.0,
              jitter=True,
              tools=["api_tool"],
              retry_on=(ConnectionError, TimeoutError),
              on_failure="continue",
          ),
      ],
  )
  ```

### Model retry

使用可配置的指数退避自动重试失败的模型调用。模型重试在以下场景中很有用：

* 处理模型 API 调用中的瞬时故障。
* 提高依赖网络的模型请求的可靠性。
* 构建能够优雅处理临时模型错误的弹性 agent。

**API 参考：** `ModelRetryMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, database_tool],
    middleware=[
        ModelRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
        ),
    ],
)
```

`max_retries`  
初始调用之后的最大重试次数（默认情况下总共 3 次尝试）

`retry_on`  
要么是要重试的异常类型的元组，要么是一个可调用对象，该对象接受一个异常并在应重试时返回 `True`。

`on_failure`  
当所有重试都耗尽时的行为。选项：

    * `'continue'`（默认）- 返回带有错误详细信息的 `AIMessage`，允许 agent 可能优雅地处理失败
    * `'error'` - 重新引发异常（停止 agent 执行）
    * 自定义可调用对象 - 接受异常并返回 `AIMessage` 内容字符串的函数

`backoff_factor`  
指数退避的乘数。每次重试等待 `initial_delay * (backoff_factor ** retry_number)` 秒。设置为 `0.0` 表示恒定延迟。

`initial_delay`  
第一次重试前的初始延迟（秒）

`max_delay`  
重试之间的最大延迟（秒）（限制指数退避增长）

`jitter`  
是否添加随机抖动（`±25%`）以避免惊群效应

中间件使用指数退避自动重试失败的模型调用。

  ```python
  from langchain.agents import create_agent
  from langchain.agents.middleware import ModelRetryMiddleware

# 使用默认设置的基本用法（2 次重试，指数退避）
  agent = create_agent(
      model="gpt-5.4",
      tools=[search_tool],
      middleware=[ModelRetryMiddleware()],
  )

  # 自定义异常过滤
  class TimeoutError(Exception):
      """超时错误的自定义异常。"""
      pass

  class ConnectionError(Exception):
      """连接错误的自定义异常。"""
      pass

  # 仅重试特定异常
  retry = ModelRetryMiddleware(
      max_retries=4,
      retry_on=(TimeoutError, ConnectionError),
      backoff_factor=1.5,
  )

def should_retry(error: Exception) -> bool:
      # 仅在速率限制错误时重试
      if isinstance(error, TimeoutError):
          return True
      # 或检查特定的 HTTP 状态码
      if hasattr(error, "status_code"):
          return error.status_code in (429, 503)
      return False

  retry_with_filter = ModelRetryMiddleware(
      max_retries=3,
      retry_on=should_retry,
  )

  # 返回错误消息而不是引发异常
  retry_continue = ModelRetryMiddleware(
      max_retries=4,
      on_failure="continue",  # 返回带有错误的 AIMessage 而不是引发异常
  )

  # 自定义错误消息格式
  def format_error(error: Exception) -> str:
      return f"Model call failed: {error}. Please try again later."

  retry_with_formatter = ModelRetryMiddleware(
      max_retries=4,
      on_failure=format_error,
  )

  # 恒定退避（无指数增长）
  constant_backoff = ModelRetryMiddleware(
      max_retries=5,
      backoff_factor=0.0,  # 无指数增长
      initial_delay=2.0,   # 始终等待 2 秒
  )

  # 失败时引发异常
  strict_retry = ModelRetryMiddleware(
      max_retries=2,
      on_failure="error",  # 重新引发异常而不是返回消息
  )
  ```

### LLM tool emulator

使用 LLM 模拟工具执行以用于测试目的，用 AI 生成的响应替换实际的 tool calls。LLM 工具模拟器在以下场景中很有用：

* 在不执行真实工具的情况下测试 agent 行为。
* 在外部工具不可用或昂贵时开发 agent。
* 在实现实际工具之前原型化 agent 工作流。

**API 参考：** `LLMToolEmulator`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolEmulator

agent = create_agent(
    model="gpt-5.4",
    tools=[get_weather, search_database, send_email],
    middleware=[
        LLMToolEmulator(),  # 模拟所有工具
    ],
)
```

`tools`  
要模拟的工具名称（str）或 `BaseTool` 实例列表。如果为 `None`（默认），将模拟**所有**工具。如果为空列表 `[]`，则不会模拟任何工具。如果是包含工具名称/实例的数组，则仅模拟这些工具。

`model`  
用于生成模拟工具响应的模型。可以是模型标识符字符串（例如 `'google_genai:gemini-3.1-pro-preview'`）或 `BaseChatModel` 实例。如果未指定，默认为 agent 的模型。有关更多信息，请参阅 `init_chat_model`。

中间件使用 LLM 为 tool calls 生成看似合理的响应，而不是执行实际工具。

  ```python
  from langchain.agents import create_agent
  from langchain.agents.middleware import LLMToolEmulator
  from langchain.tools import tool

@tool
  def get_weather(location: str) -> str:
      """获取某个位置的当前天气。"""
      return f"Weather in {location}"

  @tool
  def send_email(to: str, subject: str, body: str) -> str:
      """发送电子邮件。"""
      return "Email sent"

# 模拟所有工具（默认行为）
  agent = create_agent(
      model="gpt-5.4",
      tools=[get_weather, send_email],
      middleware=[LLMToolEmulator()],
  )

  # 仅模拟特定工具
  agent2 = create_agent(
      model="gpt-5.4",
      tools=[get_weather, send_email],
      middleware=[LLMToolEmulator(tools=["get_weather"])],
  )

  # 使用自定义模型进行模拟
  agent4 = create_agent(
      model="gpt-5.4",
      tools=[get_weather, send_email],
      middleware=[LLMToolEmulator(model="claude-sonnet-4-6")],
  )
  ```

### Context editing

当达到 token 限制时，通过清除较旧的工具调用来管理对话上下文，同时保留最近的结果。这有助于在具有许多工具调用的长对话中保持上下文窗口的可管理性。上下文编辑在以下场景中很有用：

* 具有许多超出 token 限制的工具调用的长对话
* 通过删除不再相关的较旧工具输出来降低 token 成本
* 在上下文中仅保留最近 N 个工具结果

**API 参考：** `ContextEditingMiddleware`, `ClearToolUsesEdit`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ContextEditingMiddleware, ClearToolUsesEdit

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        ContextEditingMiddleware(
            edits=[
                ClearToolUsesEdit(
                    trigger=100000,
                    keep=3,
                ),
            ],
        ),
    ],
)
```

`edits`  
要应用的 `ContextEdit` 策略列表

`token_counter`  
Token 计数方法。选项：`'approximate'` 或 `'model'`

**`ClearToolUsesEdit` 选项：**

`trigger`  
触发编辑的 token 计数。当对话超过此 token 计数时，将清除较旧的工具输出。

`reclaim`  
当编辑运行时，要回收的最小 token 数。如果设置为 0，则根据需要清除尽可能多的内容。

`keep`  
必须保留的最近工具结果的数量。这些永远不会被清除。

`clear_tool_inputs`  
是否清除 AI 消息上原始工具调用参数。当为 `True` 时，工具调用参数被替换为空对象。

`exclude_tools`  
要从清除中排除的工具名称列表。这些工具的输出永远不会被清除。

`placeholder`  
为清除的工具输出插入的占位文本。这替换了原始工具消息内容。

中间件在达到 token 限制时应用上下文编辑策略。最常见的策略是 `ClearToolUsesEdit`，它在保留最近结果的同时清除较旧的工具结果。

  **工作原理：**

  1. 监控对话中的 token 计数
  2. 当达到阈值时，清除较旧的工具输出
  3. 保留最近 N 个工具结果
  4. 可选地保留工具调用参数作为上下文

  ```python
  from langchain.agents import create_agent
  from langchain.agents.middleware import ContextEditingMiddleware, ClearToolUsesEdit

agent = create_agent(
      model="gpt-5.4",
      tools=[search_tool, your_calculator_tool, database_tool],
      middleware=[
          ContextEditingMiddleware(
              edits=[
                  ClearToolUsesEdit(
                      trigger=2000,
                      keep=3,
                      clear_tool_inputs=False,
                      exclude_tools=[],
                      placeholder="[cleared]",
                  ),
              ],
          ),
      ],
  )
  ```

### Shell tool

向 agent 暴露持久的 shell 会话以执行命令。Shell 工具中间件在以下场景中很有用：

* 需要执行系统命令的 agent
* 开发和部署自动化任务
* 测试和验证工作流
* 文件系统操作和脚本执行

**安全考虑**：使用适当的执行策略（`HostExecutionPolicy`、`DockerExecutionPolicy` 或 `CodexSandboxExecutionPolicy`）以匹配部署的安全要求。

**限制**：持久 shell 会话当前不适用于中断（人机交互）。我们预计将来会添加对此的支持。

**API 参考：** `ShellToolMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ShellToolMiddleware,
    HostExecutionPolicy,
)

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool],
    middleware=[
        ShellToolMiddleware(
            workspace_root="/workspace",
            execution_policy=HostExecutionPolicy(),
        ),
    ],
)
```

`workspace_root`  
Shell 会话的基本目录。如果省略，则在 agent 启动时创建一个临时目录，并在 agent 结束时删除。

`startup_commands`  
会话启动后顺序执行的可选命令

`shutdown_commands`  
会话关闭前执行的可选命令

`execution_policy`  
控制超时、输出限制和资源配置的执行策略。选项：

    * `HostExecutionPolicy` - 完全主机访问（默认）；最适合代理已经在容器或 VM 内运行的可信环境
    * `DockerExecutionPolicy` - 为每个 agent 运行启动一个单独的 Docker 容器，提供更强的隔离
    * `CodexSandboxExecutionPolicy` - 重用 Codex CLI 沙箱以增加系统调用/文件系统限制

`redaction_rules`  
在将命令输出返回给模型之前，用于清理命令输出的可选编辑规则。

编辑规则在事后应用，并不能在使用 `HostExecutionPolicy` 时防止机密或敏感数据的泄露。

`tool_description`  
已注册 shell 工具描述的可选覆盖

`shell_executable`  
用于启动持久会话的可选 shell 可执行文件（字符串）或参数序列。默认为 `/bin/bash`。

`env`  
提供给 shell 会话的可选环境变量。在命令执行前，值会被强制转换为字符串。

中间件提供一个单一的持久 shell 会话，agent 可以使用它顺序执行命令。

  **执行策略 (Execution policies)：**

  * `HostExecutionPolicy`（默认）- 具有完整主机访问权限的本机执行
  * `DockerExecutionPolicy` - 隔离的 Docker 容器执行
  * `CodexSandboxExecutionPolicy` - 通过 Codex CLI 进行沙箱化执行

  ```python
  from langchain.agents import create_agent
  from langchain.agents.middleware import (
      ShellToolMiddleware,
      HostExecutionPolicy,
      DockerExecutionPolicy,
      RedactionRule,
  )

# 具有主机执行的基本 shell 工具
  agent = create_agent(
      model="gpt-5.4",
      tools=[search_tool],
      middleware=[
          ShellToolMiddleware(
              workspace_root="/workspace",
              execution_policy=HostExecutionPolicy(),
          ),
      ],
  )

  # 具有启动命令的 Docker 隔离
  agent_docker = create_agent(
      model="gpt-5.4",
      tools=[],
      middleware=[
          ShellToolMiddleware(
              workspace_root="/workspace",
              startup_commands=["pip install requests", "export PYTHONPATH=/workspace"],
              execution_policy=DockerExecutionPolicy(
                  image="python:3.11-slim",
                  command_timeout=60.0,
              ),
          ),
      ],
  )

  # 带输出编辑（事后应用）
  agent_redacted = create_agent(
      model="gpt-5.4",
      tools=[],
      middleware=[
          ShellToolMiddleware(
              workspace_root="/workspace",
              redaction_rules=[
                  RedactionRule(pii_type="api_key", detector=r"sk-[a-zA-Z0-9]{32}"),
              ],
          ),
      ],
  )
  ```

### File search

提供对文件系统的 Glob 和 Grep 搜索工具。文件搜索中间件在以下场景中很有用：

* 代码探索和分析
* 按名称模式查找文件
* 使用正则表达式搜索代码内容
* 需要文件发现的大型代码库

**API 参考：** `FilesystemFileSearchMiddleware`

```python
from langchain.agents import create_agent
from langchain.agents.middleware import FilesystemFileSearchMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        FilesystemFileSearchMiddleware(
            root_path="/workspace",
            use_ripgrep=True,
        ),
    ],
)
```

`root_path`  
要搜索的根目录。所有文件操作都相对于此路径。

`use_ripgrep`  
是否使用 ripgrep 进行搜索。如果 ripgrep 不可用，则回退到 Python 正则表达式。

`max_file_size_mb`  
要搜索的最大文件大小（MB）。大于此值的文件将被跳过。

中间件向 agents 添加了两个搜索工具：

  **Glob 工具** - 快速文件模式匹配：

  * 支持 `**/*.py`、`src/**/*.ts` 等模式
  * 返回按修改时间排序的匹配文件路径

  **Grep 工具** - 使用正则表达式进行内容搜索：

  * 完整的正则表达式语法支持
  * 使用 `include` 参数按文件模式过滤
  * 三种输出模式：`files_with_matches`、`content`、`count`

  ```python
  from langchain.agents import create_agent
  from langchain.agents.middleware import FilesystemFileSearchMiddleware
  from langchain.messages import HumanMessage

agent = create_agent(
      model="gpt-5.4",
      tools=[],
      middleware=[
          FilesystemFileSearchMiddleware(
              root_path="/workspace",
              use_ripgrep=True,
              max_file_size_mb=10,
          ),
      ],
  )

  # Agent 现在可以使用 glob_search 和 grep_search 工具
  result = agent.invoke({
      "messages": [HumanMessage("Find all Python files containing 'async def'")]
  })

  # Agent 将使用：
  # 1. glob_search(pattern="**/*.py") 查找 Python 文件
  # 2. grep_search(pattern="async def", include="*.py") 查找异步函数
  ```

### Filesystem middleware

上下文工程是构建有效 agent 的主要挑战。当使用返回可变长度结果的工具（例如 `web_search` 和 RAG）时，这一点尤其困难，因为长的工具结果会快速填满您的上下文窗口。

来自 Deep Agents 的 `FilesystemMiddleware` 提供了四个用于与短期和长期记忆交互的工具：

* `ls`：列出文件系统中的文件
* `read_file`：读取整个文件或文件的特定行数
* `write_file`：向文件系统写入新文件
* `edit_file`：编辑文件系统中的现有文件

```python
from langchain.agents import create_agent
from deepagents.middleware.filesystem import FilesystemMiddleware

# FilesystemMiddleware 默认包含在 create_deep_agent 中
# 如果构建自定义 agent，可以自定义它
agent = create_agent(
    model="claude-sonnet-4-6",
    middleware=[
        FilesystemMiddleware(
            backend=None,  # 可选：自定义后端（默认为 StateBackend）
            system_prompt="在以下情况下写入文件系统...",  # 可选：对系统提示的自定义添加
            custom_tool_descriptions={
                "ls": "在以下情况下使用 ls 工具...",
                "read_file": "使用 read_file 工具来..."
            }  # 可选：文件系统工具的自定义描述
        ),
    ],
)
```

#### 短期与长期文件系统

默认情况下，这些工具会写入图形状态中的本地“文件系统”。要启用跨线程的持久存储，请配置一个 `CompositeBackend`，将特定路径（如 `/memories/`）路由到 `StoreBackend`。

```python
from langchain.agents import create_agent
from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

agent = create_agent(
    model="claude-sonnet-4-6",
    store=store,
    middleware=[
        FilesystemMiddleware(
            backend=CompositeBackend(
                default=StateBackend(),
                routes={"/memories/": StoreBackend()}
            ),
            custom_tool_descriptions={
                "ls": "在以下情况下使用 ls 工具...",
                "read_file": "使用 read_file 工具来..."
            }  # 可选：文件系统工具的自定义描述
        ),
    ],
)
```

当您配置了带有 `/memories/` 的 `StoreBackend` 的 `CompositeBackend` 时，任何以 **/memories/** 为前缀的文件都将保存到持久存储中，并在不同线程之间保持不变。没有此前缀的文件仍保留在临时状态存储中。

### Subagent

将任务移交给子 agents 可以隔离上下文，使主（监督）agent 的上下文窗口保持干净，同时仍能深入处理任务。

来自 Deep Agents 的子 agents 中间件允许您通过 `task` 工具提供子 agents。

```python
from langchain.tools import tool
from langchain.agents import create_agent
from deepagents.middleware.subagents import SubAgentMiddleware

@tool
def get_weather(city: str) -> str:
    """获取城市的天气。"""
    return f"The weather in {city} is sunny."

agent = create_agent(
    model="claude-sonnet-4-6",
    middleware=[
        SubAgentMiddleware(
            default_model="claude-sonnet-4-6",
            default_tools=[],
            subagents=[
                {
                    "name": "weather",
                    "description": "此子 agent 可以获取城市的天气。",
                    "system_prompt": "使用 get_weather 工具获取城市的天气。",
                    "tools": [get_weather],
                    "model": "gpt-5.4",
                    "middleware": [],
                }
            ],
        )
    ],
)
```

子 agent 由 **名称 (name)**、**描述 (description)**、**系统提示 (system prompt)** 和 **工具 (tools)** 定义。您还可以为子 agent 提供自定义的 **模型 (model)**，或附加的 **中间件 (middleware)**。当您想给子 agent 一个额外的状态键与主 agent 共享时，这尤其有用。

对于更复杂的用例，您还可以提供自己预构建的 LangGraph 图作为子 agent。

```python
from langchain.agents import create_agent
from deepagents.middleware.subagents import SubAgentMiddleware
from deepagents import CompiledSubAgent
from langgraph.graph import StateGraph

# 创建一个自定义的 LangGraph 图
def create_weather_graph():
    workflow = StateGraph(...)
    # 构建您的自定义图
    return workflow.compile()

weather_graph = create_weather_graph()

# 将其包装在 CompiledSubAgent 中
weather_subagent = CompiledSubAgent(
    name="weather",
    description="此子 agent 可以获取城市的天气。",
    runnable=weather_graph
)

agent = create_agent(
    model="claude-sonnet-4-6",
    middleware=[
        SubAgentMiddleware(
            default_model="claude-sonnet-4-6",
            default_tools=[],
            subagents=[weather_subagent],
        )
    ],
)
```

除了任何用户定义的子 agent 之外，主 agent 始终可以访问一个 `general-purpose` 子 agent。此子 agent 具有与主 agent 相同的指令以及它可以访问的所有工具。`general-purpose` 子 agent 的主要目的是上下文隔离——主 agent 可以将复杂任务委托给此子 agent，并获得简洁的答案，而不会因中间工具调用而膨胀。

## 特定 Provider 的中间件 (Provider-specific middleware)

这些中间件针对特定的 LLM providers 进行了优化。有关完整详细信息和示例，请参阅每个 provider 的文档。

针对 Claude 模型的提示缓存、bash 工具、文本编辑器、记忆和文件搜索中间件。

针对 Amazon Bedrock 模型的提示缓存中间件。

针对 OpenAI 模型的内容审核中间件。
