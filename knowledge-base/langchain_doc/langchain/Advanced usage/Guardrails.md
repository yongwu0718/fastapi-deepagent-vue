# Guardrails

> 为您的 agent 实现安全检查与内容过滤

Guardrails 通过在 agent 执行的关键节点验证和过滤内容，帮助您构建安全、合规的 AI 应用。它们可以检测敏感信息、执行内容策略、验证输出，并在问题发生前阻止不安全行为。

常见用例包括：

* 防止 PII 泄露
* 检测并阻断提示注入攻击
* 屏蔽不当或有害内容
* 执行业务规则和合规要求
* 验证输出质量与准确性

您可以使用 middleware 在 strategic points（agent 启动前、完成后，或围绕模型与工具调用）拦截执行，从而实现 guardrails。

Guardrails 可以通过两种互补的方式实现：

使用基于规则的逻辑，例如正则表达式、关键词匹配或显式检查。快速、可预测、成本低，但可能遗漏细微的违规。

使用 LLM 或分类器通过语义理解评估内容。能够捕捉规则遗漏的细微问题，但速度较慢且成本更高。

LangChain 提供了内置 guardrails（如 PII 检测、人机交互）以及一个灵活的 middleware 系统，用于使用任一种方法构建自定义 guardrails。

## 内置 Guardrails

### PII 检测

LangChain 提供了用于检测和处理对话中个人身份信息（PII）的内置 middleware。该 middleware 可以检测常见的 PII 类型，如电子邮件、信用卡号、IP 地址等。

PII detection middleware 对于以下情况很有帮助：具有合规要求的医疗和金融应用、需要清理日志的客服 agent，以及通常任何处理敏感用户数据的应用。

PII middleware 支持多种策略来处理检测到的 PII：

| 策略        | 描述                               | 示例                  |
| ----------- | ---------------------------------- | --------------------- |
| `redact`    | 替换为 `[REDACTED_{PII_TYPE}]`     | `[REDACTED_EMAIL]`    |
| `mask`      | 部分遮盖（例如，仅显示后四位）      | `****-****-****-1234` |
| `hash`      | 替换为确定性哈希                   | `a8f5f167...`         |
| `block`     | 检测到时引发异常                   | 抛出错误              |

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[customer_service_tool, email_tool],
    middleware=[
        # 在发送给模型之前编辑用户输入中的电子邮件
        PIIMiddleware(
            "email",
            strategy="redact",
            apply_to_input=True,
        ),
        # 遮盖用户输入中的信用卡号
        PIIMiddleware(
            "credit_card",
            strategy="mask",
            apply_to_input=True,
        ),
        # 阻断 API 密钥 - 检测到则报错
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{32}",
            strategy="block",
            apply_to_input=True,
        ),
    ],
)

# 当用户提供 PII 时，将根据策略进行处理
result = agent.invoke({
    "messages": [{"role": "user", "content": "My email is john.doe@example.com and card is 5105-1051-0510-5100"}]
})
```

**内置 PII 类型：**

  * `email` - 电子邮件地址
  * `credit_card` - 信用卡号（Luhn 验证）
  * `ip` - IP 地址
  * `mac_address` - MAC 地址
  * `url` - URL

  **配置选项：**

  | 参数                    | 描述                                                | 默认值                 |
  | ----------------------- | --------------------------------------------------- | ---------------------- |
  | `pii_type`              | 要检测的 PII 类型（内置或自定义）                   | 必需                   |
  | `strategy`              | 处理检测到 PII 的策略（`"block"`, `"redact"`, `"mask"`, `"hash"`） | `"redact"`             |
  | `detector`              | 自定义检测函数或正则表达式模式                      | `None`（使用内置）     |
  | `apply_to_input`        | 在模型调用前检查用户消息                            | `True`                 |
  | `apply_to_output`       | 在模型调用后检查 AI 消息                            | `False`                |
  | `apply_to_tool_results` | 执行后检查工具结果消息                              | `False`                |

有关 PII 检测功能的完整详细信息，请参阅 middleware 文档。

### Human-in-the-loop

LangChain 提供了内置 middleware，用于在执行敏感操作之前要求人工批准。这是针对高风险决策最有效的 guardrails 之一。

Human-in-the-loop middleware 对于以下情况很有帮助：金融交易和转账、删除或修改生产数据、向外部方发送通信，以及任何具有重大业务影响的操作。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, send_email_tool, delete_database_tool],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                # 敏感操作需要批准
                "send_email": True,
                "delete_database": True,
                # 安全操作自动批准
                "search": False,
            }
        ),
    ],
    # 跨中断持久化状态
    checkpointer=InMemorySaver(),
)

# Human-in-the-loop 需要一个 thread ID 来实现持久化
config = {"configurable": {"thread_id": "some_id"}}

# Agent 将暂停并等待批准，然后再执行敏感工具
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Send an email to the team"}]},
    config=config
)

result = agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config  # 使用相同的 thread ID 恢复暂停的对话
)
```

