# 如何取消运行

> 通过 API 取消单个运行或多个运行，并在 interrupt 和 rollback 操作之间进行选择。

本指南介绍如何通过 LangSmith Deployment API 取消代理的运行。您可以按 ID 取消单个运行，也可以按 thread 或状态取消多个运行。取消功能对于停止长时间运行或卡住的运行，或者在用户放弃请求时非常有用。

## 设置

创建客户端和 thread：

```python
from langgraph_sdk import get_client

client = get_client(url=)
assistant_id = "agent"
thread = await client.threads.create()
```

## 取消单个运行

以下示例创建一个运行，使用不同选项取消它，并打印运行以显示每种情况下的结果。您可以取消状态为 `pending` 或 `running` 的运行。尝试取消不处于 `pending` 或 `running` 状态的运行将导致错误。

### 使用 interrupt 取消（默认）

**interrupt** 停止执行该运行的工作进程，并将运行标记为 `interrupted`。不会删除任何内容：

- 运行记录保留（状态为 `interrupted`）。您可以获取它，检查输入/输出，并查看执行历史。
- 该运行的所有 checkpoints 仍然存储。thread 在最后完成步骤的状态被保留。
- 您可以稍后从 checkpoint 恢复（例如使用 time travel）或检查部分状态。

当您希望停止运行但保留它用于调试、审计或从 checkpoint 恢复时，请使用 **interrupt**。

```python
run = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "Long task"}]},
)
await client.runs.cancel(thread["thread_id"], run["run_id"])

run_after = await client.runs.get(thread["thread_id"], run["run_id"], wait=True)
print(run_after["status"])   # "interrupted"
```
### 使用 rollback 取消

**rollback** 停止运行，然后将其及其 checkpoints 从存储中删除：

- 运行记录被删除。该运行不再出现在该 thread 的运行列表或历史中。
- 该运行创建的所有 checkpoints 被删除。thread 的状态恢复到运行开始之前的状态（就像该运行从未执行过一样）。
- rollback 后您无法恢复或检查该运行。

当您希望完全丢弃一个运行及其影响时（例如，在用户放弃请求后，您不需要保留部分工作），请使用 **rollback**。

```python
run = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "Long task"}]},
)
await client.runs.cancel(thread["thread_id"], run["run_id"], action="rollback", wait=True)

# 因为运行已被删除，所以抛出错误
try:
    await client.runs.get(thread["thread_id"], run["run_id"])
except Exception:
    print("Run was correctly deleted")
```
### 使用 wait 取消

默认情况下，取消请求在请求取消后返回，并且运行被异步取消。`wait=True` 使取消请求阻塞，直到运行被完全取消。当您想了解运行被取消后的最终状态（例如，创建了哪些 checkpoints，最终输出是什么）时，这很有用。

```python
run = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "Long task"}]},
)
# 异步取消运行
await client.runs.cancel(thread["thread_id"], run["run_id"])
# 获取运行状态
run_after = await client.runs.get(thread["thread_id"], run["run_id"])
print(run_after["status"])  # "pending" 或 "running"

# 等待运行被正确取消
await client.runs.join(thread["thread_id"], run["run_id"])
run_after = await client.runs.get(thread["thread_id"], run["run_id"])
print(run_after["status"])  # "interrupted"
```

## 取消多个运行

使用批量取消端点在一个请求中取消多个运行。支持 interrupt 和 rollback 操作。

### 按 thread ID 和 run IDs 取消

通过传入 run IDs 来取消特定的运行。

```python
run1 = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "First request"}]},
)
run2 = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "Second request"}]},
    multitask_strategy="enqueue",
)

await client.runs.cancel_many(
    thread_id=thread["thread_id"],
    run_ids=[run1["run_id"], run2["run_id"]]
)

# 等待运行被取消
await client.runs.join(thread["thread_id"], run2["run_id"])
runs_after = await client.runs.list(thread["thread_id"])
for run in runs_after:
    if run["run_id"] in (run1["run_id"], run2["run_id"]):
        print(run["run_id"], run["status"])  # "interrupted"
```
### 按状态取消

取消部署中所有 threads 上匹配某个状态的所有运行。有效的状态选项为 `pending`、`running` 或 `all`。

```python
run1 = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "First request"}]},
)
thread2 = await client.threads.create()
run2 = await client.runs.create(
    thread2["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "Second request"}]},
)

await client.runs.cancel_many(
    status="running",
)

# 等待运行被取消
await client.runs.join(thread2["thread_id"], run2["run_id"])
run_after = await client.runs.get(thread["thread_id"], run1["run_id"])
print(run_after["status"])  # 正在运行的 run 现在为 "interrupted"
run_after2 = await client.runs.get(thread2["thread_id"], run2["run_id"])
print(run_after2["status"])  # 所有 threads 上的 runs 都被取消
```
## 断开连接时取消

在启动带有流式传输的运行或等待运行完成时，您可以设置 `on_disconnect="cancel"`，以便在客户端断开连接时取消运行。这可以避免在用户关闭应用程序或失去连接时留下正在进行的运行。

```python
# 使用 runs.wait：如果客户端断开连接，运行将被取消
result = await client.runs.wait(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "Long task"}]},
    on_disconnect="cancel",
)

# 使用 runs.stream：如果客户端断开连接，运行将被取消
async for chunk in client.runs.stream(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "Long task"}]},
    on_disconnect="cancel",
):
    print(chunk)

# 使用 runs.join：等待现有运行；如果客户端断开连接则取消
run = await client.runs.create(
    thread["thread_id"],
    assistant_id,
    input={"messages": [{"role": "user", "content": "Long task"}]},
)
await client.runs.join(
    thread["thread_id"],
    run["run_id"],
    on_disconnect="cancel",
)

# 使用 runs.join_stream：加入现有运行并流式传输；如果客户端断开连接则取消
async for chunk in client.runs.join_stream(
    thread["thread_id"],
    run["run_id"],
    on_disconnect="cancel",
):
    print(chunk)
```

## 常见场景

- **Human-in-the-loop 和 interrupts**：代理可以在 interrupts 处暂停以等待人工输入。取消运行会停止执行；这与 interrupt 不同，interrupt 是运行暂停并可以使用新输入恢复。
- **Time travel**：使用 `interrupt` 操作取消后，运行和 checkpoints 仍然可用。您可以从 checkpoint 恢复（time travel）以重放或分支执行。
- **Double-texting**：当用户在运行进行中发送新输入时，multitask strategy（enqueue、reject、interrupt、rollback）决定是中断还是回滚现有运行，以及如何处理新运行。要明确地从您的应用程序取消运行，请使用本页描述的 cancel API。
- **Studio**：在 Studio 中，使用运行 UI 中的 **Cancel** 按钮取消当前运行。