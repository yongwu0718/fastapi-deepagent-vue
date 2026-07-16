# Prune unused Docker objects（清理未使用的 Docker 对象）

Docker 对清理未使用的对象（通常称为“垃圾回收”）采取较为保守的策略，这些对象包括 images（镜像）、containers（容器）、volumes（数据卷）和 networks（网络）。除非您明确要求 Docker 这样做，否则这些对象通常不会被删除。这可能会导致 Docker 占用额外的磁盘空间。针对每种类型的对象，Docker 都提供了对应的 `prune` 命令。此外，您还可以使用 `docker system prune` 一次性清理多种类型的对象。本主题将介绍如何使用这些 `prune` 命令。

## Prune images（清理镜像）

`docker image prune` 命令允许您清理未使用的镜像。默认情况下，`docker image prune` 仅清理 _dangling_ 镜像。dangling 镜像是指没有 tag（标签），并且不被任何容器引用的镜像。要删除 dangling 镜像：

```console
$ docker image prune

WARNING! This will remove all dangling images.
Are you sure you want to continue? [y/N] y
```

要删除所有未被现有容器使用的镜像，请使用 `-a` 标志：

```console
$ docker image prune -a

WARNING! This will remove all images without at least one container associated to them.
Are you sure you want to continue? [y/N] y
```

默认情况下，系统会提示您确认继续。要跳过提示，请使用 `-f` 或 `--force` 标志。

您可以使用 `--filter` 标志配合过滤表达式来限制被 prune 的镜像范围。例如，仅考虑创建时间超过 24 小时的镜像：

```console
$ docker image prune -a --filter "until=24h"
```

还有其他过滤表达式可用。更多示例请参阅 [`docker image prune` 参考文档](/reference/cli/docker/image/prune/)。

## Prune containers（清理容器）

当您停止一个容器时，除非您在启动时使用了 `--rm` 标志，否则该容器不会被自动删除。要查看 Docker 主机上的所有容器（包括已停止的容器），请使用 `docker ps -a`。您可能会对存在的容器数量感到惊讶，尤其是在开发系统上！已停止容器的可写层仍然占用磁盘空间。要清理这些空间，您可以使用 `docker container prune` 命令。

```console
$ docker container prune

WARNING! This will remove all stopped containers.
Are you sure you want to continue? [y/N] y
```

默认情况下，系统会提示您确认继续。要跳过提示，请使用 `-f` 或 `--force` 标志。

默认情况下，所有已停止的容器都会被删除。您可以使用 `--filter` 标志限制范围。例如，以下命令仅删除停止时间超过 24 小时的容器：

```console
$ docker container prune --filter "until=24h"
```

还有其他过滤表达式可用。更多示例请参阅 [`docker container prune` 参考文档](/reference/cli/docker/container/prune/)。

## Prune volumes（清理数据卷）

Volumes 可以被一个或多个容器使用，并占用 Docker 主机的空间。Volumes 永远不会被自动删除，因为这样做可能会销毁数据。

```console
$ docker volume prune

WARNING! This will remove all volumes not used by at least one container.
Are you sure you want to continue? [y/N] y
```

默认情况下，系统会提示您确认继续。要跳过提示，请使用 `-f` 或 `--force` 标志。

默认情况下，所有未使用的 volumes 都会被删除。您可以使用 `--filter` 标志限制范围。例如，以下命令仅删除没有 `keep` label（标签）的 volumes：

```console
$ docker volume prune --filter "label!=keep"
```

还有其他过滤表达式可用。更多示例请参阅 [`docker volume prune` 参考文档](/reference/cli/docker/volume/prune/)。

## Prune networks（清理网络）

Docker networks 不会占用太多磁盘空间，但它们会创建 `iptables` 规则、bridge 网络设备和路由表条目。要清理这些内容，您可以使用 `docker network prune` 来清理未被任何容器使用的 networks。

```console
$ docker network prune

WARNING! This will remove all networks not used by at least one container.
Are you sure you want to continue? [y/N] y
```

默认情况下，系统会提示您确认继续。要跳过提示，请使用 `-f` 或 `--force` 标志。

默认情况下，所有未使用的 networks 都会被删除。您可以使用 `--filter` 标志限制范围。例如，以下命令仅删除创建时间超过 24 小时的 networks：

```console
$ docker network prune --filter "until=24h"
```

还有其他过滤表达式可用。更多示例请参阅 [`docker network prune` 参考文档](/reference/cli/docker/network/prune/)。

## Prune build cache（清理构建缓存）

`docker buildx prune` 会移除当前选定 builder 的构建缓存。如果您使用多个 builder，每个 builder 维护自己的缓存——可以使用 `--builder` 标志来针对特定的 builder 实例。

```console
$ docker buildx prune

WARNING! This will remove all dangling build cache.
Are you sure you want to continue? [y/N] y
```

默认情况下，系统会提示您确认继续。要跳过提示，请使用 `-f` 或 `--force` 标志。

有关所有选项，请参阅 [`docker buildx prune` 参考文档](/reference/cli/docker/buildx/prune/)，其中包括 `--all` 选项，用于同时移除内部镜像和前端镜像。

## Prune everything（清理所有对象）

`docker system prune` 命令是一个快捷方式，可以同时 prune images、containers 和 networks。默认情况下，volumes 不会被 prune，您必须为 `docker system prune` 指定 `--volumes` 标志才能 prune volumes。

```console
$ docker system prune

WARNING! This will remove:
        - all stopped containers
        - all networks not used by at least one container
        - all dangling images
        - unused build cache

Are you sure you want to continue? [y/N] y
```

要同时 prune volumes，请添加 `--volumes` 标志：

```console
$ docker system prune --volumes

WARNING! This will remove:
        - all stopped containers
        - all networks not used by at least one container
        - all volumes not used by at least one container
        - all dangling images
        - all build cache

Are you sure you want to continue? [y/N] y
```

默认情况下，系统会提示您确认继续。要跳过提示，请使用 `-f` 或 `--force` 标志。

默认情况下，所有未使用的 containers、networks 和 images 都会被删除。您可以使用 `--filter` 标志限制范围。例如，以下命令删除存在时间超过 24 小时的对象：

```console
$ docker system prune --filter "until=24h"
```

还有其他过滤表达式可用。更多示例请参阅 [`docker system prune` 参考文档](/reference/cli/docker/system/prune/)。