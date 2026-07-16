# Volumes（卷）

**Volumes** 是用于容器的持久化数据存储，由 Docker 创建和管理。您可以使用 `docker volume create` 命令显式创建卷，也可以在创建容器或服务时由 Docker 自动创建卷。

创建卷时，它会存储在 Docker 主机上的一个目录中。当您将卷挂载到容器时，这个目录就会被挂载到容器中。这与 **bind mounts** 的工作方式类似，不同之处在于 **volumes** 由 Docker 管理，并且与主机的核心功能隔离。

## 何时使用 **volumes**

**Volumes** 是持久化由 Docker 容器生成和使用的数据的首选机制。[**bind mounts**](/engine/storage/volumes/bind-mounts/) 依赖于主机的目录结构和操作系统，而 **volumes** 则完全由 Docker 管理。对于以下用例，**volumes** 是一个不错的选择：

- **Volumes** 比 **bind mounts** 更容易备份或迁移。
- 您可以使用 Docker CLI 命令或 Docker API 来管理 **volumes**。
- **Volumes** 同时适用于 Linux 和 Windows 容器。
- **Volumes** 可以更安全地在多个容器之间共享。
- 新卷的内容可以由容器或构建预先填充。
- 当您的应用程序需要高性能 I/O 时。

如果您需要从主机访问文件，则 **volumes** 不是一个好的选择，因为卷完全由 Docker 管理。如果您需要同时从容器和主机访问文件或目录，请使用 [**bind mounts**](/engine/storage/volumes/bind-mounts/)。

**Volumes** 通常比直接将数据写入容器更好，因为卷不会增加使用它的容器的大小。使用卷也更快；写入容器的可写层需要[存储驱动](/engine/storage/drivers/)来管理文件系统。存储驱动使用 Linux 内核提供联合文件系统。与直接写入主机文件系统的卷相比，这种额外的抽象会降低性能。

如果您的容器生成非持久状态数据，请考虑使用 [**tmpfs mount**](/engine/storage/volumes/tmpfs/)，以避免将数据永久存储在任何地方，并通过避免写入容器的可写层来提高容器的性能。

**Volumes** 使用 `rprivate`（递归私有）绑定传播，并且卷的绑定传播不可配置。

## 卷的生命周期

卷的内容存在于给定容器的生命周期之外。当容器被销毁时，可写层也会随之销毁。使用卷可以确保即使使用该卷的容器被删除，数据也会被持久化。

一个给定的卷可以同时挂载到多个容器。当没有正在运行的容器使用某个卷时，该卷仍然对 Docker 可用，并且不会自动删除。您可以使用 `docker volume prune` 删除未使用的卷。

## 将卷挂载到已有数据的目录

如果您将一个 _非空卷_ 挂载到容器中的一个目录，而该目录中已经存在文件或目录，那么预先存在的文件会被挂载所掩盖。这类似于您将文件保存到 Linux 主机的 `/mnt` 下，然后将一个 USB 驱动器挂载到 `/mnt` 中。在 USB 驱动器卸载之前，`/mnt` 的内容将被 USB 驱动器的内容所掩盖。

对于容器，没有简单的方法来移除挂载以再次显示被掩盖的文件。最好的选择是重新创建不带挂载的容器。

如果您将一个 _空卷_ 挂载到容器中的一个目录，而该目录中已经存在文件或目录，那么默认情况下，这些文件或目录会被传播（复制）到卷中。类似地，如果您启动一个容器并指定一个尚不存在的卷，则会为您创建一个空卷。这是预先填充另一个容器需要的数据的好方法。

