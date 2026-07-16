# 如何添加自定义 middleware

在将 agent 部署到 LangSmith 时，您可以向服务器添加自定义 **middleware**，以处理诸如记录请求指标、注入或检查 headers 以及强制执行安全策略等关注点，而无需修改核心服务器逻辑。这与添加自定义路由的方式相同。您只需要提供自己的 `Starlette` 应用（包括 `FastAPI`、`FastHTML` 和其他兼容的应用）。

添加 **middleware** 允许您在部署的全局范围内拦截和修改请求和响应，无论这些请求是访问您的自定义端点还是内置的 LangSmith API。

以下是一个使用 FastAPI 的示例。

“仅 Python”
  我们目前仅在 Python 部署中支持自定义 **middleware**，需要 `langgraph-api>=0.0.26`。

## 创建应用

从一个**现有的** LangSmith 应用开始，将以下 **middleware** 代码添加到您的 `webapp.py` 文件中。如果您是从头开始，可以使用 CLI 从模板创建一个新应用。

```bash
langgraph new --template=new-langgraph-project-python my_new_project
```

一旦拥有 LangGraph 项目，请添加以下应用代码：

```python
# ./src/agent/webapp.py
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Custom-Header'] = 'Hello from middleware!'
        return response

# 将 middleware 添加到应用
app.add_middleware(CustomHeaderMiddleware)
```

## 配置 `langgraph.json`

将以下内容添加到您的 `langgraph.json` 配置文件中。确保路径指向您上面创建的 `webapp.py` 文件。

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "http": {
    "app": "./src/agent/webapp.py:app"
  }
  // 其他配置选项，如 auth、store 等。
}
```

### 自定义 middleware 顺序

默认情况下，自定义 **middleware** 在认证逻辑之前运行。要让自定义 **middleware** 在认证**之后**运行，请在 `http` 配置中将 `middleware_order` 设置为 `auth_first`。（此定制需要 API server v0.4.35 或更高版本。）

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "http": {
    "app": "./src/agent/webapp.py:app",
    "middleware_order": "auth_first"
  },
  "auth": {
    "path": "./auth.py:my_auth"
  }
}
```

## 启动服务器

在本地测试服务器：

```bash
langgraph dev --no-browser
```

现在，对您服务器的任何请求都将在其响应中包含自定义 header `X-Custom-Header`。

## 部署

您可以按原样将此应用部署到云或您自己的自托管平台。

## 后续步骤

现在您已经为部署添加了自定义 **middleware**，可以使用类似的技术添加自定义路由或定义自定义生命周期事件，以进一步定制服务器的行为。