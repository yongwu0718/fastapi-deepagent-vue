# Bind mounts（绑定挂载）

当您使用 **bind mount** 时，主机上的文件或目录会从主机挂载到容器中。相比之下，当您使用 **volume** 时，会在主机上的 Docker 存储目录中创建一个新目录。Docker 创建并维护这个存储位置，但容器使用标准的文件系统操作直接访问它。

## 何时使用 **bind mounts**

**Bind mounts** 适用于以下类型的用例：

- 在 Docker 主机上的开发环境与容器之间共享源代码或构建产物。
- 当您希望在容器中创建或生成文件，并将这些文件持久化到主机的文件系统上。
- 将配置文件从主机共享到容器。这是 Docker 默认通过将主机的 `/etc/resolv.conf` 挂载到每个容器中，从而为容器提供 DNS 解析的方式。

**Bind mounts** 也可用于构建：您可以将主机的源代码绑定挂载到构建容器中，以测试、检查或编译项目。

## 将 bind mount 挂载到已有数据的目录

如果您将文件或目录绑定挂载到容器中的一个目录，而该目录中已经存在文件或目录，那么预先存在的文件会被挂载所掩盖。这类似于您将文件保存到 Linux 主机的 `/mnt` 下，然后将一个 USB 驱动器挂载到 `/mnt` 中。在 USB 驱动器卸载之前，`/mnt` 的内容将被 USB 驱动器的内容所掩盖。

对于容器，没有简单的方法来移除挂载以再次显示被掩盖的文件。最好的选择是重新创建不带挂载的容器。

## 注意事项和限制

- **Bind mounts** 默认对主机上的文件具有写访问权限。

  使用 **bind mounts** 的一个副作用是，您可以通过容器中运行的进程更改主机文件系统，包括创建、修改或删除重要的系统文件或目录。这种能力可能带来安全隐患。例如，它可能影响主机系统上的非 Docker 进程。

  您可以使用 `readonly` 或 `ro` 选项来防止容器写入挂载。

- **Bind mounts** 是针对 Docker 守护进程主机创建的，而不是客户端。

  如果您使用远程 Docker 守护进程，则无法创建 **bind mount** 来访问容器中客户端机器上的文件。

  对于 Docker Desktop，守护进程运行在 Linux 虚拟机内部，而不是直接在本机主机上。Docker Desktop 具有内置机制，可以透明地处理 **bind mounts**，允许您将本机主机的文件系统路径与在虚拟机中运行的容器共享。

- 带有 **bind mounts** 的容器与主机紧密绑定。

  **Bind mounts** 依赖主机文件系统具有特定的目录结构。这种依赖性意味着，如果在没有相同目录结构的不同主机上运行，带有 **bind mounts** 的容器可能会失败。

## 语法

要创建 **bind mount**，您可以使用 `--mount` 或 `--volume` 标志。

```console
$ docker run --mount type=bind,src=<host-path>,dst=<container-path>
$ docker run --volume <host-path>:<container-path>
```

通常，`--mount` 是首选。主要区别在于 `--mount` 标志更加明确，并且支持所有可用选项。

如果您使用 `--volume` 绑定挂载一个 Docker 主机上尚不存在的文件或目录，Docker 会自动在主机上为您创建该目录。它始终被创建为一个目录。

默认情况下，如果指定的挂载路径在主机上不存在，`--mount` 不会自动创建目录。相反，它会报错：

```console
$ docker run --mount type=bind,src=/dev/noexist,dst=/mnt/foo alpine
docker: Error response from daemon: invalid mount config for type "bind": bind source path does not exist: /dev/noexist.
```

您可以使用 `bind-create-src` 选项在主机上自动创建源目录（如果它不存在）：

```console
$ docker run --mount type=bind,src=/home/user/mydir,dst=/mnt/foo,bind-create-src alpine
```

### --mount 的选项

`--mount` 标志由多个键值对组成，用逗号分隔，每个键值对的形式为 `<key>=<value>`。键的顺序不重要。

```console
$ docker run --mount type=bind,src=<host-path>,dst=<container-path>[,<key>=<value>...]
```

`--mount type=bind` 的有效选项包括：

