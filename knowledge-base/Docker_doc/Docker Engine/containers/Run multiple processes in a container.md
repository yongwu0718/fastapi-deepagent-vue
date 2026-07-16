# 在容器中运行多个进程（Run multiple processes in a container）

容器的主要运行进程是 `Dockerfile` 末尾的 `ENTRYPOINT` 和/或 `CMD`。最佳实践是通过每个容器一个服务（one service per container）来分离关注点。该服务可能会派生（fork）出多个进程（例如，Apache Web 服务器会启动多个工作进程）。拥有多个进程是可以的，但为了充分利用 Docker，应避免让一个容器负责整个应用程序的多个方面。您可以使用用户定义的网络（user-defined networks）和共享卷（shared volumes）连接多个容器。

容器的主进程负责管理它启动的所有进程。在某些情况下，主进程设计不佳，无法在容器退出时优雅地“收割”（reaping）子进程。如果您的进程属于这种情况，可以在运行容器时使用 `--init` 选项。`--init` 标志会向容器中插入一个微小的 init 进程作为主进程，并在容器退出时处理所有进程的收割。以这种方式处理此类进程优于使用完整的 init 进程（如 `sysvinit` 或 `systemd`）来管理容器内的进程生命周期。

如果您需要在一个容器内运行多个服务，可以通过几种不同的方式实现。

## 使用包装脚本（Use a wrapper script）

将所有命令放入一个包装脚本（wrapper script）中，并包含测试和调试信息。将包装脚本作为 `CMD` 运行。下面是一个简单的示例。首先是包装脚本：

```bash
#!/bin/bash

# 启动第一个进程
./my_first_process &

# 启动第二个进程
./my_second_process &

# 等待任意进程退出
wait -n

# 以最先退出的进程的状态码退出
exit $?
```

接下来是 Dockerfile：

```dockerfile
# syntax=docker/dockerfile:1
FROM ubuntu:latest
COPY my_first_process my_first_process
COPY my_second_process my_second_process
COPY my_wrapper_script.sh my_wrapper_script.sh
CMD ./my_wrapper_script.sh
```

## 使用 Bash 作业控制（Use Bash job controls）

如果您有一个需要首先启动并保持运行的主进程，但临时需要运行一些其他进程（可能与主进程交互），那么可以使用 bash 的作业控制。首先是包装脚本：

```bash
#!/bin/bash

# 开启 bash 的作业控制
set -m

# 启动主进程并将其放入后台
./my_main_process &

# 启动辅助进程
./my_helper_process

# 辅助进程可能需要知道如何等待主进程启动后才能完成其工作并返回

# 现在将主进程重新带到前台
# 并使其保持在前台
fg %1
```

```dockerfile
# syntax=docker/dockerfile:1
FROM ubuntu:latest
COPY my_main_process my_main_process
COPY my_helper_process my_helper_process
COPY my_wrapper_script.sh my_wrapper_script.sh
CMD ./my_wrapper_script.sh
```

## 使用进程管理器（Use a process manager）

使用像 `supervisord` 这样的进程管理器。这比其他选项更复杂，因为它需要您将 `supervisord` 及其配置以及它所管理的不同应用程序打包到镜像中（或将您的镜像基于包含 `supervisord` 的镜像）。然后启动 `supervisord`，它会为您管理进程。

以下 Dockerfile 示例展示了这种方法。该示例假设在构建上下文的根目录中存在以下文件：

- `supervisord.conf`
- `my_first_process`
- `my_second_process`

```dockerfile
# syntax=docker/dockerfile:1
FROM ubuntu:latest
RUN apt-get update && apt-get install -y supervisor
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY my_first_process my_first_process
COPY my_second_process my_second_process
CMD ["/usr/bin/supervisord"]
```

如果希望确保两个进程将其 `stdout` 和 `stderr` 输出到容器日志，可以将以下内容添加到 `supervisord.conf` 文件中：

```ini
[supervisord]
nodaemon=true
logfile=/dev/null
logfile_maxbytes=0

[program:app]
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
```