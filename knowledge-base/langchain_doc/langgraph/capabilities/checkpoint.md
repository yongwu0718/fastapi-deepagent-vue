# 检查点

LangGraph 有一个内置的持久化层，将图状态保存为检查点 (checkpoints)。当您使用 checkpointer 编译图时，图状态的快照将在执行的每一步被保存，并按线程 (threads) 组织。这支持了人机交互工作流、对话记忆、时间旅行调试和容错执行。

**Agent Server 会自动处理 checkpointing**
  当使用 Agent Server 时，您无需手动实现或配置 checkpointers。服务器会在后台为您处理所有持久化基础设施。

## 为什么使用持久化

持久化是以下功能所必需的：

*   **人机交互 (Human-in-the-loop)**：Checkpointers 通过允许人们检查、中断和批准图步骤来促进人机交互工作流。这些工作流需要 checkpointers，因为人必须能够随时查看图的状态，并且图必须能够在人对状态进行任何更新后恢复执行。请参阅 Interrupts 中的示例。
*   **记忆 (Memory)**：Checkpointers 允许交互之间的“记忆”。在重复的人类交互（如对话）的情况下，任何后续消息都可以发送到该线程，该线程将保留之前消息的记忆。请参阅 Add memory 以了解如何使用 checkpointers 添加和管理对话记忆。
*   **时间旅行 (Time travel)**：Checkpointers 允许“时间旅行”，使用户能够重放先前的图执行，以审查和/或调试特定的图步骤。此外，checkpointers 使得可以在任意检查点处 fork 图状态，以探索替代轨迹。
*   **容错 (Fault-tolerance)**：Checkpointing 提供了容错和错误恢复：如果一个或多个节点在给定的超级步骤 (superstep) 中失败，您可以从最后成功的步骤重新启动图。

*   **待处理写入 (Pending writes)**：当一个图节点在给定的超级步骤中执行失败时，LangGraph 会存储该超级步骤中任何其他成功完成节点的待处理检查点写入。当您从该超级步骤恢复图执行时，您不会重新运行成功的节点。

## 核心概念

### 线程 (Threads)

线程是一个唯一的 ID 或线程标识符，分配给由 checkpointer 保存的每个检查点。它包含一系列运行的累积状态。当执行一个运行时，助手底层图的状态将被持久化到该线程。

当使用 checkpointer 调用图时，您**必须**在配置的 `configurable` 部分中指定一个 `thread_id`：

```python
{"configurable": {"thread_id": "1"}}
```

可以检索线程的当前状态和历史状态。要持久化状态，必须在执行运行之前创建线程。LangSmith API 提供了多个用于创建和管理线程及线程状态的端点。有关更多详细信息，请参阅 API 参考。

Checkpointer 使用 `thread_id` 作为存储和检索检查点的主键。没有它，checkpointer 无法保存状态或在中断后恢复执行，因为 checkpointer 使用 `thread_id` 来加载保存的状态。

### 检查点 (Checkpoints)

