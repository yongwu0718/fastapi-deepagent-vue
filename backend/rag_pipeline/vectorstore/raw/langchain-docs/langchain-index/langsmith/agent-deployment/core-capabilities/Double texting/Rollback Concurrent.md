# 回滚并发

本指南假定您了解什么是双文本（double-texting），您可以在双文本概念指南中了解相关内容。

本指南介绍用于处理双文本的 `rollback` 选项，该选项会中断先前对 graph 的 run，并使用双文本启动一个新的 run。此选项与 `interrupt` 选项非常相似，但在这种情况下，第一个 run 会从数据库中被完全删除，无法重新启动。以下是使用 `rollback` 选项的快速示例。

## 设置
导入所需的包并实例化 client、assistant 和 thread。

```python
import asyncio

import httpx
from langchain_core.messages import convert_to_messages
from langgraph_sdk import get_client

client = get_client(url=<your_url>)
# Using the graph deployed with the name "agent"
assistant_id = "agent"
thread = await client.threads.create()
```
## 创建 runs

现在，让我们使用设置为 “rollback” 的多任务参数来运行一个 thread：

```python
# the first run will be rolled back
rolled_back_run = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "what's the weather in sf?"}]},
)
run = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "what's the weather in nyc?"}]},
    multitask_strategy="rollback",
)
# wait until the second run completes
await client.runs.join(thread["thread_id"], run["run_id"])
```
## 查看 run 结果

我们可以看到 thread 中仅有来自第二个 run 的数据：

```python
state = await client.threads.get_state(thread["thread_id"])

for m in convert_to_messages(state["values"]["messages"]):
    m.pretty_print()
```
输出（略，详见原文）。

验证原始的、被回滚的 run 已被删除：

```python
try:
    await client.runs.get(thread["thread_id"], rolled_back_run["run_id"])
except httpx.HTTPStatusError as _:
    print("Original run was correctly deleted")
```
输出：

```
Original run was correctly deleted
```