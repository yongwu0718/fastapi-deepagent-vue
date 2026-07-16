# Publishing and exposing ports（发布和暴露端口）

## 解释

如果你一直在跟随前面的指南，你已经了解容器（containers）为应用的每个组件提供了隔离的进程。每个组件——比如 React 前端、Python API 和 Postgres 数据库——都运行在各自独立的沙箱环境中，与宿主机上的其他一切完全隔离。这种隔离对安全性和依赖管理非常有利，但也意味着你无法直接访问它们。例如，你无法在浏览器中直接访问 Web 应用。

这就是 **publishing ports（发布端口）** 的作用所在。

### Publishing ports（发布端口）

发布端口通过设置转发规则，能够突破部分网络隔离。例如，你可以指定将宿主机上 `8080` 端口的请求转发到容器的 `80` 端口。发布端口操作在容器创建时进行，使用 `docker run` 命令的 `-p`（或 `--publish`）标志。语法如下：

```console
docker run -d -p HOST_PORT:CONTAINER_PORT nginx
```

- `HOST_PORT`：宿主机上用于接收流量的端口号
- `CONTAINER_PORT`：容器内部监听的端口号

例如，将容器的 `80` 端口发布到宿主机的 `8080` 端口：

```console
docker run -d -p 8080:80 nginx
```

现在，发送到宿主机 `8080` 端口的所有流量都将被转发到容器内的 `80` 端口。

> [!IMPORTANT]
>
> 默认情况下，端口发布时会发布到所有网络接口。这意味着任何能访问你机器的流量都可以访问已发布的应用。请注意发布数据库或任何敏感信息。[在此了解关于 published ports 的更多信息](/engine/network/#published-ports)。

### Publishing to ephemeral ports（发布到临时端口）

有时你可能只想发布端口，但并不关心具体使用宿主机的哪个端口。在这种情况下，你可以让 Docker 为你选择端口。只需省略 `HOST_PORT` 配置即可。

例如，以下命令将容器的 `80` 端口发布到宿主机的某个临时端口（ephemeral port）上：

```console
$ docker run -p 80 nginx
```

容器运行后，使用 `docker ps` 会显示被选中的端口：

```console
docker ps
CONTAINER ID   IMAGE         COMMAND                  CREATED          STATUS          PORTS                    NAMES
a527355c9c53   nginx         "/docker-entrypoint.…"   4 seconds ago    Up 3 seconds    0.0.0.0:54772->80/tcp    romantic_williamson
```

在此示例中，应用在宿主机的 `54772` 端口上暴露。

### Publishing all ports（发布所有端口）

在创建容器镜像时，`EXPOSE` 指令用于表明打包的应用将使用指定的端口。这些端口默认不会发布。

使用 `-P` 或 `--publish-all` 标志，你可以自动将所有已暴露的端口发布到临时端口上。这在开发或测试环境中试图避免端口冲突时非常有用。

例如，以下命令将发布镜像配置的所有已暴露端口：

```console
docker run -P nginx
```

## 动手试一试

在本动手指南中，你将学习如何使用 CLI 和 Docker Compose 为部署 Web 应用发布容器端口。

### 使用 Docker CLI

在此步骤中，你将运行一个容器并使用 Docker CLI 发布其端口。

1. [下载并安装](/get-started/get-docker/) Docker Desktop。

2. 在终端中，运行以下命令启动一个新容器：

```console
$ docker run -d -p 8080:80 docker/welcome-to-docker
```

第一个 `8080` 指的是宿主机端口（host port）。这是你本地机器上用于访问容器内运行的应用程序的端口。第二个 `80` 指的是容器端口（container port）。这是容器内部应用监听的端口。因此，该命令将宿主机的 `8080` 端口绑定到容器系统的 `80` 端口。

3. 通过进入 Docker Desktop Dashboard 的 **Containers** 视图来验证已发布的端口。

4. 通过选择容器 **Port(s)** 列中的链接，或在浏览器中访问 [http://localhost:8080](http://localhost:8080) 来打开网站。

### 使用 Docker Compose

以下示例将使用 Docker Compose 启动相同的应用：

1. 创建一个新目录，并在该目录中创建一个 `compose.yaml` 文件，内容如下：

```yaml
services:
   app:
      image: docker/welcome-to-docker
      ports:
      - 8080:80
```

`ports` 配置接受几种不同的端口定义语法。在这里，我们使用了与 `docker run` 命令中相同的 `HOST_PORT:CONTAINER_PORT` 格式。

2. 打开终端并导航到上一步创建的目录。

3. 使用 `docker compose up` 命令启动应用。

4. 在浏览器中打开 [http://localhost:8080](http://localhost:8080)。

## 更多资源

如果你想更深入地学习这个主题，请务必查看以下资源：

- [`docker container port` CLI reference](/reference/cli/docker/container/port/)
- [Published ports](/engine/network/#published-ports)

## 下一步

现在你已经理解了如何发布和暴露端口，接下来可以学习如何使用 `docker run` 命令覆盖容器默认配置。

Overriding container defaults（覆盖容器默认配置）