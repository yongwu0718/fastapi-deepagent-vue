# 为扩缩容配置 LangSmith Agent Server

LangSmith Agent Server 的默认配置旨在处理各种不同工作负载下的大量读写负载。通过遵循下述最佳实践，您可以调整 Agent Server 以使其在特定工作负载下达到最优性能。本页介绍 Agent Server 的扩缩容考虑因素，并提供示例帮助您配置部署。

如果您还不熟悉 API 服务器和队列工作进程在容器层面如何运作，请先阅读运行时架构概述。

有关一些自托管的示例配置，请参阅“为扩缩容配置 Agent Server 示例”部分。

## 应对写入负载的扩缩容

写入负载主要由以下因素驱动：

* 创建新的 run
* 在 run 执行期间创建新的 checkpoint
* 写入长期记忆
* 创建新的 thread
* 创建新的 assistant
* 删除 run、checkpoint、thread、assistant 和 cron job

以下组件主要负责处理写入负载：

* API server：处理初始请求并将数据持久化到数据库。
* Queue worker：处理 run 的执行。
* Redis：处理关于进行中 run 的临时数据存储。
* Postgres：处理所有数据的存储，包括 run、thread、assistant、cron job、checkpoint 和长期记忆。

### 扩缩容写入路径的最佳实践

#### 根据 assistant 特征更改 `N_JOBS_PER_WORKER`

`N_JOBS_PER_WORKER` 的默认值为 10。您可以根据 assistant 的特征更改该值，以调整单个 queue worker 一次可以执行的最大 run 数量。

更改 `N_JOBS_PER_WORKER` 的一些通用指南：

* 如果您的 assistant 是 CPU 密集型，默认值 10 可能就足够了。如果您发现 queue worker 的 CPU 使用率过高或 run 执行延迟，可以降低 `N_JOBS_PER_WORKER`。
* 如果您的 assistant 是 I/O 密集型，请增加 `N_JOBS_PER_WORKER` 以让每个 worker 处理更多并发 run。

`N_JOBS_PER_WORKER` 没有上限。然而，queue worker 在获取新 run 时是贪婪的，这意味着它们会尝试拾取尽可能多的 run（数量不超过其可用作业数）并立即开始执行。在流量突发的环境中，将 `N_JOBS_PER_WORKER` 设置过高可能导致 worker 利用不均和 run 执行时间增加。

#### 避免同步阻塞操作

在代码中避免同步阻塞操作，优先使用异步操作。长时间的同步操作可能会阻塞主事件循环，导致请求和 run 执行时间延长以及潜在的超时。

例如，考虑一个需要休眠 1 秒的应用。不要使用像这样的同步代码：

```python
import time

def my_function():
    time.sleep(1)
```

而应优先使用异步代码：

```python
import asyncio

async def my_function():
    await asyncio.sleep(1)
```

如果 assistant 需要同步阻塞操作，请在 `asyncio.to_thread()` 或等效机制中运行它们。

#### 最小化冗余 checkpointing

通过将 `durability` 设置为确保数据持久性的最小值来最小化冗余 checkpointing。

默认的持久化模式是 `"async"`，意味着 checkpoint 在每个步骤后异步写入。如果 assistant 只需要持久化 run 的最终状态，可以将 `durability` 设置为 `"exit"`，仅存储 run 的最终状态。这可以在创建 run 时设置：

```python
from langgraph_sdk import get_client

client = get_client(url=)
thread = await client.threads.create()
run = await client.runs.create(
    thread_id=thread["thread_id"],
    assistant_id="agent",
    durability="exit"
)
```

#### 自托管

这些设置仅对自托管部署必需。默认情况下，云部署已启用这些最佳实践。

##### 启用 queue worker

默认情况下，API server 自己管理队列，不使用 queue worker。您可以通过将 `queue.enabled` 配置设置为 `true` 来启用 queue worker。

```yaml
queue:
  enabled: true
```

这将允许 API server 将队列管理卸载给 queue worker，显著降低 API server 的负载，使其能够专注于处理请求。

#### 提供与预期吞吐量匹配的作业数

