# 无状态运行

大多数情况下，在运行 Graph 时，您会向客户端提供 `thread_id`，以便通过 LangSmith Deployment 中实现的持久化状态来跟踪之前的 runs。但是，如果您不需要持久化这些 runs，则无需使用内置的持久化状态，可以创建无状态运行。

## 设置

首先，设置客户端：

```python
from langgraph_sdk import get_client

client = get_client(url=)
# 使用部署时名称为 "agent" 的 graph
assistant_id = "agent"
```

## 无状态流式传输

我们可以以几乎相同的方式流式传输无状态运行的结果，与带有状态属性的运行流式传输类似，但不是在 `thread_id` 参数中传递一个值，而是传递 `None`：

```python
input = {
    "messages": [
        {"role": "user", "content": "Hello! My name is Bagatur and I am 26 years old."}
    ]
}

async for chunk in client.runs.stream(
    # Don't pass in a thread_id and the stream will be stateless
    None,
    assistant_id,
    input=input,
    stream_mode="updates",
):
    if chunk.data and "run_id" not in chunk.data:
        print(chunk.data)
```
输出：

```
{'agent': {'messages': [{'content': "Hello Bagatur! It's nice to meet you. Thank you for introducing yourself and sharing your age. Is there anything specific you'd like to know or discuss? I'm here to help with any questions or topics you're interested in.", 'additional_kwargs': {}, 'response_metadata': {}, 'type': 'ai', 'name': None, 'id': 'run-489ec573-1645-4ce2-a3b8-91b391d50a71', 'example': False, 'tool_calls': [], 'invalid_tool_calls': [], 'usage_metadata': None}]}}
```

## 等待无状态结果

除了流式传输，您还可以使用 `.wait` 函数等待无状态结果，如下所示：

```python
stateless_run_result = await client.runs.wait(
    None,
    assistant_id,
    input=input,
)
print(stateless_run_result)
```
输出：

```
{
    'messages': [
        {
            'content': 'Hello! My name is Bagatur and I am 26 years old.',
            'additional_kwargs': {},
            'response_metadata': {},
            'type': 'human',
            'name': None,
            'id': '5e088543-62c2-43de-9d95-6086ad7f8b48',
            'example': False
        },
        {
            'content': 'Hello Bagatur! It's nice to meet you. Thank you for introducing yourself and sharing your age. Is there anything specific you'd like to know or discuss? I'm here to help with any questions or topics you'd like to explore.',
            'additional_kwargs': {},
            'response_metadata': {},
            'type': 'ai',
            'name': None,
            'id': 'run-d6361e8d-4d4c-45bd-ba47-39520257f773',
            'example': False,
            'tool_calls': [],
            'invalid_tool_calls': [],
            'usage_metadata': None
        }
    ]
}
```