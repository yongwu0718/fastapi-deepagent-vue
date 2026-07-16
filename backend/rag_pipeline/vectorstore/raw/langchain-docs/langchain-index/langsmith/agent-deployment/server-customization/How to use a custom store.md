# 如何使用自定义 store

> 在您的 agent 部署中，用自定义的 `BaseStore` 实现替换内置的 Postgres store。

当将 agent 部署到 LangSmith 时，服务器提供了一个内置的基于 Postgres 的长期记忆存储，并通过 pgvector 支持可选的向量搜索。您可以用自己的 `BaseStore` 实现替换它，以使用不同的存储后端、自定义索引或专门的搜索能力。

您需要提供一个指向异步上下文管理器的路径，该上下文管理器生成一个 `BaseStore` 实例，服务器会自动管理该 store 的生命周期。

自定义 store 处于 **alpha** 阶段。此功能可能在次版本更新中出现破坏性变更。

## 定义 store

从一个**现有的** LangSmith 应用开始，创建一个文件，定义一个异步上下文管理器，用于生成您的自定义 store。如果您刚开始一个新项目，可以使用 CLI 从模板创建应用。

```bash
langgraph new --template=new-langgraph-project-python my_new_project
```

异步上下文管理器模式允许服务器在应用生命周期的适当时机打开和关闭 store 连接。以下示例使用 `AsyncSqliteStore` 并启用了语义搜索：

SQLite 不建议在生产部署中使用。

```python
# ./src/agent/store.py
import contextlib

from langchain.embeddings import init_embeddings
from langgraph.store.base import IndexConfig
from langgraph.store.sqlite import AsyncSqliteStore

embeddings = init_embeddings("openai:text-embedding-3-small")

@contextlib.asynccontextmanager
async def generate_store():
    """生成一个 BaseStore，在服务器整个生命周期内保持打开状态。"""
    async with AsyncSqliteStore.from_conn_string(
        "./custom_store.sql",
        index=IndexConfig(
            dims=1536,
            embed=embeddings,
            fields=["$"],
        ),
    ) as store:
        await store.setup()
        yield store
```

当配置了自定义 store 后，它将**完全替换**内置的 Postgres store。语义搜索和 TTL 扫描等功能取决于您的具体实现。

## 配置 `langgraph.json`

在 `langgraph.json` 配置文件中添加 `store` 键。`path` 指向您之前定义的异步上下文管理器。

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "store": {
    "path": "./src/agent/store.py:generate_store"
  }
}
```

## 启动服务器

在本地测试服务器：

```bash
langgraph dev --no-browser
```

服务器日志将确认您的自定义 store 已激活：

```
Using custom store. Skipping store TTL sweeper.
```

## 部署

您可以按原样将此应用部署到 LangSmith 或您自己的自托管平台。

## 后续步骤

* 使用自定义 checkpointer 替换内置的 checkpoint 存储。
* 了解 LangGraph 中的持久化和记忆。