线程在特定时间点的状态称为检查点 (checkpoint)。检查点是每个超级步骤保存的图状态快照，并由一个 `StateSnapshot` 对象表示（有关完整字段参考，请参见 [StateSnapshot 字段](#statesnapshot-字段)字段）。

#### 超级步骤 (Super-steps)

LangGraph 会在每个**超级步骤（super-step）边界**创建一个检查点。超级步骤是指图的一次完整"时钟周期"，在此期间所有被安排执行的节点会运行（可能并行执行）。例如，对于 `START → A → B → END` 这样的顺序图，输入、节点 A 和节点 B 会分别处于不同的超级步骤中——每个步骤完成后都会生成一个检查点。理解超级步骤边界对**状态回溯（time travel）** 至关重要，因为系统只能从检查点（即超级步骤边界）恢复执行。

除了超级步骤级别的检查点外，LangGraph 还会**持久化节点（任务）级别的写入操作**。当超级步骤中的某个节点完成执行后，其输出会作为任务条目写入检查点管理器的 `checkpoint_writes` 表，并关联到当前进行中的检查点。这些**任务级写入**实现了**待处理写入恢复机制**：如果同一超级步骤中的其他节点后续执行失败，已成功节点的写入结果已持久化，恢复时无需重新执行。

当超级步骤完成时，系统才会提交完整的状态快照（StateSnapshot）。LangGraph 同时还会持久化超级步骤内**单个节点执行的写入结果**。这些写入以任务形式存储，用于实现容错能力：若同一超级步骤中其他节点失败，恢复执行时已成功节点的写入无需重新计算。需要注意的是，任务级写入**不是完整的 StateSnapshot 检查点**，因此状态回溯功能仅能从超级步骤边界的完整检查点恢复执行。

检查点被持久化，可用于稍后恢复线程的状态。

让我们看看当按如下方式调用一个简单图时，保存了哪些检查点：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig
from typing import Annotated
from typing_extensions import TypedDict
from operator import add

class State(TypedDict):
    foo: str
    bar: Annotated[list[str], add]

def node_a(state: State):
    return {"foo": "a", "bar": ["a"]}

def node_b(state: State):
    return {"foo": "b", "bar": ["b"]}

workflow = StateGraph(State)
workflow.add_node(node_a)
workflow.add_node(node_b)
workflow.add_edge(START, "node_a")
workflow.add_edge("node_a", "node_b")
workflow.add_edge("node_b", END)

checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}
graph.invoke({"foo": "", "bar":[]}, config)
```

在运行图之后，我们期望看到正好 4 个检查点：

*   空检查点，下一个要执行的节点为 `START`
*   带有用户输入 `{'foo': '', 'bar': []}` 且下一个要执行节点为 `node_a` 的检查点
*   带有 `node_a` 输出 `{'foo': 'a', 'bar': ['a']}` 且下一个要执行节点为 `node_b` 的检查点
*   带有 `node_b` 输出 `{'foo': 'b', 'bar': ['a', 'b']}` 且没有下一个要执行节点的检查点

请注意，`bar` 通道值包含来自两个节点的输出，因为我们为 `bar` 通道定义了一个 reducer。

#### 检查点命名空间

每个检查点都有一个 `checkpoint_ns`（检查点命名空间）字段，用于标识它属于哪个图或子图：

*   **`""`**（空字符串）：检查点属于父（根）图。
*   **`"node_name:uuid"`**：检查点属于作为给定节点调用的子图。对于嵌套子图，命名空间使用 `|` 分隔符连接（例如 `"outer_node:uuid|inner_node:uuid"`）。

您可以通过配置从节点内部访问检查点命名空间：

```python
from langchain_core.runnables import RunnableConfig

def my_node(state: State, config: RunnableConfig):
    checkpoint_ns = config["configurable"]["checkpoint_ns"]
    # 对于父图是 ""，对于子图是 "node_name:uuid"
```

有关使用子图状态和检查点的更多详细信息，请参阅 Subgraphs。

## 获取和更新状态

### 获取状态

当与保存的图状态交互时，您**必须**指定一个线程标识符。您可以通过调用 `graph.get_state(config)` 查看图的*最新*状态。这将返回一个 `StateSnapshot` 对象，该对象对应于配置中提供的线程 ID 的最新检查点，或者，如果提供了检查点 ID，则对应于该线程的特定检查点 ID 的检查点。

```python
# 获取最新的状态快照
config = {"configurable": {"thread_id": "1"}}
graph.get_state(config)

