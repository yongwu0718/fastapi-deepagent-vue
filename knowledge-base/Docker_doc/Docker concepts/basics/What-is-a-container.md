# 什么是 Container？

## 解释

假设你正在开发一个 killer Web 应用，它有三个主要组件：一个 React 前端、一个 Python API 和一个 PostgreSQL 数据库。如果你想在这个项目上工作，就必须安装 Node、Python 和 PostgreSQL。

如何确保你与团队其他开发者（或 CI/CD 系统，或生产环境）使用的版本完全相同？

如何保证你的应用所需的 Python（或 Node，或数据库）版本不受你机器上已有内容的影响？如何管理潜在的冲突？

这时候就该 Container 登场了！

**什么是 Container？** 简单来说，Container 是为应用的每个组件提供的隔离进程。每个组件（前端 React 应用、Python API 引擎、数据库）都运行在各自独立的环境中，与机器上的其他一切完全隔离。

Container 的厉害之处在于：

- **自包含（Self-contained）**：每个 Container 拥有运行所需的一切，不依赖宿主机上任何预安装的依赖项。
- **隔离（Isolated）**：由于 Container 运行在隔离环境中，它们对宿主机和其他 Container 的影响极小，从而提高应用的安全性。
- **独立（Independent）**：每个 Container 独立管理。删除一个 Container 不会影响其他任何 Container。
- **可移植（Portable）**：Container 可以在任何地方运行！在你的开发机器上运行的 Container，在数据中心或云中的任何地方都会以相同的方式工作。

### Container 与虚拟机（VM）的对比

简单来说，虚拟机（VM）是一个完整的操作系统，拥有自己的内核、硬件驱动程序、程序和应用程序。仅仅为了隔离单个应用而启动一个 VM 会产生大量开销。

Container 只是一个隔离的进程，附带运行所需的所有文件。如果你运行多个 Container，它们都共享同一个内核，从而允许你在更少的基础设施上运行更多的应用。

> **VM 和 Container 的配合使用**
>
> 通常情况下，你会看到 Container 和 VM 一起使用。例如，在云环境中，预配置的机器通常是 VM。然而，与其配置一台机器来运行一个应用，不如让一台带有容器运行时的 VM 运行多个容器化应用，这样可以提高资源利用率并降低成本。

## 动手试一试

在这个动手环节中，你将看到如何使用 Docker Desktop GUI 运行一个 Docker Container。

### 使用 GUI

按照以下指令运行一个 Container。

1. 打开 Docker Desktop，选择顶部导航栏的 **Search** 字段。
2. 在搜索输入框中指定 `welcome-to-docker`，然后选择 **Pull** 按钮。
3. 镜像成功拉取后，选择 **Run** 按钮。
4. 展开 **Optional settings**。
5. 在 **Container name** 中指定 `welcome-to-docker`。
6. 在 **Host port** 中指定 `8080`。
7. 选择 **Run** 启动你的 Container。

恭喜！你已经运行了第一个 Container！🎉

#### 查看你的 Container

你可以通过进入 Docker Desktop Dashboard 的 **Containers** 视图来查看所有 Container。

这个 Container 运行一个 Web 服务器，显示一个简单的网站。在处理更复杂的项目时，你会将不同部分运行在不同的 Container 中。例如，你可能为前端、后端和数据库分别运行一个不同的 Container。

#### 访问前端

当你启动 Container 时，你将 Container 的一个端口暴露给了你的机器。你可以把这看作是创建一种配置，让你能够通过 Container 的隔离环境进行连接。

对于这个 Container，前端可以通过端口 `8080` 访问。要打开网站，请选择 Container 的 **Port(s)** 列中的链接，或在浏览器中访问 [http://localhost:8080](http://localhost:8080)。

#### 探索你的 Container

Docker Desktop 允许你探索和与 Container 的不同方面进行交互。自己动手试试。

1. 进入 Docker Desktop Dashboard 的 **Containers** 视图。
2. 选择你的 Container。
3. 选择 **Files** 选项卡，探索 Container 的隔离文件系统。

#### 停止你的 Container

`docker/welcome-to-docker` Container 会一直运行，直到你停止它。

1. 进入 Docker Desktop Dashboard 的 **Containers** 视图。
2. 找到你想要停止的 Container。
3. 在 **Actions** 列中选择 **Stop** 操作。

### 使用 CLI

按照以下指令使用 CLI 运行一个 Container：

1. 打开你的 CLI 终端，使用 [`docker run`] 命令启动一个 Container：

   ```console
   $ docker run -d -p 8080:80 docker/welcome-to-docker
   ```

   该命令的输出是完整的 Container ID。

恭喜！你刚刚用命令行启动了第一个 Container！🎉

#### 查看运行中的 Container

你可以使用 [`docker ps`] 命令验证 Container 是否已启动并运行：

```console
docker ps
```

你会看到类似下面的输出：

```console
 CONTAINER ID   IMAGE                      COMMAND                  CREATED          STATUS          PORTS                      NAMES
 a1f7a4bb3a27   docker/welcome-to-docker   "/docker-entrypoint.…"   11 seconds ago   Up 11 seconds   0.0.0.0:8080->80/tcp       gracious_keldysh
```

这个 Container 运行一个 Web 服务器，显示一个简单的网站。在处理更复杂的项目时，你会将不同部分运行在不同的 Container 中。例如，为 `frontend`、`backend` 和 `database` 分别运行不同的 Container。

> [!TIP]
>
> `docker ps` 命令只显示*正在运行*的 Container。要查看已停止的 Container，可以添加 `-a` 标志来列出所有 Container：`docker ps -a`

#### 访问前端

当你启动 Container 时，你将 Container 的一个端口暴露给了你的机器。你可以把这看作是创建一种配置，让你能够通过 Container 的隔离环境进行连接。

对于这个 Container，前端可以通过端口 `8080` 访问。要打开网站，请选择 Container 的 **Port(s)** 列中的链接，或在浏览器中访问 [http://localhost:8080](http://localhost:8080)。

#### 停止你的 Container

`docker/welcome-to-docker` Container 会一直运行，直到你停止它。你可以使用 `docker stop` 命令停止一个 Container。

1. 运行 `docker ps` 获取 Container 的 ID。
2. 将 Container ID 或名称传递给 [`docker stop`] 命令：

   ```console
   docker stop <the-container-id>
   ```

> [!TIP]
>
> 当通过 ID 引用 Container 时，你不需要提供完整的 ID。只需提供足够长以使其唯一的部分即可。例如，可以通过运行以下命令来停止之前的 Container：
>
> ```console
> docker stop a1f
> ```