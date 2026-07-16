# What is an image?（什么是 Image？）

## 解释

既然 [Container](What_is_a_container.md) 是一个隔离的进程，那么它从哪里获取文件和配置？如何共享这些环境？

这就是 Container Image 的作用。**Container Image（容器镜像）** 是一个标准化的包，包含运行一个 Container 所需的所有文件、二进制文件、库和配置。

对于一个 [PostgreSQL](https://hub.docker.com/_/postgres) Image，该 Image 会打包数据库的二进制文件、配置文件和其他依赖项。对于一个 Python Web 应用，它会包含 Python 运行时、你的应用代码以及所有的依赖项。

Image 有两个重要原则：

1. **Image 是不可变的（Immutable）**。一旦 Image 被创建，就不能被修改。你只能创建一个新的 Image，或者在其之上添加更改。

2. **Container Image 由层（Layers）组成**。每一层代表一组文件系统更改，包括添加、删除或修改文件。

这两个原则让你可以扩展现有 Image 或向其添加内容。例如，如果你正在构建一个 Python 应用，你可以从 [Python Image](https://hub.docker.com/_/python) 开始，然后添加额外的层来安装应用的依赖项并添加你的代码。这让你可以专注于你的应用，而不是 Python 本身。

### 查找 Images（Finding images）

[Docker Hub](https://hub.docker.com) 是用于存储和分发 Image 的默认全球市场。它拥有超过 10 万个由开发者创建的 Image，你可以在本地运行它们。你可以搜索 Docker Hub 的 Images 并直接从 Docker Desktop 运行它们。

Docker Hub 提供了多种由 Docker 支持或认可的 Images，称为 Docker Trusted Content（Docker 可信内容）。它们提供完全托管的服务，或者作为你自己 Image 的优秀起点。这些包括：

- **Docker Official Images（Docker 官方镜像）**：一套经过筛选的 Docker 仓库，是大多数用户的起点，也是 Docker Hub 上最安全的镜像之一。
- **Docker Hardened Images（Docker 强化镜像）**：极简、安全、生产就绪的 Image，具有接近零的 CVE（常见漏洞与暴露），旨在减少攻击面并简化合规性。在 Apache 2.0 下免费且开源。
- **Docker Verified Publishers（Docker 验证发布者）**：由 Docker 验证的商业发布者提供的高质量 Image。
- **Docker-Sponsored Open Source（Docker 赞助的开源项目）**：由 Docker 通过其开源项目赞助的开源项目发布和维护的 Image。

例如，[Redis](https://hub.docker.com/_/redis) 和 [Memcached](https://hub.docker.com/_/memcached) 就是几个流行的、开箱即用的 Docker Official Images。你可以下载这些 Image，并在几秒钟内让这些服务启动并运行。还有一些基础 Image，比如 [Node.js](https://hub.docker.com/_/node) Docker Image，你可以将其作为起点，并添加自己的文件和配置。对于需要增强安全性的生产工作负载，Docker Hardened Images 提供了流行 Image（如 Node.js、Python 和 Go）的极简变体。

## 动手试一试

### 使用 GUI（Using the GUI）

在本动手环节中，你将学习如何使用 Docker Desktop GUI 搜索和拉取（pull）一个 Container Image。

#### 搜索并下载一个 Image

1. 打开 Docker Desktop Dashboard，在左侧导航菜单中选择 **Images** 视图。
2. 选择 **Search images to run** 按钮。如果看不到该按钮，请选择屏幕顶部的 _全局搜索栏_。
3. 在 **Search** 字段中输入 "welcome-to-docker"。搜索完成后，选择 `docker/welcome-to-docker` Image。
4. 选择 **Pull** 下载该 Image。

#### 了解该 Image

下载完一个 Image 后，你可以通过 GUI 或 CLI 了解关于该 Image 的很多详细信息。

1. 在 Docker Desktop Dashboard 中，选择 **Images** 视图。
2. 选择 **docker/welcome-to-docker** Image 以打开该 Image 的详细信息。
3. Image 详情页面会向你展示有关该 Image 的层（Layers）、Image 中安装的包和库，以及任何已发现的漏洞的信息。

### 使用 CLI（Using the CLI）

按照以下指令使用 CLI 搜索并拉取一个 Docker Image，以查看其层。

#### 搜索并下载一个 Image

1. 打开终端，使用 [`docker search`](/reference/cli/docker/search/) 命令搜索 Images：

   ```console
   docker search docker/welcome-to-docker
   ```

   你会看到类似下面的输出：

   ```console
   NAME                       DESCRIPTION                                     STARS     OFFICIAL
   docker/welcome-to-docker   Docker image for new users getting started w…   20
   ```

   该输出显示有关 Docker Hub 上可用相关 Image 的信息。

2. 使用 [`docker pull`](/reference/cli/docker/image/pull/) 命令拉取 Image：

   ```console
   docker pull docker/welcome-to-docker
   ```

   你会看到类似下面的输出：

   ```console
   Using default tag: latest
   latest: Pulling from docker/welcome-to-docker
   579b34f0a95b: Download complete
   d11a451e6399: Download complete
   1c2214f9937c: Download complete
   b42a2f288f4d: Download complete
   54b19e12c655: Download complete
   1fb28e078240: Download complete
   94be7e780731: Download complete
   89578ce72c35: Download complete
   Digest: sha256:eedaff45e3c78538087bdd9dc7afafac7e110061bbdd836af4104b10f10ab693
   Status: Downloaded newer image for docker/welcome-to-docker:latest
   docker.io/docker/welcome-to-docker:latest
   ```

   每一行代表 Image 的一个不同的已下载层。请记住，每一层都是一组文件系统更改，并提供 Image 的功能。

#### 了解该 Image

1. 使用 [`docker image ls`](/reference/cli/docker/image/ls/) 命令列出你下载的 Images：

   ```console
   docker image ls
   ```

   你会看到类似下面的输出：

   ```console
   REPOSITORY                 TAG       IMAGE ID       CREATED        SIZE
   docker/welcome-to-docker   latest    eedaff45e3c7   4 months ago   29.7MB
   ```

   该命令显示当前系统上可用的 Docker Images 列表。`docker/welcome-to-docker` 的总大小约为 29.7MB。

   > **Image 大小（Image size）**
   >
   > 这里显示的 Image 大小反映的是 Image 的未压缩大小，而不是层的下载大小。

2. 使用 [`docker image history`](/reference/cli/docker/image/history/) 命令列出 Image 的层：

   ```console
   docker image history docker/welcome-to-docker
   ```

   你会看到类似下面的输出：

   ```console
   IMAGE          CREATED        CREATED BY                                      SIZE      COMMENT
   648f93a1ba7d   4 months ago   COPY /app/build /usr/share/nginx/html # buil…   1.6MB     buildkit.dockerfile.v0
   <missing>      5 months ago   /bin/sh -c #(nop)  CMD ["nginx" "-g" "daemon…   0B
   <missing>      5 months ago   /bin/sh -c #(nop)  STOPSIGNAL SIGQUIT           0B
   <missing>      5 months ago   /bin/sh -c #(nop)  EXPOSE 80                    0B
   <missing>      5 months ago   /bin/sh -c #(nop)  ENTRYPOINT ["/docker-entr…   0B
   <missing>      5 months ago   /bin/sh -c #(nop) COPY file:9e3b2b63db9f8fc7…   4.62kB
   <missing>      5 months ago   /bin/sh -c #(nop) COPY file:57846632accc8975…   3.02kB
   <missing>      5 months ago   /bin/sh -c #(nop) COPY file:3b1b9915b7dd898a…   298B
   <missing>      5 months ago   /bin/sh -c #(nop) COPY file:caec368f5a54f70a…   2.12kB
   <missing>      5 months ago   /bin/sh -c #(nop) COPY file:01e75c6dd0ce317d…   1.62kB
   <missing>      5 months ago   /bin/sh -c set -x     && addgroup -g 101 -S …   9.7MB
   <missing>      5 months ago   /bin/sh -c #(nop)  ENV PKG_RELEASE=1            0B
   <missing>      5 months ago   /bin/sh -c #(nop)  ENV NGINX_VERSION=1.25.3     0B
   <missing>      5 months ago   /bin/sh -c #(nop)  LABEL maintainer=NGINX Do…   0B
   <missing>      5 months ago   /bin/sh -c #(nop)  CMD ["/bin/sh"]              0B
   <missing>      5 months ago   /bin/sh -c #(nop) ADD file:ff3112828967e8004…   7.66MB
   ```

   该输出显示了所有的层、它们的大小以及用于创建该层的命令。

   > **查看完整命令（Viewing the full command）**
   >
   > 如果在命令中添加 `--no-trunc` 标志，你将看到完整的命令。请注意，由于输出是表格形式的，较长的命令会导致输出难以浏览。

在本演练中，你搜索并拉取了一个 Docker Image。除了拉取 Docker Image 之外，你还了解了 Docker Image 的层。

