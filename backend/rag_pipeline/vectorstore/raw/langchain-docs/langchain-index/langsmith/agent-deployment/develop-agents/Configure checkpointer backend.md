# 配置 checkpointer 后端

> 配置 Agent Server 使用 PostgreSQL、MongoDB 或自定义实现来存储 checkpoint。

Agent Server 使用 checkpointer 后端持久化 graph 状态。默认情况下，LangSmith 将 checkpoint 与其它服务器数据一起存储在 PostgreSQL 中。您可以切换到 MongoDB 或提供自定义实现。

无论使用哪种 checkpointer 后端，LangSmith 始终需要 PostgreSQL 来存储 threads、runs、assistants、crons 以及 memory store。checkpointer 后端仅控制 checkpoint 数据的存储位置。

## 可用后端

| Backend   | 存储          | 配置方式                                                     | 适用场景                                                              |
| --------- | ------------- | ------------------------------------------------------------- | --------------------------------------------------------------------- |
| `default` | PostgreSQL    | 无需配置（内置）                                              | 标准部署                                                              |
| `mongo`   | MongoDB       | `langgraph.json` 或 `LS_DEFAULT_CHECKPOINTER_BACKEND` 环境变量 | 已有 MongoDB 基础设施的团队                                            |
| `custom`  | 用户自定义    | `langgraph.json`                                              | 自定义存储后端（参见 custom checkpointer）                              |

## 默认（PostgreSQL）

PostgreSQL 是默认的 checkpointer 后端，无需任何配置。要使用自定义 PostgreSQL 实例，请设置 `POSTGRES_URI_CUSTOM` 环境变量。

## 设置 MongoDB checkpointing

需要 Agent Server v0.7.64 或更高版本。

### 前提条件

* 一个 MongoDB **replica set**（不支持独立的 `mongod`）。可以是自管理的 replica set、`mongos` 路由器，或 MongoDB Atlas 等托管服务。
* 一个包含数据库名称的连接 URI（例如，路径中包含 `/langgraph`）。

### 选择后端

使用以下方法之一将后端设置为 `"mongo"`：

**在 `langgraph.json` 中**（应用级别——与应用代码打包在一起）：

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./agent.py:graph"
  },
  "checkpointer": {
    "backend": "mongo",
    "ttl": {
      "strategy": "delete",
      "default_ttl": 43200,
      "sweep_interval_minutes": 10
    }
  }
}
```

**通过环境变量**（平台级别——适用于管理 standalone 部署的运维人员）：

```shell
LS_DEFAULT_CHECKPOINTER_BACKEND=mongo
```

该环境变量为没有在 `langgraph.json` 中指定后端的 Agent Server 设置默认后端。如果 `langgraph.json` 中包含 `backend` 值，则优先使用该值。

### 提供 MongoDB URI

在部署时设置 `LS_MONGODB_URI` 环境变量：

```shell
LS_MONGODB_URI="mongodb://user:password@host:27017/langgraph?replicaSet=rs0"
```

### 连接 URI 要求

URI 必须满足：

* 指向 replica set 成员或 `mongos` 路由器
* 在路径中包含目标数据库名称

有效示例：

```
mongodb://user:password@host:27017/langgraph?replicaSet=rs0
mongodb://host1:27017,host2:27017,host3:27017/mydb?replicaSet=prod-rs
mongodb+srv://user:password@cluster.example.net/langgraph
```

### 按环境部署

langgraph-cloud Helm chart (v0.2.6+) 内置了 MongoDB 支持。在您的 values 文件中启用：

**捆绑 MongoDB**（用于开发和测试）：

```yaml
mongo:
  enabled: true
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
  persistence:
    size: 8Gi
```

该 chart 会部署一个单节点 MongoDB replica set，并自动配置服务器使用它。

**外部 MongoDB**（用于生产）：

```yaml
mongo:
  enabled: true
  external:
    enabled: true
    connectionUrl: "mongodb://user:password@mongo.example.net:27017/langgraph?replicaSet=rs0"
```

或者引用已有的 Kubernetes secret：

```yaml
mongo:
  enabled: true
  external:
    enabled: true
    existingSecretName: "my-mongo-secret"
```

该 secret 必须包含一个 `mongodb_connection_url` 键。

如果您的 `langgraph.json` 已将 `backend` 设置为 `"mongo"`，则只需提供 URI。否则，请同时设置两个环境变量：

```shell
docker run \
    --env-file .env \
    -p 8123:8000 \
    -e REDIS_URI="redis://redis:6379" \
    -e DATABASE_URI="postgres://postgres:postgres@postgres:5432/postgres" \
    -e LS_DEFAULT_CHECKPOINTER_BACKEND=mongo \
    -e LS_MONGODB_URI="mongodb://mongo:27017/langgraph?replicaSet=rs0" \
    -e LANGSMITH_API_KEY="..." \
    my-image
```

有关完整的 Docker Compose 示例（含 MongoDB），请参阅 standalone server 指南。

在您的 `langgraph.json` 中将 `backend` 设置为 `"mongo"`，然后在 LangSmith UI 的部署设置中将 `LS_MONGODB_URI` 添加为环境变量。

您的 MongoDB 实例必须能够从 Cloud 数据平面访问。MongoDB Atlas 等托管服务非常适合此场景。

注意：PostgreSQL 仍然会被自动预配，用于存储非 checkpoint 数据。

## 自定义 checkpointer

要使用 PostgreSQL 或 MongoDB 之外的存储后端，请实现自定义的 `BaseCheckpointSaver`。详情请参阅“添加自定义 checkpointer”。

## 相关内容

* 为 checkpoint 和 store item 配置 TTL 过期策略
* LangGraph 中的持久化概念
* 数据平面架构
* 环境变量参考