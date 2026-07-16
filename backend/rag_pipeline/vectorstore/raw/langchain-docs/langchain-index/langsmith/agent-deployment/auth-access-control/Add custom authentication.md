# 添加自定义认证

本指南向您展示如何为 LangSmith 应用添加自定义认证。本页的步骤适用于云部署和自托管部署。不适用于在您自己的自定义服务器中独立使用 LangGraph 开源库的情况。

## 为您的部署添加自定义认证

要利用自定义认证并在您的部署中访问用户级别的元数据，请通过自定义认证处理程序设置自定义认证，以自动填充 `config["configurable"]["langgraph_auth_user"]` 对象。然后，您可以在 graph 中使用 `langgraph_auth_user` 键访问该对象，以允许代理代表用户执行经过认证的操作。

1. 实现认证：

如果没有自定义的 `@auth.authenticate` 处理程序，LangGraph 只能看到 API 密钥所有者（通常是开发者），因此请求不会限定到单个最终用户。要传播自定义令牌，您必须实现自己的处理程序。

```python
from langgraph_sdk import Auth
import requests

auth = Auth()

def is_valid_key(api_key: str) -> bool:
    is_valid = # your API key validation logic
    return is_valid

@auth.authenticate # (1)!
async def authenticate(headers: dict) -> Auth.types.MinimalUserDict:
    api_key = headers.get(b"x-api-key")
    if not api_key or not is_valid_key(api_key):
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid API key")

    # Fetch user-specific tokens from your secret store
    user_tokens = await fetch_user_tokens(api_key)

    return { # (2)!
        "identity": api_key,  #  fetch user ID from LangSmith
        "github_token" : user_tokens.github_token
        "jira_token" : user_tokens.jira_token
        # ... custom fields/secrets here
    }
```

- 此处理程序接收请求（headers 等），验证用户，并返回一个至少包含 identity 字段的字典。
- 您可以添加任何您想要的自定义字段（例如 OAuth 令牌、角色、组织 ID 等）。

2. 在您的 `langgraph.json` 中，添加指向您的认证文件的路径：

```json
{
    "dependencies": ["."],
    "graphs": {
    "agent": "./agent.py:graph"
    },
    "env": ".env",
    "auth": {
        "path": "./auth.py:my_auth"
    }
}
```
3. 一旦您在服务器中设置了认证，请求必须根据您选择的方案包含所需的授权信息。假设您使用 JWT 令牌认证，您可以通过以下任何方法访问您的部署：
**client**
```python
from langgraph_sdk import get_client

my_token = "your-token" # In practice, you would generate a signed token with your auth provider
client = get_client(
    url="http://localhost:2024",
    headers={"Authorization": f"Bearer {my_token}"}
)
threads = await client.threads.search()
```

有关 RemoteGraph 的更多详细信息，请参阅使用 RemoteGraph 指南。

## 启用代理认证

认证后，平台会创建一个特殊的配置对象（`config`），该对象被传递给 LangSmith 部署。此对象包含有关当前用户的信息，包括您从 `@auth.authenticate` 处理程序返回的任何自定义字段。

要允许代理代表用户执行经过认证的操作，请在 graph 中使用 `langgraph_auth_user` 键访问此对象：

```python
def my_node(state, config):
    user_config = config["configurable"].get("langgraph_auth_user")
    # token was resolved during the @auth.authenticate function
    token = user_config.get("github_token","")
    ...
```

从安全的密钥存储中获取用户凭据。不建议将密钥存储在 graph 状态中。

### 为 Studio 授权用户

默认情况下，如果您在资源上添加了自定义授权，这同样适用于从 Studio 进行的交互。如果您愿意，可以通过检查 `is_studio_user()` 来区分处理已登录的 Studio 用户。

`is_studio_user` 在 langgraph-sdk 的 0.1.73 版本中添加。如果您使用的是旧版本，您仍然可以检查 `isinstance(ctx.user, StudioUser)`。

```python
from langgraph_sdk.auth import is_studio_user, Auth
auth = Auth()

# ... Setup authenticate, etc.

@auth.on
async def add_owner(
    ctx: Auth.types.AuthContext,
    value: dict  # The payload being sent to this access method
) -> dict:  # Returns a filter dict that restricts access to resources
    if is_studio_user(ctx.user):
        return {}

    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)
    return filters
```

仅当您希望允许开发者访问托管在托管 LangSmith SaaS 上的 graph 时才使用此方法。

## 了解更多

- Authentication & Access Control
- 设置自定义认证教程