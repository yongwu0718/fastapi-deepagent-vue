# 运行容器（Running containers）

Docker 在隔离的容器中运行进程。容器是运行在主机上的进程。主机可以是本地或远程的。当你执行 `docker run` 时，运行的容器进程是隔离的：它拥有自己的文件系统、自己的网络，以及独立于主机的进程树。

本页详细介绍如何使用 `docker run` 命令来运行容器。

## 一般形式

`docker run` 命令的形式如下：

```console
$ docker run [OPTIONS] IMAGE[:TAG|@DIGEST] [COMMAND] [ARG...]
```

`docker run` 命令必须指定一个**镜像引用（image reference）** 来从中创建容器。

### 镜像引用（Image references）

镜像引用是镜像的名称和版本。你可以使用镜像引用来创建或运行基于镜像的容器。

- `docker run IMAGE[:TAG][@DIGEST]`
- `docker create IMAGE[:TAG][@DIGEST]`

**镜像标签（image tag）** 是镜像的版本，省略时默认为 `latest`。使用标签可以从特定版本的镜像运行容器。例如，运行 `ubuntu` 镜像的 `24.04` 版本：`docker run ubuntu:24.04`。

#### 镜像摘要（Image digests）

使用 v2 或更高版本镜像格式的镜像具有一个内容可寻址的标识符，称为**摘要（digest）**。只要用于生成镜像的输入不变，摘要值就是可预测的。

以下示例从 `alpine` 镜像运行容器，使用摘要 `sha256:9cacb71397b640eca97488cf08582ae4e4068513101088e9f96c9814bfda95e0`：

```console
$ docker run alpine@sha256:9cacb71397b640eca97488cf08582ae4e4068513101088e9f96c9814bfda95e0 date
```

### 选项（Options）

`[OPTIONS]` 允许你配置容器的选项。例如，你可以给容器命名（`--name`），或将其作为后台进程运行（`-d`）。你还可以设置选项来控制资源限制和网络等。

### 命令与参数（Commands and arguments）

你可以使用位置参数 `[COMMAND]` 和 `[ARG...]` 来指定容器启动时要运行的命令和参数。例如，结合 `-i` 和 `-t` 标志，可以指定 `sh` 作为 `[COMMAND]`，从而在容器中启动一个交互式 shell（如果你选择的镜像在 `PATH` 中有 `sh` 可执行文件）。

```console
$ docker run -it IMAGE sh
```

> [!NOTE]
> 根据你的 Docker 系统配置，可能需要在 `docker run` 命令前加上 `sudo`。为了避免在使用 `docker` 命令时使用 `sudo`，系统管理员可以创建一个名为 `docker` 的 Unix 组并将用户添加进去。有关此配置的更多信息，请参阅适用于你操作系统的 Docker 安装文档。

## 前台与后台（Foreground and background）

当你启动容器时，默认情况下容器在前台运行。如果希望容器在后台运行，可以使用 `--detach`（或 `-d`）标志。这样启动的容器不会占用你的终端窗口。

```console
$ docker run -d <IMAGE>
```

当容器在后台运行时，你可以使用其他 CLI 命令与之交互。例如，`docker logs` 可以查看容器的日志，`docker attach` 将其带到前台。

```console
$ docker run -d nginx
0246aa4d1448a401cabd2ce8f242192b6e7af721527e48a810463366c7ff54f1
$ docker ps
CONTAINER ID   IMAGE     COMMAND                  CREATED         STATUS        PORTS     NAMES
0246aa4d1448   nginx     "/docker-entrypoint.…"   2 seconds ago   Up 1 second   80/tcp    pedantic_liskov
$ docker logs -n 5 0246aa4d1448
2023/11/06 15:58:23 [notice] 1#1: start worker process 33
2023/11/06 15:58:23 [notice] 1#1: start worker process 34
2023/11/06 15:58:23 [notice] 1#1: start worker process 35
2023/11/06 15:58:23 [notice] 1#1: start worker process 36
2023/11/06 15:58:23 [notice] 1#1: start worker process 37
$ docker attach 0246aa4d1448
^C
2023/11/06 15:58:40 [notice] 1#1: signal 2 (SIGINT) received, exiting
...
```

关于与前台/后台模式相关的 `docker run` 标志的更多信息，请参阅：