并行执行的 run 越多，处理负载所需的作业就越多。有两个主要参数用于扩缩可用作业：

* `number_of_queue_workers`：预配的 queue worker 数量。
* `N_JOBS_PER_WORKER`：单个 queue worker 一次可执行的 run 数量。默认为 10。

可用作业数可通过以下公式计算：

```
available_jobs = number_of_queue_workers * N_JOBS_PER_WORKER
```

吞吐量则是指可用作业每秒可执行的 run 数量：

```
throughput_per_second = available_jobs / average_run_execution_time_seconds
```

因此，为支持预期的稳态吞吐量，您应预配的最小 queue worker 数量为：

```
number_of_queue_workers = throughput_per_second * average_run_execution_time_seconds / N_JOBS_PER_WORKER
```

##### 为突发性工作负载配置自动扩缩容

自动扩缩容默认是禁用的，但对于突发性工作负载应进行配置。使用与上一节相同的计算方法，您可以根据最大预期吞吐量确定允许自动扩缩器扩展到的最大 queue worker 数量。

## 应对读取负载的扩缩容

读取负载主要由以下因素驱动：

* 获取 run 的结果
* 获取 thread 的状态
* 搜索 run、thread、cron job 和 assistant
* 检索 checkpoint 和长期记忆

以下组件主要负责处理读取负载：

* API server：处理请求并直接从数据库检索数据。
* Postgres：处理所有数据的存储，包括 run、thread、assistant、cron job、checkpoint 和长期记忆。
* Redis：处理关于进行中 run 的临时数据存储，包括从 queue worker 到 API server 的流式消息。

### 扩缩容读取路径的最佳实践

#### 使用过滤减少每次请求返回的资源数量

Agent Server 为每种资源类型提供了搜索 API。这些 API 默认实现分页并提供多种过滤选项。使用过滤来减少每次请求返回的资源数量，从而提高性能。

#### 设置 TTL 以自动删除旧数据

在 thread 上设置 TTL 以自动清理旧数据。当关联的 thread 被删除时，run 和 checkpoint 会自动被删除。

#### 避免轮询，使用 `/join` 来监控 run 的状态

避免轮询 run 的状态，使用 `/join` API 端点。该方法在 run 完成后返回其最终状态。

如果您需要实时监控 run 的输出，请使用 `/stream` API 端点。该方法会流式传输 run 的输出，包括 run 的最终状态。

#### 自托管

这些设置仅对自托管部署必需。默认情况下，云部署已启用这些最佳实践。

##### 为突发性工作负载配置自动扩缩容

自动扩缩容默认是禁用的，但对于突发性工作负载应进行配置。您可以根据最大预期吞吐量确定允许自动扩缩器扩展到的最大 API server 数量。云部署的默认最大 API server 数量为 10。

## 自托管 Agent Server 配置示例

确切的最佳配置取决于您的应用复杂性、请求模式和数据需求。请结合前面各节的信息以及您的具体使用情况，使用以下示例来更新您的部署配置。如有任何疑问，请通过 support.langchain.com 联系支持团队。

下表概览了针对不同负载模式（读请求/秒 / 写请求/秒）和标准 assistant 特征（平均 run 执行时间 1 秒，适中的 CPU 和内存使用）的各种 LangSmith Agent Server 配置：

|                                                                                                                          | **低 / 低** | **低 / 高** | **高 / 低** | **中 / 中** | **高 / 高** |
| :----------------------------------------------------------------------------------------------------------------------- | :------------------------------------- | :--------------------------------------- | :--------------------------------------- | :--------------------------------------------- | :------------------------------------- |
| 写请求/秒 | 5                                      | 5                                        | 500                                      | 50                                             | 500                                    |
| 读请求/秒   | 5                                      | 500                                      | 5                                        | 50                                             | 500                                    |
| **API servers**(1 CPU, 2Gi per server)                                                                             | 1 (默认)                            | 6                                        | 10                                       | 3                                              | 15                                     |
| **Queue workers**(1 CPU, 2Gi per worker)                                                                           | 1 (默认)                            | 10                                       | 1 (默认)                              | 5                                              | 10                                     |
| **`N_JOBS_PER_WORKER`**                                                                                                  | 10 (默认)                           | 50                                       | 10                                       | 10                                             | 50                                     |
| **Redis resources**                                                                                                      | 2 Gi (默认)                         | 2 Gi (默认)                           | 2 Gi (默认)                           | 2 Gi (默认)                                 | 2 Gi (默认)                         |
| **Postgres resources**                                                                                                   | 2 CPU, 8 Gi (默认)              | 4 CPU, 16 Gi 内存                  | 4 CPU, 16 Gi                         | 4 CPU, 16 Gi 内存                        | 8 CPU, 32 Gi 内存                |