# 为特定的 checkpoint_id 获取状态快照
config = {"configurable": {"thread_id": "1", "checkpoint_id": "1ef663ba-28fe-6528-8002-5a559208592c"}}
graph.get_state(config)
```

在我们的示例中，`get_state` 的输出将如下所示：

```
StateSnapshot(
    values={'foo': 'b', 'bar': ['a', 'b']},
    next=(),
    config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28fe-6528-8002-5a559208592c'}},
    metadata={'source': 'loop', 'writes': {'node_b': {'foo': 'b', 'bar': ['b']}}, 'step': 2},
    created_at='2024-08-29T19:19:38.821749+00:00',
    parent_config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28f9-6ec4-8001-31981c2c39f8'}}, tasks=()
)
```

#### StateSnapshot 字段

| 字段           | 类型                     | 描述                                                                                                                                                |
| -------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `values`       | `dict`                   | 此检查点处的状态通道值。                                                                                                                            |
| `next`         | `tuple[str, ...]`        | 接下来要执行的节点名称。空的 `()` 表示图已完成。                                                                                                    |
| `config`       | `dict`                   | 包含 `thread_id`、`checkpoint_ns` 和 `checkpoint_id`。                                                                                              |
| `metadata`     | `dict`                   | 执行元数据。包含 `source`（`"input"`、`"loop"` 或 `"update"`）、`writes`（节点输出）和 `step`（超级步骤计数器）。                                   |
| `created_at`   | `str`                    | 此检查点创建时的 ISO 8601 时间戳。                                                                                                                 |
| `parent_config`| `dict \| None`           | 先前检查点的配置。对于第一个检查点为 `None`。                                                                                                      |
| `tasks`        | `tuple[PregelTask, ...]` | 此步骤要执行的任务。每个任务都有 `id`、`name`、`error`、`interrupts`，并且可选地有 `state`（子图快照，当使用 `subgraphs=True` 时）。               |

### 获取状态历史

您可以通过调用 `graph.get_state_history(config)` 获取给定线程的图执行完整历史。这将返回一个 `StateSnapshot` 对象列表，这些对象与配置中提供的线程 ID 相关联。重要的是，检查点将按时间顺序排列，最新的检查点 / `StateSnapshot` 位于列表的第一个。

```python
config = {"configurable": {"thread_id": "1"}}
list(graph.get_state_history(config))
```

在我们的示例中，`get_state_history` 的输出将如下所示：

```
[
    StateSnapshot(
        values={'foo': 'b', 'bar': ['a', 'b']},
        next=(),
        config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28fe-6528-8002-5a559208592c'}},
        metadata={'source': 'loop', 'writes': {'node_b': {'foo': 'b', 'bar': ['b']}}, 'step': 2},
        created_at='2024-08-29T19:19:38.821749+00:00',
        parent_config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28f9-6ec4-8001-31981c2c39f8'}},
        tasks=(),
    ),
    StateSnapshot(
        values={'foo': 'a', 'bar': ['a']},
        next=('node_b',),
        config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28f9-6ec4-8001-31981c2c39f8'}},
        metadata={'source': 'loop', 'writes': {'node_a': {'foo': 'a', 'bar': ['a']}}, 'step': 1},
        created_at='2024-08-29T19:19:38.819946+00:00',
        parent_config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28f4-6b4a-8000-ca575a13d36a'}},
        tasks=(PregelTask(id='6fb7314f-f114-5413-a1f3-d37dfe98ff44', name='node_b', error=None, interrupts=()),),
    ),
    StateSnapshot(
        values={'foo': '', 'bar': []},
        next=('node_a',),
        config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28f4-6b4a-8000-ca575a13d36a'}},
        metadata={'source': 'loop', 'writes': None, 'step': 0},
        created_at='2024-08-29T19:19:38.817813+00:00',
        parent_config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28f0-6c66-bfff-6723431e8481'}},
        tasks=(PregelTask(id='f1b14528-5ee5-579c-949b-23ef9bfbed58', name='node_a', error=None, interrupts=()),),
    ),
    StateSnapshot(
        values={'bar': []},
        next=('__start__',),
        config={'configurable': {'thread_id': '1', 'checkpoint_ns': '', 'checkpoint_id': '1ef663ba-28f0-6c66-bfff-6723431e8481'}},
        metadata={'source': 'input', 'writes': {'foo': ''}, 'step': -1},
        created_at='2024-08-29T19:19:38.816205+00:00',
        parent_config=None,
        tasks=(PregelTask(id='6d27aa2e-d72b-5504-a36f-8620e54a76dd', name='__start__', error=None, interrupts=()),),
    )
]
```

#### 查找特定的检查点

您可以筛选状态历史以查找匹配特定条件的检查点：

```python
history = list(graph.get_state_history(config))

# 查找特定节点执行之前的检查点
before_node_b = next(s for s in history if s.next == ("node_b",))

# 按步骤编号查找检查点
step_2 = next(s for s in history if s.metadata["step"] == 2)

# 查找由 update_state 创建的检查点
forks = [s for s in history if s.metadata["source"] == "update"]