有关实现批准工作流的完整详细信息，请参阅 human-in-the-loop 文档。

## 自定义 Guardrails

对于更复杂的 guardrails，您可以创建在 agent 执行之前或之后运行的自定义 middleware。这使您能够完全控制验证逻辑、内容过滤和安全检查。

### 在 Agent 之前的 Guardrails

使用 "before agent" hooks 在每次调用的开始时对请求进行一次验证。这对于会话级别的检查（如身份验证、速率限制或在任何处理开始前阻止不适当请求）非常有用。

```python
from typing import Any
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langgraph.runtime import Runtime

class ContentFilterMiddleware(AgentMiddleware):
  """确定性 guardrail：阻止包含禁用关键词的请求。"""

  def __init__(self, banned_keywords: list[str]):
	  super().__init__()
	  self.banned_keywords = [kw.lower() for kw in banned_keywords]

  @hook_config(can_jump_to=["end"])
  def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
	  # 获取第一条用户消息
	  if not state["messages"]:
		  return None

	  first_message = state["messages"][0]
	  if first_message.type != "human":
		  return None

	  content = first_message.content.lower()

	  # 检查禁用关键词
	  for keyword in self.banned_keywords:
		  if keyword in content:
			  # 在任何处理之前阻止执行
			  return {
				  "messages": [{
					  "role": "assistant",
					  "content": "I cannot process requests containing inappropriate content. Please rephrase your request."
				  }],
				  "jump_to": "end"
			  }

	  return None

# 使用自定义 guardrail
from langchain.agents import create_agent

agent = create_agent(
  model="gpt-5.4",
  tools=[search_tool, calculator_tool],
  middleware=[
	  ContentFilterMiddleware(
		  banned_keywords=["hack", "exploit", "malware"]
	  ),
  ],
)

# 此请求将在任何处理之前被阻止
result = agent.invoke({
  "messages": [{"role": "user", "content": "How do I hack into a database?"}]
})
```

```python
from typing import Any

from langchain.agents.middleware import before_agent, AgentState, hook_config
from langgraph.runtime import Runtime

banned_keywords = ["hack", "exploit", "malware"]

@before_agent(can_jump_to=["end"])
def content_filter(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
  """确定性 guardrail：阻止包含禁用关键词的请求。"""
  # 获取第一条用户消息
  if not state["messages"]:
	  return None

  first_message = state["messages"][0]
  if first_message.type != "human":
	  return None

  content = first_message.content.lower()

  # 检查禁用关键词
  for keyword in banned_keywords:
	  if keyword in content:
		  # 在任何处理之前阻止执行
		  return {
			  "messages": [{
				  "role": "assistant",
				  "content": "I cannot process requests containing inappropriate content. Please rephrase your request."
			  }],
			  "jump_to": "end"
		  }

  return None

# 使用自定义 guardrail
from langchain.agents import create_agent

agent = create_agent(
  model="gpt-5.4",
  tools=[search_tool, calculator_tool],
  middleware=[content_filter],
)

# 此请求将在任何处理之前被阻止
result = agent.invoke({
  "messages": [{"role": "user", "content": "How do I hack into a database?"}]
})
```

