# Configure logging drivers（配置日志驱动程序）

Docker 包含了多种日志记录机制，帮助您从运行中的容器和服务获取信息。这些机制被称为 logging drivers（日志驱动程序）。每个 Docker daemon 都有一个默认的 logging driver，每个容器默认会使用该 driver，除非您将其配置为使用不同的 logging driver（或简称为 log driver）。

默认情况下，Docker 使用 [`json-file` logging driver](/engine/logging/configure/drivers/json-file/)，它在内部将容器日志以 JSON 格式缓存。除了使用 Docker 自带的 logging drivers 之外，您还可以实现并使用 [logging driver plugins（日志驱动程序插件）](/engine/logging/configure/plugins/)。

> [!TIP]
>
> 使用 `local` logging driver 可以防止磁盘空间耗尽。默认情况下，日志不会进行轮转（log-rotation）。因此，对于产生大量输出的容器，默认的 [`json-file` logging driver](/engine/logging/configure/drivers/json-file/) 存储的日志文件可能会占用大量磁盘空间，从而导致磁盘空间耗尽。
>
> Docker 保留了不进行日志轮转的 json-file logging driver 作为默认选项，以保持与旧版本 Docker 的向后兼容性，以及用于 Docker 作为 Kubernetes 运行时的场景。
>
> 对于其他场景，建议使用 `local` logging driver，因为它默认执行日志轮转，并使用更高效的文件格式。请参阅下面的 [配置默认 logging driver](#configure-the-default-logging-driver) 部分，了解如何将 `local` logging driver 配置为默认选项；有关 `local` logging driver 的更多详细信息，请参阅 [local file logging driver（本地文件日志驱动程序）](/engine/logging/configure/drivers/local/) 页面。

## Configure the default logging driver（配置默认的 logging driver）

要将 Docker daemon 的默认 logging driver 配置为特定的 driver，请在 `daemon.json` 配置文件中将 `log-driver` 的值设置为该 logging driver 的名称。有关详细信息，请参阅 [`dockerd` 参考手册](/reference/cli/dockerd/#daemon-configuration-file)中的 “daemon configuration file” 部分。

默认的 logging driver 是 `json-file`。下面的示例将默认 logging driver 设置为 [`local` log driver](/engine/logging/configure/drivers/local/)：

```json
{
  "log-driver": "local"
}
```

如果该 logging driver 有可配置的选项，您可以在 `daemon.json` 文件中以 JSON 对象的形式进行设置，键名为 `log-opts`。下面的示例为 `json-file` logging driver 设置了四个可配置选项：

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3",
    "labels": "production_status",
    "env": "os,customer"
  }
}
```

重新启动 Docker，使更改对新创建的容器生效。已有的容器不会自动使用新的日志配置。

> [!NOTE]
>
> `daemon.json` 配置文件中的 `log-opts` 配置选项必须以字符串形式提供。因此，布尔值和数值（如上例中的 `max-file` 的值）必须用引号（`"`）括起来。

如果您未指定 logging driver，默认使用 `json-file`。要查看 Docker daemon 当前的默认 logging driver，请运行 `docker info` 并搜索 `Logging Driver`。您可以在 Linux、macOS 或 Windows 的 PowerShell 中使用以下命令：

```console
$ docker info --format '{{.LoggingDriver}}'

json-file
```

