# 如何添加自定义生命周期事件

在将 agent 部署到 LangSmith 时，您通常需要在服务器启动时初始化资源（如数据库连接），并在关闭时确保它们被正确清理。生命周期事件允许您挂接到服务器的启动和关闭序列中，以处理这些关键的设置和清理任务。

这与添加自定义路由的方式相同。您只需要提供自己的 `Starlette` 应用（包括 `FastAPI`、`FastHTML` 和其他兼容的应用）。

以下是一个使用 FastAPI 的示例。

“仅 Python”
  我们目前仅在 Python 部署中支持自定义生命周期事件，需要 `langgraph-api>=0.0.26`。

## 创建应用

从一个**现有的** LangSmith 应用开始，将以下生命周期代码添加到您的 `webapp.py` 文件中。如果您是从头开始，可以使用 CLI 从模板创建一个新应用。

```bash
langgraph new --template=new-langgraph-project-python my_new_project
```

一旦拥有 LangGraph 项目，请添加以下应用代码：

```python
# ./src/agent/webapp.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 例如...
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    # 创建可重用的 session 工厂
    async_session = sessionmaker(engine, class_=AsyncSession)
    # 存储在 app.state 中
    app.state.db_session = async_session
    yield
    # 清理连接
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

# ... 如需添加自定义路由，可在此添加。
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

## 启动服务器

在本地测试服务器：

```bash
langgraph dev --no-browser
```

当服务器启动时，您应该会看到启动消息被打印出来；当您使用 `Ctrl+C` 停止服务器时，会看到清理消息。

## 部署

您可以按原样将应用部署到云或您自己的自托管平台。

## 后续步骤

现在您已经为部署添加了生命周期事件，可以使用类似的技术添加自定义路由或自定义中间件，以进一步定制服务器的行为。