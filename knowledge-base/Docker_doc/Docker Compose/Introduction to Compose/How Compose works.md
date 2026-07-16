# Compose 的工作原理

使用 Docker Compose 时，您需要通过一个 YAML 配置文件（即 [Compose file](#the-compose-file)）来配置应用的服务（services），然后通过 [Compose CLI](#cli) 从该配置中创建并启动所有服务。

Compose 文件（即 `compose.yaml` 文件）遵循 [Compose Specification](/reference/compose-file/) 中关于如何定义多容器应用的规则。这是正式 [Compose Specification](https://github.com/compose-spec/compose-spec) 的 Docker Compose 实现。

**Compose 应用模型**

应用的各个计算组件被定义为 [services](/reference/compose-file/services/)。服务（service）是一个抽象概念，在平台上通过运行相同的容器镜像和配置（一次或多次）来实现。

服务之间通过 [networks](/reference/compose-file/networks/) 相互通信。在 Compose Specification 中，网络（network）是一种平台能力抽象，用于在连接在一起的服务中的容器之间建立 IP 路由。

services 将持久化数据存储和共享到 [volumes](/reference/compose-file/volumes/) 中。该规范将这种持久化数据描述为具有全局选项的高级文件系统挂载。

某些服务需要依赖于运行时或平台的配置数据。为此，规范定义了一个专用的 [configs](/reference/compose-file/configs/) 概念。从容器内部看，configs 的行为类似于 volumes——它们以文件形式挂载。然而，configs 在平台层面的定义方式有所不同。

[secret](/reference/compose-file/secrets/) 是一种特定类型的配置数据，用于不应在未考虑安全性的情况下暴露的敏感数据。secrets 以文件形式挂载到容器中并提供给服务，但由于提供敏感数据的平台特定资源非常特殊，因此在 Compose Specification 中需要作为一个独立的概念和定义。

> [!NOTE]
>
> 通过 volumes、configs 和 secrets，您可以在顶层进行简单声明，然后在服务层面添加更多特定于平台的信息。

项目（project）是应用规范在平台上的单次部署。项目名称通过顶层 [`name`](/reference/compose-file/version-and-name/) 属性设置，用于将资源分组，并将其与其他应用或同一 Compose 规范应用的不同参数安装隔离开来。如果在平台上创建资源，必须使用项目名称作为资源名称的前缀，并设置标签 `com.docker.compose.project`。

Compose 提供了一种方式让您可以设置自定义项目名称并覆盖默认名称，这样即使基础设施相同，只需传递不同的名称，就可以在不修改 `compose.yaml` 文件的情况下进行两次部署。

## Compose 文件

Compose 文件的默认路径是工作目录下的 `compose.yaml`（首选）或 `compose.yml`。Compose 也支持 `docker-compose.yaml` 和 `docker-compose.yml`，以向后兼容早期版本。如果两个文件同时存在，Compose 会优先使用规范的 `compose.yaml`。

您可以使用 [fragments](/reference/compose-file/fragments/) 和 [extensions](/reference/compose-file/extension/) 来保持 Compose 文件的高效和易于维护。

多个 Compose 文件可以 [合并（merge）](/reference/compose-file/merge/) 在一起以定义应用模型。YAML 文件的合并是通过根据您设置的 Compose 文件顺序来追加或覆盖 YAML 元素实现的。简单的属性和映射会被顺序更高的 Compose 文件覆盖，列表则通过追加来合并。当被合并的补充文件位于其他文件夹时，相对路径将基于第一个 Compose 文件的父文件夹进行解析。由于某些 Compose 文件元素既可以表示为单个字符串也可以表示为复杂对象，合并会应用于展开后的形式。更多信息请参阅 [使用多个 Compose 文件](/compose/how-tos/multiple-compose-files/)。

如果您想复用其他 Compose 文件，或者将应用模型的一部分拆分到单独的 Compose 文件中，也可以使用 [`include`](/reference/compose-file/include/)。当您的 Compose 应用依赖于另一个由不同团队管理或需要与他人共享的应用时，这将非常有用。

## CLI

Docker CLI 通过 `docker compose` 命令及其子命令，让您能够与 Docker Compose 应用进行交互。如果您使用的是 Docker Desktop，则默认已包含 Docker Compose CLI。

使用 CLI，您可以管理 `compose.yaml` 文件中定义的多容器应用的完整生命周期。CLI 命令使您能够轻松启动、停止和配置应用。

### 常用命令

启动 `compose.yaml` 文件中定义的所有服务：

```console
$ docker compose up
```

停止并移除正在运行的服务：

```console
$ docker compose down
```

如果您想监控运行中容器的输出并调试问题，可以使用以下命令查看日志：

```console
$ docker compose logs
```

列出所有服务及其当前状态：

```console
$ docker compose ps
```

要查看所有 Compose CLI 命令的完整列表，请参阅 [参考文档](/reference/cli/docker/compose/)。

## 示例说明

以下示例阐释了上述 Compose 概念。该示例是非规范性的。

假设一个应用被拆分为前端 Web 应用和后端服务。

前端在运行时通过基础设施管理的 HTTP 配置文件进行配置，该文件提供了外部域名，并且平台的安全 secret 存储注入了一个 HTTPS 服务器证书。

后端将数据存储在持久卷（volume）中。

两个服务通过一个隔离的后端网络（back-tier network）相互通信，同时前端还连接到一个前端网络（front-tier network）并对外暴露 443 端口以供外部使用。

![](compose-application.webp)

该示例应用包含以下部分：

- 两个服务（services），基于 Docker 镜像：`webapp` 和 `database`
- 一个 secret（HTTPS 证书），注入到前端
- 一个配置（config）（HTTP 配置），注入到前端
- 一个持久卷（volume），挂载到后端
- 两个网络（networks）

```yml
services:
  frontend:
    image: example/webapp
    ports:
      - "443:8043"
    networks:
      - front-tier
      - back-tier
    configs:
      - httpd-config
    secrets:
      - server-certificate

  backend:
    image: example/database
    volumes:
      - db-data:/etc/data
    networks:
      - back-tier

volumes:
  db-data:
    driver: flocker
    driver_opts:
      size: "10GiB"

configs:
  httpd-config:
    external: true

secrets:
  server-certificate:
    external: true

networks:
  # 这些对象的存在足以定义它们
  front-tier: {}
  back-tier: {}
```

`docker compose up` 命令会启动 `frontend` 和 `backend` 服务，创建必要的网络和卷，并将 config 和 secret 注入到前端服务中。

`docker compose ps` 提供服务当前状态的快照，让您轻松查看哪些容器正在运行、它们的状态以及所使用的端口：

```text
$ docker compose ps

NAME                IMAGE                COMMAND                  SERVICE             CREATED             STATUS              PORTS
example-frontend-1  example/webapp       "nginx -g 'daemon of…"   frontend            2 minutes ago       Up 2 minutes        0.0.0.0:443->8043/tcp
example-backend-1   example/database     "docker-entrypoint.s…"   backend             2 minutes ago       Up 2 minutes
```

## 下一步

- [尝试快速入门指南](/compose/gettingstarted/)
- [探索一些示例应用](https://github.com/docker/awesome-compose)
- [熟悉 Compose Specification](/reference/compose-file/)