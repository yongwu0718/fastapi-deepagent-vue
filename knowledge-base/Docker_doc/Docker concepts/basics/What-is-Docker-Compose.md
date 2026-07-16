# What is Docker Compose?（什么是 Docker Compose？）

## 解释

如果你一直在跟随前面的指南，那你一直在处理单 Container 应用。但现在，你想做更复杂的事情——运行数据库、消息队列、缓存或各种其他服务。是把所有东西都安装在一个 Container 里？还是运行多个 Container？如果运行多个，又如何将它们全部连接起来？

Container 的一个最佳实践是：**每个 Container 应该只做一件事，并且把它做好**。虽然这个规则也有例外，但应避免让一个 Container 做多件事的倾向。

你可以使用多个 `docker run` 命令来启动多个 Container。但很快你会发现，你需要管理网络、将 Container 连接到这些网络所需的各种标志等等。当你完成后，清理工作也会更复杂。

使用 **Docker Compose**，你可以在一个 YAML 文件中定义所有的 Container 及其配置。如果你把这个文件包含在代码仓库中，任何克隆你的仓库的人都可以通过一个简单的命令启动并运行。

重要的是要理解，Compose 是一个**声明式（declarative）** 的工具——你只需定义它，然后就可以运行。你不必每次都从头开始重建所有东西。如果你做了更改，再次运行 `docker compose up`，Compose 会协调文件中的更改并智能地应用它们。

> **Dockerfile 与 Compose file 的区别**
>
> Dockerfile 提供构建 Container Image 的指令，而 Compose file 则定义你正在运行的 Container。通常情况下，Compose file 会引用一个 Dockerfile 来构建特定服务所使用的 Image。

## 动手试一试

在本动手环节中，你将学习如何使用 Docker Compose 运行一个多 Container 应用。你将使用一个用 Node.js 构建的简单待办事项列表应用，并使用 MySQL 作为数据库服务器。

### 启动应用

按照以下指令在你的系统上运行待办事项列表应用。

1. [下载并安装](https://www.docker.com/products/docker-desktop/) Docker Desktop。
2. 打开一个终端，[克隆这个示例应用](https://github.com/dockersamples/todo-list-app)：

   ```console
   git clone https://github.com/dockersamples/todo-list-app 
   ```

3. 进入 `todo-list-app` 目录：

   ```console
   cd todo-list-app
   ```

   在这个目录中，你会找到一个名为 `compose.yaml` 的文件。这个 YAML 文件就是所有神奇之处发生的地方！它定义了构成你的应用的所有服务以及它们的配置。每个服务指定了它的 Image、端口、Volumes、网络以及其功能所需的任何其他设置。花一些时间探索这个 YAML 文件，熟悉它的结构。

4. 使用 [`docker compose up`](/reference/cli/docker/compose/up/) 命令启动应用：

   ```console
   docker compose up -d --build
   ```

   运行此命令时，你应该会看到类似这样的输出：

   ```console
   [+] Running 5/5
   ✔ app 3 layers [⣿⣿⣿]      0B/0B            Pulled          7.1s
     ✔ e6f4e57cc59e Download complete                          0.9s
     ✔ df998480d81d Download complete                          1.0s
     ✔ 31e174fedd23 Download complete                          2.5s
     ✔ 43c47a581c29 Download complete                          2.0s
   [+] Running 4/4
     ⠸ Network todo-list-app_default           Created         0.3s
     ⠸ Volume "todo-list-app_todo-mysql-data"  Created         0.3s
     ✔ Container todo-list-app-app-1           Started         0.3s
     ✔ Container todo-list-app-mysql-1         Started         0.3s
   ```

   这里发生了很多事情！需要指出几点：

   - 从 Docker Hub 下载了两个 Container Images——node 和 MySQL
   - 为你的应用创建了一个网络（Network）
   - 创建了一个 Volume 来在 Container 重启之间持久化数据库文件
   - 两个 Container 以其所有必需的配置启动

   如果这让你感到不知所措，别担心！你会掌握的！

5. 现在一切都已启动并运行，你可以在浏览器中打开 [http://localhost:3000](http://localhost:3000) 来查看网站。请注意，应用可能需要 10-15 秒才能完全启动。如果页面没有立即加载，请稍等片刻并刷新。随意添加、勾选和删除列表中的项目。

6. 如果你查看 Docker Desktop GUI，可以看到这些 Container 并深入了解其配置。

### 拆除应用

由于这个应用是使用 Docker Compose 启动的，因此在你完成后很容易将其全部拆除。

1. 在 CLI 中，使用 [`docker compose down`](/reference/cli/docker/compose/down/) 命令移除所有内容：

   ```console
   docker compose down
   ```

   你会看到类似下面的输出：

   ```console
   [+] Running 3/3
   ✔ Container todo-list-app-mysql-1  Removed        2.9s
   ✔ Container todo-list-app-app-1    Removed        0.1s
   ✔ Network todo-list-app_default    Removed        0.1s
   ```

   > **Volume 持久化（Volume persistence）**
   >
   > 默认情况下，当你拆除 Compose 栈时，Volumes **不会**被自动删除。其理念是，如果你再次启动该栈，你可能希望恢复数据。
   >
   > 如果你确实想要删除 Volumes，可以在运行 `docker compose down` 命令时添加 `--volumes` 标志：
   >
   > ```console
   > docker compose down --volumes
   > [+] Running 1/0
   > ✔ Volume todo-list-app_todo-mysql-data  Removed
   > ```

2. 或者，你可以使用 Docker Desktop GUI，通过选择应用栈然后选择 **Delete** 按钮来删除 Container。

   > **使用 GUI 管理 Compose 栈（Using the GUI for Compose stacks）**
   >
   > 请注意，如果你在 GUI 中删除 Compose 应用的 Container，它只会删除 Container。如果你还想删除网络和 Volumes，则需要手动删除。

在本演练中，你学习了如何使用 Docker Compose 启动和停止一个多 Container 应用。

## 更多资源

本页是对 Compose 的简要介绍。在以下资源中，你可以更深入地了解 Compose 以及如何编写 Compose 文件。

- [Overview of Docker Compose](/compose/)
- [Overview of Docker Compose CLI](/reference/cli/docker/compose/)
- [How Compose works](/compose/intro/compose-application-model/)