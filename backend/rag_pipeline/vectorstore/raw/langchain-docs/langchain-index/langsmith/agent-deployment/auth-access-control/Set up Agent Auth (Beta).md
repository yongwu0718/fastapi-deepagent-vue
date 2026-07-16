# 设置 Agent Auth (Beta)

> 使用 Agent Auth 通过 OAuth 2.0 凭据实现从代理到任何系统的安全访问。

Agent Auth 处于 **Beta** 阶段，正在积极开发中。要提供反馈或使用此功能，请联系 LangChain 团队。

## 安装

```bash
uv add langchain-auth
```
## 快速入门

### 1. 初始化客户端

```python
from langchain_auth import Client

client = Client(api_key="your-langsmith-api-key")
```

#### 自托管配置

对于自托管的 LangSmith 实例，请使用实例上的 `/api-host` 路径指定 API URL。

```bash
export LANGSMITH_API_URL="https://your-langsmith-instance.com/api-host"
```

然后正常初始化客户端：

```python
client = Client(api_key="your-langsmith-api-key")
```

### 2. 设置 OAuth 提供者

在代理可以认证之前，您需要使用以下过程配置一个 OAuth 提供者：

1. 为您的 OAuth 提供者选择一个在 LangChain 平台中使用的唯一标识符（例如 "github-local-dev"、"google-workspace-prod"）。

2. 前往您的 OAuth 提供者的开发者控制台并创建一个新的 OAuth 应用。

3. 在您的 OAuth 提供者中设置回调 URL：

**langsmith cloud**
```
https://smith.langchain.com/host-oauth-callback/{provider_id}
```

例如，如果您的 provider_id 是 "github-local-dev"，请使用：

```
https://smith.langchain.com/host-oauth-callback/github-local-dev
```
**self-hosted**
```
https://{your-langsmith-instance}/host-oauth-callback/{provider_id}
```

例如，如果您的实例是 `langsmith.example.com` 且 provider_id 是 "github"，请使用：

```
https://langsmith.example.com/host-oauth-callback/github
```

4. 使用来自 OAuth 应用的凭据调用 `client.create_oauth_provider()`：

```python
new_provider = await client.create_oauth_provider(
    provider_id="{provider_id}",  # Provide any unique ID
    name="{provider_display_name}",  # Provide any display name
    client_id="{your_client_id}",
    client_secret="{your_client_secret}",
    auth_url="{auth_url_of_your_provider}",
    token_url="{token_url_of_your_provider}",
)
```

### 3. 从代理进行认证

客户端 `authenticate()` API 用于从预先配置的提供者获取 OAuth 令牌。首次调用时，它会引导调用者完成 OAuth 2.0 授权流程。

#### 在 LangGraph 上下文中

默认情况下，令牌使用 Assistant ID 参数限定给调用代理。

```python
auth_result = await client.authenticate(
    provider="{provider_id}",
    scopes=["scopeA"],
    user_id="your_user_id"  # Any unique identifier to scope this token to the human caller
)

# Or explicitly specify an agent_id for agent-scoped tokens
auth_result = await client.authenticate(
    provider="{provider_id}",
    scopes=["scopeA"],
    user_id="your_user_id",
    agent_id="specific-agent-id"  # Optional: explicitly set agent scope
)
```

在执行期间，如果需要认证，SDK 将抛出一个中断。代理执行暂停并向用户呈现 OAuth URL：

用户完成 OAuth 认证并且我们收到来自提供者的回调后，他们将看到认证成功页面。

然后代理从它停止的地方恢复执行，并且该令牌可用于任何 API 调用。我们会存储并刷新 OAuth 令牌，以便用户或代理以后使用该服务时不需要再次进行 OAuth 流程。

```python
token = auth_result.token
```

#### 在 LangGraph 上下文之外

向用户提供 `auth_url` 以进行带外 OAuth 流程。

```python
auth_result = await client.authenticate(
    provider="{provider_id}",
    scopes=["scopeA"],
    user_id="your_user_id"
)

if auth_result.status == "pending":
    print(f"Complete OAuth at: {auth_result.url}")
    # Wait for user to complete OAuth
    completed_auth = await client.wait_for_completion(auth_result.auth_id)
    print("Authentication completed!")
else:
    token = auth_result.token
    print(f"Already authenticated, token: {token}")
```

## 故障排除

### 自托管：405 Method Not Allowed

如果您收到 `405 Method Not Allowed` 错误，请确保 `LANGSMITH_API_URL` 指向 `/api-host` 路径：

```bash
export LANGSMITH_API_URL="https://your-instance.com/api-host"
```

### 自托管：格式错误的 OAuth 回调 URL

确保您的 OAuth 提供者的重定向 URI 与您的 LangSmith 实例 URL 匹配：

```
https://your-instance.com/host-oauth-callback/{provider_id}
```