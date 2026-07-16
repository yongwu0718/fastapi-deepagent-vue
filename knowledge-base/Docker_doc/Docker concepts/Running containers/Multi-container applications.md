# Multi-container applications（多容器应用）

## 解释

启动单容器应用很容易。例如，一个执行特定数据处理任务的 Python 脚本可以在容器中与其所有依赖项一起运行。同样，一个提供静态网站和小型 API 端点的 Node.js 应用也可以与其所有必要的库和依赖项一起被容器化。然而，随着应用规模的增长，将它们作为单个容器进行管理会变得更加困难。

想象一下：那个数据处理 Python 脚本需要连接到一个数据库。突然间，你不仅需要管理脚本，还需要在同一个容器中管理数据库服务器。如果脚本需要用户登录，你还需要一个认证机制，这会进一步增加容器体积。

容器的一个最佳实践是：每个容器应该只做一件事，并且把它做好。虽然这个规则也有例外，但应避免让一个容器做多件事的倾向。

现在你可能会问：“我需要分别运行这些容器吗？如果分开运行，我该如何将它们全部连接起来？”

虽然 `docker run` 是启动容器的便捷工具，但用它来管理不断增长的应用栈会变得困难。原因如下：

- 想象一下为开发、测试和生产环境运行多个 `docker run` 命令（前端、后端和数据库），并配以不同的配置。这容易出错且耗时。
- 应用之间往往相互依赖。随着应用栈的扩展，按特定顺序手动启动容器并管理网络连接变得困难。
- 每个应用都需要自己的 `docker run` 命令，这使得扩展单个服务变得困难。扩展整个应用意味着可能在不需提升的组件上浪费资源。
- 为每个应用持久化数据需要在每个 `docker run` 命令中单独挂载 volumes 或进行配置，这导致数据管理方式分散。
- 通过单独的 `docker run` 命令为每个应用设置环境变量既繁琐又容易出错。

这时，**Docker Compose** 就派上了用场。

Docker Compose 在单个名为 `compose.yml` 的 YAML 文件中定义你的整个多容器应用。该文件指定了所有容器的配置、它们的依赖项、环境变量，甚至 volumes 和 networks。使用 Docker Compose：

- 你不需要运行多个 `docker run` 命令。你只需在单个 YAML 文件中定义整个多容器应用。这集中了配置并简化了管理。
- 你可以按特定顺序运行容器，并轻松管理网络连接。
- 你可以在多容器设置中简单地向上或向下扩展单个服务。这允许基于实时需求进行高效的资源分配。
- 你可以轻松实现持久化 volumes。
- 在 Docker Compose 文件中一次性设置环境变量非常容易。

通过利用 Docker Compose 运行多容器设置，你可以构建以模块化、可扩展性和一致性为核心的复杂应用。

## 动手试一试

在本动手指南中，你将首先看到如何使用 `docker run` 命令构建并运行一个基于 Node.js、Nginx 反向代理和 Redis 数据库的计数器 Web 应用。你还将看到如何使用 Docker Compose 简化整个部署过程。

### 准备工作

1. 获取示例应用。如果你有 Git，可以克隆示例应用的仓库。否则，你可以下载示例应用。选择以下选项之一。

**使用 git 克隆**

在终端中使用以下命令克隆示例应用仓库：

```console
git clone https://github.com/dockersamples/nginx-node-redis
```

进入 `nginx-node-redis` 目录：

```console
cd nginx-node-redis
```

在此目录中，你会找到两个子目录：`nginx` 和 `web`。

2. [下载并安装](/get-started/get-docker/) Docker Desktop。

### 构建镜像

1. 进入 `nginx` 目录，通过运行以下命令构建镜像：

```console
docker build -t nginx .
```

2. 进入 `web` 目录，运行以下命令构建第一个 web 镜像：

```console
docker build -t web .
```

### 运行容器

1. 在运行多容器应用之前，你需要为它们创建一个网络以便相互通信。你可以使用 `docker network create` 命令来完成：

```console
docker network create sample-app
```

2. 通过运行以下命令启动 Redis 容器，该命令会将其附加到先前创建的网络并创建一个网络别名（用于 DNS 查找）：

```console
docker run -d --name redis --network sample-app --network-alias redis redis
```

3. 通过运行以下命令启动第一个 web 容器：

```console
docker run -d --name web1 -h web1 --network sample-app --network-alias web1 web
```

