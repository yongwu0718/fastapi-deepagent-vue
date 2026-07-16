# 使用 Prometheus 收集 Docker metrics

[Prometheus](https://prometheus.io/) 是一个开源系统监控和告警工具包。您可以将 Docker 配置为 Prometheus 的监控目标（target）。

> [!WARNING]
>
> 当前可用的 metrics 以及这些 metrics 的名称正在积极开发中，可能随时更改。

目前，您只能监控 Docker 本身。您尚无法使用 Docker target 来监控您的应用程序。

## 示例

以下示例向您展示如何配置 Docker 守护进程，如何在本地机器上将 Prometheus 作为容器运行，以及如何使用 Prometheus 监控您的 Docker 实例。

### 配置守护进程

要将 Docker 守护进程配置为 Prometheus target，您需要在 `daemon.json` 配置文件中指定 `metrics-addr`。默认情况下，守护进程期望该文件位于以下位置之一。如果文件不存在，请创建它。

- **Linux**：`/etc/docker/daemon.json`
- **Windows Server**：`C:\ProgramData\docker\config\daemon.json`
- **Docker Desktop**：打开 Docker Desktop 设置并选择 **Docker Engine** 以编辑该文件。

添加以下配置：

```json
{
  "metrics-addr": "127.0.0.1:9323"
}
```

保存文件（对于 Docker Desktop for Mac 或 Docker Desktop for Windows，保存配置）。重启 Docker。

现在，Docker 通过回环接口在 9323 端口上暴露与 Prometheus 兼容的 metrics。您可以将其配置为使用通配地址 `0.0.0.0`，但这会将 Prometheus 端口暴露给更广泛的网络。在决定哪种选项最适合您的环境时，请仔细考虑您的威胁模型。

### 创建 Prometheus 配置

复制以下配置文件并将其保存到您选择的位置，例如 `/tmp/prometheus.yml`。这是一个标准的 Prometheus 配置文件，除了在文件底部添加了 Docker job 定义。

```yml
# my global config
global:
  scrape_interval: 15s # Set the scrape interval to every 15 seconds. Default is every 1 minute.
  evaluation_interval: 15s # Evaluate rules every 15 seconds. The default is every 1 minute.
  # scrape_timeout is set to the global default (10s).

  # Attach these labels to any time series or alerts when communicating with
  # external systems (federation, remote storage, Alertmanager).
  external_labels:
    monitor: "codelab-monitor"

# Load rules once and periodically evaluate them according to the global 'evaluation_interval'.
rule_files:
  # - "first.rules"
  # - "second.rules"

# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: prometheus

    # metrics_path defaults to '/metrics'
    # scheme defaults to 'http'.

    static_configs:
      - targets: ["localhost:9090"]

  - job_name: docker
      # metrics_path defaults to '/metrics'
      # scheme defaults to 'http'.

    static_configs:
      - targets: ["host.docker.internal:9323"]
```

### 在容器中运行 Prometheus

接下来，使用此配置启动一个 Prometheus 容器。

```console
$ docker run --name my-prometheus \
    --mount type=bind,source=/tmp/prometheus.yml,destination=/etc/prometheus/prometheus.yml \
    -p 9090:9090 \
    --add-host host.docker.internal=host-gateway \
    prom/prometheus
```

如果您使用的是 Docker Desktop，则 `--add-host` 标志是可选的。此标志确保主机的内部 IP 暴露给 Prometheus 容器。Docker Desktop 默认会这样做。主机 IP 作为 `host.docker.internal` 主机名暴露。这与上一步在 `prometheus.yml` 中定义的配置匹配。

### 打开 Prometheus Dashboard

验证 Docker target 是否列在 `http://localhost:9090/targets/`。

![Prometheus targets page](/engine/daemon/prometheus/images/prometheus-targets.webp)

> [!NOTE]
>
> 如果您使用 Docker Desktop，则无法直接访问此页面上的端点 URL。

### 使用 Prometheus

创建一个图表。在 Prometheus UI 中选择 **Graphs** 链接。从 **Execute** 按钮右侧的组合框中选择一个 metric，然后单击 **Execute**。下面的截图显示了 `engine_daemon_network_actions_seconds_count` 的图表。

![Idle Prometheus report](/engine/daemon/prometheus/images/prometheus-graph_idle.webp)

除非您的系统上已经在运行活跃的工作负载，否则该图表显示的是一个相当空闲的 Docker 实例。

为了使图表更有趣，运行一个使用一些网络操作的容器，例如通过包管理器下载一些包：

```console
$ docker run --rm alpine apk add git make musl-dev go
```

等待几秒钟（默认抓取间隔为 15 秒），然后重新加载图表。您应该会看到图表上升，显示您刚刚运行的容器引起的网络流量增加。

![Prometheus report showing traffic](/engine/daemon/prometheus/images/prometheus-graph_load.webp)

## 下一步

这里提供的示例展示了如何在本地系统上将 Prometheus 作为容器运行。在实践中，您可能需要在另一个系统或作为云服务运行 Prometheus。您也可以在这些场景中将 Docker 守护进程设置为 Prometheus target。配置守护进程的 `metrics-addr`，并将守护进程的地址作为抓取端点添加到您的 Prometheus 配置中。

```yaml
- job_name: docker
  static_configs:
    - targets: ["docker.daemon.example:<PORT>"]
```

有关 Prometheus 的更多信息，请参阅 [Prometheus 文档](https://prometheus.io/docs/introduction/overview/)。