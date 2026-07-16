# 使用 webhook

Webhook 支持从您的 LangSmith 应用程序到外部服务的事件驱动通信。例如，当对 LangSmith 的 API 调用完成运行后，您可能希望向另一个服务发出更新。

许多 LangSmith 端点接受 `webhook` 参数。如果某个可以接受 POST 请求的端点指定了该参数，LangSmith 将在 run 完成时发送一个请求。

在使用 LangSmith 时，您可能希望使用 webhook 在 API 调用完成后接收更新。Webhook 对于在 run 处理完成后触发您服务中的操作非常有用。要实现这一点，您需要暴露一个可以接受 `POST` 请求的端点，并将此端点作为 `webhook` 参数传递到您的 API 请求中。

目前，SDK 没有提供定义 webhook 端点的内置支持，但您可以手动使用 API 请求来指定它们。

## 支持的端点

以下 API 端点接受 `webhook` 参数：

| 操作                     | HTTP 方法   | 端点                                  |
| ------------------------ | ----------- | ------------------------------------- |
| Create Run               | `POST`      | `/thread/{thread_id}/runs`            |
| Create Thread Cron       | `POST`      | `/thread/{thread_id}/runs/crons`      |
| Stream Run               | `POST`      | `/thread/{thread_id}/runs/stream`     |
| Wait Run                 | `POST`      | `/thread/{thread_id}/runs/wait`       |
| Create Cron              | `POST`      | `/runs/crons`                         |
| Stream Run Stateless     | `POST`      | `/runs/stream`                        |
| Wait Run Stateless       | `POST`      | `/runs/wait`                          |

在本指南中，我们将展示如何在流式传输 run 后触发 webhook。

## 设置 assistant 和 thread

在进行 API 调用之前，先设置您的 assistant 和 thread。

```python
from langgraph_sdk import get_client

client = get_client(url=<your_url>)
assistant_id = "agent"
thread = await client.threads.create()
print(thread)
```

示例响应：

```json
{
  "thread_id": "9dde5490-2b67-47c8-aa14-4bfec88af217",
  "created_at": "2024-08-30T23:07:38.242730+00:00",
  "updated_at": "2024-08-30T23:07:38.242730+00:00",
  "metadata": {},
  "status": "idle",
  "config": {},
  "values": null
}
```

## 在 graph run 中使用 webhook

要使用 webhook，请在 API 请求中指定 `webhook` 参数。当 run 完成时，LangSmith 会向指定的 webhook URL 发送一个 `POST` 请求。

例如，如果您的服务器在 `https://my-server.app/my-webhook-endpoint` 监听 webhook 事件，请在您的请求中包含该 URL：

```python
input = { "messages": [{ "role": "user", "content": "Hello!" }] }

async for chunk in client.runs.stream(
    thread_id=thread["thread_id"],
    assistant_id=assistant_id,
    input=input,
    stream_mode="events",
    webhook="https://my-server.app/my-webhook-endpoint"
):
    pass
```

## Webhook 载荷

LangSmith 以 Run 的格式发送 webhook 通知。请求载荷包括 `kwargs` 字段中的 run 输入、配置和其他元数据。除了标准的 run 字段外，webhook 载荷还包含 `values`、`webhook_sent_at` 和 `error` 字段。

完整的 webhook 载荷包含以下字段：

| 字段                 | 类型                     | 描述                                     |
| -------------------- | ------------------------ | -------------------------------------- |
| `run_id`             | `string` (UUID)          | run 的唯一标识符。                    |
| `thread_id`          | `string` (UUID)          | run 所属 thread 的标识符。                  |
| `assistant_id`       | `string`                 | 执行该 run 的 assistant 的标识符。                   |
| `status`             | `string`                 | run 的最终状态（例如 `"success"`、`"error"`）。      |
| `created_at`         | `string` (datetime)      | run 创建时的时间戳。                              |
| `updated_at`         | `string` (datetime)      | run 最后更新时的时间戳。                             |
| `run_started_at`     | `string` (datetime)      | run 开始执行时的时间戳。                     |
| `run_ended_at`       | `string` (datetime)      | run 结束时的时间戳。如果 run 尚未结束，则省略该字段。     |
| `webhook_sent_at`    | `string` (datetime)      | webhook 请求发送时的时间戳。                |
| `metadata`           | `JSON object`            | 与 run 关联的自定义元数据。                  |
| `kwargs`             | `JSON object`            | run 输入、配置及其他调用参数。              |
| `values`             | `JSON object`            | 线程最新 checkpoint 中的状态值。仅对有状态的 run 存在。   |
| `multitask_strategy` | `string`                 | 用于该 run 的多任务策略。              |
| `error`              | `JSON object \| null`    | 仅在 run 失败时存在。包含 `error`（错误类型）和 `message`（详情）字段。 |

