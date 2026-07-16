# Understanding the image layers（理解 Image 层）

## 解释

正如你在 What is an image 中学到的，Container Image 由层（layers）组成。并且这些层一旦被创建，就是不可变的（immutable）。但这实际上意味着什么？这些层又是如何被用来创建 Container 可以使用的文件系统的呢？

### Image layers（镜像层）

Image 中的每一层都包含一组文件系统更改——添加、删除或修改。让我们来看一个理论上的 Image：

1. 第一层添加基本命令和一个包管理器，例如 apt。
2. 第二层安装 Python 运行时和用于依赖管理的 pip。
3. 第三层复制应用的特定 `requirements.txt` 文件。
4. 第四层安装该应用的特定依赖项。
5. 第五层复制应用的实际源代码。

这个例子可能看起来像这样：
![alt text](container_image_layers.webp)

这样做的好处是允许层在不同 Image 之间被重用。例如，假设你想创建另一个 Python 应用。由于分层，你可以利用相同的 Python 基础层。这将使构建更快，并减少分发 Image 所需的存储和带宽。Image 分层可能类似于下面的样子：

![alt text](container_image_layer_reuse.webp)

层（Layers）让你可以通过重用他人的基础层来扩展他们的 Image，只添加你的应用所需的数据。

### 堆叠层（Stacking the layers）

分层是通过内容可寻址存储（content-addressable storage）和联合文件系统（union filesystems）实现的。虽然这会变得技术性，但下面是它的工作原理：

1. 每一层下载后，会被解压到主机文件系统上的自己的目录中。
2. 当你从 Image 运行 Container 时，会创建一个联合文件系统，其中层被堆叠在一起，创建一个新的统一视图。
3. 当 Container 启动时，其根目录通过 `chroot` 设置为此统一目录的位置。

当联合文件系统被创建时，除了 Image 层之外，还会为正在运行的 Container 专门创建一个目录。这允许 Container 进行文件系统更改，同时保持原始 Image 层不被修改。这使得你可以从同一个底层 Image 运行多个 Container。

## 动手试一试

