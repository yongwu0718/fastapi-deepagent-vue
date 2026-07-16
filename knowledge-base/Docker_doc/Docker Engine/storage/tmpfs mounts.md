# tmpfs mounts（tmpfs 挂载）

[**Volumes**](/engine/storage/tmpfs/volumes/) 和 [**bind mounts**](/engine/storage/tmpfs/bind-mounts/) 允许您在主机和容器之间共享文件，以便即使在容器停止后也能持久化数据。

如果您在 Linux 上运行 Docker，还有第三种选择：**tmpfs mounts**。当您创建一个带有 **tmpfs mount** 的容器时，容器可以在容器的可写层之外创建文件。

与 **volumes** 和 **bind mounts** 不同，**tmpfs mount** 是临时的，并且仅持久保存在主机内存中。当容器停止时，**tmpfs mount** 会被移除，写入其中的文件不会被持久化。

**tmpfs mounts** 最适合用于您不希望数据持久保存在主机或容器中的情况。这可能是出于安全原因，或者当您的应用程序需要写入大量非持久状态数据时，为了保护容器的性能。

> [!IMPORTANT]
> Docker 中的 **tmpfs mounts** 直接映射到 Linux 内核中的 [tmpfs](https://en.wikipedia.org/wiki/Tmpfs)。因此，临时数据可能会被写入交换文件，从而持久化到文件系统。

## 挂载到已有数据的目录

如果您将 **tmpfs mount** 创建到容器中的一个目录，而该目录中已经存在文件或目录，那么预先存在的文件会被挂载所掩盖。这类似于您将文件保存到 Linux 主机的 `/mnt` 下，然后将一个 USB 驱动器挂载到 `/mnt` 中。在 USB 驱动器卸载之前，`/mnt` 的内容将被 USB 驱动器的内容所掩盖。

对于容器，没有简单的方法来移除挂载以再次显示被掩盖的文件。最好的选择是重新创建不带挂载的容器。

## tmpfs mounts 的限制

- 与 **volumes** 和 **bind mounts** 不同，您不能在容器之间共享 **tmpfs mounts**。
- 此功能仅在 Linux 上运行 Docker 时可用。
- 在 tmpfs 上设置权限可能会导致它们在[容器重启后重置](https://github.com/docker/for-linux/issues/138)。在某些情况下，[设置 uid/gid](https://github.com/docker/compose/issues/3425#issuecomment-423091370) 可以作为一种解决方法。

## 语法

要在 `docker run` 命令中挂载 tmpfs，您可以使用 `--mount` 或 `--tmpfs` 标志。

```console
$ docker run --mount type=tmpfs,dst=<mount-path>
$ docker run --tmpfs <mount-path>
```

通常，`--mount` 是首选。主要区别在于 `--mount` 标志更加明确。另一方面，`--tmpfs` 更简洁，并且让您可以设置更多挂载选项，从而提供更大的灵活性。

`--tmpfs` 标志不能用于 swarm 服务。您必须使用 `--mount`。

### --tmpfs 的选项

`--tmpfs` 标志由两个字段组成，用冒号 (`:`) 分隔。

```console
$ docker run --tmpfs <mount-path>[:opts]
```

第一个字段是要挂载到 tmpfs 的容器路径。第二个字段是可选的，允许您设置挂载选项。`--tmpfs` 的有效挂载选项包括：

| 选项           | 描述                                                                                 |
| ------------ | ----------------------------------------------------------------------------------- |
| `ro`         | 创建一个只读的 **tmpfs mount**。                                                            |
| `rw`         | 创建一个读写的 **tmpfs mount**（默认行为）。                                                |
| `nosuid`     | 防止在执行期间识别 `setuid` 和 `setgid` 位。                                            |
| `suid`       | 允许在执行期间识别 `setuid` 和 `setgid` 位（默认行为）。                                      |
| `nodev`      | 可以创建设备文件，但无法正常工作（访问会导致错误）。                                            |
| `dev`        | 可以创建设备文件，并且完全可用。                                                              |
| `exec`       | 允许在挂载的文件系统中执行可执行二进制文件。                                                     |
| `noexec`     | 不允许在挂载的文件系统中执行可执行二进制文件。                                                     |
| `sync`       | 对文件系统的所有 I/O 操作都是同步完成的。                                                       |
| `async`      | 对文件系统的所有 I/O 操作都是异步完成的（默认行为）。                                               |
| `dirsync`    | 文件系统内的目录更新是同步完成的。                                                            |
| `atime`      | 每次访问文件时都会更新文件访问时间。                                                            |
| `noatime`    | 访问文件时不更新文件访问时间。                                                              |
| `diratime`   | 每次访问目录时都会更新目录访问时间。                                                            |
| `nodiratime` | 访问目录时不更新目录访问时间。                                                              |
| `size`       | 指定 **tmpfs mount** 的大小，例如 `size=64m`。                                             |
| `mode`       | 指定 **tmpfs mount** 的文件模式（权限），例如 `mode=1777`。                                   |
| `uid`        | 指定 **tmpfs mount** 所有者的用户 ID，例如 `uid=1000`。                                   |
| `gid`        | 指定 **tmpfs mount** 所有者的组 ID，例如 `gid=1000`。                                   |
| `nr_inodes`  | 指定 **tmpfs mount** 的最大 inode 数量，例如 `nr_inodes=400k`。                             |
| `nr_blocks`  | 指定 **tmpfs mount** 的最大块数，例如 `nr_blocks=1024`。                                   |

```console {title="示例"}
$ docker run --tmpfs /data:noexec,size=1024,mode=1777
```

并非 Linux `mount` 命令中所有可用的 tmpfs 挂载功能都受 `--tmpfs` 标志支持。如果您需要高级的 tmpfs 选项或功能，您可能需要使用特权容器或在 Docker 外部配置挂载。

> [!CAUTION]
> 使用 `--privileged` 运行容器会授予提升的权限，并可能使主机系统面临安全风险。仅在绝对必要且环境可信的情况下使用此选项。

```console
$ docker run --privileged -it debian sh
/# mount -t tmpfs -o <options> tmpfs /data
```

### --mount 的选项

`--mount` 标志由多个键值对组成，用逗号分隔，每个键值对的形式为 `<key>=<value>`。键的顺序不重要。

```console
$ docker run --mount type=tmpfs,dst=<mount-path>[,<key>=<value>...]
```

`--mount type=tmpfs` 的有效选项包括：

| 选项                           | 描述                                                                                                                |
| :----------------------------- | :----------------------------------------------------------------------------------------------------------------- |
| `destination`, `dst`, `target` | 要挂载到 tmpfs 的容器路径。                                                                                          |
| `tmpfs-size`                   | **tmpfs mount** 的大小，以字节为单位。如果未设置，tmpfs 卷的默认最大大小为主机总 RAM 的 50%。                         |
| `tmpfs-mode`                   | tmpfs 的文件模式，以八进制表示。例如 `700` 或 `0770`。默认为 `1777`（即全局可写）。                                    |

```console {title="示例"}
$ docker run --mount type=tmpfs,dst=/app,tmpfs-size=21474836480,tmpfs-mode=1770
```

## 在容器中使用 tmpfs mount

要在容器中使用 `tmpfs` 挂载，请使用 `--tmpfs` 标志，或者使用带有 `type=tmpfs` 和 `destination` 选项的 `--mount` 标志。`tmpfs` 挂载没有 `source`。以下示例在 Nginx 容器中的 `/app` 处创建一个 `tmpfs` 挂载。第一个示例使用 `--mount` 标志，第二个示例使用 `--tmpfs` 标志。

**`--mount`**

```console
$ docker run -d \
  -it \
  --name tmptest \
  --mount type=tmpfs,destination=/app \
  nginx:latest
```

通过查看 `docker inspect` 输出中的 `Mounts` 部分，验证挂载是否为 `tmpfs` 挂载：

```console
$ docker inspect tmptest --format '{{ json .Mounts }}'
[{"Type":"tmpfs","Source":"","Destination":"/app","Mode":"","RW":true,"Propagation":""}]
```

**`--tmpfs`**

```console
$ docker run -d \
  -it \
  --name tmptest \
  --tmpfs /app \
  nginx:latest
```

通过查看 `docker inspect` 输出中的 `Mounts` 部分，验证挂载是否为 `tmpfs` 挂载：

```console
$ docker inspect tmptest --format '{{ json .Mounts }}'
{"/app":""}
```

停止并移除容器：

```console
$ docker stop tmptest
$ docker rm tmptest
```

## 下一步

- 了解 [**volumes**](/engine/storage/tmpfs/volumes/)
- 了解 [**bind mounts**](/engine/storage/tmpfs/bind-mounts/)
- 了解[存储驱动（**storage drivers**）](/engine/storage/drivers/)