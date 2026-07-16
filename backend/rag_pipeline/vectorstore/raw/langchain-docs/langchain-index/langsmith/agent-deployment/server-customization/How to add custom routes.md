# 如何添加自定义路由

当将 agent 部署到 LangSmith Deployment 时，您的服务器会自动暴露用于创建 runs 和 threads、与长期记忆存储交互、管理可配置 assistants 以及其他核心功能的端点（请参阅所有默认 API 端点）。

您可以通过提供自己的 app 对象并在 `langgraph.json` 中传递其路径来添加自定义路由（例如，Python 中的 `Starlette` app 或 TypeScript 中的 `Hono` app）。

定义自定义 app 对象允许您添加任何所需的路由，因此您可以执行从添加 `/login` 端点到编写整个全栈 Web 应用程序的任何操作，所有这些都部署在单个 Agent Server 中。

以下分别是 Python 和 TypeScript 的示例。

## 创建 app

从一个**现有的** LangSmith 应用开始，将以下自定义路由代码添加到您的 app 文件中。如果您是从头开始，可以使用 CLI 从模板创建一个新应用。

```bash
langgraph new --template=new-langgraph-project-python my_new_project
```

一旦拥有 LangGraph 项目，请添加以下 app 代码：

```python
# ./src/agent/webapp.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
def read_root():
return {"Hello": "World"}
```

```bash
yarn create langgraph
npm install hono
```

## 配置 `langgraph.json`

将以下内容添加到您的 `langgraph.json` 配置文件中。确保路径指向您在前一部分中创建的 app 实例。

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

## 启动服务器

在本地测试服务器：

```bash
langgraph dev --no-browser
```

如果在浏览器中导航到 `localhost:2024/hello`（`2024` 是默认的开发端口），您应该会看到 `/hello` 端点返回一个 JSON 响应。对于 TypeScript 示例，请导航到 `localhost:2024/custom/hello`。

**影子覆盖默认端点**
您在 app 中创建的路由优先级高于系统默认路由，这意味着您可以影子覆盖并重新定义任何默认端点的行为。

## 部署

您可以按原样将此应用部署到 LangSmith 或您自己的自托管平台。

## 后续步骤

现在您已经为部署添加了自定义路由，可以使用相同技术进一步定制服务器的行为，例如定义自定义 **middleware** 和自定义生命周期事件。