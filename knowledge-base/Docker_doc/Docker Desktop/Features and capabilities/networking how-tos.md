# 在 Docker Desktop 上探索网络操作指南（networking how-tos）

本页说明如何配置和使用网络功能、将容器连接到主机服务、在代理或 VPN 后工作，以及排查常见问题。

关于 Docker Desktop 如何在容器、虚拟机和主机之间路由网络流量和文件 I/O 的详细信息，请参阅[网络概述](/desktop/features/networking/#overview)。

## 核心网络操作指南（Core networking how-tos）

### 将容器连接到主机上的服务（Connect a container to a service on the host）

主机的 IP 地址是变化的，或者在没有网络访问时可能没有地址。要连接到运行在主机上的服务，请使用特殊的 DNS 名称：

| 名称                      | 描述                                      |
| ------------------------- | ------------------------------------------------ |
| `host.docker.internal`    | 解析为主机的内部 IP 地址 |
| `gateway.docker.internal` | 解析为 Docker VM 的网关 IP |

#### 示例

在主机上运行一个简单的 HTTP 服务器，监听端口 `8000`：

```console
$ python -m http.server 8000
```

然后运行一个容器，安装 `curl`，并使用以下命令尝试连接到主机：

```console
$ docker run --rm -it alpine sh
# apk add curl
# curl http://host.docker.internal:8000
# exit
```

### 从主机连接到容器（Connect to a container from the host）

要从您的主机或本地网络访问容器化的服务，请使用 `-p` 或 `--publish` 标志发布端口。例如：

```console
$ docker run -d -p 80:80 --name webserver nginx
```

Docker Desktop 会使容器中运行在端口 `80` 上的任何服务（此例中为 `nginx`）在 `localhost` 的端口 `80` 上可用。

> [!TIP]
>
> `-p` 的语法是 `HOST_PORT:CLIENT_PORT`。

要发布所有端口，请使用 `-P` 标志。例如，以下命令启动一个容器（在 detached 模式下），`-P` 标志将容器的所有暴露端口发布到主机上的随机端口。

```console
$ docker run -d -P --name webserver nginx
```

或者，您也可以使用[主机网络（host networking）](/engine/network/drivers/host/#docker-desktop)让容器直接访问主机的网络栈。

有关与 `docker run` 一起使用的发布选项的更多详细信息，请参阅 [run 命令](/reference/cli/docker/container/run/)。

所有入站连接都经过 Docker Desktop 后端进程（Mac 上的 `com.docker.backend`、Windows 上的 `com.docker.backend` 或 Linux 上的 `qemu`），该进程处理进入 VM 的端口转发。更多详情，请参阅[暴露端口的工作原理](/desktop/features/networking/#how-exposed-ports-work)。

### 使用 VPN（Working with VPNs）

Docker Desktop 网络在连接到 VPN 时也能正常工作。

为此，Docker Desktop 会拦截来自容器的流量，并将其注入主机，就好像流量源自 Docker 应用程序一样。

有关此流量如何对主机防火墙和端点检测系统呈现的详细信息，请参阅[防火墙和端点可见性](/desktop/features/networking/#firewalls-and-endpoint-visibility)。

### 使用代理（Working with proxies）

Docker Desktop 可以使用系统代理或手动配置。要配置代理：

1. 导航到 **Settings** 中的 **Resources** 选项卡。
2. 从下拉菜单中选择 **Proxies**。
3. 打开 **Manual proxy configuration** 开关。
4. 输入您的 HTTP、HTTPS 或 SOCKS5 代理 URL。

有关代理和代理配置的更多详细信息，请参阅[代理设置文档](/desktop/settings-and-maintenance/settings/#proxies)。

## Mac 和 Windows 的网络操作指南（Network how-tos for Mac and Windows）

您可以控制 Docker 如何处理容器网络和 DNS 解析，以更好地支持各种环境——从仅 IPv4 到双栈（dual-stack）和仅 IPv6 的系统。这些设置有助于防止因不兼容或配置不当的主机网络导致的超时和连接问题。

您可以在 Docker Desktop Dashboard 设置的 **Network** 选项卡上设置以下选项，或者如果您是管理员，可以通过设置管理（Settings Management）使用 [`admin-settings.json` 文件](/enterprise/security/hardened-desktop/settings-management/configure-json-file/#networking)或[管理控制台（Admin Console）](/enterprise/security/hardened-desktop/settings-management/configure-admin-console/)进行设置。

> [!NOTE]
>
> 这些设置可以使用 CLI 标志或 Compose 文件选项按每个网络（per-network）进行覆盖。

### 默认网络模式（Default networking mode）

选择 Docker 创建新网络时使用的默认 IP 协议。这使您能够使 Docker 与主机的网络功能或组织要求（例如强制仅 IPv6 访问）保持一致。

| 模式                         | 描述                                 |
| ---------------------------- | ------------------------------------------- |
| **Dual IPv4/IPv6（默认）**   | 同时支持 IPv4 和 IPv6。最灵活。 |
| **IPv4 only**                | 仅使用 IPv4 寻址。                  |
| **IPv6 only**                | 仅使用 IPv6 寻址。                  |

### DNS 解析行为（DNS resolution behavior）

控制 Docker 如何过滤返回给容器的 DNS 记录，从而提高在仅支持 IPv4 或 IPv6 的环境中的可靠性。此设置对于防止应用程序尝试使用实际不可用的 IP 家族进行连接特别有用，否则可能导致可避免的延迟或故障。

| 选项                         | 描述                                                                 |
| ------------------------------ | --------------------------------------------------------------------------- |
| **Auto（推荐）**         | 自动过滤不支持的记录类型（A 记录对应 IPv4，AAAA 记录对应 IPv6）。 |
| **Filter IPv4 (A records)**    | 阻止 IPv4 查找。仅在双栈模式下可用。                     |
| **Filter IPv6 (AAAA records)** | 阻止 IPv6 查找。仅在双栈模式下可用。                     |
| **No filtering**               | 同时返回 A 记录和 AAAA 记录。                                            |

> [!IMPORTANT]
>
> 切换默认网络模式会将 DNS 过滤器重置为 Auto。

## Mac 和 Linux 的网络操作指南（Network how-tos for Mac and Linux）

### SSH agent 转发（SSH agent forwarding）

Docker Desktop for Mac 和 Linux 允许您在容器内使用主机的 SSH agent。操作方法如下：

1. 通过向 `docker run` 命令添加以下参数来绑定挂载 SSH agent socket：

   ```console
   $ --mount type=bind,src=/run/host-services/ssh-auth.sock,target=/run/host-services/ssh-auth.sock
   ```

2. 在容器中添加 `SSH_AUTH_SOCK` 环境变量：

    ```console
    $ -e SSH_AUTH_SOCK="/run/host-services/ssh-auth.sock"
    ```

要在 Docker Compose 中启用 SSH agent，请将以下标志添加到您的服务中：

```yaml
services:
  web:
    image: nginx:alpine
    volumes:
      - type: bind
        source: /run/host-services/ssh-auth.sock
        target: /run/host-services/ssh-auth.sock
    environment:
      - SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock
```

## 已知限制（Known limitations）

### 更改内部 IP 地址（Changing internal IP addresses）

Docker 使用的内部 IP 地址可以通过 **Settings** 更改。更改 IP 后，您需要重置 Kubernetes 集群并退出任何活动的 Swarm。

### 主机上没有 `docker0` 桥接（There is no `docker0` bridge on the host）

由于 Docker Desktop 中网络实现的方式，您无法在主机上看到 `docker0` 接口。该接口实际上位于虚拟机内部。

### 无法 ping 通我的容器（I cannot ping my containers）

Docker Desktop 无法将流量路由到 Linux 容器。但是，如果您是 Windows 用户，则可以 ping 通 Windows 容器。

### 无法实现每个容器单独的 IP 寻址（Per-container IP addressing is not possible）

这是因为 Docker 的 `bridge` 网络无法从主机访问。但如果您是 Windows 用户，对于 Windows 容器，每个容器单独的 IP 寻址是可能的。