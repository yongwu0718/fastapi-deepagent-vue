# Human-in-the-loop

Human-in-the-loop (HITL) middleware 允许您在 agent 的工具调用中添加人工审核环节。
当模型提出一个可能需要审查的操作时——例如，写入文件或执行 SQL——中间件可以暂停执行并等待决策。

它的工作原理是根据可配置的策略检查每个工具调用。如果需要干预，中间件会发出一个中断 (interrupt) 来暂停执行。图的状态通过 LangGraph 的持久化层保存，因此执行可以安全地暂停，并在之后恢复。

然后，由人决定下一步做什么：可以原样批准 (`approve`) 操作，在执行前进行修改 (`edit`)，带反馈地拒绝 (`reject`)，或者对于“询问用户”类型的工具直接响应 (`respond`)。

## 中断决策类型

中间件定义了四种内置的人工响应中断的方式：

| 决策类型        | 描述                                                                  | 示例用例                                |
| --------------- | --------------------------------------------------------------------- | --------------------------------------- |
| ✅ `approve`    | 操作被原样批准并执行，不做更改。                                      | 按原样发送电子邮件草稿                  |
| ✏️ `edit`       | 工具调用经过修改后执行。                                              | 在发送电子邮件前更改收件人              |
| ❌ `reject`     | 工具调用被拒绝，并在对话中添加解释说明。                              | 拒绝电子邮件草稿，并解释如何重写        |
| 💬 `respond`    | 跳过工具执行；人工的消息直接成为工具结果。                            | 用直接回复来回答“ask_user”提示          |

每个工具可用的决策类型取决于您在 `interrupt_on` 中配置的策略。
当多个工具调用同时被暂停时，每个操作都需要单独的决策。
决策必须按照中断请求中操作出现的顺序提供。

在**编辑**工具参数时，请保守地进行更改。对原始参数进行重大修改可能会导致模型重新评估其方法，并可能多次执行工具或采取意外操作。

## 配置中断

要使用 HITL，请在创建 agent 时将中间件添加到 agent 的 `middleware` 列表中。

您可以使用工具操作到允许的决策类型的映射来配置它。当工具调用与映射中的操作匹配时，中间件将中断执行。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware 
from langgraph.checkpoint.memory import InMemorySaver 

agent = create_agent(
    model="gpt-5.4",
    tools=[write_file, execute_sql, read_data],
    middleware=[
        HumanInTheLoopMiddleware( 
            interrupt_on={
                "write_file": True,  # 允许所有决策 (approve, edit, reject, respond)
                "execute_sql": {"allowed_decisions": ["approve", "reject"]},  # 不允许编辑
                "read_data": False, # 安全操作，无需批准
            },
            # 中断消息的前缀 - 将与工具名称和参数组合成完整消息
            # 例如，"Tool execution pending approval: execute_sql with query='DELETE FROM...'"
            # 单个工具可以通过在其中断配置中指定 "description" 来覆盖此前缀
            description_prefix="Tool execution pending approval",
        ),
    ],
    # Human-in-the-loop 需要 checkpointing 来处理中断。
    # 在生产环境中，请使用持久化的 checkpointer，如 AsyncPostgresSaver。
    checkpointer=InMemorySaver(),  
)
```

您必须配置一个 checkpointer 来持久化跨中断的图状态。
在生产环境中，使用持久化的 checkpointer，例如 `AsyncPostgresSaver`。对于测试或原型开发，可以使用 `InMemorySaver`。

在调用 agent 时，传递一个包含 **thread ID** 的 `config`，以将执行与对话线程关联起来。
有关详细信息，请参阅 LangGraph interrupts 文档。

工具名称到批准配置的映射。值可以是 `True`（使用默认配置中断）、`False`（自动批准）或 `InterruptOnConfig` 对象。

操作请求描述的前缀

**`InterruptOnConfig` 选项：**

允许的决策列表：`'approve'`, `'edit'`, `'reject'`, 或 `'respond'`

用于自定义描述的静态字符串或可调用函数

## 响应中断

当您调用 agent 时，它会一直运行直到完成或引发中断。当工具调用与您在 `interrupt_on` 中配置的策略匹配时，会触发中断。使用 `version="v2"` 时，结果是一个 `GraphOutput`，带有一个 `interrupts` 属性，其中包含需要审查的操作。然后，您可以将这些操作呈现给审核者，并在提供决策后恢复执行。

```python
from langgraph.types import Command

# Human-in-the-loop 利用 LangGraph 的持久化层。
# 您必须提供一个 thread ID 来将执行与对话线程关联起来，
# 以便对话可以被暂停和恢复（这是人工审核所必需的）。
config = {"configurable": {"thread_id": "some_id"}} 
# 运行图直到触发中断。
result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Delete old records from the database",
            }
        ]
    },
    config=config, 
    version="v2", 
)

# result 是一个带有 .value 和 .interrupts 的 GraphOutput
print(result.interrupts)  
# > (
# >    Interrupt(
# >       value={
# >          'action_requests': [
# >             {
# >                'name': 'execute_sql',
# >                'arguments': {'query': 'DELETE FROM records WHERE created_at < NOW() - INTERVAL \'30 days\';'},
# >                'description': 'Tool execution pending approval\n\nTool: execute_sql\nArgs: {...}'
# >             }
# >          ],
# >          'review_configs': [
# >             {
# >                'action_name': 'execute_sql',
# >                'allowed_decisions': ['approve', 'reject']
# >             }
# >          ]
# >       }
# >    ),
# > )