# 查找发生中断的检查点
interrupted = next(
    s for s in history
    if s.tasks and any(t.interrupts for t in s.tasks)
)
```

### Replay  

Replay 会从先前的 checkpoint 重新执行步骤。使用先前的 checkpoint_id 调用图，即可重新运行该 checkpoint 之后的节点。checkpoint 之前的节点会被跳过（其结果已保存）。checkpoint 之后的节点会重新执行，包括任何 LLM 调用、API 请求或中断——这些在 replay 期间始终会重新触发。

### Update state  

您可以使用 update_state 编辑图 state。这会创建一个包含更新值的新 checkpoint——它不会修改原始 checkpoint。该更新被视为与节点更新相同：如果定义了 reducer 函数，值会通过 reducer 传递，因此带有 reducer 的 channel 会累积值而不是覆盖它们。 

您可以选择指定 as_node 来控制该更新被视为来自哪个节点，这会影响接下来执行哪个节点。

## Durability modes  

LangGraph 支持三种 durability mode，让您可以在性能和数据一致性之间取得平衡。您可以在调用任何图执行方法时指定 durability mode：

```python
graph.stream(
    {"input": "test"},
    durability="sync"
)
```

三种模式按持久性从低到高如下：  

- **"exit"**：LangGraph 仅在图执行退出时（成功、出错或因 human-in-the-loop 中断）持久化更改。这为长时间运行的图提供了最佳性能，但意味着中间 state 不会被保存，因此您无法在系统故障（如进程崩溃）时从执行中途恢复。  

- **"async"**：LangGraph 在执行下一步的同时异步持久化更改。这提供了良好的性能和持久性，但如果进程在执行期间崩溃，则 LangGraph 有小概率不会写入 checkpoint。

- **"sync"**：LangGraph 在下一步开始之前同步持久化更改。这确保 LangGraph 在继续执行之前写入每个 checkpoint，以一定的性能开销为代价提供高持久性。

## Optimize checkpoint storage  

默认情况下，LangGraph checkpoint 在每个 super-step 写入每个 state channel 的完整值。对于长时间运行的线程且具有大量累积（例如多轮对话），这可能会随时间推移导致存储显著增长。  

DeltaChannel 仅存储增量 delta，而不是完整的累积值，从而大幅减少追加密集型 channel 的 checkpoint 大小。  

DeltaChannel 需要 langgraph>=1.2，目前处于 beta 阶段。API 在未来版本中可能会发生变化。

## Checkpointer libraries  

在底层，checkpointing 由符合 BaseCheckpointSaver 接口的 checkpointer 对象提供支持。LangGraph 提供了几种 checkpointer 实现，均通过独立的、可安装的库实现。  

- **langgraph-checkpoint**：checkpointer 保存器（BaseCheckpointSaver）及序列化/反序列化接口（SerializerProtocol）的基础接口。包含用于实验的内存 checkpointer 实现（InMemorySaver）。LangGraph 自带 langgraph-checkpoint。

- **langgraph-checkpoint-sqlite**：使用 SQLite 数据库的 LangGraph checkpointer 实现（SqliteSaver / AsyncSqliteSaver）。非常适合实验和本地工作流。需要单独安装。  

- **langgraph-checkpoint-postgres**：使用 Postgres 数据库的高级 checkpointer（PostgresSaver / AsyncPostgresSaver），用于 LangSmith。非常适合生产环境。需要单独安装。  

- **langchain-azure-cosmosdb**：使用 Azure Cosmos DB for NoSQL 的 LangGraph checkpointer 实现（CosmosDBSaverSync / CosmosDBSaver）。非常适合在 Azure 上用于生产环境。支持同步和异步操作，具有 Microsoft Entra ID 身份验证。需要单独安装。

### Checkpointer interface  

每个 checkpointer 都符合 BaseCheckpointSaver 接口，并实现以下方法：  

- **.put** - 存储 checkpoint 及其配置和 metadata。  

- **.put_writes** - 存储链接到 checkpoint 的中间写入（即 pending writes）。

- **.get_tuple** - 根据给定配置（thread_id 和 checkpoint_id）获取 checkpoint tuple。用于在 graph.get_state() 中填充 StateSnapshot。  

- **.list** - 列出与给定配置和过滤条件匹配的 checkpoint。用于在 graph.get_state_history() 中填充 state 历史记录。  

如果 checkpointer 用于异步图执行（即通过 .ainvoke、.astream、.abatch 执行图），则将使用上述方法的异步版本（.aput、.aput_writes、.aget_tuple、.alist）。 

要异步运行图，您可以使用 InMemorySaver，或 Sqlite/Postgres checkpointers 的异步版本——AsyncSqliteSaver / AsyncPostgresSaver。

### Serializer  

当 checkpointer 保存图 state 时，需要序列化 state 中的 channel 值。这是通过 serializer 对象完成的。  

langgraph_checkpoint 定义了实现序列化器的协议，并提供了默认实现（JsonPlusSerializer），可处理各种类型，包括 LangChain 和 LangGraph 原语、日期时间、枚举等。

#### Serialization with pickle  

默认的 serializer，JsonPlusSerializer，底层使用 ormsgpack 和 JSON，这并不适合所有类型的对象。  

如果您想对 msgpack 编码器当前不支持的对象（例如 Pandas dataframes）回退到 pickle，可以使用 JsonPlusSerializer 的 pickle_fallback 参数：

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

# ... Define the graph ...
graph.compile(
    checkpointer=InMemorySaver(serde=JsonPlusSerializer(pickle_fallback=True))
)
```