| 选项                           | 描述                                                                                                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `source`, `src`                | 主机上文件或目录的位置。可以是绝对路径或相对路径。                                                                                                            |
| `destination`, `dst`, `target` | 文件或目录在容器中挂载的路径。必须是绝对路径。                                                                                                                |
| `readonly`, `ro`               | 如果存在，则导致 **bind mount** 以[只读方式挂载到容器中](#use-a-read-only-bind-mount)。                                                                       |
| `bind-propagation`             | 如果存在，则更改[绑定传播](#configure-bind-propagation)。                                                                                                      |
| `bind-create-src`              | 如果源目录在主机上不存在，则自动创建它。默认情况下，如果源路径在守护进程主机上不存在，`--mount` 会产生错误。                                                   |

```console {title="示例"}
$ docker run --mount type=bind,src=.,dst=/project,ro,bind-propagation=rshared
```

### --volume 的选项

`--volume` 或 `-v` 标志由三个字段组成，用冒号 (`:`) 分隔。字段必须按正确顺序排列。

```console
$ docker run -v <host-path>:<container-path>[:opts]
```

第一个字段是要绑定挂载到容器中的主机路径。第二个字段是文件或目录在容器中挂载的路径。

第三个字段是可选的，是一个逗号分隔的选项列表。对于 **bind mount**，`--volume` 的有效选项包括：

| 选项                   | 描述                                                                                                                |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `readonly`, `ro`       | 如果存在，则导致 **bind mount** 以[只读方式挂载到容器中](#use-a-read-only-bind-mount)。                             |
| `z`, `Z`               | 配置 SELinux 标签。请参阅[配置 SELinux 标签](#configure-the-selinux-label)。                                        |
| `rprivate` (默认)      | 为此挂载将绑定传播设置为 `rprivate`。请参阅[配置绑定传播](#configure-bind-propagation)。                            |
| `private`              | 为此挂载将绑定传播设置为 `private`。请参阅[配置绑定传播](#configure-bind-propagation)。                             |
| `rshared`              | 为此挂载将绑定传播设置为 `rshared`。请参阅[配置绑定传播](#configure-bind-propagation)。                             |
| `shared`               | 为此挂载将绑定传播设置为 `shared`。请参阅[配置绑定传播](#configure-bind-propagation)。                              |
| `rslave`               | 为此挂载将绑定传播设置为 `rslave`。请参阅[配置绑定传播](#configure-bind-propagation)。                              |
| `slave`                | 为此挂载将绑定传播设置为 `slave`。请参阅[配置绑定传播](#configure-bind-propagation)。                               |

```console {title="示例"}
$ docker run -v .:/project:ro,rshared
```

## 使用 bind mount 启动容器

考虑一个场景：您有一个目录 `source`，当您构建源代码时，构建产物被保存到另一个目录 `source/target/` 中。您希望这些产物在容器中的 `/app/` 目录可用，并且希望每次在开发主机上构建源代码时，容器都能访问新的构建产物。使用以下命令将 `target/` 目录绑定挂载到容器中的 `/app/`。在 `source` 目录中运行该命令。`$(pwd)` 子命令在 Linux 或 macOS 主机上扩展为当前工作目录。如果您在 Windows 上，另请参阅 [Windows 上的路径转换](/desktop/troubleshoot-and-support/troubleshoot/topics/)。

以下 `--mount` 和 `-v` 示例产生相同的结果。除非您在运行第一个示例后删除 `devtest` 容器，否则不能同时运行它们。

`-it` 表示**创建一个交互式终端会话**，让你可以像在本地终端中一样与容器内的 shell 进行交互。

**`--mount`**

```console
$ docker run -d \
  -it \
  --name devtest \
  --mount type=bind,source="$(pwd)"/target,target=/app \
  nginx:latest
```

**`-v`**

```console
$ docker run -d \
  -it \
  --name devtest \
  -v "$(pwd)"/target:/app \
  nginx:latest
```

使用 `docker inspect devtest` 验证 **bind mount** 是否正确创建。查找 `Mounts` 部分：

```json
"Mounts": [
    {
        "Type": "bind",
        "Source": "/tmp/source/target",
        "Destination": "/app",
        "Mode": "",
        "RW": true,
        "Propagation": "rprivate"
    }
],
```

这表明挂载是一个 `bind` 挂载，显示了正确的源和目标，显示了挂载是可读写的，并且传播设置为 `rprivate`。

停止并移除容器：

```console
$ docker container rm -fv devtest
```

### 挂载到容器中的非空目录

如果您将目录绑定挂载到容器中的一个非空目录，该目录中现有的内容会被绑定挂载所掩盖。这可能是有益的，例如当您想测试应用程序的新版本而无需构建新镜像时。然而，这也可能令人意外，并且这种行为与 [volumes](/engine/storage/bind-mounts/volumes/) 不同。

这个例子是刻意极端的，它将容器 `/usr/` 目录的内容替换为主机上的 `/tmp/` 目录。在大多数情况下，这将导致容器无法正常工作。

`--mount` 和 `-v` 示例具有相同的结果。

**`--mount`**

```console
$ docker run -d \
  -it \
  --name broken-container \
  --mount type=bind,source=/tmp,target=/usr \
  nginx:latest

docker: Error response from daemon: oci runtime error: container_linux.go:262:
starting container process caused "exec: \"nginx\": executable file not found in $PATH".
```

**`-v`**

```console
$ docker run -d \
  -it \
  --name broken-container \
  -v /tmp:/usr \
  nginx:latest

docker: Error response from daemon: oci runtime error: container_linux.go:262:
starting container process caused "exec: \"nginx\": executable file not found in $PATH".
```

容器已创建但未启动。将其移除：

```console
$ docker container rm broken-container
```

## 使用只读的 bind mount

对于某些开发应用程序，容器需要写入 **bind mount**，以便将更改传播回 Docker 主机。在其他时候，容器只需要读取权限。

此示例修改了之前的示例，但在容器内的挂载点之后，将 `ro` 添加到（默认为空的）选项列表中，从而将目录挂载为只读的 **bind mount**。当存在多个选项时，用逗号分隔它们。

`--mount` 和 `-v` 示例具有相同的结果。

**`--mount`**

```console
$ docker run -d \
  -it \
  --name devtest \
  --mount type=bind,source="$(pwd)"/target,target=/app,readonly \
  nginx:latest
```

**`-v`**

```console
$ docker run -d \
  -it \
  --name devtest \
  -v "$(pwd)"/target:/app:ro \
  nginx:latest
```

使用 `docker inspect devtest` 验证 **bind mount** 是否正确创建。查找 `Mounts` 部分：

```json
"Mounts": [
    {
        "Type": "bind",
        "Source": "/tmp/source/target",
        "Destination": "/app",
        "Mode": "ro",
        "RW": false,
        "Propagation": "rprivate"
    }
],
```

停止并移除容器：

```console
$ docker container rm -fv devtest
```

## 递归挂载（Recursive mounts）

当您绑定挂载一个自身包含挂载的路径时，默认情况下这些子挂载也会被包含在绑定挂载中。此行为是可配置的，使用 `--mount` 的 `bind-recursive` 选项。此选项仅受 `--mount` 标志支持，不受 `-v` 或 `--volume` 支持。

如果绑定挂载是只读的，Docker Engine 会尽最大努力也将子挂载设为只读。这称为递归只读挂载（recursive read-only mounts）。递归只读挂载需要 Linux 内核版本 5.12 或更高。如果您运行的是较旧的内核版本，默认情况下子挂载会自动挂载为读写。尝试在内核版本低于 5.12 的系统上使用 `bind-recursive=readonly` 选项将子挂载设置为只读会导致错误。

`bind-recursive` 选项支持的值有：

| 值                       | 描述                                                                                                       |
| :---------------------- | :--------------------------------------------------------------------------------------------------------- |
| `enabled`（默认）       | 如果内核为 v5.12 或更高，只读挂载会被递归地设置为只读。否则，子挂载为读写。                                |
| `disabled`              | 忽略子挂载（不包含在绑定挂载中）。                                                                          |
| `writable`              | 子挂载为读写。                                                                                             |
| `readonly`              | 子挂载为只读。需要内核 v5.12 或更高。                                                                      |

## 配置绑定传播（Bind propagation）

绑定传播对于 **bind mounts** 和 **volumes** 都默认为 `rprivate`。它仅可配置用于 **bind mounts**，并且仅在 Linux 主机上。绑定传播是一个高级主题，许多用户从不需要配置它。

绑定传播指的是在给定 **bind mount** 内创建的挂载是否可以传播到该挂载的副本。考虑一个挂载点 `/mnt`，它也挂载在 `/tmp` 上。传播设置控制 `/tmp/a` 上的挂载是否也将在 `/mnt/a` 上可用。每个传播设置都有一个递归对应项。在递归的情况下，考虑 `/tmp/a` 也挂载为 `/foo`。传播设置控制 `/mnt/a` 和/或 `/tmp/a` 是否存在。

> [!NOTE]
> 挂载传播不适用于 Docker Desktop。

| 传播设置   | 描述                                                                                                                                                                                                          |
| :--------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `shared`   | 原始挂载的子挂载会暴露给副本挂载，并且副本挂载的子挂载也会传播回原始挂载。                                                                                                                                      |
| `slave`    | 类似于 `shared` 挂载，但只是单向的。如果原始挂载暴露了一个子挂载，副本挂载可以看到它。但是，如果副本挂载暴露了一个子挂载，原始挂载无法看到它。                                                                  |
| `private`  | 挂载是私有的。其中的子挂载不会暴露给副本挂载，并且副本挂载的子挂载也不会暴露给原始挂载。                                                                                                                        |
| `rshared`  | 与 `shared` 相同，但传播也扩展到嵌套在任何原始或副本挂载点内的挂载点。                                                                                                                                         |
| `rslave`   | 与 `slave` 相同，但传播也扩展到嵌套在任何原始或副本挂载点内的挂载点。                                                                                                                                         |
| `rprivate` | 默认值。与 `private` 相同，意味着原始或副本挂载点内任何地方的挂载点都不会向任一方向传播。                                                                                                                      |

在您可以在挂载点上设置绑定传播之前，主机文件系统需要已经支持绑定传播。

有关绑定传播的更多信息，请参阅 [Linux 内核文档中关于共享子树的内容](https://www.kernel.org/doc/Documentation/filesystems/sharedsubtree.txt)。

以下示例将 `target/` 目录挂载到容器中两次，第二次挂载同时设置了 `ro` 选项和 `rslave` 绑定传播选项。

`--mount` 和 `-v` 示例具有相同的结果。

**`--mount`**

```console
$ docker run -d \
  -it \
  --name devtest \
  --mount type=bind,source="$(pwd)"/target,target=/app \
  --mount type=bind,source="$(pwd)"/target,target=/app2,readonly,bind-propagation=rslave \
  nginx:latest
```

**`-v`**

```console
$ docker run -d \
  -it \
  --name devtest \
  -v "$(pwd)"/target:/app \
  -v "$(pwd)"/target:/app2:ro,rslave \
  nginx:latest
```

现在，如果您创建 `/app/foo/`，`/app2/foo/` 也会存在。

## 配置 SELinux 标签

如果您使用 SELinux，可以添加 `z` 或 `Z` 选项来修改正在挂载到容器中的主机文件或目录的 SELinux 标签。这会影响主机机器上的文件或目录本身，并可能产生 Docker 范围之外的后果。

- `z` 选项表示 **bind mount** 内容在多个容器之间共享。
- `Z` 选项表示 **bind mount** 内容是私有的且不共享。

使用这些选项时要格外小心。使用 `Z` 选项绑定挂载系统目录（如 `/home` 或 `/usr`）会导致您的主机无法操作，您可能需要手动重新标记主机文件。

> [!IMPORTANT]
>
> 在服务中使用 **bind mounts** 时，SELinux 标签（`:Z` 和 `:z`）以及 `:ro` 会被忽略。有关详细信息，请参阅 [moby/moby #32579](https://github.com/moby/moby/issues/32579)。

此示例设置 `z` 选项以指定多个容器可以共享 **bind mount** 的内容：

无法使用 `--mount` 标志修改 SELinux 标签。

```console
$ docker run -d \
  -it \
  --name devtest \
  -v "$(pwd)"/target:/app:z \
  nginx:latest
```

## 在 Docker Compose 中使用 bind mount

一个带有 **bind mount** 的 Docker Compose 服务如下所示：

```yaml
services:
  frontend:
    image: node:lts
    volumes:
      - type: bind
        source: ./static
        target: /opt/app/static
volumes:
  myapp:
```

有关在 Compose 中使用 `bind` 类型卷的更多信息，请参阅 [Compose 关于 volumes 顶层元素的参考](/reference/compose-file/volumes/) 和 [Compose 关于 volume 属性的参考](/reference/compose-file/services/#volumes)。

## 下一步

- 了解 [**volumes**](/engine/storage/volumes/)。
- 了解 [**tmpfs mounts**](/engine/storage/tmpfs/)。
- 了解[存储驱动（**storage drivers**）](/engine/storage/drivers/)。