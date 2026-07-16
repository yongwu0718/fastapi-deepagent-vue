# 如何向应用添加 TTL

**前提条件**
  本指南假定您熟悉 LangSmith、Persistence 和跨线程持久化（Cross-thread persistence）概念。

LangSmith 会持久化 checkpoint（线程状态）和跨线程记忆（store items）。您可以在 `langgraph.json` 中配置生存时间（Time-to-Live, TTL）策略来自动管理这些数据的生命周期，防止无限积累。

## 配置线程和 checkpoint TTL

Checkpoint 捕获会话线程的状态。设置 TTL 可确保旧的 checkpoint 和线程元数据被自动删除。

在您的 `langgraph.json` 文件中添加 `checkpointer.ttl` 配置：

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./agent.py:graph"
  },
  "checkpointer": {
    "ttl": {
      "strategy": "delete",
      "sweep_interval_minutes": 60,
      "default_ttl": 43200
    }
  }
}
```

* `strategy`：指定过期时采取的操作。
  * `"delete"`：当 TTL 过期时，删除整个线程及其所有关联的 run 和 checkpoint 数据。
  * `"keep_latest"`：保留线程和最新的 checkpoint，但删除后续运行不再需要的旧 checkpoint 数据。
* `sweep_interval_minutes`：定义系统检查过期 checkpoint 的频率（单位：分钟）。
* `default_ttl`：设置线程（以及相应 checkpoint）的默认生命周期（单位：分钟，例如 43200 分钟 = 30 天）。仅适用于此配置部署后创建的 checkpoint；现有的 checkpoint/线程不会改变。要清除旧数据，请显式删除。

## 配置 store item TTL

Store items 允许跨线程数据持久化。为 store items 配置 TTL 有助于通过移除过期数据来管理内存。

在您的 `langgraph.json` 文件中添加 `store.ttl` 配置：

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./agent.py:graph"
  },
  "store": {
    "ttl": {
      "refresh_on_read": true,
      "sweep_interval_minutes": 120,
      "default_ttl": 10080
    }
  }
}
```

* `refresh_on_read`：（可选，默认为 `true`）如果为 `true`，通过 `get` 或 `search` 访问某条目会重置其过期计时器。如果为 `false`，TTL 仅在 `put` 时刷新。
* `sweep_interval_minutes`：（可选）定义系统检查过期条目的频率（单位：分钟）。如果省略，则不进行扫描。
* `default_ttl`：（可选）设置 store items 的默认生命周期（单位：分钟，例如 10080 分钟 = 7 天）。仅适用于此配置部署后创建的条目；现有条目不会改变。如果您需要清除旧条目，请手动删除。如果省略，默认情况下条目不会过期。

## 组合 TTL 配置

您可以在同一个 `langgraph.json` 文件中为 checkpoint 和 store items 分别配置 TTL，为每种数据类型设置不同的策略。示例如下：

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./agent.py:graph"
  },
  "checkpointer": {
    "ttl": {
      "strategy": "delete",
      "sweep_interval_minutes": 60,
      "default_ttl": 43200
    }
  },
  "store": {
    "ttl": {
      "refresh_on_read": true,
      "sweep_interval_minutes": 120,
      "default_ttl": 10080
    }
  }
}
```

## 配置 per-thread TTL

您可以按线程应用 TTL 配置。

```python
thread = await client.threads.create(
    ttl={
        "strategy": "delete",
        "ttl": 43200  # 30 days in minutes
    }
)
```

线程级别的 TTL 也会删除所有关联的 checkpoint。因此，您可以设置线程级别的 TTL，而无需为 checkpoint 单独设置 TTL。

## 运行时覆盖

在 SDK 方法调用（如 `get`、`put` 和 `search`）中提供特定的 TTL 值，可以在运行时覆盖来自 `langgraph.json` 的默认 `store.ttl` 设置。

## 部署流程

在 `langgraph.json` 中配置 TTL 后，请部署或重启您的 LangGraph 应用以使更改生效。本地开发请使用 `langgraph dev`，Docker 部署请使用 `langgraph up`。

有关其他可配置选项的详细信息，请参阅 LangGraph CLI 参考页面。