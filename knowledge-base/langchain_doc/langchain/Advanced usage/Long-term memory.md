# Long-term memory

> 为 LangChain agents 添加长期记忆，以便跨对话和会话存储和回忆数据

长期记忆让您的 agent 能够跨不同对话和会话存储和回忆信息。与仅作用于单个线程的短期记忆不同，长期记忆可以跨线程持久化，并可在任何时间被召回。

长期记忆基于 LangGraph 存储（stores）构建，这些存储将数据保存为按命名空间（namespace）和键（key）组织的 JSON 文档。

## 使用方法

要为 agent 添加长期记忆，请创建一个 store 并将其传递给 `create_agent`：
```shell
pip install langgraph-checkpoint-postgres
```

```python
from langchain.agents import create_agent
from langchain_core.runnables import Runnable
from langgraph.store.postgres import PostgresStore  # type: ignore[import-not-found]

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
	store.setup()
	agent: Runnable = create_agent(
		"claude-sonnet-4-6",
		tools=[],
		store=store,
	)
```

然后，工具可以使用 `runtime.store` 参数从存储中读取和写入。示例请参见“在工具中读取长期记忆”和“从工具写入长期记忆”。

如需更深入地了解记忆类型（语义、情节、程序）以及写入记忆的策略，请参阅 Memory 概念指南。

## 记忆存储

LangGraph 将长期记忆作为 JSON 文档存储在 store 中。

每个记忆都在一个自定义的 `namespace`（类似于文件夹）和一个唯一的 `key`（类似于文件名）下组织。命名空间通常包含用户或组织 ID 或其他标签，便于信息组织。

这种结构支持记忆的层次化组织。然后，通过内容过滤器支持跨命名空间的搜索。
```python
from collections.abc import Sequence

from langgraph.store.base import IndexConfig
from langgraph.store.postgres import PostgresStore  # type: ignore[import-not-found]


def embed(texts: Sequence[str]) -> list[list[float]]:
    # Replace with an actual embedding function or LangChain embeddings object
    return [[1.0, 2.0] for _ in texts]


DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"

with PostgresStore.from_conn_string(
    DB_URI,
    index=IndexConfig(embed=embed, dims=2),  # type: ignore[arg-type]
) as store:
    store.setup()
    user_id = "my-user"
    application_context = "chitchat"
    namespace = (user_id, application_context)
    store.put(
        namespace,
        "a-memory",
        {
            "rules": [
                "User likes short, direct language",
                "User only speaks English & python",
            ],
            "my-key": "my-value",
        },
    )
    item = store.get(namespace, "a-memory")
    items = store.search(
        namespace, filter={"my-key": "my-value"}, query="language preferences"
    )
```

有关内存存储的更多信息，请参阅 Persistence 指南。

## 在工具中读取长期记忆

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import Runnable
from langgraph.store.postgres import PostgresStore  # type: ignore[import-not-found]


@dataclass
class Context:
    user_id: str


DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()
    store.put(("users",), "user_123", {"name": "John Smith", "language": "English"})

    @tool
    def get_user_info(runtime: ToolRuntime[Context]) -> str:
        """Look up user info."""
        assert runtime.store is not None
        user_info = runtime.store.get(("users",), runtime.context.user_id)
        return str(user_info.value) if user_info else "Unknown user"

    agent: Runnable = create_agent(
        "claude-sonnet-4-6",
        tools=[get_user_info],
        store=store,
        context_schema=Context,
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "look up user information"}]},
        context=Context(user_id="user_123"),
    )
```

## 从工具写入长期记忆

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import Runnable
from langgraph.store.postgres import PostgresStore  # type: ignore[import-not-found]
from typing_extensions import TypedDict

@dataclass
class Context:
    user_id: str

class UserInfo(TypedDict):
    name: str

@tool
def save_user_info(user_info: UserInfo, runtime: ToolRuntime[Context]) -> str:
    """Save user info."""
    assert runtime.store is not None
    runtime.store.put(("users",), runtime.context.user_id, dict(user_info))
    return "Successfully saved user info."

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()
    agent: Runnable = create_agent(
        "claude-sonnet-4-6",
        tools=[save_user_info],
        store=store,
        context_schema=Context,
    )

    agent.invoke(
        {"messages": [{"role": "user", "content": "My name is John Smith"}]},
        context=Context(user_id="user_123"),
    )
```