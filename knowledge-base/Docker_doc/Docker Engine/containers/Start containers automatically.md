# 自动启动容器（Start containers automatically）

Docker 提供了[重启策略（restart policies）](/reference/cli/docker/container/run/#restart)，用于控制容器在退出时或 Docker 重启时是否自动启动。重启策略会按正确顺序启动有依赖关系的容器。Docker 推荐使用重启策略，而不是使用进程管理器来启动容器。

重启策略与 `dockerd` 命令的 `--live-restore` 标志不同。使用 `--live-restore` 可以在 Docker 升级期间让容器保持运行，但网络和用户输入会中断。

## 使用重启策略（Use a restart policy）

要为容器配置重启策略，请在 `docker run` 命令中使用 [`--restart`](/reference/cli/docker/container/run/#restart) 标志。`--restart` 标志的值可以是以下任意一种：

| 标志                           | 描述                                                                                                                                                                                                                                                                                                                                                           |
| :----------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `no`                           | 不自动重启容器。（默认）                                                                                                                                                                                                                                                                                                                  |
| `on-failure[:max-retries]`     | 如果容器因错误（非零退出码）而退出，则重启容器。可以选择使用 `:max-retries` 选项限制 Docker 守护进程尝试重启容器的次数。`on-failure` 策略仅在容器因失败退出时触发重启。守护进程重启时不会触发此策略。 |
| `always`                       | 容器停止时总是重启。如果容器被手动停止，只有在 Docker 守护进程重启或容器本身被手动重启时才会重启。（参见[重启策略详情](#restart-policy-details)中的第二条）                                                                                                                |
| `unless-stopped`               | 类似于 `always`，但当容器被（手动或其他方式）停止后，即使 Docker 守护进程重启，也不会再重启该容器。                                                                                                                                                                                             |

以下命令启动一个 Redis 容器，并配置其总是重启，除非容器被显式停止或守护进程重启。

```console
$ docker run -d --restart unless-stopped redis
```

以下命令更改一个已运行容器（名为 `redis`）的重启策略。

```console
$ docker update --restart unless-stopped redis
```

以下命令确保所有正在运行的容器都会（在停止时）重启。

```console
$ docker update --restart unless-stopped $(docker ps -q)
```

### 重启策略详情（Restart policy details）

使用重启策略时，请记住以下几点：

- 重启策略仅在容器成功启动后才生效。这里“成功启动”意味着容器至少运行了 10 秒，并且 Docker 已经开始监控它。这可以防止一个根本无法启动的容器陷入重启循环。

- 如果手动停止一个容器，则重启策略将被忽略，直到 Docker 守护进程重启或容器被手动重启。这可以防止重启循环。

- 重启策略仅适用于容器。要为 Swarm 服务配置重启策略，请参阅[与服务重启相关的标志](/reference/cli/docker/service/create/)。

### 前台容器的重启（Restarting foreground containers）

当前台运行容器时，停止容器会导致附加的 CLI 也退出，无论容器的重启策略如何。下面的示例说明了此行为。

1. 创建一个 Dockerfile，打印数字 1 到 5，然后退出。

   ```dockerfile
   FROM busybox:latest
   COPY --chmod=755 <<"EOF" /start.sh
   echo "Starting..."
   for i in $(seq 1 5); do
     echo "$i"
     sleep 1
   done
   echo "Exiting..."
   exit 1
   EOF
   ENTRYPOINT /start.sh
   ```

2. 根据 Dockerfile 构建镜像。

   ```console
   $ docker build -t startstop .
   ```

3. 从镜像运行一个容器，并为其指定重启策略为 `always`。

   容器将数字 1..5 打印到标准输出，然后退出。这会导致附加的 CLI 也退出。

   ```console
   $ docker run --restart always startstop
   Starting...
   1
   2
   3
   4
   5
   Exiting...
   $
   ```

4. 运行 `docker ps` 显示，由于重启策略，容器仍在运行或正在重启。但是，CLI 会话已经退出。它不会在容器首次退出后继续存在。

   ```console
   $ docker ps
   CONTAINER ID   IMAGE       COMMAND                  CREATED         STATUS         PORTS     NAMES
   081991b35afe   startstop   "/bin/sh -c /start.sh"   9 seconds ago   Up 4 seconds             gallant_easley
   ```

5. 您可以在容器重启之间使用 `docker container attach` 命令重新将终端附加到容器。下次容器退出时，终端将再次分离。

   ```console
   $ docker container attach 081991b35afe
   4
   5
   Exiting...
   $
   ```

## 使用进程管理器（Use a process manager）

如果重启策略不适合您的需求（例如，当 Docker 外部的进程依赖于 Docker 容器时），您可以使用进程管理器，例如 [systemd](https://systemd.io/) 或 [supervisor](http://supervisord.org/)。

> [!WARNING]
>
> 不要将 Docker 的重启策略与主机级别的进程管理器结合使用，因为这样会产生冲突。

要使用进程管理器，请配置它以通常手动启动容器时使用的相同 `docker start` 或 `docker service` 命令来启动您的容器或服务。有关更多详细信息，请查阅特定进程管理器的文档。

### 在容器内部使用进程管理器（Using a process manager inside containers）

进程管理器也可以在容器内部运行，以检查进程是否在运行，如果不在则启动/重启它。

> [!WARNING]
>
> 这些进程管理器不了解 Docker，并且只监控容器内的操作系统进程。Docker 不推荐这种方法，因为它是平台相关的，并且在给定 Linux 发行版的不同版本之间可能会有所不同。