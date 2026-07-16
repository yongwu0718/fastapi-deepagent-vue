# 如何使用自定义 checkpointer

> 在您的 agent 部署中，用自定义的 `BaseCheckpointSaver` 实现替换内置的 Postgres checkpointer。

当将 agent 部署到 LangSmith 时，服务器提供了一个内置的基于 Postgres 的 checkpointer，用于处理 graph 运行之间的状态持久化。您可以用自己的 `BaseCheckpointSaver` 实现替换它，以使用不同的存储后端。

您需要提供一个指向异步上下文管理器的路径，该上下文管理器生成一个 `BaseCheckpointSaver` 实例，服务器会自动管理其生命周期。

自定义 checkpointer 处于 **alpha** 阶段。此功能可能在次版本更新中出现破坏性变更。

要为 checkpoint 存储使用 MongoDB 而非 PostgreSQL，请参阅“配置 checkpointer 后端”。本页适用于实现完全自定义的存储后端。

## 定义 checkpointer

从一个**现有的** LangSmith 应用开始，创建一个文件，定义一个异步上下文管理器，用于生成您的自定义 checkpointer。如果您刚开始一个新项目，可以使用 CLI 从模板创建应用。

```bash
langgraph new --template=new-langgraph-project-python my_new_project
```

异步上下文管理器模式允许服务器在应用生命周期的适当时机打开和关闭数据库连接：

```python
# ./src/agent/checkpointer.py
import contextlib

class MyCheckpointer(BaseCheckpointSaver):
    def __init__(self):
        super().__init__()
        # 在此初始化您的自定义 checkpointer
    ...

    @contextlib.asynccontextmanager
    async def aget(self, config: RunnableConfig):
        # 在此编写自定义逻辑，例如创建连接池并初始化您的 checkpointer
        yield

@contextlib.asynccontextmanager
async def generate_checkpointer():
    """生成一个 BaseCheckpointSaver，在服务器整个生命周期内保持打开状态。"""
    async with AsyncSqliteSaver.from_conn_string("./checkpoints.db") as saver:
        await saver.setup()
        yield saver
```

## 与一致性测试套件进行验证

大多数开源 checkpointer 实现尚未实现 Agent Server 所需的所有操作。在配置您的 checkpointer 之前，请使用一致性测试套件对其进行验证，以确保兼容性。

安装包：

```bash
pip install langgraph-checkpoint-conformance
```

注册您的 checkpointer 并运行验证：

```python
import asyncio

from langgraph.checkpoint.conformance import checkpointer_test, validate

@checkpointer_test(name="MyCheckpointer")
async def my_checkpointer():
    async with MyCheckpointer(...) as saver:
        yield saver

async def main():
    report = await validate(my_checkpointer)
    report.print_report()
    assert report.passed_all_base()

asyncio.run(main())
```

该套件会自动检测您的 checkpointer 实现了哪些扩展能力，并运行相应的测试。您也可以将其作为 pytest 测试运行：

```python
import pytest

from langgraph.checkpoint.conformance import checkpointer_test, validate

@checkpointer_test(name="MyCheckpointer")
async def my_checkpointer():
    async with MyCheckpointer(...) as saver:
        yield saver

@pytest.mark.asyncio
async def test_conformance():
    report = await validate(my_checkpointer)
    report.print_report()
    assert report.passed_all_base()
```

要查看套件验证的基础和扩展操作的完整列表，请参阅 capabilities 部分。

## 配置 `langgraph.json`

在 `langgraph.json` 配置文件中添加 `checkpointer` 键。`path` 指向您之前定义的异步上下文管理器。

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "checkpointer": {
    "path": "./src/agent/checkpointer.py:generate_checkpointer"
  }
}
```

## 启动服务器

在本地测试服务器：

```bash
langgraph dev --no-browser
```

服务器日志将确认您的自定义 checkpointer 已激活。

## 能力集

服务器在启动时会检查您的 checkpointer 是否具有**基础**（必需）和**扩展**（可选）能力。如果缺少某项扩展能力，服务器会使用后备方案或禁用相应功能。

### 基础能力（必需）

| 方法             | 描述               |
| ---------------- | ------------------ |
| `aput`           | 存储一个 checkpoint |
| `aput_writes`    | 存储待写入数据       |
| `aget_tuple`     | 检索一个 checkpoint |
| `alist`          | 列出 checkpoints   |
| `adelete_thread` | 删除一个 thread    |

### 扩展能力（可选）

| 方法               | 描述                           | 缺少时的后备方案                           |
| ------------------ | ------------------------------ | ------------------------------------------ |
| `adelete_for_runs` | 删除特定 runs 的 checkpoints | 无法使用多任务回滚策略                     |
| `acopy_thread`     | 复制一个 thread                | 慢速后备方案（逐个重新插入 checkpoints） |
| `aprune`           | 修剪 thread 历史               | 无法修剪 thread 历史                       |

## 部署

您可以按原样将此应用部署到 LangSmith 或您自己的自托管平台。

## 后续步骤

* 使用自定义 store 替换内置的长期记忆存储。
* 了解 LangGraph 中的持久化和记忆。