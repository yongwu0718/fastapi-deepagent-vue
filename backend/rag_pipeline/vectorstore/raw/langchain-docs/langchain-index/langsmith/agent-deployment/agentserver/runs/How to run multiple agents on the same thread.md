# 如何在同一 thread 上运行多个代理

在 LangSmith Deployment 中，thread 不会显式关联到特定的代理。这意味着您可以在同一个 thread 上运行多个代理，从而允许不同的代理从初始代理的进度继续执行。

在本例中，我们将创建两个代理，然后在同一个 thread 上分别调用它们。您将看到第二个代理会使用 thread 中由第一个代理生成的 checkpoint 中的信息作为上下文来响应。

## 设置

```python
from langgraph_sdk import get_client

client = get_client(url=)

openai_assistant = await client.assistants.create(
    graph_id="agent", config={"configurable": {"model_name": "openai"}}
)

# There should always be a default assistant with no configuration
assistants = await client.assistants.search()
default_assistant = [a for a in assistants if not a["config"]][0]
```

可以看到这些代理是不同的：

```python
print(openai_assistant)
```
输出：

```
{
"assistant_id": "db87f39d-b2b1-4da8-ac65-cf81beb3c766",
"graph_id": "agent",
"created_at": "2024-08-30T21:18:51.850581+00:00",
"updated_at": "2024-08-30T21:18:51.850581+00:00",
"config": {
"configurable": {
"model_name": "openai"
}
},
"metadata": {}
}
```

```python
print(default_assistant)
```
输出：

```
{
    "assistant_id": "fe096781-5601-53d2-b2f6-0d3403f7e9ca",
    "graph_id": "agent",
    "created_at": "2024-08-08T22:45:24.562906+00:00",
    "updated_at": "2024-08-08T22:45:24.562906+00:00",
    "config": {},
    "metadata": {
    "created_by": "system"
    }
}
```

## 在 thread 上运行 assistants

### 运行 OpenAI assistant

我们可以先在 thread 上运行 OpenAI assistant。

```python
thread = await client.threads.create()
input = {"messages": [{"role": "user", "content": "who made you?"}]}
async for event in client.runs.stream(
    thread["thread_id"],
    openai_assistant["assistant_id"],
    input=input,
    stream_mode="updates",
):
    print(f"Receiving event of type: {event.event}")
    print(event.data)
    print("\n\n")
```
输出：

```
Receiving event of type: metadata
{'run_id': '1ef671c5-fb83-6e70-b698-44dba2d9213e'}

Receiving event of type: updates
{'agent': {'messages': [{'content': 'I was created by OpenAI, a research organization focused on developing and advancing artificial intelligence technology.', 'additional_kwargs': {}, 'response_metadata': {'finish_reason': 'stop', 'model_name': 'gpt-4o-2024-05-13', 'system_fingerprint': 'fp_157b3831f5'}, 'type': 'ai', 'name': None, 'id': 'run-f5735b86-b80d-4c71-8dc3-4782b5a9c7c8', 'example': False, 'tool_calls': [], 'invalid_tool_calls': [], 'usage_metadata': None}]}}
```

### 运行 default assistant

现在，我们在 default assistant 上运行它，可以看到第二个 assistant 能够感知到最初的问题，并且可以回答“那你呢？”：

```python
input = {"messages": [{"role": "user", "content": "and you?"}]}
async for event in client.runs.stream(
    thread["thread_id"],
    default_assistant["assistant_id"],
    input=input,
    stream_mode="updates",
):
    print(f"Receiving event of type: {event.event}")
    print(event.data)
    print("\n\n")
```

输出：

```
Receiving event of type: metadata
{'run_id': '1ef6722d-80b3-6fbb-9324-253796b1cd13'}

Receiving event of type: updates
{'agent': {'messages': [{'content': [{'text': 'I am an artificial intelligence created by Anthropic, not by OpenAI. I should not have stated that OpenAI created me, as that is incorrect. Anthropic is the company that developed and trained me using advanced language models and AI technology. I will be more careful about providing accurate information regarding my origins in the future.', 'type': 'text', 'index': 0}], 'additional_kwargs': {}, 'response_metadata': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'type': 'ai', 'name': None, 'id': 'run-ebaacf62-9dd9-4165-9535-db432e4793ec', 'example': False, 'tool_calls': [], 'invalid_tool_calls': [], 'usage_metadata': {'input_tokens': 302, 'output_tokens': 72, 'total_tokens': 374}}]}}
```