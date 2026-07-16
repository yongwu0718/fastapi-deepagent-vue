# Overriding container defaults（覆盖容器默认配置）

## 解释

当 Docker 容器启动时，它会执行一个应用程序或命令。容器从镜像的配置中获取这个可执行文件（脚本或二进制文件）。容器带有通常运行良好的默认设置，但你可以根据需要更改它们。这些调整有助于容器的程序完全按照你想要的方式运行。

例如，如果你有一个现有的数据库容器监听标准端口，并且你想运行同一个数据库容器的新的实例，那么你可能想要更改新容器监听的端口设置，以避免与现有容器冲突。有时，如果程序需要更多资源来处理繁重的工作负载，你可能希望增加容器的可用内存，或者设置环境变量以提供程序正常运行所需的具体配置细节。

`docker run` 命令提供了一种强大的方式来覆盖这些默认设置，并根据你的喜好调整容器行为。该命令提供了几个标志（flags），让你可以动态定制容器行为。

以下是一些实现此目的的方法。

### Overriding the network ports（覆盖网络端口）

有时你可能希望为开发和测试目的使用单独的数据库实例。将这些数据库实例运行在同一个端口上可能会产生冲突。你可以使用 `docker run` 中的 `-p` 选项将容器端口映射到宿主机端口，从而允许你运行多个容器实例而不会发生冲突。

```console
$ docker run -d -p HOST_PORT:CONTAINER_PORT postgres
```

### Setting environment variables（设置环境变量）

该选项在容器内设置一个值为 `bar` 的环境变量 `foo`。

```console
$ docker run -e foo=bar postgres env
```

你会看到类似下面的输出：

```console
HOSTNAME=2042f2e6ebe4
foo=bar
```

> [!TIP]
>
> `.env` 文件是一种方便的方式，可以为你的 Docker 容器设置环境变量，而无需用大量的 `-e` 标志使命令行变得混乱。要使用 `.env` 文件，你可以向 `docker run` 命令传递 `--env-file` 选项。
> ```console
> $ docker run --env-file .env postgres env
> ```

### Restricting the container to consume the resources（限制容器资源消耗）

你可以使用 `docker run` 命令的 `--memory` 和 `--cpus` 标志来限制容器可以使用的 CPU 和内存。例如，你可以为 Python API 容器设置内存限制，防止它在宿主机上消耗过多资源。命令如下：

```console
$ docker run -e POSTGRES_PASSWORD=secret --memory="512m" --cpus="0.5" postgres
```

该命令将容器内存使用限制为 512 MB，并将 CPU 配额定义为 0.5 个核心。

> **监控实时资源使用情况（Monitor the real-time resource usage）**
>
> 你可以使用 `docker stats` 命令监控运行中容器的实时资源使用情况。这有助于你了解分配的资源是否足够或需要调整。

通过有效使用这些 `docker run` 标志，你可以定制容器化应用的行为以满足你的特定需求。

## 动手试一试

在本动手指南中，你将了解如何使用 `docker run` 命令覆盖容器默认配置。

1. [下载并安装](/get-started/get-docker/) Docker Desktop。

### Run multiple instances of the Postgres database（运行多个 Postgres 数据库实例）