4. 通过运行以下命令启动第二个 web 容器：

```console
docker run -d --name web2 -h web2 --network sample-app --network-alias web2 web
```

5. 通过运行以下命令启动 Nginx 容器：

```console
docker run -d --name nginx --network sample-app -p 80:80 nginx
```

> [!NOTE]
>
> Nginx 通常用作 Web 应用的反向代理，将流量路由到后端服务器。在本例中，它将流量路由到 Node.js 后端容器（web1 或 web2）。

6. 通过运行以下命令验证容器是否已启动：

```console
docker ps
```

你会看到类似下面的输出：

```text
CONTAINER ID   IMAGE     COMMAND                  CREATED              STATUS              PORTS                NAMES
2cf7c484c144   nginx     "/docker-entrypoint.…"   9 seconds ago        Up 8 seconds        0.0.0.0:80->80/tcp   nginx
7a070c9ffeaa   web       "docker-entrypoint.s…"   19 seconds ago       Up 18 seconds                            web2
6dc6d4e60aaf   web       "docker-entrypoint.s…"   34 seconds ago       Up 33 seconds                            web1
008e0ecf4f36   redis     "docker-entrypoint.s…"   About a minute ago   Up About a minute   6379/tcp             redis
```

7. 如果你查看 Docker Desktop Dashboard，可以看到这些容器并深入了解其配置。


8. 一切启动并运行后，你可以在浏览器中打开 [http://localhost](http://localhost) 查看网站。多次刷新页面，查看处理请求的主机以及总请求数：

```console
web2: Number of visits is: 9
web1: Number of visits is: 10
web2: Number of visits is: 11
web1: Number of visits is: 12
```

> [!NOTE]
>
> 你可能已经注意到，Nginx 作为反向代理，可能在两个后端容器之间以轮询方式分发传入请求。这意味着每个请求可能轮流被定向到不同的容器（web1 和 web2）。输出显示了 web1 和 web2 容器的连续增量，而存储在 Redis 中的实际计数器值仅在响应发送回客户端后才会更新。

9. 你可以使用 Docker Desktop Dashboard，通过选择容器然后选择 **Delete** 按钮来删除容器。

## 使用 Docker Compose 简化部署

Docker Compose 提供了一种结构化且精简的方法来管理多容器部署。如前所述，使用 Docker Compose，你不需要运行多个 `docker run` 命令。你只需在单个名为 `compose.yml` 的 YAML 文件中定义整个多容器应用。让我们看看它是如何工作的。

导航到项目根目录。在此目录中，你会找到一个名为 `compose.yml` 的文件。这个 YAML 文件是所有神奇之处发生的地方。它定义了构成你的应用的所有服务以及它们的配置。每个服务指定了它的镜像、端口、volumes、网络以及功能所需的任何其他设置。

1. 使用 `docker compose up` 命令启动应用：

```console
docker compose up -d --build
```

运行此命令时，你应该会看到类似下面的输出：

```console
   ✔ Network nginx-node-redis_default   Created                                                                                                   0.0s
   ✔ Container nginx-node-redis-web2-1  Created                                                                                                   0.1s
   ✔ Container nginx-node-redis-web1-1  Created                                                                                                   0.1s
   ✔ Container nginx-node-redis-redis-1 Created                                                                                                   0.1s
   ✔ Container nginx-node-redis-nginx-1 Created   
```

2. 如果你查看 Docker Desktop Dashboard，可以看到这些容器并深入了解其配置。

   ![Docker Desktop Dashboard 截图，显示使用 Docker Compose 部署的应用栈的容器](/get-started/docker-concepts/running-containers/multi-container-applications/images/list-containers.webp?border=true)

3. 或者，你可以使用 Docker Desktop Dashboard，通过选择应用栈然后选择 **Delete** 按钮来删除容器。

   ![Docker Desktop Dashboard 截图，显示如何删除使用 Docker Compose 部署的容器](/get-started/docker-concepts/running-containers/multi-container-applications/images/delete-containers.webp?border=true)

在本指南中，你学习了与容易出错且难以管理的 `docker run` 相比，使用 Docker Compose 启动和停止多容器应用是多么容易。

## 更多资源

- [`docker container run` CLI reference](/get-started/docker-concepts/running-containers/multi-container-applications/reference/cli/docker/container/run)
- [What is Docker Compose（什么是 Docker Compose？）](/get-started/docker-concepts/the-basics/what-is-docker-compose/)