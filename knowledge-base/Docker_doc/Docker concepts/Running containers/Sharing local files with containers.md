# Sharing local files with containers（与容器共享本地文件）

## 解释

每个容器都拥有运行所需的一切，不依赖宿主机上任何预安装的依赖项。由于容器运行在隔离环境中，它们对宿主机和其他容器的影响极小。这种隔离有一个主要好处：容器最大限度地减少了与宿主机系统和其他容器的冲突。然而，这种隔离也意味着容器默认无法直接访问宿主机上的数据。

考虑这样一个场景：你有一个 Web 应用容器，需要访问存储在宿主机系统文件中的配置设置。该文件可能包含敏感数据，如数据库凭据或 API 密钥。将此类敏感信息直接存储在容器镜像中会带来安全风险，尤其是在共享镜像时。为了解决这个问题，Docker 提供了在容器隔离和宿主机数据之间架起桥梁的存储选项。

Docker 提供了两种主要的存储选项，用于持久化数据以及在宿主机和容器之间共享文件：**volume** 和 **bind mount**。

### Volume 与 Bind mount 的区别

如果你想确保容器内部生成或修改的数据即使在容器停止运行后仍然存在，你应该选择 **volume**。请参阅 Persisting container data（持久化容器数据） 以了解更多关于 volume 及其用例的信息。

如果你的宿主机上有特定的文件或目录（如配置文件或开发代码）想要直接与容器共享，那么你应该使用 **bind mount**。它就像在你的宿主机和容器之间打开了一个直接的门户进行共享。Bind mount 非常适合开发环境，因为在这些环境中，宿主机和容器之间的实时文件访问和共享至关重要。

### 在宿主机和容器之间共享文件

与 `docker run` 命令一起使用的 `-v`（或 `--volume`）和 `--mount` 标志都允许你在本地机器（宿主机）和 Docker 容器之间共享文件或目录。然而，它们的行为和用法存在一些关键差异。

`-v` 标志更简单、更方便，适用于基本的 volume 或 bind mount 操作。当使用 `-v` 或 `--volume` 时，如果宿主机位置不存在，会自动创建一个目录。

想象你是一个正在从事项目的开发人员。你的开发机器上有一个源代码目录。当你编译或构建代码时，生成的产物（编译后的代码、可执行文件、镜像等）会保存在源代码目录内的一个单独子目录中。在以下示例中，这个子目录是 `/HOST/PATH`。现在，你希望这些构建产物能够在运行你应用的 Docker 容器内被访问。此外，你希望每次重新构建代码时，容器都能自动访问最新的构建产物。

以下是使用 `docker run` 通过 bind mount 启动容器并将其映射到容器内文件位置的方法：

```console
$ docker run -v /HOST/PATH:/CONTAINER/PATH -it nginx
```

`--mount` 标志提供了更高级的功能和更精细的控制，使其适用于复杂的挂载场景或生产部署。默认情况下，如果你使用 `--mount` 来 bind mount 一个在 Docker 宿主机上尚不存在的文件或目录，`docker run` 命令不会自动为你创建它，而是会生成一个错误。

```console
$ docker run --mount type=bind,source=/HOST/PATH,target=/CONTAINER/PATH,readonly nginx
```

> [!NOTE]
>
> Docker 推荐使用 `--mount` 语法而不是 `-v`。它提供了对挂载过程更好的控制，并避免了可能出现的目录缺失问题。

### Docker 访问宿主机文件的文件权限

使用 bind mount 时，确保 Docker 拥有访问宿主机目录的必要权限至关重要。要授予读/写权限，你可以在容器创建期间使用 `:ro` 标志（只读）或 `:rw`（读写）与 `-v` 或 `--mount` 标志配合使用。
例如，以下命令授予读写访问权限：

```console
$ docker run -v HOST-DIRECTORY:/CONTAINER-DIRECTORY:rw nginx
```

只读 bind mount 允许容器访问宿主机上已挂载的文件进行读取，但不能更改或删除文件。使用读写 bind mount，容器可以修改或删除已挂载的文件，这些更改或删除也会反映在宿主机系统上。只读 bind mount 确保宿主机上的文件不会被容器意外修改或删除。

> **Synchronized File Share（同步文件共享）**
>
> 随着代码库变得越来越大，传统的文件共享方法（如 bind mount）可能会变得低效或缓慢，尤其是在需要频繁访问文件的开发环境中。[Synchronized file shares](/desktop/features/synchronized-file-sharing/) 通过利用同步文件系统缓存来提高 bind mount 性能。这种优化确保了宿主机和虚拟机（VM）之间的文件访问快速高效。

## 动手试一试

在本动手指南中，你将练习如何创建和使用 bind mount 在宿主机和容器之间共享文件。

### 运行容器

