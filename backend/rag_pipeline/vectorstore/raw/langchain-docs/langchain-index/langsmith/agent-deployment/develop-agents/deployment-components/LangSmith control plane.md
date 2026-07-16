# LangSmith control plane

*控制平面*是 LangSmith 中管理部署的部分。它包括 control plane UI（用户在此创建和更新 Agent Server）以及 control plane API（为 UI 提供支持并提供编程式访问）。

当您通过 control plane 进行更新时，该更新将存储在 control plane 状态中。数据平面的“监听器”通过调用 control plane API 来轮询这些更新。control plane 从不直接连接到数据平面。

## Control plane UI

通过 control plane UI，您可以：

* 查看未完成部署的列表。
* 查看单个部署的详情。
* 创建新部署。
* 更新部署。
* 更新部署的环境变量。
* 查看部署的构建和服务器日志。
* 查看部署的指标，例如 CPU 和内存使用情况。
* 删除部署。

Control plane UI 嵌入在 LangSmith 中。

## Control plane API

本节描述 control plane API 的数据模型。该 API 用于创建、更新和删除部署。更多详情请参阅 control plane API 参考。

### Integrations

**Integration** 是 `git` 仓库提供商（例如 GitHub）的抽象。它包含了与 `git` 仓库连接并从中部署所需的所有元数据。

### Deployments

**Deployment** 是一个 Agent Server 的实例。单个 deployment 可以有许多 **revision**。

### Revisions

**Revision** 是 deployment 的一次迭代。当创建新 deployment 时，会自动创建一个初始 revision。要部署代码更改或更新 deployment 的密钥，必须创建新的 revision。

### Listeners

**Listener** 是“监听器”应用程序的一个实例。listener 包含关于应用程序的元数据（例如版本）以及关于它可以部署到的计算基础设施的元数据（例如 Kubernetes 命名空间）。

listener 数据模型仅适用于自托管部署。

## Control plane 特性

本节描述 control plane 的各种特性。

### 部署类型

为简化起见，control plane 提供两种具有不同资源分配的部署类型：`Development` 和 `Production`。

| **部署类型** | **CPU/内存**      | **扩缩容**       | **数据库**                                                                     |
| ------------------- | --------------- | ----------------- | -------------------------------------------------------------------------------- |
| Development         | 1 CPU, 1 GB RAM | 最多 1 个副本 | 10 GB 磁盘，无备份                                                           |
| Production          | 2 CPU, 2 GB RAM | 最多 10 个副本 | 自动扩缩磁盘，自动备份，高可用（多可用区配置） |

CPU 和内存资源按副本计算。

**不可变的部署类型**
  一旦 deployment 创建完成，部署类型无法更改。

**自托管部署**
  自托管部署的资源可以完全自定义。部署类型仅适用于 Cloud 部署。

#### Production

`Production` 类型部署适用于“生产”工作负载。例如，为面向客户的關鍵路径应用选择 `Production`。

`Production` 类型部署的资源可以根据用例和容量限制，按具体情况手动增加。如需申请增加资源，请通过 support.langchain.com 联系支持团队。

#### Development

`Development` 类型部署适用于开发和测试。例如，为内部测试环境选择 `Development`。`Development` 类型部署不适用于“生产”工作负载。

**可抢占的计算基础设施**
  `Development` 类型部署（API 服务器、队列服务器和数据库）是在可抢占的计算基础设施上提供的。这意味着计算基础设施**可能随时终止，恕不另行通知**。这可能导致间歇性的...

  * Redis 连接超时/错误
  * Postgres 连接超时/错误
  * 后台运行失败或重试

  这种行为是预期的。可抢占的计算基础设施**显著降低了提供 `Development` 类型部署的成本**。Agent Server 在设计上具有容错性。实现将自动尝试从 Redis/Postgres 连接错误中恢复，并重试失败的后台运行。

  `Production` 类型部署在持久计算基础设施上提供，而非可抢占计算基础设施。

`Development` 类型部署的数据库磁盘大小可以根据用例和容量限制，按具体情况手动增加。对于大多数用例，应配置 TTL 来管理磁盘使用。如需申请增加资源，请通过 support.langchain.com 联系支持团队。

### 数据库预配

control plane 和数据平面“监听器”应用程序协同工作，为每个 deployment 自动创建一个 Postgres 数据库。该数据库作为 deployment 的持久化层。

在实现 LangGraph 应用时，开发者不需要配置 checkpointer。相反，系统会为 graph 自动配置一个 checkpointer。为 graph 配置的任何 checkpointer 都将被自动配置的那个所替换。

无法直接访问数据库。对数据库的所有访问都通过 Agent Server 进行。

在 deployment 本身被删除之前，数据库永远不会被删除。

对于自托管部署，可以配置自定义 Postgres 实例。

### 异步部署

deployment 和 revision 的基础设施是异步预配和部署的。它们不会在提交后立即部署。目前，部署可能需要几分钟的时间。

* 当创建新 deployment 时，会为该 deployment 创建一个新数据库。数据库创建是一次性步骤。此步骤会导致 deployment 的初始 revision 部署时间较长。
* 当为 deployment 创建后续 revision 时，没有数据库创建步骤。后续 revision 的部署时间比初始 revision 的部署时间快得多。
* 每个 revision 的部署过程都包含一个构建步骤，该步骤可能需要几分钟。

control plane 和数据平面“监听器”应用程序协同实现异步部署。

### 监控

deployment 就绪后，control plane 会监控 deployment 并记录各种指标，例如：

* deployment 的 CPU 和内存使用情况。
* 容器重启次数。
* 副本数量（随自动扩缩容而增加）。
* PostgreSQL CPU、内存使用情况和磁盘使用情况。
* Agent Server 队列中待处理/活跃的运行数量。
* Agent Server API 成功响应计数、错误响应计数和延迟。

这些指标以图表形式显示在 Control Plane UI 中。

### LangSmith 集成

为每个 deployment 自动创建一个 LangSmith 追踪项目。追踪项目与 deployment 同名。创建 deployment 时，不需要指定 `LANGCHAIN_TRACING` 和 `LANGSMITH_API_KEY`/`LANGCHAIN_API_KEY` 环境变量；它们由 control plane 自动设置。

当 deployment 被删除时，追踪数据和追踪项目不会被删除。