示例载荷：

```json
{
  "run_id": "1ef6a5b8-4457-6db0-8b15-cffd3797fa04",
  "thread_id": "9dde5490-2b67-47c8-aa14-4bfec88af217",
  "assistant_id": "agent",
  "status": "success",
  "created_at": "2024-08-30T23:07:38.242730+00:00",
  "updated_at": "2024-08-30T23:07:40.120000+00:00",
  "run_started_at": "2024-08-30T23:07:38.300000+00:00",
  "run_ended_at": "2024-08-30T23:07:40.100000+00:00",
  "webhook_sent_at": "2024-08-30T23:07:40.150000+00:00",
  "metadata": {},
  "kwargs": {
    "input": {
      "messages": [{"role": "user", "content": "Hello!"}]
    }
  },
  "values": {
    "messages": [
      {"role": "user", "content": "Hello!"},
      {"role": "assistant", "content": "Hi there! How can I help you today?"}
    ]
  },
  "multitask_strategy": "reject",
  "error": null
}
```

当 run 失败时，`error` 字段包含失败的详细信息：

```json
{
  "error": {
    "error": "TimeoutError",
    "message": "Run exceeded maximum execution time"
  }
}
```

## 保护 webhook

为了确保只有授权的请求访问您的 webhook 端点，可以考虑添加一个安全 token 作为查询参数：

```
https://my-server.app/my-webhook-endpoint?token=YOUR_SECRET_TOKEN
```

您的服务器应在处理请求之前提取并验证此 token。

## 向 webhook 请求添加 headers

需要 `langgraph-api>=0.5.36`。

您可以配置静态 headers，将其包含在所有出站的 webhook 请求中。这对于认证、路由或向 webhook 端点传递元数据非常有用。

在 `langgraph.json` 文件中添加 `webhooks.headers` 配置：

```json
{
  "webhooks": {
    "headers": {
      "X-Custom-Header": "my-value",
      "X-Environment": "production"
    }
  }
}
```

### 在 headers 中使用环境变量

要包含 secrets 或环境特定的值而不将其检入配置文件，请使用 `${{ env.VAR }}` 模板语法：

```json
{
  "webhooks": {
    "headers": {
      "Authorization": "Bearer ${{ env.LG_WEBHOOK_TOKEN }}"
    }
  }
}
```

出于安全考虑，默认情况下只能引用以 `LG_WEBHOOK_` 开头的环境变量。这可以防止意外泄露不相关的环境变量。您可以使用 `env_prefix` 自定义此前缀：

```json
{
  "webhooks": {
    "env_prefix": "MY_APP_",
    "headers": {
      "Authorization": "Bearer ${{ env.MY_APP_SECRET }}"
    }
  }
}
```

缺少必需的环境变量将阻止服务器启动，确保您不会使用不完整的配置进行部署。

## 限制 webhook 目标

需要 `langgraph-api>=0.5.36`。

出于安全或合规目的，您可以使用 `webhooks.url` 配置限制哪些 URL 是有效的 webhook 目标：

```json
{
  "webhooks": {
    "url": {
      "allowed_domains": ["*.mycompany.com", "api.trusted-service.com"],
      "require_https": true
    }
  }
}
```

可用选项：

| 选项                | 描述                                                               |
| ------------------- | ------------------------------------------------------------------ |
| `allowed_domains`   | 主机名白名单。支持子域通配符（例如 `*.mycompany.com`）。           |
| `require_https`     | 当为 `true` 时，拒绝 `http://` 的 URL。                           |
| `allowed_ports`     | 显式端口白名单。默认为 443（https）和 80（http）。                 |
| `disable_loopback`  | 当为 `true` 时，禁止相对 URL（内部环回调用）。                     |
| `max_url_length`    | 允许的最大 URL 长度（字符数）。                                    |

## 禁用 webhook

从 `langgraph-api>=0.2.78` 开始，开发人员可以在 `langgraph.json` 文件中禁用 webhook：

```json
{
  "http": {
    "disable_webhooks": true
  }
}
```

此功能主要面向自托管部署，平台管理员或开发人员可能希望禁用 webhook 以简化其安全态势——尤其是在他们没有配置防火墙规则或其他网络控制的情况下。禁用 webhook 有助于防止不受信任的载荷被发送到内部端点。

有关完整的配置详情，请参考配置文件参考。

## 测试 webhook

您可以使用在线服务测试您的 webhook，例如：

* **Beeceptor** – 快速创建测试端点并检查传入的 webhook 载荷。
* **Webhook.site** – 实时查看、调试和记录传入的 webhook 请求。

这些工具可帮助您验证 LangSmith 是否正确触发并将 webhook 发送到您的服务。