1. [下载并安装](/get-started/get-docker/) Docker Desktop。

2. 使用 [httpd](https://hub.docker.com/_/httpd) 镜像，通过以下命令启动一个容器：

   ```console
   $ docker run -d -p 8080:80 --name my_site httpd:2.4
   ```

   这将在后台启动 `httpd` 服务，并将网页发布到宿主机的 `8080` 端口。

3. 打开浏览器访问 [http://localhost:8080](http://localhost:8080) 或使用 curl 命令验证其是否正常工作。

    ```console
    $ curl localhost:8080
    ```

### 使用 Bind mount

使用 bind mount，你可以将宿主机上的配置文件映射到容器内的特定位置。在此示例中，你将看到如何使用 bind mount 更改网页的外观：

1. 使用 Docker Desktop Dashboard 删除现有容器：

   ![Docker Desktop Dashboard 截图，显示如何删除 httpd 容器](/get-started/docker-concepts/running-containers/sharing-local-files/images/delete-httpd-container.webp?border=true)

2. 在宿主机系统上创建一个名为 `public_html` 的新目录。

    ```console
    $ mkdir public_html
    ```

3. 进入新创建的 `public_html` 目录，创建一个名为 `index.html` 的文件，内容如下。这是一个基本的 HTML 文档，创建了一个简单的网页，用友好的鲸鱼欢迎你。

    ```html
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title> My Website with a Whale & Docker!</title>
    </head>
    <body>
    <h1>Whalecome!!</h1>
    <p>Look! There's a friendly whale greeting you!</p>
    <pre id="docker-art">
       ##         .
      ## ## ##        ==
     ## ## ## ## ##    ===
     /"""""""""""""""""\___/ ===
   {                       /  ===-
   \______ O           __/
    \    \         __/
     \____\_______/

    Hello from Docker!
    </pre>
    </body>
    </html>
    ```

4. 是时候运行容器了。`--mount` 和 `-v` 示例产生相同的结果。除非在运行第一个容器后删除 `my_site` 容器，否则不能同时运行两者。

   **`-v`**

   ```console
   $ docker run -d --name my_site -p 8080:80 -v .:/usr/local/apache2/htdocs/ httpd:2.4
   ```

   **`--mount`**

   ```console
   $ docker run -d --name my_site -p 8080:80 --mount type=bind,source=./,target=/usr/local/apache2/htdocs/ httpd:2.4
   ```

   > [!TIP]  
   > 在 Windows PowerShell 中使用 `-v` 或 `--mount` 标志时，你需要提供目录的绝对路径，而不是仅仅使用 `./`。这是因为 PowerShell 处理相对路径的方式与 bash（常用于 Mac 和 Linux 环境）不同。

   现在一切已启动并运行，你应该能够通过 [http://localhost:8080](http://localhost:8080) 访问该站点，并看到一个用友好的鲸鱼欢迎你的新网页。

### 在 Docker Desktop Dashboard 中访问文件

1. 你可以通过选择容器的 **Files** 选项卡，然后选择 `/usr/local/apache2/htdocs/` 目录中的文件来查看容器内已挂载的文件。然后选择 **Open file editor**。

   ![Docker Desktop Dashboard 截图，显示容器内已挂载的文件](/get-started/docker-concepts/running-containers/sharing-local-files/images/mounted-files.webp?border=true)

2. 在宿主机上删除该文件，并验证该文件在容器中也被删除。你会发现在 Docker Desktop Dashboard 的 **Files** 下这些文件不再存在。

   ![Docker Desktop Dashboard 截图，显示容器内已删除的文件](/get-started/docker-concepts/running-containers/sharing-local-files/images/deleted-files.webp?border=true)

3. 在宿主机系统上重新创建 HTML 文件，然后看到该文件在 Docker Desktop Dashboard 的 **Containers** 下的 **Files** 选项卡中重新出现。此时，你也应该能够访问该站点。

### 停止容器

容器会一直运行，直到你停止它。

1. 进入 Docker Desktop Dashboard 的 **Containers** 视图。
2. 找到你想要停止的容器。
3. 在 **Actions** 列中选择 **Stop** 操作。

## 更多资源

以下资源将帮助你进一步学习 bind mounts：

- [Manage data in Docker](/storage/)
- [Volumes](/storage/volumes/)
- [Bind mounts](/storage/bind-mounts/)
- [Running containers](/reference/run/)
- [Troubleshoot storage errors](/storage/troubleshooting_volume_errors/)
- [Persisting container data](/get-started/docker-concepts/running-containers/persisting-container-data/)

## 下一步

现在你已经学习了与容器共享本地文件，接下来该学习多容器应用了。

[Multi-container applications（多容器应用）](/get-started/docker-concepts/running-containers/sharing-local-files/Multi-container%20applications)