# Agent 评估

> 使用 AgentEvals 和 LangSmith，通过 deterministic matching 或 LLM-as-judge evaluator 来评估 agent 的 trajectory。

评估 (evals) 通过考察 agent 的执行 trajectory，即它产生的 message 和 tool call 序列，来衡量 agent 的表现好坏。与验证基本正确性的 integration tests 不同，evals 会依据参考或评分标准对 agent 行为进行打分，因此在更改 prompts、tools 或模型时，它们能有效发现回归问题。

evaluator 是一个函数，它接收 agent 的输出（以及可选的参考输出）并返回一个分数：

```python
def evaluator(*, outputs: dict, reference_outputs: dict):
    output_messages = outputs["messages"]
    reference_messages = reference_outputs["messages"]
    score = compare_messages(output_messages, reference_messages)
    return {"key": "evaluator_score", "score": score}
```

`agentevals` 包为 agent trajectory 提供了预构建的 evaluator。您可以通过执行 **trajectory match**（确定性比较）或使用 **LLM judge**（定性评估）来进行评估：

| 方法                                        | 何时使用                                                                     |
| ----------------------------------------------- | ------------------------------------------------------------------------------- |
| Trajectory match | 当您知道预期的 tool call 并且希望进行快速、确定、零成本的检查时 |
| LLM-as-judge         | 当您希望评估整体质量和推理过程，而不局限于严格的预期时    |

## 安装 AgentEvals

```bash
pip install agentevals
```

或者，直接克隆 AgentEvals 仓库。

## Trajectory match evaluator

AgentEvals 提供了 `create_trajectory_match_evaluator` 函数，用于将 agent 的 trajectory 与参考进行匹配。共有四种模式：

| 模式        | 描述                                                                                    | 适用场景                                                              |
| ----------- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `strict`    | 消息结构和 tool call 顺序完全匹配（消息内容可以不同） | 测试特定序列（例如，授权前的策略查询） |
| `unordered` | 消息结构和 tool call 与参考相同，但 tool call 可以以任意顺序发生     | 当顺序无关紧要时验证信息检索             |
| `subset`    | agent 只调用了参考中的 tool（没有多余调用）                                              | 确保 agent 不超出预期范围                          |
| `superset`  | agent 至少调用了参考中的 tool（允许多余调用）                                      | 验证是否执行了最低要求的操作                          |

以下示例共享相同的设置，即一个带有 `get_weather` 工具的 agent：

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.messages import HumanMessage, AIMessage, ToolMessage
from agentevals.trajectory.match import create_trajectory_match_evaluator

@tool
def get_weather(city: str):
    """Get weather information for a city."""
    return f"It's 75 degrees and sunny in {city}."

agent = create_agent("claude-sonnet-4-6", tools=[get_weather])
```

`strict` 模式要求 trajectory 包含完全相同的消息、相同的顺序以及相同的 tool call，但允许消息内容存在差异。当您需要强制执行特定操作顺序时，这非常有用，例如要求在授权某个操作之前必须进行策略查询。

  ```python
  evaluator = create_trajectory_match_evaluator(  
      trajectory_match_mode="strict",  
  )  

  def test_weather_tool_called_strict():
      result = agent.invoke({
          "messages": [HumanMessage(content="What's the weather in San Francisco?")]
      })

      reference_trajectory = [
          HumanMessage(content="What's the weather in San Francisco?"),
          AIMessage(content="", tool_calls=[
              {"id": "call_1", "name": "get_weather", "args": {"city": "San Francisco"}}
          ]),
          ToolMessage(content="It's 75 degrees and sunny in San Francisco.", tool_call_id="call_1"),
          AIMessage(content="The weather in San Francisco is 75 degrees and sunny."),
      ]

      evaluation = evaluator(
          outputs=result["messages"],
          reference_outputs=reference_trajectory
      )
      # {
      #     'key': 'trajectory_strict_match',
      #     'score': True,
      #     'comment': None,
      # }
      assert evaluation["score"] is True
  ```

`unordered` 模式允许相同的 tool call 以任意顺序出现。当您想验证是否检索到了特定信息而不关心调用顺序时，这会很有帮助。例如，一个 agent 用不同的 tool call 来检查某个城市的天气和活动。

  ```python
  @tool
  def get_events(city: str):
      """Get events happening in a city."""
      return f"Concert at the park in {city} tonight."

  agent = create_agent("claude-sonnet-4-6", tools=[get_weather, get_events])

  evaluator = create_trajectory_match_evaluator(  
      trajectory_match_mode="unordered",  
  )  

  def test_multiple_tools_any_order():
      result = agent.invoke({
          "messages": [HumanMessage(content="What's happening in SF today?")]
      })

      reference_trajectory = [
          HumanMessage(content="What's happening in SF today?"),
          AIMessage(content="", tool_calls=[
              {"id": "call_1", "name": "get_events", "args": {"city": "SF"}},
              {"id": "call_2", "name": "get_weather", "args": {"city": "SF"}},
          ]),
          ToolMessage(content="Concert at the park in SF tonight.", tool_call_id="call_1"),
          ToolMessage(content="It's 75 degrees and sunny in SF.", tool_call_id="call_2"),
          AIMessage(content="Today in SF: 75 degrees and sunny with a concert at the park tonight."),
      ]

      evaluation = evaluator(
          outputs=result["messages"],
          reference_outputs=reference_trajectory,
      )
      assert evaluation["score"] is True
  ```

`superset` 和 `subset` 模式用于匹配局部 trajectory。`superset` 模式验证 agent 至少调用了参考 trajectory 中的 tool，并允许额外的 tool call。`subset` 模式则确保 agent 没有调用参考 trajectory 之外的任何 tool。

  ```python
  @tool
  def get_detailed_forecast(city: str):
      """Get detailed weather forecast for a city."""
      return f"Detailed forecast for {city}: sunny all week."

  agent = create_agent("claude-sonnet-4-6", tools=[get_weather, get_detailed_forecast])

  evaluator = create_trajectory_match_evaluator(  
      trajectory_match_mode="superset",  
  )  

  def test_agent_calls_required_tools_plus_extra():
      result = agent.invoke({
          "messages": [HumanMessage(content="What's the weather in Boston?")]
      })

      # Reference only requires get_weather, but agent may call additional tools
      reference_trajectory = [
          HumanMessage(content="What's the weather in Boston?"),
          AIMessage(content="", tool_calls=[
              {"id": "call_1", "name": "get_weather", "args": {"city": "Boston"}},
          ]),
          ToolMessage(content="It's 75 degrees and sunny in Boston.", tool_call_id="call_1"),
          AIMessage(content="The weather in Boston is 75 degrees and sunny."),
      ]

      evaluation = evaluator(
          outputs=result["messages"],
          reference_outputs=reference_trajectory,
      )
      assert evaluation["score"] is True
  ```

您还可以设置 `tool_args_match_mode` 属性和/或 `tool_args_match_overrides`，以自定义 evaluator 如何判定实际 trajectory 与参考 trajectory 中 tool call 的相等性。默认情况下，只有参数相同的同名 tool call 才被视为相等。详情请访问仓库。

## LLM-as-judge evaluator

您可以使用 LLM 来评估 agent 的执行路径，通过 `create_trajectory_llm_as_judge` 函数实现。与 trajectory match evaluator 不同，它不需要参考 trajectory，但如果有，也可以提供。

```python
  from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT

  evaluator = create_trajectory_llm_as_judge(  
      model="openai:o3-mini",  
      prompt=TRAJECTORY_ACCURACY_PROMPT,  
  )  

  def test_trajectory_quality():
      result = agent.invoke({
          "messages": [HumanMessage(content="What's the weather in Seattle?")]
      })

      evaluation = evaluator(
          outputs=result["messages"],
      )
      assert evaluation["score"] is True
