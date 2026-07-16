# 如何为 Agent Server 运行收集用户反馈

本教程介绍如何为 Agent Server 运行收集用户反馈，并将其自动关联到 LangSmith 中的 traces。在创建 run 时，在请求体的 `feedback_keys` 字段中包含这些键。响应将为每个键返回一个预签名 URL，您的客户端可以使用该 URL 为 Agent Server 运行收集用户反馈。

LangSmith 使用反馈来持续改进代理的实现。要了解有关 LangSmith 中反馈如何工作的更多信息，请参阅 LangSmith feedback。

## 工作原理

1. 创建一个 run，并在请求体中包含 `feedback_keys`。例如，调用 `POST /threads/{thread_id}/runs/stream` 时，将请求体中的 `feedback_keys` 设置为：
```
["user_liked", "user_disliked"]
```
2. 响应中的 `feedback` 对象包含每个键的预签名 URL。例如，`feedback` 对象为：
```
{
    "user_liked": "https://api.smith.langchain.com/api/v1/feedback/tokens/ef19fedf-dcac-4cbb-a59c-00661efd6425",
    "user_disliked": "https://api.smith.langchain.com/api/v1/feedback/tokens/e952734e-c0a0-417b-a04d-fc2209691ed5"
}
```
3. 请求返回的 URL（例如 `POST /api/v1/feedback/tokens/{token_id}`），以将反馈键与 Agent Server 运行生成的 trace 关联。更多详情请参阅 LangSmith API 参考。
4. LangSmith 使用选定的反馈键（例如 `user_liked` 或 `user_disliked`）将提交的反馈与运行关联起来。

## 使用 `feedback_keys` 调用流式运行 API

创建一个 run 并从响应中解析 `feedback` 对象。

```python
from langgraph_sdk import get_client

client = get_client(url="", api_key="")

thread = await client.threads.create()
thread_id = thread["thread_id"]

feedback_urls = {}

async for event in client.runs.stream(
    thread_id,
    "agent",
    input={
        "messages": [
            {"role": "user", "content": "Tell me a joke about databases."}
        ]
    },
    stream_mode="updates",
    feedback_keys=["user_liked", "user_disliked"],
):
    if event.event == "feedback":
        # Example: {"user_liked": ".../feedback/tokens/", "user_disliked": "..."}
        feedback_urls = event.data
        print("Feedback URLs:", feedback_urls)
    elif event.event == "updates":
        print(event.data)
```
## 处理流式传输的 `feedback` 事件

流会发出类似下面的 `feedback` 事件：

```text
event: feedback
data: {"user_liked":"https://api.smith.langchain.com/api/v1/feedback/tokens/ef19fedf-dcac-4cbb-a59c-00661efd6425", "user_disliked": "https://api.smith.langchain.com/api/v1/feedback/tokens/e952734e-c0a0-417b-a04d-fc2209691ed5"}
```

`data` 中的每个键都与您传入 `feedback_keys` 的值之一匹配。每个值都是一个生成的 URL，您的客户端可以调用它来为该运行提交反馈。

## 使用生成的 URL 提交反馈

当用户选择某个反馈选项时，向对应的 URL 发送 `POST` 请求。也支持 `GET`。更多详情请参阅 LangSmith API 参考。

例如，如果用户点击了“踩”按钮，则调用 `user_disliked` URL：

```bash
curl --request POST \
  --url "https://api.smith.langchain.com/api/v1/feedback/tokens/e952734e-c0a0-417b-a04d-fc2209691ed5" \
  --header "Content-Type: application/json" \
  --data '{
    "score": 1,
    "value": 0,
    "comment": "I didn't like this joke because it didn't make me laugh.",
    "correction": {},
    "metadata": {}
  }'
```

`GET` 方法不支持 `metadata`。

```bash
curl --request GET \
  --url "https://api.smith.langchain.com/api/v1/feedback/tokens/e952734e-c0a0-417b-a04d-fc2209691ed5?score=1&value=0&comment=I%20didn%27t%20like%20this%20joke%20because%20it%20didn%27t%20make%20me%20laugh.&correction=%7B%7D"
```

此请求成功后，LangSmith 会使用键 `user_disliked` 在 trace 上记录反馈。

## 优化反馈数据模型

`user_liked` 和 `user_disliked` 键也可以建模为单个键（例如 `user_score`）。

例如：

* 使用 `key="user_score"` 配合 `score=1` 表示 `user_liked`
* 使用 `key="user_score"` 配合 `score=-1` 表示 `user_disliked`

这可以简化分析，因为所有用户偏好信号都归入一个反馈键下。

反馈数据模型是灵活的，应根据您的用例进行设计。例如，某些应用可能更喜欢分开的布尔型键（`user_liked`、`user_disliked`），而另一些应用可能更喜欢单个数值分数（`user_score`）或具有多个反馈键的更丰富的评分标准。

## 在客户端 UI 中生产化

生产化的解决方案将通过前端公开生成的反馈 URL，而不是手动调用它们。

高级实现示例：

1. 从后端或前端创建 run。
2. 捕获 `feedback` 对象并存储返回的 URL。
3. 渲染反馈控件，例如“赞/踩”按钮和反馈表单。
4. 在提交反馈时，根据用户的反馈意图向反馈 URL 发送 `POST` 或 `GET` 请求。
5. 可选地，在提交后禁用反馈控件并向用户显示确认信息。