# 使用批准决策恢复
agent.invoke(
    Command( 
        resume={"decisions": [{"type": "approve"}]}  # 或 "reject" [!code highlight]
    ), 
    config=config, # 使用相同的 thread ID 恢复暂停的对话
    version="v2",
)
```

### 决策类型

使用 `approve` 原样批准工具调用并执行，不做更改。

```python
agent.invoke(
	Command(
		# 决策以列表形式提供，每个审查中的操作对应一个决策。
		# 决策的顺序必须与中断请求中操作的顺序匹配。
		resume={
			"decisions": [
				{
					"type": "approve",
				}
			]
		}
	),
	config=config,  # 使用相同的 thread ID 恢复暂停的对话
	version="v2",
)
```

使用 `edit` 在执行前修改工具调用。
    提供包含新工具名称和参数的编辑后操作。

```python
agent.invoke(
	Command(
		# 决策以列表形式提供，每个审查中的操作对应一个决策。
		# 决策的顺序必须与中断请求中操作的顺序匹配。
		resume={
			"decisions": [
				{
					"type": "edit",
					# 包含工具名称和参数的编辑后操作
					"edited_action": {
						# 要调用的工具名称。
						# 通常与原始操作相同。
						"name": "new_tool_name",
						# 传递给工具的参数。
						"args": {"key1": "new_value", "key2": "original_value"},
					}
				}
			]
		}
	),
	config=config,  # 使用相同的 thread ID 恢复暂停的对话
	version="v2",
)
```

在**编辑**工具参数时，请保守地进行更改。对原始参数进行重大修改可能会导致模型重新评估其方法，并可能多次执行工具或采取意外操作。

使用 `reject` 拒绝工具调用，并提供反馈而不是执行。

```python
agent.invoke(
	Command(
		# 决策以列表形式提供，每个审查中的操作对应一个决策。
		# 决策的顺序必须与中断请求中操作的顺序匹配。
		resume={
			"decisions": [
				{
					"type": "reject",
					# 关于操作被拒绝原因的解释
					"message": "No, this is wrong because ..., instead do this ...",
				}
			]
		}
	),
	config=config,  # 使用相同的 thread ID 恢复暂停的对话
	version="v2",
)
```

`message` 将作为反馈添加到对话中，以帮助 agent 理解操作被拒绝的原因以及应该采取什么替代操作。

    ***

    ### 多个决策

    当多个操作正在审查中时，请按照它们在中断中出现的顺序为每个操作提供一个决策：

```python
{
	"decisions": [
		{"type": "approve"},
		{
			"type": "edit",
			"edited_action": {
				"name": "tool_name",
				"args": {"param": "new_value"}
			}
		},
		{
			"type": "reject",
			"message": "This action is not allowed"
		}
	]
}
```

使用 `respond` 处理“询问用户”类型的工具，这些工具的实际实现就是人工的回复。`message` 内容直接作为工具结果返回；工具本身不执行。

```python
agent.invoke(
	Command(
		# 决策以列表形式提供，每个审查中的操作对应一个决策。
		# 决策的顺序必须与中断请求中操作的顺序匹配。
		resume={
			"decisions": [
				{
					"type": "respond",
					# 人工的回复，直接作为工具结果返回
					"message": "Blue.",
				}
			]
		}
	),
	config=config,  # 使用相同的 thread ID 恢复暂停的对话
	version="v2",
)
```

`message` 作为成功的 `ToolMessage` 返回给 agent。当工具故意设计为人工输入的占位符时——例如，一个提示澄清问题的 `ask_user` 工具——请使用 `respond`。

## 使用 Human-in-the-loop 进行流式传输

您可以使用 `stream()` 而不是 `invoke()` 来在 agent 运行和处理中断时获取实时更新。使用 `stream_mode=['updates', 'messages']` 和 `version="v2"` 以统一的 v2 格式流式传输 agent 进度和 LLM tokens。

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "some_id"}}

# 流式传输 agent 进度和 LLM tokens，直到中断
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Delete old records from the database"}]},
    config=config,
    stream_mode=["updates", "messages"],  
    version="v2",  
):
    if chunk["type"] == "messages":  
        # LLM token
        token, metadata = chunk["data"]  
        if token.content:
            print(token.content, end="", flush=True)
    elif chunk["type"] == "updates":  
        # 检查中断
        if "__interrupt__" in chunk["data"]:  
            print(f"\n\nInterrupt: {chunk['data']['__interrupt__']}")

# 在人工决策后使用流式传输恢复
for chunk in agent.stream(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config,
    stream_mode=["updates", "messages"],
    version="v2",  
):
    if chunk["type"] == "messages":  
        token, metadata = chunk["data"]  
        if token.content:
            print(token.content, end="", flush=True)
```

有关流模式的更多详细信息，请参阅 Streaming 指南。

## 执行生命周期

中间件定义了一个 `after_model` hook，它在模型生成响应之后、任何工具调用执行之前运行：

1.  agent 调用模型生成响应。
2.  中间件检查响应中的工具调用。
3.  如果有任何调用需要人工输入，中间件会构建一个带有 `action_requests` 和 `review_configs` 的 `HITLRequest`，并调用 interrupt。
4.  agent 等待人工决策。
5.  根据 `HITLResponse` 决策，中间件执行批准或编辑后的调用，为被拒绝的调用合成 ToolMessage，对于 `respond` 决策直接将人工回复作为 ToolMessage 返回，并恢复执行。

## 自定义 HITL 逻辑

对于更专业化的工作流程，您可以使用 interrupt 原语和 middleware 抽象直接构建自定义 HITL 逻辑。

请回顾上面的执行生命周期，以了解如何将中断集成到 agent 的操作中。