```

如果您有参考 trajectory，可以使用预构建的 `TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE` 提示：

  ```python
  from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE

  evaluator = create_trajectory_llm_as_judge(
      model="openai:o3-mini",
      prompt=TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE,
  )
  evaluation = evaluator(
      outputs=result["messages"],
      reference_outputs=reference_trajectory,
  )
```

如需对 LLM 如何评估 trajectory 进行更多配置，请访问仓库。

## 异步支持

所有 `agentevals` evaluator 都支持 Python asyncio。在函数名中的 `create_` 之后添加 `async` 即可获得异步版本。

```python
  from agentevals.trajectory.llm import create_async_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT
  from agentevals.trajectory.match import create_async_trajectory_match_evaluator

  async_judge = create_async_trajectory_llm_as_judge(
      model="openai:o3-mini",
      prompt=TRAJECTORY_ACCURACY_PROMPT,
  )

  async_evaluator = create_async_trajectory_match_evaluator(
      trajectory_match_mode="strict",
  )

  async def test_async_evaluation():
      result = await agent.ainvoke({
          "messages": [HumanMessage(content="What's the weather?")]
      })

      evaluation = await async_judge(outputs=result["messages"])
      assert evaluation["score"] is True
  ```

## 在 LangSmith 中运行 evals

若要随时间跟踪实验，请将 evaluator 结果记录到 LangSmith。首先，设置所需的环境变量：

```bash
export LANGSMITH_API_KEY="your_langsmith_api_key"
export LANGSMITH_TRACING="true"
```

LangSmith 提供了两种主要的评估运行方式：pytest 集成和 `evaluate` 函数。

```python
  import pytest
  from langsmith import testing as t
  from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT

  trajectory_evaluator = create_trajectory_llm_as_judge(
      model="openai:o3-mini",
      prompt=TRAJECTORY_ACCURACY_PROMPT,
  )

  @pytest.mark.langsmith
  def test_trajectory_accuracy():
      result = agent.invoke({
          "messages": [HumanMessage(content="What's the weather in SF?")]
      })

      reference_trajectory = [
          HumanMessage(content="What's the weather in SF?"),
          AIMessage(content="", tool_calls=[
              {"id": "call_1", "name": "get_weather", "args": {"city": "SF"}},
          ]),
          ToolMessage(content="It's 75 degrees and sunny in SF.", tool_call_id="call_1"),
          AIMessage(content="The weather in SF is 75 degrees and sunny."),
      ]

      t.log_inputs({})
      t.log_outputs({"messages": result["messages"]})
      t.log_reference_outputs({"messages": reference_trajectory})

      trajectory_evaluator(
          outputs=result["messages"],
          reference_outputs=reference_trajectory
      )
```

  使用 pytest 运行评估：

```bash
  pytest test_trajectory.py --langsmith-output
```

创建 LangSmith 数据集并使用 `evaluate` 函数。数据集必须具有以下 schema：

  * **input**: `{"messages": [...]}` 用于调用 agent 的输入消息。
  * **output**: `{"messages": [...]}` agent 输出中预期的消息历史。对于 trajectory 评估，您可以选择只保留助手消息。

```python
  from langsmith import Client
  from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT

  client = Client()

  trajectory_evaluator = create_trajectory_llm_as_judge(
      model="openai:o3-mini",
      prompt=TRAJECTORY_ACCURACY_PROMPT,
  )

  def run_agent(inputs):
      return agent.invoke(inputs)["messages"]

  experiment_results = client.evaluate(
      run_agent,
      data="your_dataset_name",
      evaluators=[trajectory_evaluator]
  )
```

要了解有关评估 agent 的更多信息，请参阅 LangSmith 文档。