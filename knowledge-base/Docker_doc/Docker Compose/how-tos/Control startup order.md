# 在 Compose 中控制启动和关闭顺序

您可以使用 [`depends_on`](/reference/compose-file/services/#depends_on) 属性来控制服务（service）的启动和关闭顺序。Compose 总是按照依赖顺序启动和停止容器（container），

依赖关系由 `depends_on`、`links`、`volumes_from` 和 `network_mode: "service:…"` 决定。

例如，如果您的应用需要访问数据库，而两个服务都通过 `docker compose up` 启动，则有可能失败，因为应用服务可能先于数据库服务启动，从而找不到能够处理其 SQL 语句的数据库。

## 控制启动顺序

在启动时，Compose 并不会等待容器“就绪（ready）”，而只会等待它运行（running）。如果您的应用依赖于一个关系数据库系统，而该系统需要先启动自身服务才能处理传入连接，这就会引发问题。

检测服务就绪状态的方法是使用 `condition` 属性，并配合以下选项之一：

- `service_started`
- `service_healthy`：表示依赖项在被依赖的服务启动之前，预期应处于“健康（healthy）”状态，该状态由 `healthcheck` 定义。
- `service_completed_successfully`：表示依赖项预期成功运行完成（successful completion）后，才会启动依赖它的服务。

## 示例

```yaml
services:
  web:
    build: .
    depends_on:
      db:
        condition: service_healthy
        restart: true
      redis:
        condition: service_started
  redis:
    image: redis
  db:
    image: postgres:18
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      retries: 5
      start_period: 30s
      timeout: 10s
```

Compose 按照依赖顺序创建服务。`db` 和 `redis` 会在 `web` 之前创建。

Compose 会等待标记为 `service_healthy` 的依赖项通过健康检查（healthchecks）。`db` 被预期为“healthy”（如 `healthcheck` 所示），然后才会创建 `web`。

`restart: true` 确保如果 `db` 因为明确的 Compose 操作（例如 `docker compose restart`）而被更新或重启，`web` 服务也会自动重启，从而确保它正确地重新建立连接或依赖关系。

`db` 服务的健康检查使用 `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` 命令来检查 PostgreSQL 数据库是否就绪。该服务每 10 秒重试一次，最多重试 5 次。

Compose 也会按照依赖顺序移除服务。`web` 会在 `db` 和 `redis` 之前被移除。

## 参考信息

- [`depends_on`](/reference/compose-file/services/#depends_on)
- [`healthcheck`](/reference/compose-file/services/#healthcheck)