# Host 网络驱动（Host network driver）

如果您为容器使用 `host` 网络模式，则该容器的网络栈不会与 Docker 主机隔离（容器共享主机的网络命名空间），并且容器不会被分配自己的 IP 地址。例如，如果您运行一个绑定到端口 80 的容器并使用 `host` 网络，则该容器的应用程序将在主机的 IP 地址上的端口 80 可用。

> [!NOTE]
>
> 由于使用 `host` 模式网络时容器没有自己的 IP 地址，[端口映射](/engine/network/drivers/host/overlay/#publish-ports) 不会生效，并且 `-p`、`--publish`、`-P` 和 `--publish-all` 选项将被忽略，取而代之的是产生一个警告：
>
> ```console
> WARNING: Published ports are discarded when using host network mode
> ```

Host 模式网络对以下用例很有用：

- 优化性能
- 容器需要处理大量端口的场景

这是因为不需要网络地址转换（NAT），也不会为每个端口创建“用户态代理（userland-proxy）”。

## 平台支持

Host 网络驱动在以下平台上受支持：

- Linux 上的 Docker Engine
- Docker Desktop 4.34 及更高版本（需要在设置中启用该功能）

> [!NOTE]
> 对于 Docker Desktop 用户，请参阅下面的 [Docker Desktop 部分](#docker-desktop) 了解设置说明。

您也可以将 `host` 网络用于 Swarm 服务，只需将 `--network host` 传递给 `docker service create` 命令。在这种情况下，控制流量（与管理 Swarm 和服务相关的流量）仍然通过 overlay 网络发送，但各个 Swarm 服务容器使用 Docker 守护进程的主机网络和端口发送数据。这会产生一些额外的限制。例如，如果一个服务容器绑定到端口 80，那么在给定的 Swarm 节点上只能运行一个服务容器。

## Docker Desktop

Host 网络在 Docker Desktop 4.34 及更高版本中受支持。要启用此功能：

1. 在 Docker Desktop 中登录您的 Docker 账户。
2. 导航到 **Settings**。
3. 在 **Resources** 选项卡下，选择 **Network**。
4. 勾选 **Enable host networking** 选项。
5. 选择 **Apply and restart**。

此功能是双向工作的。这意味着您可以从主机访问运行在容器中的服务器，也可以从启用了 host 网络的任何容器访问运行在您主机上的服务器。支持 TCP 和 UDP 作为通信协议。

### 示例

以下命令在一个容器中启动 netcat，该容器监听端口 `8000`：

```console
$ docker run --rm -it --net=host nicolaka/netshoot nc -lkv 0.0.0.0 8000
```

然后端口 `8000` 将在主机上可用，您可以从另一个终端使用以下命令连接到它：

```console
$ nc localhost 8000
```

您在此处输入的内容将显示在容器运行的终端上。

要从容器访问主机上运行的服务，您可以使用以下命令启动一个启用了 host 网络的容器：

```console
$ docker run --rm -it --net=host nicolaka/netshoot
```

然后，如果您想从容器访问主机上的服务（在此示例中为运行在端口 `80` 上的 Web 服务器），可以这样做：

```console
$ nc localhost 80
```

### 限制

- 容器内的进程无法绑定到主机的 IP 地址，因为容器无法直接访问主机的接口。
- Docker Desktop 的 host 网络功能工作在第四层。这意味着与 Linux 上的 Docker 不同，低于 TCP 或 UDP 的网络协议不受支持。
- 此功能在启用增强型容器隔离（Enhanced Container Isolation）时无法工作，因为将容器与主机隔离又允许它们访问主机网络是相互矛盾的。
- 仅支持 Linux 容器。Host 网络不适用于 Windows 容器。

## 使用示例

此示例展示了如何启动一个直接绑定到 Docker 主机上端口 80 的 Nginx 容器。从网络角度来看，这提供了与 Nginx 直接运行在主机上相同的隔离级别，但容器在所有其他方面（存储、进程命名空间、用户命名空间）保持隔离。

### 先决条件

- 端口 80 必须在 Docker 主机上可用。要让 Nginx 监听其他端口，请参阅 [Nginx 镜像文档](https://hub.docker.com/_/nginx/)。
- Host 网络驱动仅在 Linux 主机上工作，并在 Docker Desktop 4.34 及更高版本中作为可选功能。

### 步骤

1. 以后台进程方式创建并启动容器。`--rm` 选项会在容器退出时将其移除。`-d` 标志使其在后台运行：

   ```console
   $ docker run --rm -d --network host --name my_nginx nginx
   ```

2. 通过浏览 [http://localhost:80/](http://localhost:80/) 访问 Nginx。

3. 检查您的网络栈：

   检查所有网络接口，验证没有创建新接口：

   ```console
   $ ip addr show
   ```

   使用 `netstat` 验证哪个进程绑定到端口 80。您需要 `sudo`，因为该进程由 Docker 守护进程用户拥有：

   ```console
   $ sudo netstat -tulpn | grep :80
   ```

4. 停止容器。由于 `--rm` 选项，它会被自动移除：

   ```console
   $ docker container stop my_nginx
   ```

## 下一步

- 了解[从容器角度的网络](/engine/drivers/)
- 了解 [bridge 网络](/engine/network/drivers/bridge/)
- 了解 [overlay 网络](/engine/network/drivers/overlay/)
- 了解 [Macvlan 网络](/engine/network/drivers/macvlan/)
- 