1. 使用以下命令启动一个使用 [Postgres image](https://hub.docker.com/_/postgres) 的容器：

   ```console
   $ docker run -d -e POSTGRES_PASSWORD=secret -p 5432:5432 postgres
   ```

   这将在后台启动 Postgres 数据库，监听标准容器端口 `5432`，并映射到宿主机的 `5432` 端口。

2. 启动第二个 Postgres 容器，映射到不同的端口。

   ```console
   $ docker run -d -e POSTGRES_PASSWORD=secret -p 5433:5432 postgres
   ```

   这将在后台启动另一个 Postgres 容器，在容器内监听标准 Postgres 端口 `5432`，但映射到宿主机的 `5433` 端口。你覆盖宿主机端口只是为了确保这个新容器不会与现有运行中的容器冲突。

3. 通过进入 Docker Desktop Dashboard 的 **Containers** 视图验证两个容器都在运行。

   ![Docker Desktop Dashboard 截图，显示运行中的 Postgres 容器实例](/get-started/docker-concepts/running-containers/overriding-container-defaults/images/running-postgres-containers.webp?border=true)

### Run Postgres container in a controlled network（在受控网络中运行 Postgres 容器）

默认情况下，容器在运行时会自动连接到一个称为 bridge network（桥接网络）的特殊网络。这个桥接网络就像一个虚拟桥接器，允许同一宿主机上的容器相互通信，同时将它们与外部世界和其他宿主机隔离开来。对于大多数容器交互来说，这是一个方便的起点。但对于特定场景，你可能希望对网络配置有更多的控制。

这就是 custom network（自定义网络）发挥作用的地方。你可以通过向 `docker run` 命令传递 `--network` 标志来创建自定义网络。没有 `--network` 标志的容器都连接到默认的 bridge network。

按照以下步骤查看如何将 Postgres 容器连接到自定义网络。

1. 使用以下命令创建一个新的自定义网络：

   ```console
   $ docker network create mynetwork
   ```

2. 运行以下命令验证网络：

   ```console
   $ docker network ls
   ```

   此命令列出所有网络，包括新创建的 "mynetwork"。

3. 使用以下命令将 Postgres 连接到自定义网络：

   ```console
   $ docker run -d -e POSTGRES_PASSWORD=secret -p 5434:5432 --network mynetwork postgres
   ```

   这将在后台启动 Postgres 容器，映射到宿主机端口 5434，并连接到 `mynetwork` 网络。你传递了 `--network` 参数，通过将容器连接到自定义 Docker 网络来覆盖容器默认配置，以实现更好的隔离和与其他容器的通信。你可以使用 `docker network inspect` 命令查看容器是否绑定到这个新的桥接网络。

   > **默认桥接网络与自定义网络的主要区别（Key difference between default bridge and custom networks）**
   >
   > 1. DNS 解析：默认情况下，连接到默认桥接网络的容器可以相互通信，但只能通过 IP 地址（除非你使用 `--link` 选项，该选项已被视为遗留方式）。由于各种[技术缺陷](/engine/network/drivers/bridge/#differences-between-user-defined-bridges-and-the-default-bridge)，不建议在生产环境中使用。在自定义网络上，容器可以通过名称或别名相互解析。
   > 2. 隔离：未指定 `--network` 的所有容器都连接到默认桥接网络，这可能带来风险，因为不相关的容器也可以相互通信。使用自定义网络提供了一个带作用域的网络，只有连接到该网络的容器才能通信，从而提供更好的隔离。

### Manage the resources（管理资源）

默认情况下，容器不限制其资源使用。然而，在共享系统上，有效管理资源至关重要。不能让运行中的容器消耗太多宿主机的内存。

这时 `docker run` 命令再次大显身手。它提供了 `--memory` 和 `--cpus` 等标志来限制容器可以使用的 CPU 和内存。

```console
$ docker run -d -e POSTGRES_PASSWORD=secret --memory="512m" --cpus=".5" postgres
```

`--cpus` 标志指定容器的 CPU 配额。这里设置为半个 CPU 核心（0.5）。而 `--memory` 标志指定容器的内存限制，在此示例中设置为 512 MB。

### Override the default CMD and ENTRYPOINT in Docker Compose（在 Docker Compose 中覆盖默认的 CMD 和 ENTRYPOINT）

有时，你可能需要覆盖 Docker 镜像中定义的默认命令（`CMD`）或入口点（`ENTRYPOINT`），尤其是在使用 Docker Compose 时。

1. 创建一个 `compose.yml` 文件，内容如下：

   ```yaml
   services:
     postgres:
       image: postgres:18
       entrypoint: ["docker-entrypoint.sh", "postgres"]
       command: ["-h", "localhost", "-p", "5432"]
       environment:
         POSTGRES_PASSWORD: secret 
   ```

   Compose 文件定义了一个名为 `postgres` 的服务，使用官方 Postgres 镜像，设置入口点脚本，并启动带有密码认证的容器。

2. 通过运行以下命令启动服务：

   ```console
   $ docker compose up -d
   ```

   该命令启动 Docker Compose 文件中定义的 Postgres 服务。

3. 使用 Docker Desktop Dashboard 验证认证。

   打开 Docker Desktop Dashboard，选择 **Postgres** 容器，然后选择 **Exec** 进入容器 shell。你可以输入以下命令连接到 Postgres 数据库：

   ```console
   # psql -U postgres
   ```

   ![Docker Desktop Dashboard 截图，选择 Postgres 容器并使用 EXEC 按钮进入其 shell](/get-started/docker-concepts/running-containers/overriding-container-defaults/images/exec-into-postgres-container.webp?border=true)

   > [!NOTE]
   > 
   > PostgreSQL 镜像在本地设置了信任认证，因此你可能注意到从 localhost（在同一容器内）连接时不需要密码。但是，如果从不同的主机/容器连接，则需要密码。

### Override the default CMD and ENTRYPOINT with `docker run`（使用 `docker run` 覆盖默认的 CMD 和 ENTRYPOINT）

你也可以直接使用 `docker run` 命令覆盖默认配置，命令如下：

```console 
$ docker run -e POSTGRES_PASSWORD=secret postgres docker-entrypoint.sh -h localhost -p 5432
```

此命令运行一个 Postgres 容器，设置密码认证的环境变量，覆盖默认启动命令，并配置主机名和端口映射。

## 更多资源

- [Ways to set environment variables with Compose](/compose/how-tos/environment-variables/set-environment-variables/)
- [What is a container](/get-started/docker-concepts/the-basics/what-is-a-container/)

## 下一步

现在你已经学习了覆盖容器默认配置，接下来该学习如何持久化容器数据了。

[Persisting container data（持久化容器数据）](/get-started/docker-concepts/running-containers/overriding-container-defaults/persisting-container-data)