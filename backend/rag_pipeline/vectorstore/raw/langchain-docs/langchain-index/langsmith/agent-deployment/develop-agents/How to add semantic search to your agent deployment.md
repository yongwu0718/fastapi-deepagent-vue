# 如何向 agent 部署添加语义搜索

本指南介绍如何为部署中的跨线程 store 添加语义搜索，以便您的 agent 能够根据语义相似度搜索记忆和其他文档。

## 前提条件

* 一个部署（请参阅如何设置应用进行部署）以及托管选项的详细信息。
* 您的嵌入提供商（本例中为 OpenAI）的 API key。
* `langchain >= 0.3.8`（如果您使用下面的字符串格式指定嵌入）。

## 步骤

1. 更新您的 `langgraph.json` 配置文件，加入 store 配置：

```json
{
    ...
    "store": {
        "index": {
            "embed": "openai:text-embedding-3-small",
            "dims": 1536,
            "fields": ["$"]
        }
    }
}
```

该配置：

* 使用 OpenAI 的 `text-embedding-3-small` 模型生成嵌入向量；
* 设置嵌入维度为 1536（与模型输出维度匹配）；
* 索引存储数据中的所有字段（`["$"]` 表示索引全部内容，也可以指定特定字段，如 `["text", "metadata.title"]`）。

每个部署只支持单个嵌入模型。不支持配置多个嵌入模型，因为这样会导致 `/store` 端点的歧义和混合索引问题。

2. 要使用上述字符串嵌入格式，请确保您的依赖中包含 `langchain >= 0.3.8`：

```toml
# 在 pyproject.toml 中
[project]
dependencies = [
    "langchain>=0.3.8"
]
```

或者如果使用 `requirements.txt`：

```
langchain>=0.3.8
```

## 使用方法

配置完成后，您可以在 **node** 中使用语义搜索。**store** 需要一个 **namespace** 元组来组织记忆：

```python
async def search_memory(state: State, *, store: BaseStore):
    # 使用语义相似度搜索 store
    # namespace 元组有助于按类型组织不同的记忆
    # 例如：("user_facts", "preferences") 或 ("conversation", "summaries")
    results = await store.asearch(
        namespace=("memory", "facts"),  # 按类型组织记忆
        query="您的搜索查询",
        limit=3  # 返回的结果数量
    )
    return results
```

每个结果是一个 `SearchItem`（扩展自 `Item`，并增加一个 `score` 字段）。当配置了语义搜索时，`score` 包含相似度分数：

```python
results[0].key       # "07e0caf4-1631-47b7-b15f-65515d4c1843"
results[0].value     # {"text": "用户偏好深色模式"}
results[0].namespace # ("memory", "facts")
results[0].score     # 0.92（语义搜索配置后出现的相似度分数）
```

### 更换嵌入模型

更改嵌入模型或维度需要重新嵌入所有现有数据。目前没有针对此操作的自动迁移工具。如果您需要切换模型，请做好相应规划。

## 自定义嵌入

如果您想使用自定义嵌入函数，可以传递一个指向自定义嵌入函数的路径：

```json
{
    ...
    "store": {
        "index": {
            "embed": "path/to/embedding_function.py:embed",
            "dims": 1536,
            "fields": ["$"]
        }
    }
}
```

部署会在指定路径中查找该函数。该函数必须是异步的，并接受一个字符串列表：

```python
# path/to/embedding_function.py
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def aembed_texts(texts: list[str]) -> list[list[float]]:
    """自定义嵌入函数，必须：
    1. 是异步的
    2. 接受一个字符串列表
    3. 返回一个浮点数数组（嵌入向量）的列表
    """
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [e.embedding for e in response.data]
```

## 通过 API 查询

您也可以使用 LangGraph SDK 查询 **store**。由于 SDK 使用异步操作：

```python
from langgraph_sdk import get_client

async def search_store():
    client = get_client()
    results = await client.store.search_items(
        ("memory", "facts"),
        query="您的搜索查询",
        limit=3  # 返回的结果数量
    )
    return results

# 在异步上下文中使用
results = await search_store()
```

当配置了语义搜索时，每个结果项都包含一个 `score` 字段：

```python
results["items"][0]["key"]       # "07e0caf4-1631-47b7-b15f-65515d4c1843"
results["items"][0]["value"]     # {"text": "用户偏好深色模式"}
results["items"][0]["namespace"] # ["memory", "facts"]
results["items"][0]["score"]     # 0.92（相似度分数）
```