> [!NOTE]
>
> 在 daemon 配置中更改默认的 logging driver 或 logging driver 选项，只会影响配置更改后创建的容器。已有的容器会保留其创建时使用的 logging driver 选项。要更新容器的 logging driver，必须使用所需的选项重新创建该容器。
> 请参阅下面的 [为容器配置 logging driver](#configure-the-logging-driver-for-a-container) 部分，了解如何查找容器的 logging-driver 配置。

## Configure the logging driver for a container（为容器配置 logging driver）

当您启动容器时，可以使用 `--log-driver` 标志将其配置为使用与 Docker daemon 默认不同的 logging driver。如果该 logging driver 有可配置选项，您可以使用一个或多个 `--log-opt <NAME>=<VALUE>` 标志来设置这些选项。即使容器使用默认的 logging driver，它也可以使用不同的可配置选项。

以下示例使用 `none` logging driver 启动一个 Alpine 容器。

```console
$ docker run -it --log-driver none alpine ash
```

要查看运行中容器的当前 logging driver（假设 daemon 使用的是 `json-file` logging driver），请运行以下 `docker inspect` 命令，将 `<CONTAINER>` 替换为容器的名称或 ID：

```console
$ docker inspect -f '{{.HostConfig.LogConfig.Type}}' <CONTAINER>

json-file
```

## Configure the delivery mode of log messages from container to log driver（配置日志消息从容器到 log driver 的传递模式）

Docker 提供了两种将消息从容器传递到 log driver 的模式：

- （默认）直接从容器到 driver 的阻塞式传递（blocking delivery）
- 非阻塞传递（non-blocking delivery），将日志消息存储在中间每个容器的缓冲区中，供 driver 消费

`non-blocking` 消息传递模式可以防止应用程序因日志回压（logging back pressure）而阻塞。当 `STDERR` 或 `STDOUT` 流阻塞时，应用程序很可能会以意外的方式失败。

> [!WARNING]
>
> 当缓冲区已满时，新消息将无法入队。丢弃消息通常比阻塞应用程序的日志写入进程更可取。

`mode` 日志选项用于控制使用 `blocking`（默认）还是 `non-blocking` 消息传递。

`max-buffer-size` 控制当 `mode` 设置为 `non-blocking` 时用于中间消息存储的缓冲区大小。默认值为 `1m`，表示 1 MB（一百万个字节）。有关允许的格式字符串，请参见 [`go-units` 包中的 `FromHumanSize()` 函数](https://pkg.go.dev/github.com/docker/go-units#FromHumanSize)，例如 `1KiB` 表示 1024 字节，`2g` 表示 20 亿字节。

以下示例以非阻塞模式启动一个 Alpine 容器，并使用 4 兆字节的缓冲区：

```console
$ docker run -it --log-opt mode=non-blocking --log-opt max-buffer-size=4m alpine ping 127.0.0.1
```

### Use environment variables or labels with logging drivers（将环境变量或 labels 与 logging drivers 一起使用）

某些 logging drivers 会将容器的 `--env|-e` 或 `--label` 标志的值添加到容器的日志中。此示例使用 Docker daemon 的默认 logging driver（以下示例中为 `json-file`）启动一个容器，并设置了环境变量 `os=ubuntu`。

```console
$ docker run -dit --label production_status=testing -e os=ubuntu alpine sh
```

如果 logging driver 支持，这会在日志输出中添加额外的字段。以下是 `json-file` logging driver 生成的输出：

```json
"attrs":{"production_status":"testing","os":"ubuntu"}
```

## Supported logging drivers（支持的 logging drivers）

支持以下 logging drivers。如果适用，请参阅每个 driver 文档以了解其可配置选项。如果您正在使用 [logging driver plugins（日志驱动程序插件）](/engine/logging/configure/plugins/)，可能会看到更多选项。

| Driver                                | 描述                                                                                                                       |
| :------------------------------------ | :------------------------------------------------------------------------------------------------------------------------- |
| `none`                                | 容器没有可用的日志，`docker logs` 不返回任何输出。                                                                          |
| [`local`](/engine/logging/configure/drivers/local/)           | 日志以自定义格式存储，设计用于最小化开销。                                                                                  |
| [`json-file`](/engine/logging/configure/drivers/json-file/)   | 日志格式为 JSON。Docker 的默认 logging driver。                                                                             |
| [`syslog`](/engine/logging/configure/drivers/syslog/)         | 将日志消息写入 `syslog` 设施。`syslog` 守护进程必须在主机上运行。                                                             |
| [`journald`](/engine/logging/configure/drivers/journald/)     | 将日志消息写入 `journald`。`journald` 守护进程必须在主机上运行。                                                              |
| [`gelf`](/engine/logging/configure/drivers/gelf/)             | 将日志消息写入 Graylog 扩展日志格式（GELF）端点，例如 Graylog 或 Logstash。                                                   |
| [`fluentd`](/engine/logging/configure/drivers/fluentd/)       | 将日志消息写入 `fluentd`（forward input）。`fluentd` 守护进程必须在主机上运行。                                                |
| [`awslogs`](/engine/logging/configure/drivers/awslogs/)       | 将日志消息写入 Amazon CloudWatch Logs。                                                                                    |
| [`splunk`](/engine/logging/configure/drivers/splunk/)         | 使用 HTTP Event Collector 将日志消息写入 `splunk`。                                                                         |
| [`etwlogs`](/engine/logging/configure/drivers/etwlogs/)       | 将日志消息作为 Windows 事件跟踪（ETW）事件写入。仅在 Windows 平台上可用。                                                      |
| [`gcplogs`](/engine/logging/configure/drivers/gcplogs/)       | 将日志消息写入 Google Cloud Platform（GCP）Logging。                                                                        |

## Limitations of logging drivers（logging drivers 的限制）

- 读取日志信息需要解压缩轮转后的日志文件，这会导致磁盘使用量暂时增加（直到轮转文件中的日志条目被读取），并且解压缩期间 CPU 使用率会增加。
- Docker 数据目录所在主机的存储容量决定了日志文件信息的最大大小。