#### Encryption  

checkpointer 可以选择加密所有持久化的 state。要启用此功能，请将 EncryptedSerializer 的实例传递给任何 BaseCheckpointSaver 实现的 serde 参数。创建加密 serializer 最简单的方法是通过 from_pycryptodome_aes，它从 LANGGRAPH_AES_KEY 环境变量读取 AES 密钥（或接受 key 参数）：

```python
import sqlite3
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.sqlite import SqliteSaver

serde = EncryptedSerializer.from_pycryptodome_aes()  # reads LANGGRAPH_AES_KEY
checkpointer = SqliteSaver(sqlite3.connect("checkpoint.db"), serde=serde)
```

```python
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.postgres import PostgresSaver

serde = EncryptedSerializer.from_pycryptodome_aes()
checkpointer = PostgresSaver.from_conn_string("postgresql://...", serde=serde)
checkpointer.setup()
```

在 LangSmith 上运行时，只要存在 LANGGRAPH_AES_KEY，加密就会自动启用，因此您只需提供环境变量。其他加密方案可通过实现 CipherProtocol 并将其提供给 EncryptedSerializer 来使用。

## Build a custom checkpointer  

在构建过程中使用 conformance test suite 验证您的实现。它涵盖了全部五个基础方法及包括 delta channel 在内的扩展功能。在交付前于 CI 中运行。

本节涵盖从头开始为自定义存储后端实现 BaseCheckpointSaver。

### Overview  

LangGraph 的持久化层构建在两个存储抽象之上：

- **Checkpoints table** — 每个 superstep 一行；存储序列化的图 state（channel_values、channel_versions、versions_seen），并链接到其父 checkpoint。  

- **Writes table** — 每个 superstep 内每个节点输出一行；存储链接到 checkpoint 的 (task_id, channel, value) 元组。  

您的 checkpointer 管理这两个表。put 写入 checkpoint 行；put_writes 写入节点输出行；get_tuple 将两者读回为 CheckpointTuple。

### Base contract  

子类化 BaseCheckpointSaver 并实现这五个方法。所有方法都是必需的——缺失任一方法会在运行时引发 NotImplementedError。

```python
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

class MyCheckpointer(BaseCheckpointSaver):
    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        ...

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        ...

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        ...

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        ...
        yield  # make this an async generator

    async def adelete_thread(self, thread_id: str) -> None:
        ...
```

#### put / aput  

存储一个 checkpoint 行。返回带有存储的 checkpoint_id 的更新配置。  

关键要求：  

- 使用 self.serde.dumps_typed(checkpoint) 序列化 checkpoint——这将处理所有 LangGraph 原生类型，包括 delta channel 使用的 _DeltaSnapshot blob。  
- 完整存储 metadata——不要去除未知键。LangGraph 在次要版本中添加新的 metadata 字段（例如 delta channel 的 counters_since_delta_snapshot）；丢弃它们会在不知不觉中破坏功能。  
- 将 config["configurable"].get("checkpoint_id") 作为父 checkpoint ID 存储，以便 get_tuple 可以填充 parent_config。

```python
async def aput(self, config, checkpoint, metadata, new_versions):
    thread_id = config["configurable"]["thread_id"]
    checkpoint_ns = config["configurable"]["checkpoint_ns"]
    checkpoint_id = checkpoint["id"]
    parent_id = config["configurable"].get("checkpoint_id")

    type_, blob = self.serde.dumps_typed(checkpoint)
    serialized_metadata = self.serde.dumps_typed(metadata)

    await self.db.execute(
        "INSERT INTO checkpoints (...) VALUES (...)",
        thread_id, checkpoint_ns, checkpoint_id, parent_id,
        type_, blob, *serialized_metadata,
    )
    return {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint_id,
        }
    }
```

#### put_writes / aput_writes  

存储当前 superstep 内单个任务的节点输出行。这些行通过 (thread_id, checkpoint_ns, checkpoint_id) 链接到 checkpoint。