- [`docker run --detach`](https://docs.docker.com/reference/cli/docker/container/run/#detach)：在后台运行容器
- [`docker run --attach`](https://docs.docker.com/reference/cli/docker/container/run/#attach)：附加到 `stdin`、`stdout` 和 `stderr`
- [`docker run --tty`](https://docs.docker.com/reference/cli/docker/container/run/#tty)：分配一个伪终端（pseudo-TTY）
- [`docker run --interactive`](https://docs.docker.com/reference/cli/docker/container/run/#interactive)：即使没有附加也保持 `stdin` 打开

关于重新附加到后台容器的更多信息，请参阅 [`docker attach`](https://docs.docker.com/reference/cli/docker/container/attach/)。

## 容器标识（Container identification）

你可以通过三种方式标识容器：

| 标识符类型             | 示例值                                                              |
|:----------------------|:--------------------------------------------------------------------|
| UUID 长标识符         | `f78375b1c487e03c9438c729345e54db9d20cfa2ac1fc3494b6eb60872e74778` |
| UUID 短标识符         | `f78375b1c487`                                                      |
| 名称（Name）          | `evil_ptolemy`                                                      |

**UUID 标识符** 是守护进程分配给容器的随机 ID。

守护进程会自动为容器生成一个随机字符串名称。你也可以使用 [`--name` 标志](https://docs.docker.com/reference/cli/docker/container/run/#name) 定义自定义名称。定义 `name` 是为容器增加意义的便捷方法。如果指定了 `name`，你可以在用户定义的网络中使用它来引用容器。这对后台和前台 Docker 容器都适用。

容器标识符与镜像引用不同。镜像引用指定运行容器时使用哪个镜像。你不能运行 `docker exec nginx:alpine sh` 来打开基于 `nginx:alpine` 镜像的容器的 shell，因为 `docker exec` 期望的是容器标识符（名称或 ID），而不是镜像。

虽然容器使用的镜像不是容器的标识符，但你可以使用 `--filter` 标志找出使用某镜像的容器的 ID。例如，以下 `docker ps` 命令获取所有基于 `nginx:alpine` 镜像运行的容器的 ID：

```console
$ docker ps -q --filter ancestor=nginx:alpine
```

关于使用过滤器的更多信息，请参阅[过滤（Filtering）](https://docs.docker.com/config/filter/)。

## 容器网络（Container networking）

容器默认启用网络，并且可以发起出站连接。如果你运行多个需要相互通信的容器，可以创建一个自定义网络并将容器附加到该网络。

当多个容器附加到同一个自定义网络时，它们可以使用容器名称作为 DNS 主机名相互通信。以下示例创建一个名为 `my-net` 的自定义网络，并运行两个附加到该网络的容器。

```console
$ docker network create my-net
$ docker run -d --name web --network my-net nginx:alpine
$ docker run --rm -it --network my-net busybox
/ # ping web
PING web (172.18.0.2): 56 data bytes
64 bytes from 172.18.0.2: seq=0 ttl=64 time=0.326 ms
64 bytes from 172.18.0.2: seq=1 ttl=64 time=0.257 ms
64 bytes from 172.18.0.2: seq=2 ttl=64 time=0.281 ms
^C
--- web ping statistics ---
3 packets transmitted, 3 packets received, 0% packet loss
round-trip min/avg/max = 0.257/0.288/0.326 ms
```

关于容器网络的更多信息，请参阅[网络概述（Networking overview）](https://docs.docker.com/network/)。

## 文件系统挂载（Filesystem mounts）

默认情况下，容器中的数据存储在临时的、可写的容器层中。删除容器也会删除其数据。如果你想在容器中使用持久化数据，可以使用文件系统挂载将数据持久化到主机系统上。文件系统挂载还可以让你在容器和主机之间共享数据。

Docker 支持两大类挂载：

- **卷挂载（Volume mounts）**
- **绑定挂载（Bind mounts）**

**卷挂载（Volume mounts）** 非常适合持久化存储容器数据，以及在容器之间共享数据。而**绑定挂载（Bind mounts）** 则用于在容器和主机之间共享数据。

你可以使用 `docker run` 命令的 `--mount` 标志向容器添加文件系统挂载。

以下部分展示了如何创建卷和绑定挂载的基本示例。更多深入的示例和描述，请参阅文档中的[存储部分（storage section）](https://docs.docker.com/storage/)。

### 卷挂载（Volume mounts）

要创建卷挂载：

```console
$ docker run --mount source=<VOLUME_NAME>,target=[PATH] [IMAGE] [COMMAND...]
```

在这种情况下，`--mount` 标志接受两个参数：`source` 和 `target`。`source` 参数的值是卷的名称。`target` 的值是卷在容器内的挂载位置。一旦创建了卷，你写入该卷的任何数据都会被持久化，即使你停止或删除容器：

```console
$ docker run --rm --mount source=my_volume,target=/foo busybox \
  echo "hello, volume!" > /foo/hello.txt
$ docker run --mount source=my_volume,target=/bar busybox
  cat /bar/hello.txt
hello, volume!
```

`target` 必须始终是绝对路径，例如 `/src/docs`。绝对路径以 `/`（正斜杠）开头。卷名称必须以字母数字字符开头，后跟 `a-z0-9`、`_`（下划线）、`.`（点）或 `-`（连字符）。

### 绑定挂载（Bind mounts）

要创建绑定挂载：

```console
$ docker run -it --mount type=bind,source=[PATH],target=[PATH] busybox
```

在这种情况下，`--mount` 标志接受三个参数：一个类型（`bind`），以及两个路径。`source` 路径是主机上要绑定挂载到容器中的位置。`target` 路径是容器内的挂载目标。

默认情况下，绑定挂载要求源路径在守护进程主机上存在。如果源路径不存在，会返回错误。如果源路径在守护进程主机上不存在，要创建它，请使用 `bind-create-src` 选项：

```console
$ docker run -it --mount type=bind,source=[PATH],target=[PATH],bind-create-src busybox
```

绑定挂载默认可读可写，这意味着你可以从容器的挂载位置读取和写入文件。你所做的更改（如添加或编辑文件）会反映在主机文件系统上：

```console
$ docker run -it --mount type=bind,source=.,target=/foo busybox
/ # echo "hello from container" > /foo/hello.txt
/ # exit
$ cat hello.txt
hello from container
```

## 退出状态（Exit status）

`docker run` 的退出码提供了关于容器未能运行或退出原因的信息。以下部分描述了不同容器退出码值的含义。

### 125

退出码 `125` 表示错误与 Docker 守护进程本身有关。

```console
$ docker run --foo busybox; echo $?

flag provided but not defined: --foo
See 'docker run --help'.
125
```

### 126

退出码 `126` 表示指定的容器命令无法被调用。以下示例中的容器命令是：`/etc`。

```console
$ docker run busybox /etc; echo $?

docker: Error response from daemon: Container command '/etc' could not be invoked.
126
```

### 127

退出码 `127` 表示找不到容器命令。

```console
$ docker run busybox foo; echo $?

docker: Error response from daemon: Container command 'foo' not found or does not exist.
127
```

### 其他退出码

除 `125`、`126` 和 `127` 之外的任何退出码都代表所提供的容器命令的退出码。

```console
$ docker run busybox /bin/sh -c 'exit 3'
$ echo $?
3
```

## 资源的运行时约束（Runtime constraints on resources）

操作员还可以调整容器的性能参数：

| 选项                          | 描述                                                                                                                                                                                                                                                                              |
|:------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-m`, `--memory=""`           | 内存限制（格式：`<number>[<unit>]`）。数字为正整数。单位可以是 `b`、`k`、`m` 或 `g`。最小值为 6M。                                                                                                                                                       |
| `--memory-swap=""`            | 总内存限制（内存+交换，格式：`<number>[<unit>]`）。数字为正整数。单位可以是 `b`、`k`、`m` 或 `g`。                                                                                                                                                   |
| `--memory-reservation=""`     | 内存软限制（格式：`<number>[<unit>]`）。数字为正整数。单位可以是 `b`、`k`、`m` 或 `g`。                                                                                                                                                                   |
| `-c`, `--cpu-shares=0`        | CPU 份额（相对权重）                                                                                                                                                                                                                                                             |
| `--cpus=0.000`                | CPU 数量。数字为小数。0.000 表示无限制。                                                                                                                                                                                                                     |
| `--cpu-period=0`              | 限制 CPU CFS（完全公平调度器）周期                                                                                                                                                                                                                                     |
| `--cpuset-cpus=""`            | 允许执行的 CPU（0-3, 0,1）                                                                                                                                                                                                                                              |
| `--cpuset-mems=""`            | 允许执行的内存节点（MEMs）（0-3, 0,1）。仅在 NUMA 系统上有效。                                                                                                                                                                                              |
| `--cpu-quota=0`               | 限制 CPU CFS（完全公平调度器）配额                                                                                                                                                                                                                                      |
| `--cpu-rt-period=0`           | 限制 CPU 实时周期，单位为微秒。要求父 cgroup 已设置且不能高于父级。还要检查 rtprio 限制。                                                                                                                                                                             |
| `--cpu-rt-runtime=0`          | 限制 CPU 实时运行时间，单位为微秒。要求父 cgroup 已设置且不能高于父级。还要检查 rtprio 限制。                                                                                                                                                                            |
| `--blkio-weight=0`            | 块 IO 权重（相对权重），接受 10 到 1000 之间的权重值。                                                                                                                                                                                                            |
| `--blkio-weight-device=""`    | 块 IO 权重（相对设备权重，格式：`DEVICE_NAME:WEIGHT`）                                                                                                                                                                                                                   |
| `--device-read-bps=""`        | 限制从设备的读取速率（格式：`<device-path>:<number>[<unit>]`）。数字为正整数。单位可以是 `kb`、`mb` 或 `gb`。                                                                                                                                          |
| `--device-write-bps=""`       | 限制向设备的写入速率（格式：`<device-path>:<number>[<unit>]`）。数字为正整数。单位可以是 `kb`、`mb` 或 `gb`。                                                                                                                                           |
| `--device-read-iops="" `      | 限制从设备的读取速率（每秒 IO 数）（格式：`<device-path>:<number>`）。数字为正整数。                                                                                                                                                                          |
| `--device-write-iops="" `     | 限制向设备的写入速率（每秒 IO 数）（格式：`<device-path>:<number>`）。数字为正整数。                                                                                                                                                                           |
| `--oom-kill-disable=false`    | 是否禁用容器的 OOM Killer。                                                                                                                                                                                                                                  |
| `--oom-score-adj=0`           | 调整容器的 OOM 偏好（-1000 到 1000）                                                                                                                                                                                                                                         |
| `--memory-swappiness=""`      | 调整容器的内存交换行为。接受 0 到 100 之间的整数。                                                                                                                                                                                                     |
| `--shm-size=""`               | `/dev/shm` 的大小。格式为 `<number><unit>`。`number` 必须大于 `0`。单位可选，可以是 `b`（字节）、`k`（千字节）、`m`（兆字节）或 `g`（千兆字节）。如果省略单位，系统使用字节。如果完全省略大小，系统使用 `64m`。 |

### 用户内存约束（User memory constraints）

我们有四种设置用户内存使用的方法：

<table>
  <thead>
    <tr>
      <th>选项</th>
      <th>结果</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="no-wrap">
          <strong>memory=inf, memory-swap=inf</strong>（默认）
       </td>
      <td>
        容器没有内存限制。容器可以根据需要使用任意多的内存。
       </td>
    </tr>
    <tr>
      <td class="no-wrap"><strong>memory=L&lt;inf, memory-swap=inf</strong></td>
      <td>
        （指定 memory 并将 memory-swap 设置为 <code>-1</code>）容器不允许使用超过 L 字节的内存，但可以根据需要使用任意多的交换空间（如果主机支持交换内存）。
       </td>
    </tr>
    <tr>
      <td class="no-wrap"><strong>memory=L&lt;inf, memory-swap=2*L</strong></td>
      <td>
        （指定 memory 而不指定 memory-swap）容器不允许使用超过 L 字节的内存，交换 <i>加上</i> 内存使用量是其两倍。
       </td>
    </tr>
    <tr>
      <td class="no-wrap">
          <strong>memory=L&lt;inf, memory-swap=S&lt;inf, L&lt;=S</strong>
       </td>
      <td>
        （同时指定 memory 和 memory-swap）容器不允许使用超过 L 字节的内存，交换 <i>加上</i> 内存使用量受 S 限制。
       </td>
    </tr>
  </tbody>
</table>

示例：

```console
$ docker run -it ubuntu:24.04 /bin/bash
```

我们没有设置任何内存选项，这意味着容器中的进程可以使用任意多的内存和交换内存。

```console
$ docker run -it -m 300M --memory-swap -1 ubuntu:24.04 /bin/bash
```

我们设置了内存限制并禁用了交换内存限制，这意味着容器中的进程可以使用 300M 内存和任意多的交换内存（如果主机支持交换内存）。

```console
$ docker run -it -m 300M ubuntu:24.04 /bin/bash
```

我们只设置了内存限制，这意味着容器中的进程可以使用 300M 内存和 300M 交换内存，默认情况下总虚拟内存大小（`--memory-swap`）将设置为内存的两倍，在这种情况下，内存+交换将为 2*300M，因此进程也可以使用 300M 交换内存。

```console
$ docker run -it -m 300M --memory-swap 1G ubuntu:24.04 /bin/bash
```

我们同时设置了内存和交换内存，因此容器中的进程可以使用 300M 内存和 700M 交换内存。

**内存预留（memory reservation）** 是一种内存软限制，允许更大的内存共享。在正常情况下，容器可以根据需要使用尽可能多的内存，仅受 `-m`/`--memory` 选项设置的硬限制约束。当设置了内存预留时，Docker 会检测内存争用或内存不足，并强制容器将其消耗限制在预留限制内。

始终将内存预留值设置在硬限制之下，否则硬限制优先。预留值为 0 等同于未设置预留。默认情况下（未设置预留），内存预留与硬内存限制相同。

内存预留是一个软限制特性，不能保证不会超过限制。相反，该特性试图确保当内存严重争用时，根据预留提示/设置分配内存。

以下示例将内存（`-m`）限制为 500M，并将内存预留设置为 200M。

```console
$ docker run -it -m 500M --memory-reservation 200M ubuntu:24.04 /bin/bash
```

在此配置下，当容器消耗的内存超过 200M 但低于 500M 时，下一次系统内存回收会尝试将容器内存压缩到 200M 以下。

以下示例将内存预留设置为 1G，没有硬内存限制。

```console
$ docker run -it --memory-reservation 1G ubuntu:24.04 /bin/bash
```

容器可以根据需要使用任意多的内存。内存预留设置确保容器不会长时间消耗过多内存，因为每次内存回收都会将容器的消耗缩减到预留值。

默认情况下，如果发生内存不足（OOM）错误，内核会杀死容器中的进程。要更改此行为，请使用 `--oom-kill-disable` 选项。仅在同时设置了 `-m/--memory` 选项的容器上禁用 OOM killer。如果未设置 `-m` 标志，这可能导致主机耗尽内存，并需要杀死主机的系统进程以释放内存。

以下示例将内存限制为 100M，并为此容器禁用 OOM killer：

```console
$ docker run -it -m 100M --oom-kill-disable ubuntu:24.04 /bin/bash
```

以下示例说明了使用该标志的危险方式：

```console
$ docker run -it --oom-kill-disable ubuntu:24.04 /bin/bash
```

该容器拥有无限内存，可能导致主机内存耗尽，并需要杀死系统进程以释放内存。可以更改 `--oom-score-adj` 参数来选择当系统内存不足时哪些容器更可能被杀死，负分数使其更不容易被杀死，正分数使其更容易被杀死。

### 交换性约束（Swappiness constraint）

默认情况下，容器的内核可以交换出一定百分比的匿名页面。要为容器设置此百分比，请指定一个介于 0 和 100 之间的 `--memory-swappiness` 值。值为 0 表示关闭匿名页面交换。值为 100 表示将所有匿名页面设置为可交换。默认情况下，如果你不使用 `--memory-swappiness`，内存交换性值将从父级继承。

例如，你可以设置：

```console
$ docker run -it --memory-swappiness=0 ubuntu:24.04 /bin/bash
```

设置 `--memory-swappiness` 选项在你希望保留容器的工作集并避免交换性能损失时很有帮助。

### CPU 份额约束（CPU share constraint）

默认情况下，所有容器获得相同比例的 CPU 周期。可以通过更改容器的 CPU 份额权重（相对于所有其他运行中容器的权重）来修改此比例。

要修改默认值 1024，请使用 `-c` 或 `--cpu-shares` 标志将权重设置为 2 或更高。如果设置为 0，系统将忽略该值并使用默认值 1024。

该比例仅在运行 CPU 密集型进程时适用。当一个容器中的任务空闲时，其他容器可以使用剩余的 CPU 时间。实际的 CPU 时间量取决于系统上运行的容器数量。

例如，考虑三个容器，其中一个的 cpu-share 为 1024，另外两个的 cpu-share 设置为 512。当所有三个容器中的进程都试图使用 100% 的 CPU 时，第一个容器将获得总 CPU 时间的 50%。如果你添加第四个 cpu-share 为 1024 的容器，第一个容器只获得 33% 的 CPU。其余容器分别获得 16.5%、16.5% 和 33% 的 CPU。

在多核系统上，CPU 时间份额分布到所有 CPU 核心上。即使一个容器被限制为少于 100% 的 CPU 时间，它也可以使用每个单独 CPU 核心的 100%。

例如，考虑一个超过三个核心的系统。如果你启动一个容器 `{C0}` 使用 `-c=512` 运行一个进程，另一个容器 `{C1}` 使用 `-c=1024` 运行两个进程，这可能导致如下 CPU 份额分配：

    PID    container	CPU	CPU share
    100    {C0}		0	100% of CPU0
    101    {C1}		1	100% of CPU1
    102    {C1}		2	100% of CPU2

### CPU 周期约束（CPU period constraint）

默认的 CPU CFS（完全公平调度器）周期为 100ms。我们可以使用 `--cpu-period` 来设置 CPU 周期以限制容器的 CPU 使用率。通常 `--cpu-period` 应与 `--cpu-quota` 一起使用。

示例：

```console
$ docker run -it --cpu-period=50000 --cpu-quota=25000 ubuntu:24.04 /bin/bash
```

如果有 1 个 CPU，这意味着容器每 50ms 可以获得 50% CPU 的运行时间。

除了使用 `--cpu-period` 和 `--cpu-quota` 设置 CPU 周期约束外，还可以使用 `--cpus` 指定一个浮点数来达到相同目的。例如，如果有 1 个 CPU，那么 `--cpus=0.5` 将产生与设置 `--cpu-period=50000` 和 `--cpu-quota=25000`（50% CPU）相同的结果。

`--cpus` 的默认值为 `0.000`，表示没有限制。

更多信息，请参阅[关于带宽限制的 CFS 文档](https://www.kernel.org/doc/Documentation/scheduler/sched-bwc.txt)。

### Cpuset 约束（Cpuset constraint）

我们可以设置容器允许执行的 CPU。

示例：

```console
$ docker run -it --cpuset-cpus="1,3" ubuntu:24.04 /bin/bash
```

这意味着容器中的进程可以在 CPU 1 和 CPU 3 上执行。

```console
$ docker run -it --cpuset-cpus="0-2" ubuntu:24.04 /bin/bash
```

这意味着容器中的进程可以在 CPU 0、CPU 1 和 CPU 2 上执行。

我们可以设置容器允许执行的内存节点（mems）。仅在 NUMA 系统上有效。

示例：

```console
$ docker run -it --cpuset-mems="1,3" ubuntu:24.04 /bin/bash
```

此示例限制容器中的进程仅使用内存节点 1 和 3 的内存。

```console
$ docker run -it --cpuset-mems="0-2" ubuntu:24.04 /bin/bash
```

此示例限制容器中的进程仅使用内存节点 0、1 和 2 的内存。

### CPU 配额约束（CPU quota constraint）

`--cpu-quota` 标志限制容器的 CPU 使用率。默认值 0 允许容器占用 100% 的 CPU 资源（1 个 CPU）。CFS（完全公平调度器）处理执行进程的资源分配，是内核使用的默认 Linux 调度器。将此值设置为 50000 可将容器限制为 50% 的 CPU 资源。对于多个 CPU，根据需要调整 `--cpu-quota`。更多信息，请参阅[关于带宽限制的 CFS 文档](https://www.kernel.org/doc/Documentation/scheduler/sched-bwc.txt)。

### 块 IO 带宽（Blkio）约束

默认情况下，所有容器获得相同比例的块 IO 带宽（blkio）。该比例为 500。要修改此比例，请使用 `--blkio-weight` 标志更改容器的 blkio 权重（相对于所有其他运行中容器的权重）。

> [!NOTE]
> blkio 权重设置仅适用于直接 IO。目前不支持缓冲 IO。

`--blkio-weight` 标志可以将权重设置为 10 到 1000 之间的值。例如，以下命令创建了两个具有不同 blkio 权重的容器：

```console
$ docker run -it --name c1 --blkio-weight 300 ubuntu:24.04 /bin/bash
$ docker run -it --name c2 --blkio-weight 600 ubuntu:24.04 /bin/bash
```

如果你同时在两个容器中进行块 IO，例如：

```console
$ time dd if=/mnt/zerofile of=test.out bs=1M count=1024 oflag=direct
```

你会发现时间比例与两个容器的 blkio 权重比例相同。

`--blkio-weight-device="DEVICE_NAME:WEIGHT"` 标志设置特定设备的权重。`DEVICE_NAME:WEIGHT` 是一个字符串，包含冒号分隔的设备名称和权重。例如，将 `/dev/sda` 设备权重设置为 `200`：

```console
$ docker run -it \
    --blkio-weight-device "/dev/sda:200" \
    ubuntu
```

如果同时指定了 `--blkio-weight` 和 `--blkio-weight-device`，Docker 使用 `--blkio-weight` 作为默认权重，并使用 `--blkio-weight-device` 覆盖特定设备上的默认值。以下示例使用默认权重 `300`，并在 `/dev/sda` 上将其覆盖为 `200`：

```console
$ docker run -it \
    --blkio-weight 300 \
    --blkio-weight-device "/dev/sda:200" \
    ubuntu
```

`--device-read-bps` 标志限制从设备读取的速率（字节/秒）。例如，此命令创建一个容器，并限制从 `/dev/sda` 读取的速率为每秒 `1mb`：

```console
$ docker run -it --device-read-bps /dev/sda:1mb ubuntu
```

`--device-write-bps` 标志限制向设备写入的速率（字节/秒）。例如，此命令创建一个容器，并限制向 `/dev/sda` 写入的速率为每秒 `1mb`：

```console
$ docker run -it --device-write-bps /dev/sda:1mb ubuntu
```

这两个标志都采用 `<device-path>:<limit>[unit]` 格式的限制。读取和写入速率必须是正整数。你可以以 `kb`（千字节）、`mb`（兆字节）或 `gb`（千兆字节）为单位指定速率。

`--device-read-iops` 标志限制从设备读取的速率（每秒 IO 数）。例如，此命令创建一个容器，并限制从 `/dev/sda` 读取的速率为每秒 `1000` IO：

```console
$ docker run -it --device-read-iops /dev/sda:1000 ubuntu
```

`--device-write-iops` 标志限制向设备写入的速率（每秒 IO 数）。例如，此命令创建一个容器，并限制向 `/dev/sda` 写入的速率为每秒 `1000` IO：

```console
$ docker run -it --device-write-iops /dev/sda:1000 ubuntu
```

这两个标志都采用 `<device-path>:<limit>` 格式的限制。读取和写入速率必须是正整数。

## 附加组（Additional groups）

```console
--group-add: 添加附加组以运行
```

默认情况下，docker 容器进程使用为指定用户查找的附加组运行。如果希望向该组列表中添加更多组，可以使用此标志：

```console
$ docker run --rm --group-add audio --group-add nogroup --group-add 777 busybox id

uid=0(root) gid=0(root) groups=10(wheel),29(audio),99(nogroup),777
```

## 运行时权限与 Linux 能力（Runtime privilege and Linux capabilities）

| 选项               | 描述                                                                   |
|:-------------------|:-----------------------------------------------------------------------|
| `--cap-add`        | 添加 Linux 能力                                                        |
| `--cap-drop`       | 移除 Linux 能力                                                       |
| `--privileged`     | 赋予此容器扩展权限                                                    |
| `--device=[]`      | 允许你在不使用 `--privileged` 标志的情况下在容器内运行设备             |

默认情况下，Docker 容器是“非特权”的，例如，不能在 Docker 容器内运行 Docker 守护进程。这是因为默认情况下容器不允许访问任何设备，而“特权”容器被授予访问所有设备的权限（请参阅关于 [cgroups devices](https://www.kernel.org/doc/Documentation/cgroup-v1/devices.txt) 的文档）。

`--privileged` 标志赋予容器所有能力。当操作员执行 `docker run --privileged` 时，Docker 启用对主机上所有设备的访问，并重新配置 AppArmor 或 SELinux，以允许容器几乎拥有与主机上容器外部运行的进程相同的主机访问权限。请谨慎使用此标志。关于 `--privileged` 标志的更多信息，请参阅 [`docker run` 参考](https://docs.docker.com/reference/cli/docker/container/run/#privileged)。

如果你想限制对特定一个或多个设备的访问，可以使用 `--device` 标志。它允许你指定一个或多个将在容器内可访问的设备。

```console
$ docker run --device=/dev/snd:/dev/snd ...
```

默认情况下，容器将能够对这些设备执行 `read`、`write` 和 `mknod` 操作。这可以通过为每个 `--device` 标志添加第三个 `:rwm` 选项集来覆盖：

```console
$ docker run --device=/dev/sda:/dev/xvdc --rm -it ubuntu fdisk  /dev/xvdc

Command (m for help): q
$ docker run --device=/dev/sda:/dev/xvdc:r --rm -it ubuntu fdisk  /dev/xvdc
You will not be able to write the partition table.

Command (m for help): q

$ docker run --device=/dev/sda:/dev/xvdc:w --rm -it ubuntu fdisk  /dev/xvdc
    crash....

$ docker run --device=/dev/sda:/dev/xvdc:m --rm -it ubuntu fdisk  /dev/xvdc
fdisk: unable to open /dev/xvdc: Operation not permitted
```

除了 `--privileged`，操作员还可以使用 `--cap-add` 和 `--cap-drop` 对能力进行细粒度控制。默认情况下，Docker 有一个保留的默认能力列表。下表列出了默认允许且可以移除的 Linux 能力选项。

| 能力键（Capability Key） | 能力描述                                                                                                         |
|:-------------------------|:-----------------------------------------------------------------------------------------------------------------|
| AUDIT_WRITE              | 将记录写入内核审计日志。                                                                                         |
| CHOWN                    | 任意更改文件 UID 和 GID（参见 chown(2)）。                                                                       |
| DAC_OVERRIDE             | 绕过文件读、写和执行权限检查。                                                                                    |
| FOWNER                   | 绕过通常要求进程的文件系统 UID 与文件 UID 匹配的操作上的权限检查。                                                  |
| FSETID                   | 修改文件时不清除 set-user-ID 和 set-group-ID 权限位。                                                              |
| KILL                     | 绕过发送信号的权限检查。                                                                                          |
| MKNOD                    | 使用 mknod(2) 创建特殊文件。                                                                                     |
| NET_BIND_SERVICE         | 将套接字绑定到互联网域特权端口（端口号小于 1024）。                                                               |
| NET_RAW                  | 使用 RAW 和 PACKET 套接字。                                                                                      |
| SETFCAP                  | 设置文件能力。                                                                                                   |
| SETGID                   | 任意操作进程 GID 和附加 GID 列表。                                                                               |
| SETPCAP                  | 修改进程能力。                                                                                                   |
| SETUID                   | 任意操作进程 UID。                                                                                               |
| SYS_CHROOT               | 使用 chroot(2)，更改根目录。                                                                                     |

下表显示了默认未授予但可以添加的能力。

| 能力键（Capability Key） | 能力描述                                                                                                         |
|:-------------------------|:-----------------------------------------------------------------------------------------------------------------|
| AUDIT_CONTROL            | 启用和禁用内核审计；更改审计过滤规则；检索审计状态和过滤规则。                                                    |
| AUDIT_READ               | 允许通过多播 netlink 套接字读取审计日志。                                                                        |
| BLOCK_SUSPEND            | 允许阻止系统挂起。                                                                                               |
| BPF                      | 允许创建 BPF 映射、加载 BPF 类型格式（BTF）数据、检索 BPF 程序的 JITed 代码等。                                    |
| CHECKPOINT_RESTORE       | 允许检查点/恢复相关操作。在内核 5.9 中引入。                                                                      |
| DAC_READ_SEARCH          | 绕过文件读权限检查和目录读与执行权限检查。                                                                        |
| IPC_LOCK                 | 锁定内存（mlock(2)、mlockall(2)、mmap(2)、shmctl(2)）。                                                           |
| IPC_OWNER                | 绕过对 System V IPC 对象的操作权限检查。                                                                          |
| LEASE                    | 在任意文件上建立租约（参见 fcntl(2)）。                                                                            |
| LINUX_IMMUTABLE          | 设置 FS_APPEND_FL 和 FS_IMMUTABLE_FL i-node 标志。                                                                |
| MAC_ADMIN                | 允许 MAC 配置或状态更改。为 Smack LSM 实现。                                                                      |
| MAC_OVERRIDE             | 覆盖强制访问控制（MAC）。为 Smack Linux 安全模块（LSM）实现。                                                      |
| NET_ADMIN                | 执行各种网络相关操作。                                                                                            |
| NET_BROADCAST            | 进行套接字广播，并监听多播。                                                                                      |
| PERFMON                  | 允许使用 perf_events、i915_perf 和其他内核子系统进行系统性能和可观测性特权操作。                                    |
| SYS_ADMIN                | 执行一系列系统管理操作。                                                                                           |
| SYS_BOOT                 | 使用 reboot(2) 和 kexec_load(2)，重启并加载新内核以供后续执行。                                                    |
| SYS_MODULE               | 加载和卸载内核模块。                                                                                              |
| SYS_NICE                 | 提高进程 nice 值（nice(2)、setpriority(2)），并更改任意进程的 nice 值。                                            |
| SYS_PACCT                | 使用 acct(2)，打开或关闭进程记账。                                                                                |
| SYS_PTRACE               | 使用 ptrace(2) 跟踪任意进程。                                                                                     |
| SYS_RAWIO                | 执行 I/O 端口操作（iopl(2) 和 ioperm(2)）。                                                                       |
| SYS_RESOURCE             | 覆盖资源限制。                                                                                                   |
| SYS_TIME                 | 设置系统时钟（settimeofday(2)、stime(2)、adjtimex(2)）；设置实时（硬件）时钟。                                     |
| SYS_TTY_CONFIG           | 使用 vhangup(2)；对虚拟终端执行各种特权的 ioctl(2) 操作。                                                          |
| SYSLOG                   | 执行特权的 syslog(2) 操作。                                                                                       |
| WAKE_ALARM               | 触发将唤醒系统的事件。                                                                                            |

更多参考信息请参阅 [capabilities(7) - Linux man page](https://man7.org/linux/man-pages/man7/capabilities.7.html) 以及 [Linux 内核源代码](https://github.com/torvalds/linux/blob/124ea650d3072b005457faed69909221c2905a1f/include/uapi/linux/capability.h)。

这两个标志都支持值 `ALL`，因此要允许容器使用除 `MKNOD` 之外的所有能力：

```console
$ docker run --cap-add=ALL --cap-drop=MKNOD ...
```

`--cap-add` 和 `--cap-drop` 标志接受可以带 `CAP_` 前缀指定的能力。因此以下示例是等价的：

```console
$ docker run --cap-add=SYS_ADMIN ...
$ docker run --cap-add=CAP_SYS_ADMIN ...
```

对于网络栈的交互，不应使用 `--privileged`，而应使用 `--cap-add=NET_ADMIN` 来修改网络接口。

```console
$ docker run -it --rm  ubuntu:24.04 ip link add dummy0 type dummy

RTNETLINK answers: Operation not permitted

$ docker run -it --rm --cap-add=NET_ADMIN ubuntu:24.04 ip link add dummy0 type dummy
```

要挂载基于 FUSE 的文件系统，你需要同时使用 `--cap-add` 和 `--device`：

```console
$ docker run --rm -it --cap-add SYS_ADMIN sshfs sshfs sven@10.10.10.20:/home/sven /mnt

fuse: failed to open /dev/fuse: Operation not permitted

$ docker run --rm -it --device /dev/fuse sshfs sshfs sven@10.10.10.20:/home/sven /mnt

fusermount: mount failed: Operation not permitted

$ docker run --rm -it --cap-add SYS_ADMIN --device /dev/fuse sshfs

# sshfs sven@10.10.10.20:/home/sven /mnt
The authenticity of host '10.10.10.20 (10.10.10.20)' can't be established.
ECDSA key fingerprint is 25:34:85:75:25:b0:17:46:05:19:04:93:b5:dd:5f:c6.
Are you sure you want to continue connecting (yes/no)? yes
sven@10.10.10.20's password:

root@30aa0cfaf1b5:/# ls -la /mnt/src/docker

total 1516
drwxrwxr-x 1 1000 1000   4096 Dec  4 06:08 .
drwxrwxr-x 1 1000 1000   4096 Dec  4 11:46 ..
-rw-rw-r-- 1 1000 1000     16 Oct  8 00:09 .dockerignore
-rwxrwxr-x 1 1000 1000    464 Oct  8 00:09 .drone.yml
drwxrwxr-x 1 1000 1000   4096 Dec  4 06:11 .git
-rw-rw-r-- 1 1000 1000    461 Dec  4 06:08 .gitignore
....
```

默认的 seccomp 配置文件将根据所选能力进行调整，以允许使用能力所允许的功能，因此你不应需要调整此设置。

## 覆盖镜像默认值（Overriding image defaults）

当你从 [Dockerfile](https://docs.docker.com/reference/dockerfile/) 构建镜像或提交镜像时，可以设置许多默认参数，这些参数在镜像作为容器启动时生效。当你运行镜像时，可以使用 `docker run` 命令的标志覆盖这些默认值。

- [默认入口点（Default entrypoint）](#default-entrypoint)
- [默认命令和选项（Default command and options）](#default-command-and-options)
- [暴露端口（Expose ports）](#exposed-ports)
- [环境变量（Environment variables）](#environment-variables)
- [健康检查（Healthcheck）](#healthchecks)
- [用户（User）](#user)
- [工作目录（Working directory）](#working-directory)

### 默认命令和选项（Default command and options）

`docker run` 的命令语法支持可选地为容器的入口点指定命令和参数，在以下示例语法中表示为 `[COMMAND]` 和 `[ARG...]`：

```console
$ docker run [OPTIONS] IMAGE[:TAG|@DIGEST] [COMMAND] [ARG...]
```

此命令是可选的，因为创建 `IMAGE` 的人可能已经使用 Dockerfile `CMD` 指令提供了默认的 `COMMAND`。当你运行容器时，只需指定一个新的 `COMMAND` 即可覆盖该 `CMD` 指令。

如果镜像还指定了 `ENTRYPOINT`，则 `CMD` 或 `COMMAND` 将作为参数附加到 `ENTRYPOINT`。

### 默认入口点（Default entrypoint）

```text
--entrypoint="": 覆盖镜像设置的默认入口点
```

入口点是指运行容器时调用的默认可执行文件。容器的入口点是使用 Dockerfile `ENTRYPOINT` 指令定义的。这类似于指定默认命令，但区别在于你需要传递一个显式标志来覆盖入口点，而你可以使用位置参数覆盖默认命令。它定义了容器的默认行为，理念是当你设置了一个入口点，你可以*像运行那个二进制文件一样*运行容器，带有默认选项，并且你可以作为命令传入更多选项。但在某些情况下，你可能希望在容器内运行其他程序。这时，在运行时使用 `docker run` 命令的 `--entrypoint` 标志覆盖默认入口点就派上了用场。

`--entrypoint` 标志期望一个字符串值，表示你希望在容器启动时调用的二进制文件的名称或路径。以下示例向你展示了如何在一个已设置自动运行其他二进制文件（如 `/usr/bin/redis-server`）的容器中运行 Bash shell：

```console
$ docker run -it --entrypoint /bin/bash example/redis
```

以下示例展示了如何使用位置命令参数向自定义入口点传递额外参数：

```console
$ docker run -it --entrypoint /bin/bash example/redis -c ls -l
$ docker run -it --entrypoint /usr/bin/redis-cli example/redis --help
```

你可以通过传递空字符串来重置容器的入口点，例如：

```console
$ docker run -it --entrypoint="" mysql bash
```

> [!NOTE]
> 传递 `--entrypoint` 会清除镜像上设置的任何默认命令。即，用于构建镜像的 Dockerfile 中的任何 `CMD` 指令。

### 暴露端口（Exposed ports）

默认情况下，当你运行容器时，容器的任何端口都不会暴露给主机。这意味着你将无法访问容器可能正在监听的任何端口。要使容器的端口可以从主机访问，你需要发布这些端口。

你可以使用 `-P` 或 `-p` 标志启动容器以暴露其端口：

- `-P`（或 `--publish-all`）标志将所有暴露的端口发布到主机。Docker 将每个暴露的端口绑定到主机上的一个随机端口。

  `-P` 标志仅发布那些被显式标记为暴露的端口，这些端口要么使用 Dockerfile `EXPOSE` 指令，要么使用 `docker run` 命令的 `--expose` 标志。

- `-p`（或 `--publish`）标志允许你显式地将容器中的单个端口或端口范围映射到主机。

容器内部的端口号（服务监听的位置）不需要与容器外部发布的端口号（客户端连接的位置）匹配。例如，容器内部的一个 HTTP 服务可能监听 80 端口。在运行时，该端口可能绑定到主机上的 42800 端口。要查找主机端口和暴露端口之间的映射，请使用 `docker port` 命令。

### 环境变量（Environment variables）

Docker 在创建 Linux 容器时会自动设置一些环境变量。创建 Windows 容器时，Docker 不会设置任何环境变量。

以下环境变量是为 Linux 容器设置的：

| 变量       | 值                                                                                                   |
|:-----------|:------------------------------------------------------------------------------------------------------|
| `HOME`     | 基于 `USER` 的值设置                                                                                  |
| `HOSTNAME` | 与容器关联的主机名                                                                                    |
| `PATH`     | 包含常用目录，例如 `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`                      |
| `TERM`     | 如果容器分配了伪终端（pseudo-TTY），则为 `xterm`                                                      |

此外，你可以使用一个或多个 `-e` 标志在容器中设置任何环境变量。你甚至可以覆盖上述变量，或在构建镜像时使用 Dockerfile `ENV` 指令定义的变量。

如果你命名一个环境变量而不指定值，主机上该命名变量的当前值将传播到容器的环境中：

```console
$ export today=Wednesday
$ docker run -e "deep=purple" -e today --rm alpine env

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOSTNAME=d2219b854598
deep=purple
today=Wednesday
HOME=/root
```

```powershell
PS C:\> docker run --rm -e "foo=bar" microsoft/nanoserver cmd /s /c set
ALLUSERSPROFILE=C:\ProgramData
APPDATA=C:\Users\ContainerAdministrator\AppData\Roaming
CommonProgramFiles=C:\Program Files\Common Files
CommonProgramFiles(x86)=C:\Program Files (x86)\Common Files
CommonProgramW6432=C:\Program Files\Common Files
COMPUTERNAME=C2FAEFCC8253
ComSpec=C:\Windows\system32\cmd.exe
foo=bar
LOCALAPPDATA=C:\Users\ContainerAdministrator\AppData\Local
NUMBER_OF_PROCESSORS=8
OS=Windows_NT
Path=C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0\;C:\Users\ContainerAdministrator\AppData\Local\Microsoft\WindowsApps
PATHEXT=.COM;.EXE;.BAT;.CMD
PROCESSOR_ARCHITECTURE=AMD64
PROCESSOR_IDENTIFIER=Intel64 Family 6 Model 62 Stepping 4, GenuineIntel
PROCESSOR_LEVEL=6
PROCESSOR_REVISION=3e04
ProgramData=C:\ProgramData
ProgramFiles=C:\Program Files
ProgramFiles(x86)=C:\Program Files (x86)
ProgramW6432=C:\Program Files
PROMPT=$P$G
PUBLIC=C:\Users\Public
SystemDrive=C:
SystemRoot=C:\Windows
TEMP=C:\Users\ContainerAdministrator\AppData\Local\Temp
TMP=C:\Users\ContainerAdministrator\AppData\Local\Temp
USERDOMAIN=User Manager
USERNAME=ContainerAdministrator
USERPROFILE=C:\Users\ContainerAdministrator
windir=C:\Windows
```

### 健康检查（Healthchecks）

健康检查（Healthcheck）的意义在于**让 Docker 能够主动探测容器内部业务是否真正可用**，而不是仅依赖容器的进程状态（运行/退出）。

默认情况下，Docker 只关心容器的主进程是否在运行。如果主进程没有崩溃，Docker 就认为容器是“运行中”的。但实际场景中，进程虽然活着，业务可能已经不可用（例如：死锁、依赖服务失效、HTTP 接口无响应）。健康检查就是用来解决这个问题的。

#### 主要作用

1. **自动恢复**  
   当健康检查连续失败达到指定次数（`--health-retries`），Docker 会将容器标记为 `unhealthy`。如果容器配置了重启策略（`--restart`），Docker 可以自动重启该容器，尝试恢复服务。

2. **服务负载均衡与滚动更新**  
   在 Swarm 或 Kubernetes 等编排环境中，只有通过健康检查的容器才会继续接收流量。滚动更新时，新容器必须通过健康检查才会替代旧容器，保证服务不中断。

3. **状态可见**  
   `docker ps` 会显示容器的健康状态（`healthy` / `unhealthy` / `starting`），便于运维人员快速定位问题。

4. **自定义探测逻辑**  
   健康检查命令（`--health-cmd`）由用户定义，可以是任意脚本或程序（如 `curl http://localhost/health`、`pg_isready`、`redis-cli ping`）。这使其能适应各种应用的健康判断标准。

#### 典型配置示例

```bash
docker run \
  --health-cmd="curl -f http://localhost/ || exit 1" \
  --health-interval=30s \
  --health-timeout=5s \
  --health-retries=3 \
  --health-start-period=10s \
  myapp
```

- `--health-interval`：每 30 秒检查一次  
- `--health-timeout`：单次检查超时 5 秒  
- `--health-retries`：连续失败 3 次后标记为 `unhealthy`  
- `--health-start-period`：容器启动后 10 秒内不记录失败，给应用初始化时间

#### 总结

**健康检查让容器编排系统从“进程活着”进化到“服务健康”**，是实现高可用、自愈、滚动更新的基础功能。没有健康检查，容器管理工具只能盲目地根据进程状态做出决策，无法应对业务层面的异常。

以下 `docker run` 命令的标志允许你控制容器健康检查的参数：

| 选项                         | 描述                                                                            |
|:-----------------------------|:--------------------------------------------------------------------------------|
| `--health-cmd`               | 运行以检查健康的命令                                                             |
| `--health-interval`          | 运行检查之间的时间间隔                                                           |
| `--health-retries`           | 报告不健康所需的连续失败次数                                                     |
| `--health-timeout`           | 允许一次检查运行的最大时间                                                       |
| `--health-start-period`      | 容器在开始健康检查重试倒计时之前的初始化启动期                                   |
| `--health-start-interval`    | 在启动期间运行检查之间的时间间隔                                                 |
| `--no-healthcheck`           | 禁用任何容器指定的 `HEALTHCHECK`                                                |

示例：

```console
$ docker run --name=test -d \
    --health-cmd='stat /etc/passwd || exit 1' \
    --health-interval=2s \
    busybox sleep 1d
$ sleep 2; docker inspect --format='{{.State.Health.Status}}' test
healthy
$ docker exec test rm /etc/passwd
$ sleep 2; docker inspect --format='{{json .State.Health}}' test
{
  "Status": "unhealthy",
  "FailingStreak": 3,
  "Log": [
    {
      "Start": "2016-05-25T17:22:04.635478668Z",
      "End": "2016-05-25T17:22:04.7272552Z",
      "ExitCode": 0,
      "Output": "  File: /etc/passwd\n  Size: 334       \tBlocks: 8          IO Block: 4096   regular file\nDevice: 32h/50d\tInode: 12          Links: 1\nAccess: (0664/-rw-rw-r--)  Uid: (    0/    root)   Gid: (    0/    root)\nAccess: 2015-12-05 22:05:32.000000000\nModify: 2015..."
    },
    {
      "Start": "2016-05-25T17:22:06.732900633Z",
      "End": "2016-05-25T17:22:06.822168935Z",
      "ExitCode": 0,
      "Output": "  File: /etc/passwd\n  Size: 334       \tBlocks: 8          IO Block: 4096   regular file\nDevice: 32h/50d\tInode: 12          Links: 1\nAccess: (0664/-rw-rw-r--)  Uid: (    0/    root)   Gid: (    0/    root)\nAccess: 2015-12-05 22:05:32.000000000\nModify: 2015..."
    },
    {
      "Start": "2016-05-25T17:22:08.823956535Z",
      "End": "2016-05-25T17:22:08.897359124Z",
      "ExitCode": 1,
      "Output": "stat: can't stat '/etc/passwd': No such file or directory\n"
    },
    {
      "Start": "2016-05-25T17:22:10.898802931Z",
      "End": "2016-05-25T17:22:10.969631866Z",
      "ExitCode": 1,
      "Output": "stat: can't stat '/etc/passwd': No such file or directory\n"
    },
    {
      "Start": "2016-05-25T17:22:12.971033523Z",
      "End": "2016-05-25T17:22:13.082015516Z",
      "ExitCode": 1,
      "Output": "stat: can't stat '/etc/passwd': No such file or directory\n"
    }
  ]
}
```

健康状态也会显示在 `docker ps` 输出中。

### 用户（User）

容器内的默认用户是 `root`（uid = 0）。你可以使用 Dockerfile `USER` 指令设置运行第一个进程的默认用户。启动容器时，可以通过传递 `-u` 选项覆盖 `USER` 指令。

```text
-u="", --user="": 设置用户名或 UID，并可选择设置组名或 GID 用于指定命令。
```

以下示例都是有效的：

```text
--user=[ user | user:group | uid | uid:gid | user:gid | uid:group ]
```

> [!NOTE]
> 如果你传递数字用户 ID，它必须在 0-2147483647 范围内。如果你传递用户名，该用户必须存在于容器中。

### 工作目录（Working directory）

在容器内运行二进制文件的默认工作目录是根目录（`/`）。镜像的默认工作目录使用 Dockerfile `WORKDIR` 命令设置。你可以使用 `docker run` 命令的 `-w`（或 `--workdir`）标志覆盖镜像的默认工作目录：

```text
$ docker run --rm -w /my/workdir alpine pwd
/my/workdir
```

如果该目录在容器中尚不存在，则会创建它。