要防止 Docker 将容器中预先存在的文件复制到空卷中，请使用 `volume-nocopy` 选项，请参阅 [--mount 的选项](#options-for---mount)。

## 命名卷和匿名卷

卷可以是有名称的（named）或匿名的（anonymous）。匿名卷被赋予一个随机名称，该名称在给定的 Docker 主机上保证唯一。与命名卷一样，匿名卷即使在使用它们的容器被删除后也会持久存在，除非您在创建容器时使用了 `--rm` 标志，在这种情况下，与该容器关联的匿名卷将被销毁。请参阅[移除匿名卷](#remove-anonymous-volumes)。

如果您连续创建多个容器，每个容器都使用匿名卷，那么每个容器都会创建自己的卷。匿名卷不会自动在容器之间重用或共享。要在两个或多个容器之间共享一个匿名卷，您必须使用随机卷 ID 来挂载该匿名卷。

## 语法

要在 `docker run` 命令中挂载卷，您可以使用 `--mount` 或 `--volume` 标志。

```console
$ docker run --mount type=volume,src=<volume-name>,dst=<mount-path>
$ docker run --volume <volume-name>:<mount-path>
```

通常，`--mount` 是首选。主要区别在于 `--mount` 标志更加明确，并且支持所有可用选项。

如果您需要以下功能，则必须使用 `--mount`：

- 指定[卷驱动选项](#use-a-volume-driver)
- 挂载[卷的子目录](#mount-a-volume-subdirectory)
- 将卷挂载到 Swarm 服务中

### --mount 的选项

`--mount` 标志由多个键值对组成，用逗号分隔，每个键值对的形式为 `<key>=<value>`。键的顺序不重要。

```console
$ docker run --mount type=volume[,src=<volume-name>],dst=<mount-path>[,<key>=<value>...]
```

`--mount type=volume` 的有效选项包括：

| 选项                           | 描述                                                                                                                                                                                                                     |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `source`, `src`                | 挂载的源。对于命名卷，这是卷的名称。对于匿名卷，省略此字段。                                                                                                       |
| `destination`, `dst`, `target` | 文件或目录在容器中挂载的路径。                                                                                                                                                               |
| `volume-subpath`               | 卷中要挂载到容器的子目录路径。在将卷挂载到容器之前，该子目录必须存在于卷中。请参阅[挂载卷的子目录](#mount-a-volume-subdirectory)。 |
| `readonly`, `ro`               | 如果存在，则导致卷以[只读方式挂载到容器中](#use-a-read-only-volume)。                                                                                                                         |
| `volume-nocopy`                | 如果存在，则在卷为空时，不会将目标位置的数据复制到卷中。默认情况下，如果空卷被挂载，目标位置的内容会被复制到卷中。                                              |
| `volume-opt`                   | 可以多次指定，采用由选项名称及其值组成的键值对。                                                                                                                            |

```console {title="示例"}
$ docker run --mount type=volume,src=myvolume,dst=/data,ro,volume-subpath=/foo
```

### --volume 的选项

`--volume` 或 `-v` 标志由三个字段组成，用冒号 (`:`) 分隔。字段必须按正确顺序排列。

```console
$ docker run -v [<volume-name>:]<mount-path>[:opts]
```

对于命名卷，第一个字段是卷的名称，并且在给定的主机上是唯一的。对于匿名卷，省略第一个字段。第二个字段是文件或目录在容器中挂载的路径。

第三个字段是可选的，是一个逗号分隔的选项列表。对于数据卷，`--volume` 的有效选项包括：

| 选项             | 描述                                                                                                                                                                        |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `readonly`, `ro` | 如果存在，则导致卷以[只读方式挂载到容器中](#use-a-read-only-volume)。                                                                                                            |
| `volume-nocopy`  | 如果存在，则在卷为空时，不会将目标位置的数据复制到卷中。默认情况下，如果空卷被挂载，目标位置的内容会被复制到卷中。 |

```console {title="示例"}
$ docker run -v myvolume:/data:ro
```

## 创建和管理卷

与 **bind mount** 不同，您可以在任何容器的范围之外创建和管理卷。

创建卷：

```console
$ docker volume create my-vol
```

列出卷：

```console
$ docker volume ls

local               my-vol
```

检查卷：

```console
$ docker volume inspect my-vol
[
    {
        "Driver": "local",
        "Labels": {},
        "Mountpoint": "/var/lib/docker/volumes/my-vol/_data",
        "Name": "my-vol",
        "Options": {},
        "Scope": "local"
    }
]
```

删除卷：

```console
$ docker volume rm my-vol
```

## 使用卷启动容器

如果您启动一个容器时指定了一个尚不存在的卷，Docker 会为您创建该卷。以下示例将卷 `myvol2` 挂载到容器中的 `/app/` 目录。

以下 `-v` 和 `--mount` 示例产生相同的结果。您不能同时运行它们，除非在运行第一个示例后删除 `devtest` 容器和 `myvol2` 卷。

**`--mount`**

```console
$ docker run -d \
  --name devtest \
  --mount source=myvol2,target=/app \
  nginx:latest
```

**`-v`**

```console
$ docker run -d \
  --name devtest \
  -v myvol2:/app \
  nginx:latest
```

使用 `docker inspect devtest` 验证 Docker 是否创建了卷并正确挂载。查找 `Mounts` 部分：

```json
"Mounts": [
    {
        "Type": "volume",
        "Name": "myvol2",
        "Source": "/var/lib/docker/volumes/myvol2/_data",
        "Destination": "/app",
        "Driver": "local",
        "Mode": "",
        "RW": true,
        "Propagation": ""
    }
],
```

这表明挂载是一个卷，显示了正确的源和目标，并且挂载是可读写的。

停止容器并删除卷。注意删除卷是一个单独的步骤。

```console
$ docker container stop devtest

$ docker container rm devtest

$ docker volume rm myvol2
```

## 在 Docker Compose 中使用卷

以下示例展示了一个带有卷的单个 Docker Compose 服务：

```yaml
services:
  frontend:
    image: node:lts
    volumes:
      - myapp:/home/node/app
volumes:
  myapp:
```

首次运行 `docker compose up` 时会创建一个卷。当您随后运行该命令时，Docker 会重用同一个卷。

您可以在 Compose 外部直接使用 `docker volume create` 创建卷，然后在 `compose.yaml` 中引用它，如下所示：

```yaml
services:
  frontend:
    image: node:lts
    volumes:
      - myapp:/home/node/app
volumes:
  myapp:
    external: true
```

有关在 Compose 中使用卷的更多信息，请参阅 Compose 规范中的 [Volumes](/reference/compose-file/volumes/) 部分。

### 使用卷启动服务

当您启动一个服务并定义一个卷时，每个服务容器都使用自己的本地卷。如果您使用 `local` 卷驱动，则没有任何容器可以共享此数据。但是，某些卷驱动确实支持共享存储。

以下示例启动了一个带有四个副本的 `nginx` 服务，每个副本都使用一个名为 `myvol2` 的本地卷。

```console
$ docker service create -d \
  --replicas=4 \
  --name devtest-service \
  --mount source=myvol2,target=/app \
  nginx:latest
```

用于在 Swarm 集群中部署一个服务。具体解释如下：

- **`docker service create`**：在 Swarm 模式下创建一个新服务。
- **`-d`**：以 detached 模式运行，命令执行后立即返回，不附加到服务日志。
- **`--replicas=4`**：指定服务的副本数量为 4，即 Swarm 会调度并保持 4 个相同的容器实例同时运行。
- **`--name devtest-service`**：为服务命名为 `devtest-service`。
- **`--mount source=myvol2,target=/app`**：挂载一个名为 `myvol2` 的 **volume**（卷）到容器内的 `/app` 目录。这意味着容器中 `/app` 路径下的数据会持久化到该卷中，并且该卷可以在多个副本之间共享（如果卷驱动支持共享存储，否则每个副本可能使用独立的本地卷）。
- **`nginx:latest`**：指定使用 `nginx` 镜像的 `latest` 标签。

**总结**：这条命令会在 Swarm 中创建一个名为 `devtest-service` 的服务，该服务运行 4 个 Nginx 容器，每个容器都将名为 `myvol2` 的卷挂载到 `/app` 目录，用于数据持久化或共享。

使用 `docker service ps devtest-service` 验证服务是否正在运行：

```console
$ docker service ps devtest-service

ID                  NAME                IMAGE               NODE                DESIRED STATE       CURRENT STATE            ERROR               PORTS
4d7oz1j85wwn        devtest-service.1   nginx:latest        moby                Running             Running 14 seconds ago
```

您可以删除服务以停止正在运行的任务：

```console
$ docker service rm devtest-service
```

删除服务不会删除服务创建的任何卷。删除卷是一个单独的步骤。

## 使用容器填充卷

如果您启动一个创建新卷的容器，并且该容器在要挂载的目录（例如 `/app/`）中有文件或目录，Docker 会将该目录的内容复制到卷中。然后，容器挂载并使用该卷，其他使用该卷的容器也可以访问预先填充的内容。

为了演示这一点，以下示例启动了一个 `nginx` 容器，并使用容器的 `/usr/share/nginx/html` 目录的内容填充新卷 `nginx-vol`。这是 Nginx 存储其默认 HTML 内容的位置。

`--mount` 和 `-v` 示例产生相同的结果。

**`--mount`**

```console
$ docker run -d \
  --name=nginxtest \
  --mount source=nginx-vol,destination=/usr/share/nginx/html \
  nginx:latest
```

**`-v`**

```console
$ docker run -d \
  --name=nginxtest \
  -v nginx-vol:/usr/share/nginx/html \
  nginx:latest
```

运行完这些示例中的任何一个后，运行以下命令以清理容器和卷。注意删除卷是一个单独的步骤。

```console
$ docker container stop nginxtest

$ docker container rm nginxtest

$ docker volume rm nginx-vol
```

## 使用只读卷

对于某些开发应用程序，容器需要写入 **bind mount**，以便将更改传播回 Docker 主机。在其他时候，容器只需要对数据的读取访问权限。多个容器可以挂载同一个卷。您可以同时将单个卷挂载为某些容器的 `read-write`（读写），并为其他容器挂载为 `read-only`（只读）。

以下示例修改了上一个示例。它通过在容器内的挂载点之后将 `ro` 添加到（默认为空的）选项列表中来将目录挂载为只读卷。当存在多个选项时，您可以使用逗号分隔它们。

`--mount` 和 `-v` 示例具有相同的结果。

**`--mount`**

```console
$ docker run -d \
  --name=nginxtest \
  --mount source=nginx-vol,destination=/usr/share/nginx/html,readonly \
  nginx:latest
```

**`-v`**

```console
$ docker run -d \
  --name=nginxtest \
  -v nginx-vol:/usr/share/nginx/html:ro \
  nginx:latest
```

使用 `docker inspect nginxtest` 验证 Docker 是否正确创建了只读挂载。查找 `Mounts` 部分：

```json
"Mounts": [
    {
        "Type": "volume",
        "Name": "nginx-vol",
        "Source": "/var/lib/docker/volumes/nginx-vol/_data",
        "Destination": "/usr/share/nginx/html",
        "Driver": "local",
        "Mode": "",
        "RW": false,
        "Propagation": ""
    }
],
```

停止并移除容器，然后删除卷。删除卷是一个单独的步骤。

```console
$ docker container stop nginxtest

$ docker container rm nginxtest

$ docker volume rm nginx-vol
```

## 挂载卷的子目录

当您将卷挂载到容器时，您可以使用 `--mount` 标志的 `volume-subpath` 参数来指定要使用的卷的子目录。您指定的子目录必须在尝试将其挂载到容器之前存在于卷中；如果不存在，挂载将失败。

如果您只想与容器共享卷的特定部分，则指定 `volume-subpath` 很有用。例如，假设您有多个容器在运行，并且您希望将每个容器的日志存储在一个共享卷中。您可以在共享卷中为每个容器创建一个子目录，然后将该子目录挂载到容器。

以下示例创建一个 `logs` 卷，并在卷中初始化子目录 `app1` 和 `app2`。然后启动两个容器，并将 `logs` 卷的其中一个子目录挂载到每个容器。此示例假定容器中的进程将其日志写入 `/var/log/app1` 和 `/var/log/app2`。

```console
$ docker volume create logs
$ docker run --rm \
  --mount src=logs,dst=/logs \
  alpine mkdir -p /logs/app1 /logs/app2
$ docker run -d \
  --name=app1 \
  --mount src=logs,dst=/var/log/app1,volume-subpath=app1 \
  app1:latest
$ docker run -d \
  --name=app2 \
  --mount src=logs,dst=/var/log/app2,volume-subpath=app2 \
  app2:latest
```

具体解释如下：

- **`docker run --rm`**：启动一个临时容器，当容器中的命令执行完毕后，容器会自动删除，不会残留。
- **`--mount src=logs,dst=/logs`**：将名为 `logs` 的**卷（volume）**挂载到容器内的 `/logs` 目录。如果该卷不存在，Docker 会自动创建。
- **`alpine`**：使用轻量级的 Alpine Linux 镜像作为基础。
- **`mkdir -p /logs/app1 /logs/app2`**：在容器内执行 `mkdir -p` 命令，在 `/logs` 目录下创建 `app1` 和 `app2` 两个子目录。

通过这种设置，容器会将其日志写入 `logs` 卷的不同子目录中。容器无法访问其他容器的日志。

## 在机器之间共享数据

在构建容错应用程序时，您可能需要配置同一服务的多个副本以访问相同的文件。

在开发应用程序时，有几种方法可以实现这一点。一种方法是在应用程序中添加逻辑，将文件存储在云对象存储系统（如 Amazon S3）上。另一种方法是使用支持将文件写入外部存储系统（如 NFS 或 Amazon S3）的驱动来创建卷。

卷驱动（**volume drivers**）允许您从应用程序逻辑中抽象出底层存储系统。例如，如果您的服务使用带有 NFS 驱动的卷，您可以更新服务以使用不同的驱动（例如，将数据存储在云中），而无需更改应用程序逻辑。

## 使用卷驱动

当您使用 `docker volume create` 创建卷时，或者当您启动一个使用尚未创建卷的容器时，您可以指定一个卷驱动。以下示例使用 `rclone/docker-volume-rclone` 卷驱动，首先创建一个独立卷，然后启动一个创建新卷的容器。

> [!NOTE]
>
> 如果您的卷驱动接受逗号分隔的列表作为选项，您必须从外部 CSV 解析器中转义该值。要转义 `volume-opt`，请用双引号 (`"`) 将其括起来，并用单引号 (`'`) 将整个挂载参数括起来。
>
> 例如，`local` 驱动接受 `o` 参数中以逗号分隔的挂载选项列表。此示例显示了转义列表的正确方法。
>
> ```console
> $ docker service create \
>  --mount 'type=volume,src=<VOLUME-NAME>,dst=<CONTAINER-PATH>,volume-driver=local,volume-opt=type=nfs,volume-opt=device=<nfs-server>:<nfs-path>,"volume-opt=o=addr=<nfs-address>,vers=4,soft,timeo=180,bg,tcp,rw"'
>  --name myservice \
>  <IMAGE>
> ```

### 初始设置

以下示例假设您有两个节点，第一个是 Docker 主机，并且可以使用 SSH 连接到第二个节点。

在 Docker 主机上，安装 `rclone/docker-volume-rclone` 插件：

```console
$ docker plugin install --grant-all-permissions rclone/docker-volume-rclone --aliases rclone
```

### 使用卷驱动创建卷

此示例将主机 `1.2.3.4` 上的 `/remote` 目录挂载到一个名为 `rclonevolume` 的卷中。每个卷驱动可能有零个或多个可配置选项，您可以使用 `-o` 标志指定每个选项。

```console
$ docker volume create \
  -d rclone \
  --name rclonevolume \
  -o type=sftp \
  -o path=remote \
  -o sftp-host=1.2.3.4 \
  -o sftp-user=user \
  -o "sftp-password=$(cat file_containing_password_for_remote_host)"
```

此卷现在可以挂载到容器中。

### 启动一个使用卷驱动创建卷的容器

> [!NOTE]
>
> 如果卷驱动要求您传递任何选项，您必须使用 `--mount` 标志来挂载卷，而不能使用 `-v`。

```console
$ docker run -d \
  --name rclone-container \
  --mount type=volume,volume-driver=rclone,src=rclonevolume,target=/app,volume-opt=type=sftp,volume-opt=path=remote, volume-opt=sftp-host=1.2.3.4,volume-opt=sftp-user=user,volume-opt=-o "sftp-password=$(cat file_containing_password_for_remote_host)" \
  nginx:latest
```

### 创建一个创建 NFS 卷的服务

以下示例展示了如何在创建服务时创建 NFS 卷。它使用 `10.0.0.10` 作为 NFS 服务器，使用 `/var/docker-nfs` 作为 NFS 服务器上的导出目录。请注意，指定的卷驱动是 `local`。

#### NFSv3

```console
$ docker service create -d \
  --name nfs-service \
  --mount 'type=volume,source=nfsvolume,target=/app,volume-driver=local,volume-opt=type=nfs,volume-opt=device=:/var/docker-nfs,volume-opt=o=addr=10.0.0.10' \
  nginx:latest
```

#### NFSv4

```console
$ docker service create -d \
    --name nfs-service \
    --mount 'type=volume,source=nfsvolume,target=/app,volume-driver=local,volume-opt=type=nfs,volume-opt=device=:/var/docker-nfs,"volume-opt=o=addr=10.0.0.10,rw,nfsvers=4,async"' \
    nginx:latest
```

### 创建 CIFS/Samba 卷

您可以直接在 Docker 中挂载 Samba 共享，而无需在主机上配置挂载点。

```console
$ docker volume create \
	--driver local \
	--opt type=cifs \
	--opt device=//uxxxxx.your-server.de/backup \
	--opt o=addr=uxxxxx.your-server.de,username=uxxxxxxx,password=*****,file_mode=0777,dir_mode=0777 \
	--name cifs-volume
```

如果您指定主机名而不是 IP，则需要 `addr` 选项。这允许 Docker 执行主机名查找。

### 块存储设备

您可以将块存储设备（例如外部驱动器或驱动器分区）挂载到容器。以下示例展示了如何创建和使用文件作为块存储设备，以及如何将块设备挂载为容器卷。

> [!IMPORTANT]
>
> 以下过程仅是一个示例。此处说明的解决方案不推荐作为常规实践。除非您对自己的操作有信心，否则不要尝试此方法。

#### 块设备挂载的工作原理

在底层，使用 `local` 存储驱动的 `--mount` 标志会调用 Linux `mount` 系统调用，并将您传递给它的选项原封不动地转发。Docker 没有在 Linux 内核支持的原生挂载功能之上实现任何额外功能。

如果您熟悉 Linux [`mount` 命令](https://man7.org/linux/man-pages/man8/mount.8.html)，您可以认为 `--mount` 选项以下列方式转发给 `mount` 命令：

```console
$ mount -t <mount.volume-opt.type> <mount.volume-opt.device> <mount.dst> -o <mount.volume-opts.o>
```

为了进一步解释这一点，请考虑以下 `mount` 命令示例。此命令将 `/dev/loop5` 设备挂载到系统上的 `/external-drive` 路径。

```console
$ mount -t ext4 /dev/loop5 /external-drive
```

从正在运行的容器的角度来看，以下 `docker run` 命令实现了类似的结果。使用此 `--mount` 选项运行容器，其设置方式与您执行上一个示例中的 `mount` 命令相同。

```console
$ docker run \
  --mount='type=volume,dst=/external-drive,volume-driver=local,volume-opt=device=/dev/loop5,volume-opt=type=ext4'
```

您不能直接在容器内运行 `mount` 命令，因为容器无法访问 `/dev/loop5` 设备。这就是 `docker run` 命令使用 `--mount` 选项的原因。

#### 示例：在容器中挂载块设备

以下步骤创建一个 `ext4` 文件系统并将其挂载到容器中。系统的文件系统支持取决于您使用的 Linux 内核版本。

1. 创建一个文件并为其分配一些空间：

   ```console
   $ fallocate -l 1G disk.raw
   ```

2. 在 `disk.raw` 文件上构建一个文件系统：

   ```console
   $ mkfs.ext4 disk.raw
   ```

3. 创建一个循环设备：

   ```console
   $ losetup -f --show disk.raw
   /dev/loop5
   ```

   > [!NOTE]
   >
   > `losetup` 创建一个临时的循环设备，该设备在系统重启后会被移除，或者可以使用 `losetup -d` 手动移除。

4. 运行一个将循环设备挂载为卷的容器：

   ```console
   $ docker run -it --rm \
     --mount='type=volume,dst=/external-drive,volume-driver=local,volume-opt=device=/dev/loop5,volume-opt=type=ext4' \
     ubuntu bash
   ```

   当容器启动时，路径 `/external-drive` 将从主机文件系统挂载 `disk.raw` 文件作为块设备。

5. 完成后，当设备从容器中卸载时，分离循环设备以从主机系统中删除该设备：

   ```console
   $ losetup -d /dev/loop5
   ```

## 备份、恢复或迁移数据卷

**Volumes** 对于备份、恢复和迁移非常有用。使用 `--volumes-from` 标志创建一个新容器来挂载该卷。

### 备份卷

例如，创建一个名为 `dbstore` 的新容器：

```console
$ docker run -v /dbdata --name dbstore ubuntu /bin/bash
```

在下一个命令中：

- 启动一个新容器并从 `dbstore` 容器挂载卷
- 将本地主机目录挂载为 `/backup`
- 传递一个命令，将 `dbdata` 卷的内容打包到 `/backup` 目录中的 `backup.tar` 文件中

```console
$ docker run --rm --volumes-from dbstore -v $(pwd):/backup ubuntu tar cvf /backup/backup.tar /dbdata
```

当命令完成并且容器停止时，它创建了 `dbdata` 卷的备份。

### 从备份恢复卷

使用刚刚创建的备份，您可以将其恢复到同一个容器，或者恢复到您在别处创建的另一个容器。

例如，创建一个名为 `dbstore2` 的新容器：

```console
$ docker run -v /dbdata --name dbstore2 ubuntu /bin/bash
```

然后，在新容器的数据卷中解压备份文件：

```console
$ docker run --rm --volumes-from dbstore2 -v $(pwd):/backup ubuntu bash -c "cd /dbdata && tar xvf /backup/backup.tar --strip 1"
```

您可以使用这些技术，使用您喜欢的工具来自动化备份、迁移和恢复测试。

## 删除卷

Docker 数据卷在您删除容器后仍然存在。有两种类型的卷需要考虑：

- **命名卷（Named volumes）** 具有特定的名称，例如 `awesome:/bar`，其中 `awesome` 是名称。
- **匿名卷（Anonymous volumes）** 没有特定名称。因此，当容器被删除时，您可以指示 Docker Engine 守护进程删除它们。

### 删除匿名卷

要自动删除匿名卷，请使用 `--rm` 选项。例如，此命令创建一个匿名 `/foo` 卷。当您删除容器时，Docker Engine 会删除 `/foo` 卷，但不会删除 `awesome` 卷。

`--rm` 选项适用于前台和后台（`-d`）容器。当容器退出时，匿名卷会被清理。

```console
$ docker run --rm -v /foo -v awesome:/bar busybox top
```

> [!NOTE]
>
> 如果另一个容器使用 `--volumes-from` 绑定了这些卷，则卷定义会被 _复制_，并且在第一个容器被删除后，匿名卷也会保留。

### 删除所有卷

要删除所有未使用的卷并释放空间：

```console
$ docker volume prune
```

## 下一步

- 了解 [**bind mounts**](/engine/storage/volumes/bind-mounts/)。
- 了解 [**tmpfs mounts**](/engine/storage/volumes/tmpfs/)。
- 了解[存储驱动（**storage drivers**）](/engine/storage/drivers/)。
- 了解[第三方卷驱动插件（**third-party volume driver plugins**）](/engine/extend/legacy_plugins/)。