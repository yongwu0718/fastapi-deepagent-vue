# 过滤命令（Filter commands）

你可以使用 `--filter` 标志来限定命令的作用范围。进行过滤时，命令仅包含与你指定的模式匹配的条目。

## 使用过滤器（Using filters）

`--filter` 标志需要一个由操作符分隔的键值对。

```console
$ docker COMMAND --filter "KEY=VALUE"
```

键（Key）代表你想要进行过滤的字段。值（Value）是指定字段必须匹配的模式。操作符可以是等号（`=`）或不等号（`!=`）。

例如，命令 `docker images --filter reference=alpine` 会过滤 `docker images` 命令的输出，只打印 `alpine` 镜像。

```console
$ docker images
REPOSITORY   TAG       IMAGE ID       CREATED          SIZE
ubuntu       24.04     33a5cc25d22c   36 minutes ago   101MB
ubuntu       22.04     152dc042452c   36 minutes ago   88.1MB
alpine       3.21      a8cbb8c69ee7   40 minutes ago   8.67MB
alpine       latest    7144f7bab3d4   40 minutes ago   11.7MB
busybox      uclibc    3e516f71d880   48 minutes ago   2.4MB
busybox      glibc     7338d0c72c65   48 minutes ago   6.09MB
$ docker images --filter reference=alpine
REPOSITORY   TAG       IMAGE ID       CREATED          SIZE
alpine       3.21      a8cbb8c69ee7   40 minutes ago   8.67MB
alpine       latest    7144f7bab3d4   40 minutes ago   11.7MB
```

可用的字段（此处为 `reference`）取决于你运行的命令。某些过滤器要求完全匹配，其他过滤器支持部分匹配，还有一些过滤器允许使用正则表达式。

请参阅每个命令的 [CLI 参考说明](#reference)，了解每个命令支持的过滤功能。

## 组合过滤器（Combining filters）

你可以通过传递多个 `--filter` 标志来组合多个过滤器。以下示例展示了如何打印所有匹配 `alpine:latest` 或 `busybox` 的镜像——这是一个逻辑 **OR**。

```console
$ docker images
REPOSITORY   TAG       IMAGE ID       CREATED       SIZE
ubuntu       24.04     33a5cc25d22c   2 hours ago   101MB
ubuntu       22.04     152dc042452c   2 hours ago   88.1MB
alpine       3.21      a8cbb8c69ee7   2 hours ago   8.67MB
alpine       latest    7144f7bab3d4   2 hours ago   11.7MB
busybox      uclibc    3e516f71d880   2 hours ago   2.4MB
busybox      glibc     7338d0c72c65   2 hours ago   6.09MB
$ docker images --filter reference=alpine:latest --filter=reference=busybox
REPOSITORY   TAG       IMAGE ID       CREATED       SIZE
alpine       latest    7144f7bab3d4   2 hours ago   11.7MB
busybox      uclibc    3e516f71d880   2 hours ago   2.4MB
busybox      glibc     7338d0c72c65   2 hours ago   6.09MB
```

### 多个否定过滤器（Multiple negated filters）

某些命令支持在[标签（labels）](/engine/manage-resources/labels/)上使用否定过滤器。否定过滤器仅考虑与指定模式不匹配的结果。以下命令会修剪所有未标记 `foo` 的容器。

```console
$ docker container prune --filter "label!=foo"
```

组合多个否定标签过滤器时有一个陷阱。多个否定过滤器会创建一个单一的否定约束——一个逻辑 **AND**。以下命令会修剪除了同时标记有 `foo` 和 `bar` 的容器之外的所有容器。只标记了 `foo` 或只标记了 `bar`（但不同时具备两者）的容器将被修剪。

```console
$ docker container prune --filter "label!=foo" --filter "label!=bar"
```

## 参考（Reference）

有关过滤命令的更多信息，请参阅支持 `--filter` 标志的命令的 CLI 参考说明：

- [`docker config ls`](/reference/cli/docker/config/ls/)
- [`docker container prune`](/reference/cli/docker/container/prune/)
- [`docker image prune`](/reference/cli/docker/image/prune/)
- [`docker image ls`](/reference/cli/docker/image/ls/)
- [`docker network ls`](/reference/cli/docker/network/ls/)
- [`docker network prune`](/reference/cli/docker/network/prune/)
- [`docker node ls`](/reference/cli/docker/node/ls/)
- [`docker node ps`](/reference/cli/docker/node/ps/)
- [`docker plugin ls`](/reference/cli/docker/plugin/ls/)
- [`docker container ls`](/reference/cli/docker/container/ls/)
- [`docker search`](/reference/cli/docker/search/)
- [`docker secret ls`](/reference/cli/docker/secret/ls/)
- [`docker service ls`](/reference/cli/docker/service/ls/)
- [`docker service ps`](/reference/cli/docker/service/ps/)
- [`docker stack ps`](/reference/cli/docker/stack/ps/)
- [`docker system prune`](/reference/cli/docker/system/prune/)
- [`docker volume ls`](/reference/cli/docker/volume/ls/)
- [`docker volume prune`](/reference/cli/docker/volume/prune/)