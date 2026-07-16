# 设置自定义认证

在本教程中，我们将构建一个只允许特定用户访问的聊天机器人。我们将从 LangGraph 模板开始，逐步添加基于令牌的安全性。最后，您将拥有一个在允许访问之前检查有效令牌的工作聊天机器人。

这是认证系列的第 1 部分：

1. 设置自定义认证（您在这里） - 控制谁可以访问您的机器人
2. 使对话私有 - 让用户进行私有对话
3. 连接认证提供者 - 添加真实的用户账户并使用 OAuth2 进行生产环境验证

本指南假定您对以下概念有基本的了解：

- **认证与访问控制**
- **LangSmith**

自定义认证仅适用于 LangSmith SaaS 部署或企业自托管部署。

## 1. 创建您的应用

使用 LangGraph 入门模板创建一个新的聊天机器人：

```bash
uv add "langgraph-cli[inmem]"
langgraph new --template=new-langgraph-project-python custom-auth
cd custom-auth
```

该模板为我们提供了一个占位 LangGraph 应用。通过安装本地依赖并运行开发服务器来试用：

```bash
uv add .
langgraph dev
```
服务器将启动并在浏览器中打开 Studio：

```
> - 🚀 API: http://127.0.0.1:2024
> - 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
> - 📚 API Docs: http://127.0.0.1:2024/docs
>
> This in-memory server is designed for development and testing.
> For production use, please use LangSmith.
```

如果您将自托管在公共互联网上，任何人都可以访问它。

## 2. 添加认证

现在您已经有了一个基础的 LangGraph 应用，为其添加认证。

在本教程中，您将首先使用硬编码的令牌作为示例。您将在第三个教程中接触到“生产就绪”的认证方案。

`Auth` 对象允许您注册一个认证函数，LangSmith 部署将在每个请求上运行该函数。该函数接收每个请求并决定是接受还是拒绝。

创建一个新文件 `src/security/auth.py`。您的代码将在这里检查用户是否被允许访问您的机器人：

```python
from langgraph_sdk import Auth

# This is our toy user database. Do not do this in production
VALID_TOKENS = {
    "user1-token": {"id": "user1", "name": "Alice"},
    "user2-token": {"id": "user2", "name": "Bob"},
}

# The "Auth" object is a container that LangGraph will use to mark our authentication function
auth = Auth()

# The `authenticate` decorator tells LangGraph to call this function as middleware
# for every request. This will determine whether the request is allowed or not
@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    """Check if the user's token is valid."""
    assert authorization
    scheme, token = authorization.split()
    assert scheme.lower() == "bearer"
    # Check if token is valid
    if token not in VALID_TOKENS:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid token")

    # Return user info if valid
    user_data = VALID_TOKENS[token]
    return {
        "identity": user_data["id"],
    }
```

请注意，您的 `Auth.authenticate` 处理程序做了两件重要的事情：

1. 检查请求的 `Authorization` header 中是否提供了有效令牌
2. 返回用户的 `MinimalUserDict`

现在通过将以下内容添加到 `langgraph.json` 配置中来告诉 LangGraph 使用认证：

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "auth": {
    "path": "src/security/auth.py:auth"
  }
}
```

## 3. 测试您的机器人

再次启动服务器以测试一切：

```bash
langgraph dev --no-browser
```

如果您没有添加 `--no-browser`，Studio UI 将在浏览器中打开。默认情况下，即使使用自定义认证，我们也允许从 Studio 访问。这使得在 Studio 中开发和测试您的机器人更加容易。您可以通过在认证配置中设置 `disable_studio_auth: true` 来移除此替代认证选项：

```json
{
    "auth": {
        "path": "src/security/auth.py:auth",
        "disable_studio_auth": true
    }
}
```

## 4. 与您的机器人聊天

现在，只有在请求 header 中提供有效令牌时，您才能访问该机器人。然而，用户仍然可以访问彼此的资源，直到您在本教程的下一部分中添加资源授权处理程序。

在文件或笔记本中运行以下代码：

```python
from langgraph_sdk import get_client

# Try without a token (should fail)
client = get_client(url="http://localhost:2024")
try:
    thread = await client.threads.create()
    print("❌ Should have failed without token!")
except Exception as e:
    print("✅ Correctly blocked access:", e)

# Try with a valid token
client = get_client(
    url="http://localhost:2024", headers={"Authorization": "Bearer user1-token"}
)

# Create a thread and chat
thread = await client.threads.create()
print(f"✅ Created thread as Alice: {thread['thread_id']}")

response = await client.runs.create(
    thread_id=thread["thread_id"],
    assistant_id="agent",
    input={"messages": [{"role": "user", "content": "Hello!"}]},
)
print("✅ Bot responded:")
print(response)
```

您应该看到：

1. 没有有效令牌，我们无法访问机器人
2. 使用有效令牌，我们可以创建 threads 并聊天

恭喜！您已经构建了一个只允许“认证”用户访问的聊天机器人。虽然该系统（尚未）实现生产就绪的安全方案，但我们已经学习了控制机器人访问的基本机制。在下一个教程中，我们将学习如何为每个用户提供自己的私有对话。

## 后续步骤

现在您已经可以控制谁访问您的机器人，您可能希望：

1. 继续教程，前往使对话私有以了解资源授权。
2. 阅读更多关于认证概念的内容。
3. 查看 API 参考，了解 `Auth`、`Auth.authenticate` 和 `MinimalUserDict` 的更多认证细节。