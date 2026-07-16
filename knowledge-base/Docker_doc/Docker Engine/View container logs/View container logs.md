# View container logs（查看容器日志）

`docker logs` 命令显示运行中容器所记录的信息。  
`docker service logs` 命令显示参与某个服务的所有容器所记录的信息。  
记录的信息以及日志的格式几乎完全取决于容器的 endpoint command（入口点命令）。

默认情况下，`docker logs` 或 `docker service logs` 显示命令的输出，就像您在终端中交互式运行该命令时看到的那样。  
Unix 和 Linux 命令在运行时通常会打开三个 I/O 流，分别称为 `STDIN`、`STDOUT` 和 `STDERR`。  
`STDIN` 是命令的输入流，可以包含来自键盘或其他命令的输入。  
`STDOUT` 通常是命令的正常输出，而 `STDERR` 通常用于输出错误消息。  
默认情况下，`docker logs` 显示命令的 `STDOUT` 和 `STDERR`。  
要阅读更多关于 I/O 和 Linux 的内容，请参阅 [Linux 文档项目关于 I/O 重定向的文章](https://tldp.org/LDP/abs/html/io-redirection.html)。

在某些情况下，除非您采取额外步骤，否则 `docker logs` 可能不会显示有用的信息。

- 如果您使用某个 [logging driver（日志驱动程序）](/engine/logging/configure/) 将日志发送到文件、外部主机、数据库或其他日志后端，并且禁用了 [“dual logging”（双重日志）](/engine/logging/dual-logging/)，则 `docker logs` 可能不会显示有用的信息。
- 如果您的镜像运行一个非交互式进程（例如 web 服务器或数据库），该应用程序可能会将输出发送到日志文件，而不是 `STDOUT` 和 `STDERR`。

在第一种情况下，您的日志会以其他方式处理，您可以选择不使用 `docker logs`。  
在第二种情况下，官方 `nginx` 镜像展示了一种解决方法，而官方 Apache `httpd` 镜像展示了另一种方法。

官方 `nginx` 镜像创建了一个从 `/var/log/nginx/access.log` 到 `/dev/stdout` 的符号链接，并创建了另一个从 `/var/log/nginx/error.log` 到 `/dev/stderr` 的符号链接，从而覆盖日志文件，使日志被发送到相应的特殊设备。请参阅 [Dockerfile](https://github.com/nginxinc/docker-nginx/blob/8921999083def7ba43a06fabd5f80e4406651353/mainline/jessie/Dockerfile#L21-L23)。

官方 `httpd` 镜像修改了 `httpd` 应用程序的配置，将其正常输出直接写入 `/proc/self/fd/1`（即 `STDOUT`），并将错误输出写入 `/proc/self/fd/2`（即 `STDERR`）。请参阅 [Dockerfile](https://github.com/docker-library/httpd/blob/b13054c7de5c74bbaa6d595dbe38969e6d4f860c/2.2/Dockerfile#L72-L75)。

## 下一步

- 配置 [logging drivers（日志驱动程序）](/engine/logging/configure/)。
- 编写 [Dockerfile](/reference/dockerfile/)。