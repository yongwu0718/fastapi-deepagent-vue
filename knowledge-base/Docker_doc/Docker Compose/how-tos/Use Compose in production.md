# 在生产环境中使用 Compose

当您在开发环境中使用 Compose 定义应用后，可以在不同环境（如 CI、staging 和生产环境）中利用该定义来运行您的应用。

最简单的部署方式是在单台服务器上运行应用，类似于您运行开发环境的方式。如果您希望扩展应用，可以在 Swarm 集群上运行 Compose 应用。

### 修改 Compose 文件以适应生产环境

您可能需要调整应用配置，使其为生产环境做好准备。这些调整可能包括：

- 移除应用程序代码的 volume 绑定，使代码保留在 container 内部，无法从外部更改
- 绑定到主机上的不同端口
- 以不同的方式设置环境变量（environment variables），例如降低日志详细程度，或为外部服务（如邮件服务器）指定设置
- 指定重启策略（restart policy），例如 [`restart: always`](/reference/compose-file/services/#restart)，以避免停机
- 添加额外服务（如日志聚合器）

因此，建议定义一个额外的 Compose 文件，例如 `compose.production.yaml`，其中包含特定于生产环境的配置详情。该配置文件只需包含您希望从原始 Compose 文件进行的更改。然后，将额外的 Compose 文件应用于原始 `compose.yaml` 之上，以创建新的配置。

一旦有了第二个配置文件，您可以使用 `-f` 选项来运行：

```console
$ docker compose -f compose.yaml -f compose.production.yaml up -d
```

有关更完整的示例和其他选项，请参阅[使用多个 Compose 文件](/compose/how-tos/production/multiple-compose-files/)。

### 部署更改

当您对应用代码进行更改时，请记得重建 image 并重新创建应用的 containers。要重新部署一个名为 `web` 的 service，请使用：

```console
$ docker compose build web
$ docker compose up --no-deps -d web
```

第一条命令会为 `web` 重建 image，然后停止、销毁并仅重新创建 `web` service。`--no-deps` 标志可防止 Compose 同时重新创建 `web` 所依赖的任何 services。

### 在单台服务器上运行 Compose

您可以通过适当设置 `DOCKER_HOST`、`DOCKER_TLS_VERIFY` 和 `DOCKER_CERT_PATH` 环境变量，使用 Compose 将应用部署到远程 Docker 主机。更多信息请参阅[预定义的环境变量](/compose/how-tos/production/environment-variables/envvars/)。

设置好环境变量后，所有常规的 `docker compose` 命令都无需进一步配置即可工作。

## 下一步

- [熟悉 Compose 的信任模型](/compose/trust-model/)
- [使用多个 Compose 文件](/compose/how-tos/production/multiple-compose-files/)