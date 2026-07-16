# Docker CLI 的 OpenTelemetry 支持

Docker CLI 支持 [OpenTelemetry](https://opentelemetry.io/docs/) 仪表化，用于发出有关命令调用的度量指标（metrics）。此功能默认禁用。你可以配置 CLI 开始向指定的端点（endpoint）发送度量指标。这使你能够捕获 `docker` 命令调用的信息，从而更深入地了解你的 Docker 使用情况。

导出度量指标是自愿加入（opt-in）的，你可以通过指定度量收集器（metrics collector）的目标地址来控制数据发送的位置。

## 什么是 OpenTelemetry？

**OpenTelemetry**（简称 OTel）是一个开放的观测框架，用于创建和管理遥测数据（telemetry data），例如追踪（traces）、度量指标（metrics）和日志（logs）。OpenTelemetry 与厂商和工具无关，意味着它可以与多种多样的观测后端（Observability backends）一起使用。

Docker CLI 中对 OpenTelemetry 仪表化的支持，意味着 CLI 可以使用 OpenTelemetry 规范中定义的协议和约定，发出有关发生事件的信息。

## 工作原理

默认情况下，Docker CLI 不会发出遥测数据。仅当你在系统上设置了环境变量时，Docker CLI 才会尝试向你指定的端点（endpoint）发送 OpenTelemetry 度量指标。

```bash
DOCKER_CLI_OTEL_EXPORTER_OTLP_ENDPOINT=<endpoint>
```

该变量指定了一个 OpenTelemetry 收集器（collector）的端点，关于 `docker` CLI 调用的遥测数据将被发送到该端点。要捕获数据，你需要一个在该端点上监听的 OpenTelemetry 收集器。

收集器的目的是接收遥测数据、处理数据，并将其导出到后端（backend）。后端是遥测数据的存储位置。你可以选择多种不同的后端，例如 Prometheus 或 InfluxDB。

某些后端提供了直接可视化度量指标的工具。此外，你也可以运行一个专用的前端（如 Grafana），以支持生成更有用的图表。

## 设置步骤

要开始捕获 Docker CLI 的遥测数据，你需要：

- 设置 `DOCKER_CLI_OTEL_EXPORTER_OTLP_ENDPOINT` 环境变量，指向一个 OpenTelemetry 收集器端点。
- 运行一个 OpenTelemetry 收集器，接收来自 CLI 命令调用的信号。
- 运行一个后端，用于存储从收集器接收到的数据。

以下 Docker Compose 文件引导一组服务，帮助你快速上手 OpenTelemetry。它包括一个 CLI 可以发送度量指标的 OpenTelemetry 收集器，以及一个从收集器中抓取度量指标的 Prometheus 后端。

```yaml {collapse=true,title=compose.yaml}
name: cli-otel
services:
  prometheus:
    image: prom/prometheus
    command:
      - "--config.file=/etc/prometheus/prom.yml"
    ports:
      # 在 localhost:9091 上发布 Prometheus 前端
      - 9091:9090
    restart: always
    volumes:
      # 将 Prometheus 数据存储到卷中：
      - prom_data:/prometheus
      # 挂载 prom.yml 配置文件
      - ./prom.yml:/etc/prometheus/prom.yml
  otelcol:
    image: otel/opentelemetry-collector
    restart: always
    depends_on:
      - prometheus
    ports:
      - 4317:4317
    volumes:
      # 挂载 otelcol.yml 配置文件
      - ./otelcol.yml:/etc/otelcol/config.yaml

volumes:
  prom_data:
```

此服务假定在 `compose.yaml` 旁边存在以下两个配置文件：

- ```yaml {collapse=true,title=otelcol.yml}
  # 通过 gRPC 和 HTTP 接收信号
  receivers:
    otlp:
      protocols:
        grpc:
        http:

  # 建立 Prometheus 抓取的端点
  exporters:
    prometheus:
      endpoint: "0.0.0.0:8889"

  service:
    pipelines:
      metrics:
        receivers: [otlp]
        exporters: [prometheus]
  ```

- ```yaml {collapse=true,title=prom.yml}
  # 配置 Prometheus 抓取 OpenTelemetry 收集器端点
  scrape_configs:
    - job_name: "otel-collector"
      scrape_interval: 1s
      static_configs:
        - targets: ["otelcol:8889"]
  ```

准备好这些文件后：

1. 启动 Docker Compose 服务：

   ```console
   $ docker compose up
   ```

2. 配置 Docker CLI 将遥测数据导出到 OpenTelemetry 收集器。

   ```console
   $ export DOCKER_CLI_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
   ```

3. 运行一个 `docker` 命令，触发 CLI 向 OpenTelemetry 收集器发送度量信号。

   ```console
   $ docker version
   ```

4. 要查看 CLI 创建的遥测度量指标，请打开 Prometheus 表达式浏览器（expression browser），访问 <http://localhost:9091/graph>。

5. 在 **Query** 字段中，输入 `command_time_milliseconds_total`，然后执行查询以查看遥测数据。

## 可用度量指标

Docker CLI 导出一个单一的度量指标 `command.time`，它测量命令的执行持续时间（以毫秒为单位）。该度量指标具有以下属性（attributes）：

- `command.name`：命令的名称
- `command.status.code`：命令的退出码
- `command.stderr.isatty`：如果 stderr 附加到 TTY 则为 true
- `command.stdin.isatty`：如果 stdin 附加到 TTY 则为 true
- `command.stdout.isatty`：如果 stdout 附加到 TTY 则为 true
