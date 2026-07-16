# 使用 cron jobs

在很多情况下，按计划运行 assistant 非常有用。

例如，假设您正在构建一个每天运行并发送当日新闻摘要邮件的 assistant。您可以使用 cron job 每天在晚上 8:00 运行该 assistant。

LangSmith Deployment 支持 cron jobs，它们按用户定义的计划运行。用户指定计划、assistant 和一些输入。之后，在指定的计划时间，服务器将：

* 使用指定的 assistant 创建一个新的 thread
* 将指定的输入发送到该 thread

请注意，每次都会向 thread 发送相同的输入。

LangSmith Deployment API 提供了多个用于创建和管理 cron jobs 的端点。更多详情请参阅 API 参考。

有时您不希望基于用户交互来运行 Graph，而是希望按计划调度 Graph 运行——例如，您希望 Graph 每周为团队编写并发送待办事项邮件。LangSmith Deployment 允许您通过使用 `Crons` 客户端来实现这一点，而无需自己编写脚本。要调度一个 Graph 任务，您需要传入一个 cron 表达式，告知客户端您希望何时运行 Graph。`Cron` 任务在后台运行，不会干扰 Graph 的正常调用。

所有 cron 计划均以 **UTC** 时间解释。在指定计划时，请确保将您期望的执行时间转换为 UTC。

## 设置

首先，设置 SDK 客户端、assistant 和 thread：

```python
from langgraph_sdk import get_client

client = get_client(url=)
# 使用部署时名称为 "agent" 的 graph
assistant_id = "agent"
# 创建 thread
thread = await client.threads.create()
print(thread)
```

输出：

```python
{
    'thread_id': '9dde5490-2b67-47c8-aa14-4bfec88af217',
    'created_at': '2024-08-30T23:07:38.242730+00:00',
    'updated_at': '2024-08-30T23:07:38.242730+00:00',
    'metadata': {},
    'status': 'idle',
    'config': {},
    'values': None
}
```

## 在 thread 上创建 cron job

要创建与特定 thread 关联的 cron job，可以这样写：

```python
# 计划每天在 UTC 时间 15:27（下午 3:27）运行任务
cron_job = await client.crons.create_for_thread(
    thread["thread_id"],
    assistant_id,
    schedule="27 15 * * *",
    input={"messages": [{"role": "user", "content": "What time is it?"}]},
)
```

请注意，删除不再有用的 `Cron` 任务**非常**重要。否则您可能会产生不必要的 LLM API 费用！您可以使用以下代码删除 `Cron` 任务：

```python
await client.crons.delete(cron_job["cron_id"])
```
## 无状态 cron job

您还可以使用以下代码创建无状态 cron jobs。无状态 cron jobs 每次执行都会创建一个新的 thread：

```python
# 计划每天在 UTC 时间 15:27（下午 3:27）运行任务
cron_job_stateless = await client.crons.create(
    assistant_id,
    schedule="27 15 * * *",
    input={"messages": [{"role": "user", "content": "What time is it?"}]},
)
```

再次提醒，完成后记得删除您的任务！

```python
await client.crons.delete(cron_job_stateless["cron_id"])
```
## 无状态 cron 的 thread 清理

此功能需要 LangGraph API 版本 **0.5.18** 或更高版本，以及 Python SDK **0.3.2** 或更高版本，或 JavaScript SDK **1.4.0** 或更高版本。

每次触发无状态 cron 时，都会创建一个新的 thread。使用 `on_run_completed` 参数控制运行完成后如何处理该 thread：

* **`"delete"`**（默认）：运行完成后自动删除 thread。
* **`"keep"`**：保留 thread 以便后续检索。您负责清理这些 threads。请参阅如何向应用添加 TTL 以获取推荐的方法。

### 示例：保留 threads 以便后续检索

```python
# 创建一个在执行后保留 threads 的无状态 cron。
# 在 langgraph.json 中配置 checkpointer.ttl 以自动删除旧 threads。
# 参见：https://docs.langchain.com/langsmith/configure-ttl
cron_job = await client.crons.create(
    assistant_id,
    schedule="27 15 * * *",
    input={"messages": [{"role": "user", "content": "Daily report"}]},
    on_run_completed="keep"
)

# 稍后您可以检索 runs 及其结果
runs = await client.runs.search(
    metadata={"cron_id": cron_job["cron_id"]}
)
```