```python
async def aput_writes(self, config, writes, task_id, task_path=""):
    thread_id = config["configurable"]["thread_id"]
    checkpoint_ns = config["configurable"]["checkpoint_ns"]
    checkpoint_id = config["configurable"]["checkpoint_id"]

    rows = []
    for idx, (channel, value) in enumerate(writes):
        type_, blob = self.serde.dumps_typed(value)
        final_idx = WRITES_IDX_MAP.get(channel, idx)
        rows.append((thread_id, checkpoint_ns, checkpoint_id,
                      task_id, task_path, final_idx, channel, type_, blob))

    await self.db.executemany("INSERT INTO writes (...) VALUES (...)", rows)
```

从 langgraph.checkpoint.base 导入 WRITES_IDX_MAP。它将特殊 channel（__error__、__interrupt__ 等）映射到保留的负索引，以避免与常规 write 索引冲突。

#### get_tuple / aget_tuple  

检索 checkpoint。config 可能包含：  
- 无 checkpoint_id — 返回该线程+命名空间的最新 checkpoint。  
- 特定的 checkpoint_id — 返回该确切 checkpoint。  

两种路径都必须正确工作。特定 ID 路径用于 time travel，并且关键的是——在每次图调用时用于 delta channel state 重建。错误的特定 ID 查找会悄悄损坏 delta channel state。

```python
async def aget_tuple(self, config):
    thread_id = config["configurable"]["thread_id"]
    checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
    checkpoint_id = config["configurable"].get("checkpoint_id")

    if checkpoint_id:
        row = await self.db.fetchone(
            "SELECT * FROM checkpoints "
            "WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?",
            thread_id, checkpoint_ns, checkpoint_id,
        )
    else:
        row = await self.db.fetchone(
            "SELECT * FROM checkpoints "
            "WHERE thread_id=? AND checkpoint_ns=? "
            "ORDER BY checkpoint_id DESC LIMIT 1",
            thread_id, checkpoint_ns,
        )

    if row is None:
        return None

    writes = await self.db.fetchall(
        "SELECT task_id, channel, type, value FROM writes "
        "WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=? "
        "ORDER BY task_id, idx",
        thread_id, checkpoint_ns, row["checkpoint_id"],
    )
    pending_writes = [
        (w["task_id"], w["channel"], self.serde.loads_typed((w["type"], w["value"])))
        for w in writes
    ]

    checkpoint = self.serde.loads_typed((row["type"], row["blob"]))
    metadata = self.serde.loads_typed((row["metadata_type"], row["metadata"]))

    parent_config = None
    if row["parent_checkpoint_id"]:
        parent_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": row["parent_checkpoint_id"],
            }
        }

    return CheckpointTuple(
        config={
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": row["checkpoint_id"],
            }
        },
        checkpoint=checkpoint,
        metadata=metadata,
        parent_config=parent_config,
        pending_writes=pending_writes,
    )
```

行键/索引设计对于特定 ID 查找很重要。如果您的存储使用不包含 checkpoint_id 的时间排序键（例如反转的时间戳），则无法直接按 ID 读取行。您必须将 checkpoint_id 编码到行键中，或者构建二级索引。在每次查找时使用值过滤器进行扫描可以工作，但无法扩展。

#### list / alist  

返回一个线程的 checkpoint，从最新开始。遵守 before（仅返回比该配置的 checkpoint_id 更早的 checkpoint）和 limit。

#### delete_thread / adelete_thread  

删除一个线程的所有 checkpoint 和写入。checkpoint 行和 write 行都必须删除。

### Row key / index design  

您存储和索引 checkpoint 的方式直接影响正确性和性能。  
推荐模式（SQL）：

```sql
CREATE TABLE checkpoints (
    thread_id          TEXT NOT NULL,
    checkpoint_ns      TEXT NOT NULL DEFAULT '',
    checkpoint_id      TEXT NOT NULL,   -- ULID，按字典序排序，最新在最后
    parent_checkpoint_id TEXT,
    type               TEXT,
    checkpoint         BYTEA,
    metadata           JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE writes (
    thread_id     TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id       TEXT NOT NULL,
    task_path     TEXT NOT NULL DEFAULT '',
    idx           INTEGER NOT NULL,
    channel       TEXT NOT NULL,
    type          TEXT,
    value         BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, task_path, idx)
);
```

因为 checkpoint_id 是 ULID，它可以按字典序排序——值越大越新。“获取最新”使用 ORDER BY checkpoint_id DESC LIMIT 1；“按 ID 获取”是对主键的等值查找。