在本动手指南中，你将使用 [`docker container commit`](https://docs.docker.com/reference/cli/docker/container/commit/) 命令手动创建新的 Image 层。请注意，你很少会以这种方式创建 Image，因为你**通常会使用 Dockerfile**。但是，这有助于你更容易地理解整个工作原理。

### 创建一个 Base Image（基础镜像）

在第一步中，你将创建自己的 Base Image，然后将其用于后续步骤。

1. [下载并安装](https://www.docker.com/products/docker-desktop/) Docker Desktop。

2. 在终端中，运行以下命令启动一个新的 Container：

   ```console
   $ docker run --name=base-container -ti ubuntu
   ```

   一旦 Image 被下载并且 Container 启动，你应该会看到一个新的 shell 提示符。这是在你的 Container 内部运行的。它看起来类似于下面这样（Container ID 会有所不同）：

   ```console
   root@d8c5ca119fcd:/#
   ```

3. 在 Container 内部，运行以下命令来安装 Node.js：

   ```console
   $ apt update && apt install -y nodejs
   ```

   当此命令运行时，它会在 Container 内部下载并安装 Node。在联合文件系统的上下文中，这些文件系统更改发生在这个 Container 独有的目录中。

4. 通过运行以下命令验证 Node 是否已安装：

   ```console
   $ node -e 'console.log("Hello world!")'
   ```

   然后你应该会在控制台中看到 "Hello world!" 出现。

5. 现在你已经安装了 Node，你可以将所做的更改保存为一个新的 Image 层，从中你可以启动新的 Container 或构建新的 Image。为此，你将使用 [`docker container commit`](https://docs.docker.com/reference/cli/docker/container/commit/) 命令。在一个新的终端中运行以下命令：

   ```console
   $ docker container commit -m "Add node" base-container node-base
   ```

6. 使用 `docker image history` 命令查看你的 Image 的层：

   ```console
   $ docker image history node-base
   ```

   你会看到类似于下面的输出：

   ```console
   IMAGE          CREATED          CREATED BY                                      SIZE      COMMENT
   9e274734bb25   10 seconds ago   /bin/bash                                       157MB     Add node
   cd1dba651b30   7 days ago       /bin/sh -c #(nop)  CMD ["/bin/bash"]            0B
   <missing>      7 days ago       /bin/sh -c #(nop) ADD file:6089c6bede9eca8ec…   110MB
   <missing>      7 days ago       /bin/sh -c #(nop)  LABEL org.opencontainers.…   0B
   <missing>      7 days ago       /bin/sh -c #(nop)  LABEL org.opencontainers.…   0B
   <missing>      7 days ago       /bin/sh -c #(nop)  ARG LAUNCHPAD_BUILD_ARCH     0B
   <missing>      7 days ago       /bin/sh -c #(nop)  ARG RELEASE                  0B
   ```

   注意顶行的 "Add node" 注释。这一层包含你刚刚安装的 Node.js。

7. 为了证明你的 Image 已经安装了 Node，你可以使用这个新 Image 启动一个新的 Container：

   ```console
   $ docker run node-base node -e "console.log('Hello again')"
   ```

   这样，你应该会在终端中得到 "Hello again" 输出，表明 Node 已安装并正常工作。

8. 现在你已经完成了 Base Image 的创建，可以删除那个 Container 了：

   ```console
   $ docker rm -f base-container
   ```

> **Base image 定义**
>
> Base Image 是构建其他 Image 的基础。可以使用任何 Image 作为 Base Image。然而，有些 Image 被特意创建为构建块，为应用提供基础或起点。
>
> 在这个例子中，你可能不会部署这个 `node-base` Image，因为它实际上还没有做任何事情。但它是你可以用于其他构建的基础。

### 构建一个 App Image

现在你已经有了一个 Base Image，你可以扩展该 Image 来构建额外的 Image。

1. 使用新创建的 `node-base` Image 启动一个新的 Container：

   ```console
   $ docker run --name=app-container -ti node-base
   ```

2. 在这个 Container 内部，运行以下命令来创建一个 Node 程序：

   ```console
   $ echo 'console.log("Hello from an app")' > app.js
   ```

   要运行这个 Node 程序，你可以使用以下命令并在屏幕上看到打印的消息：

   ```console
   $ node app.js
   ```

3. 在另一个终端中，运行以下命令将此 Container 的更改保存为一个新的 Image：

   ```console
   $ docker container commit -c "CMD node app.js" -m "Add app" app-container sample-app
   ```

   这个命令不仅创建了一个名为 `sample-app` 的新 Image，还向 Image 添加了额外的配置，以设置启动 Container 时的默认命令。在这种情况下，你将其设置为自动运行 `node app.js`。

4. 在 Container 外部的终端中，运行以下命令查看更新后的层：

   ```console
   $ docker image history sample-app
   ```

   然后你会看到类似下面的输出。注意顶层注释是 "Add app"，下一层是 "Add node"：

   ```console
   IMAGE          CREATED              CREATED BY                                      SIZE      COMMENT
   c1502e2ec875   About a minute ago   /bin/bash                                       33B       Add app
   5310da79c50a   4 minutes ago        /bin/bash                                       126MB     Add node
   2b7cc08dcdbb   5 weeks ago          /bin/sh -c #(nop)  CMD ["/bin/bash"]            0B
   <missing>      5 weeks ago          /bin/sh -c #(nop) ADD file:07cdbabf782942af0…   69.2MB
   <missing>      5 weeks ago          /bin/sh -c #(nop)  LABEL org.opencontainers.…   0B
   <missing>      5 weeks ago          /bin/sh -c #(nop)  LABEL org.opencontainers.…   0B
   <missing>      5 weeks ago          /bin/sh -c #(nop)  ARG LAUNCHPAD_BUILD_ARCH     0B
   <missing>      5 weeks ago          /bin/sh -c #(nop)  ARG RELEASE                  0B
   ```

5. 最后，使用全新的 Image 启动一个新的 Container。由于你已经指定了默认命令，可以使用以下命令：

   ```console
   $ docker run sample-app
   ```

   你应该会在终端中看到你的问候语出现，它来自你的 Node 程序。

6. 现在你已经完成了 Container 的操作，可以使用以下命令删除它们：

   ```console
   $ docker rm -f app-container
   ```

## 更多资源

如果你想更深入地学习所学内容，请查看以下资源：

- [`docker image history`](/reference/cli/docker/image/history/)
- [`docker container commit`](/reference/cli/docker/container/commit/)

## 下一步

正如前面所暗示的，大多数 Image 构建并不使用 `docker container commit`。相反，你将使用 Dockerfile，它可以为你自动化这些步骤。

[Writing a Dockerfile（编写 Dockerfile）](/get-started/docker-concepts/building-images/understanding-image-layers/writing-a-dockerfile)