### 在 Agent 之后的 Guardrails

使用 "after agent" hooks 在返回给用户之前对最终输出进行一次验证。这对于基于模型的安全检查、质量验证或对完整 agent 响应进行最终合规扫描非常有用。

```python
  from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
  from langgraph.runtime import Runtime
  from langchain.messages import AIMessage
  from langchain.chat_models import init_chat_model
  from typing import Any

  class SafetyGuardrailMiddleware(AgentMiddleware):
      """基于模型的 guardrail：使用 LLM 评估响应安全性。"""

      def __init__(self):
          super().__init__()
          self.safety_model = init_chat_model("gpt-5.4-mini")

      @hook_config(can_jump_to=["end"])
      def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
          # 获取最终的 AI 响应
          if not state["messages"]:
              return None

          last_message = state["messages"][-1]
          if not isinstance(last_message, AIMessage):
              return None

          # 使用模型评估安全性
          safety_prompt = f"""Evaluate if this response is safe and appropriate.
          Respond with only 'SAFE' or 'UNSAFE'.

          Response: {last_message.content}"""

          result = self.safety_model.invoke([{"role": "user", "content": safety_prompt}])

          if "UNSAFE" in result.content:
              last_message.content = "I cannot provide that response. Please rephrase your request."

          return None

  # 使用安全性 guardrail
  from langchain.agents import create_agent

  agent = create_agent(
      model="gpt-5.4",
      tools=[search_tool, calculator_tool],
      middleware=[SafetyGuardrailMiddleware()],
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "How do I make explosives?"}]
  })
```

  ```python
  from langchain.agents.middleware import after_agent, AgentState, hook_config
  from langgraph.runtime import Runtime
  from langchain.messages import AIMessage
  from langchain.chat_models import init_chat_model
  from typing import Any

  safety_model = init_chat_model("gpt-5.4-mini")

  @after_agent(can_jump_to=["end"])
  def safety_guardrail(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
      """基于模型的 guardrail：使用 LLM 评估响应安全性。"""
      # 获取最终的 AI 响应
      if not state["messages"]:
          return None

      last_message = state["messages"][-1]
      if not isinstance(last_message, AIMessage):
          return None

      # 使用模型评估安全性
      safety_prompt = f"""Evaluate if this response is safe and appropriate.
      Respond with only 'SAFE' or 'UNSAFE'.

      Response: {last_message.content}"""

      result = safety_model.invoke([{"role": "user", "content": safety_prompt}])

      if "UNSAFE" in result.content:
          last_message.content = "I cannot provide that response. Please rephrase your request."

      return None

  # 使用安全性 guardrail
  from langchain.agents import create_agent

  agent = create_agent(
      model="gpt-5.4",
      tools=[search_tool, calculator_tool],
      middleware=[safety_guardrail],
  )

  result = agent.invoke({
      "messages": [{"role": "user", "content": "How do I make explosives?"}]
  })
  ```

### 组合多个 Guardrails

您可以通过将多个 guardrails 添加到 middleware 数组中来堆叠它们。它们按顺序执行，允许您构建分层保护：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware, HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, send_email_tool],
    middleware=[
        # 第 1 层：确定性输入过滤器（agent 之前）
        ContentFilterMiddleware(banned_keywords=["hack", "exploit"]),

        # 第 2 层：PII 保护（模型之前和之后）
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("email", strategy="redact", apply_to_output=True),

        # 第 3 层：敏感工具的人工批准
        HumanInTheLoopMiddleware(interrupt_on={"send_email": True}),

        # 第 4 层：基于模型的安全性检查（agent 之后）
        SafetyGuardrailMiddleware(),
    ],
)
```

## 其他资源

* Middleware 文档 - 自定义中间件的完整指南
* Middleware API 参考 - 自定义中间件的完整指南
* Human-in-the-loop - 为敏感操作添加人工审核
* 测试 agents - 测试安全机制的策略