对于非 SQL 存储：同样的原则适用。无论您使用何种键方案，通过 (thread_id, checkpoint_ns, checkpoint_id) 直接查找必须是 O(1) 或接近 O(1)。避免采用只能通过扫描线程所有行来按 ID 查找 checkpoint 的设计。

### Serialization  

始终使用 self.serde（继承自 BaseCheckpointSaver，默认为 JsonPlusSerializer）进行 checkpoint、write 和 metadata 的序列化。不要直接对 metadata 使用 pickle——它能工作，但 JsonPlusSerializer 会生成人类可读的输出，并能更好地处理版本管理。  

JsonPlusSerializer 自动处理所有 LangGraph 原生类型：  

- _DeltaSnapshot — delta channel 使用的 sentinel blob（msgpack 扩展代码 7）  
- Pydantic v2 模型、dataclasses、numpy arrays、datetimes、枚举等。  

如果您编写自定义 serializer，请确保它能往返处理来自 langgraph.checkpoint.serde.types 的 _DeltaSnapshot。

### Extended capabilities  

这些方法是可选的，但可以解锁额外的 Agent Server 功能。如果您的存储后端可以有效支持它们，请实现它们。

| 方法 | 启用功能 |
|------|----------|
| adelete_for_runs | 回滚多任务策略 |
| acopy_thread | 高效线程分叉 |
| aprune | 线程历史修剪 |
| aget_delta_channel_history | 高效 delta channel state 重建 |

Agent Server 在启动时自动检测您的 checkpointer 实现了哪些功能，并激活相应的特性。

### Delta channel support  
 
DeltaChannel 是一种 reducer channel，仅在 checkpoint blob 中存储 sentinel (MISSING)，而不是完整的 channel 值。通过 reducer 重放祖先 write 来重建 state。这使得每个 step 的 checkpoint blob 为 O(1)，而不是像 messages 这样随时间累积的 channel 的 O(N)。

#### What the runtime needs  

当加载一个 channel_values 中缺少其 delta channel 的 checkpoint 时，LangGraph 调用 saver.get_delta_channel_history(config=config, channels=[...])。对于每个 channel，它返回：  

- writes — 祖先链中对该 channel 的所有写入，从最早开始，直到最近的 snapshot。  
- seed（可选）— 最近祖先处存储的 DeltaSnapshot blob（如果存在）；如果遍历到根都没有找到 snapshot，则不存在。  

然后运行时调用 channel.from_checkpoint(seed) 和 channel.replay_writes(writes) 来重建实时值。

#### Default implementation  

BaseCheckpointSaver 提供了一个默认的 get_delta_channel_history，可与任何正确的 get_tuple 实现配合使用：

```python
# Simplified from BaseCheckpointSaver
def get_delta_channel_history(self, *, config, channels):
    target = self.get_tuple(config)          # load the head checkpoint
    cursor = target.parent_config            # walk from its parent
    collected = {ch: [] for ch in channels}
    seed = {}
    remaining = set(channels)

    while cursor and remaining:
        tup = self.get_tuple(cursor)         # ← requires correct by-id lookup
        if tup is None:
            break
        for write in reversed(tup.pending_writes or []):
            if write[1] in remaining:
                collected[write[1]].append(write)
        for ch in list(remaining):
            if ch in tup.checkpoint["channel_values"]:
                seed[ch] = tup.checkpoint["channel_values"][ch]
                remaining.discard(ch)
        cursor = tup.parent_config

    return {
        ch: {"writes": list(reversed(collected[ch])), **({"seed": seed[ch]} if ch in seed else {})}
        for ch in channels
    }
```

关键依赖：get_tuple(cursor) 始终使用特定的 checkpoint_id（父级的 ID）调用。如果该查找返回 None，遍历将立即停止，每个 delta channel 都将重建为空——毫无征兆，没有错误。这就是为什么 get_tuple 中的特定 ID 路径必须正确的原因。

#### Performance override  

默认遍历每个祖先 checkpoint 调用一次 get_tuple。对于具有良好查询支持的后端，可以覆盖 get_delta_channel_history（及其异步版本），通过两个查询检索祖先链和写入：