以下示例配置可实现上述每种设置。负载级别定义为：

* 低：约 5 请求/秒
* 中：约 50 请求/秒
* 高：约 500 请求/秒

### 低读、低写

默认的 LangSmith Deployment 配置即可处理此负载，无需自定义资源配置。

### 低读、高写

您的部署有大量写请求（500 次/秒），但读请求相对较少（5 次/秒）。

针对这种情况，我们推荐如下配置：

```yaml
# 低读、高写示例配置（5 读/500 写请求/秒）
api:
  replicas: 6
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

queue:
  replicas: 10
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

config:
  numberOfJobsPerWorker: 50

redis:
  resources:
    requests:
      memory: "2Gi"
    limits:
      memory: "2Gi"

postgres:
  resources:
    requests:
      cpu: "4"
      memory: "16Gi"
    limits:
      cpu: "8"
      memory: "32Gi"
```

### 高读、低写

您的部署有大量读请求（500 次/秒），但写请求相对较少（5 次/秒）。

针对这种情况，我们推荐如下配置：

```yaml
# 高读、低写示例配置（500 读/5 写请求/秒）
api:
  replicas: 10
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

queue:
  replicas: 1  # 默认，最小写负载
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

redis:
  resources:
    requests:
      memory: "2Gi"
    limits:
      memory: "2Gi"

postgres:
  resources:
    requests:
      cpu: "4"
      memory: "16Gi"
    limits:
      cpu: "8"
      memory: "32Gi"
  # 对于高读场景可考虑读副本
  readReplicas: 2
```

### 中读、中写

这是一个均衡的配置，应能处理中等水平的读写负载（50 读/50 写请求/秒）。

针对这种情况，我们推荐如下配置：

```yaml
# 中读、中写示例配置（50 读/50 写请求/秒）
api:
  replicas: 3
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

queue:
  replicas: 5
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

redis:
  resources:
    requests:
      memory: "2Gi"
    limits:
      memory: "2Gi"

postgres:
  resources:
    requests:
      cpu: "4"
      memory: "16Gi"
    limits:
      cpu: "8"
      memory: "32Gi"
```

### 高读、高写

您的读写请求量都很高（500 读/500 写请求/秒）。

针对这种情况，我们推荐如下配置：

```yaml
# 高读、高写示例配置（500 读/500 写请求/秒）
api:
  replicas: 15
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

queue:
  replicas: 10
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"

config:
  numberOfJobsPerWorker: 50

redis:
  resources:
    requests:
      memory: "2Gi"
    limits:
      memory: "2Gi"

postgres:
  resources:
    requests:
      cpu: "8"
      memory: "32Gi"
    limits:
      cpu: "16"
      memory: "64Gi"
```

### 自动扩缩容

如果您的部署遇到流量突发，可以启用自动扩缩容，以动态调整 API server 和 queue worker 的数量来处理负载。

以下是一个针对高读、高写场景的自动扩缩容示例配置：

```yaml
api:
  autoscaling:
    enabled: true
    minReplicas: 15
    maxReplicas: 25

queue:
  autoscaling:
    enabled: true
    minReplicas: 10
    maxReplicas: 20
```

确保您的部署环境拥有足够的资源来扩展到推荐的大小。监控您的应用和基础设施以确保最佳性能。考虑实施监控和告警来追踪资源使用情况和应用性能。