```python
async def aget_delta_channel_history(self, *, config, channels):
    if not channels:
        return {}

    thread_id = config["configurable"]["thread_id"]
    checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
    checkpoint_id = config["configurable"]["checkpoint_id"]

    # Stage 1: stream ancestors newest-first until every channel has a seed
    ancestors = await self.db.fetchall(
        "SELECT checkpoint_id, parent_checkpoint_id, type, checkpoint "
        "FROM checkpoints "
        "WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id < ? "
        "ORDER BY checkpoint_id DESC",
        thread_id, checkpoint_ns, checkpoint_id,
    )

    chain_by_ch: dict[str, list[str]] = {ch: [] for ch in channels}
    seed_by_ch: dict[str, Any] = {}
    remaining = set(channels)
    cur_id = config["configurable"]["checkpoint_id"]

    for row in ancestors:
        if not remaining:
            break
        parent_id = row["parent_checkpoint_id"]
        ckpt = self.serde.loads_typed((row["type"], row["checkpoint"]))
        cv = ckpt.get("channel_values") or {}
        for ch in list(remaining):
            chain_by_ch[ch].append(row["checkpoint_id"])
            if ch in cv:
                seed_by_ch[ch] = cv[ch]
                remaining.discard(ch)
        cur_id = parent_id

    # Stage 2: fetch writes for each channel's ancestor chain in one query
    result: dict[str, DeltaChannelHistory] = {}
    for ch in channels:
        chain = chain_by_ch[ch]
        if not chain:
            entry: DeltaChannelHistory = {"writes": []}
            if ch in seed_by_ch:
                entry["seed"] = seed_by_ch[ch]
            result[ch] = entry
            continue

        write_rows = await self.db.fetchall(
            f"SELECT checkpoint_id, task_id, idx, type, value FROM writes "
            f"WHERE thread_id=? AND checkpoint_ns=? AND channel=? "
            f"AND checkpoint_id IN ({','.join('?' * len(chain))})"
            f"ORDER BY checkpoint_id, task_id, idx",
            thread_id, checkpoint_ns, ch, *chain,
        )
        writes_by_cid: dict[str, list[PendingWrite]] = {}
        for row in write_rows:
            cid = row["checkpoint_id"]
            value = self.serde.loads_typed((row["type"], row["value"]))
            writes_by_cid.setdefault(cid, []).append((row["task_id"], ch, value))

        # chain is newest-first; iterate oldest-first to get correct replay order
        collected: list[PendingWrite] = []
        for cid in reversed(chain):
            collected.extend(writes_by_cid.get(cid, []))

        entry = {"writes": collected}
        if ch in seed_by_ch:
            entry["seed"] = seed_by_ch[ch]
        result[ch] = entry

    return result
```

#### Pruning with delta channels  

DeltaChannel state 不是在一个 checkpoint 中自包含的——它依赖于回溯到最近 DeltaSnapshot 的祖先 write 链。如果您实现了 prune 或 delete_for_runs，则不得删除幸存 checkpoint 的 delta channel 所依赖的 write 行。  

安全选项：  

- 在修剪之前遍历——对于您打算保留的每个 checkpoint，遍历其祖先链，并将直到最近 _DeltaSnapshot 的所有 write 行标记为不可删除。  
- 在修剪之前强制创建 snapshot——在要保留的 checkpoint 上重写 channel_values[ch] = _DeltaSnapshot(reconstructed_value)，然后可以自由删除祖先。  
- 跳过 delta-channel 线程的修剪——如果尚不需要修剪，这是最安全的短期选项。

#### Copy thread with delta channels  

在实现 copy_thread 时，复制完整的祖先链——而不仅仅是头 checkpoint。目标线程必须具有每个 delta channel 回溯到至少一个 _DeltaSnapshot 的 write 行，否则这些 channel 在复制后将重建为空。

### Testing with the conformance suite  

langgraph-checkpoint-conformance 根据完整合约验证您的实现，包括 delta channel history：

```bash
pip install langgraph-checkpoint-conformance
```

```python
import asyncio
from langgraph.checkpoint.conformance import checkpointer_test, validate

@checkpointer_test(name="MyCheckpointer")
async def my_checkpointer():
    async with MyCheckpointer.create() as saver:
        yield saver

async def main():
    report = await validate(my_checkpointer)
    report.print_report()
    # Fails the process if any base capability is missing or broken
    if not report.passed_all_base():
        raise RuntimeError("Checkpointer failed conformance suite")

asyncio.run(main())
```

该套件会自动检测您的 checkpointer 实现了哪些扩展功能（包括 aget_delta_channel_history），并针对每一项运行相关测试。在交付前，请将其作为 CI 的一部分运行。