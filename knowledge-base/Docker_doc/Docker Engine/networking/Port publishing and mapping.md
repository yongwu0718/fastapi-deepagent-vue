# 端口发布与映射（Port publishing and mapping）

默认情况下，对于 IPv4 和 IPv6，Docker 守护进程会阻止访问尚未发布（published）的端口。已发布的容器端口会被映射到主机的 IP 地址。为此，它使用防火墙规则来执行网络地址转换（NAT）、端口地址转换（PAT）和伪装（masquerading）。

例如，`docker run -p 8080:80 [...]` 会在 Docker 主机的任何地址上的端口 8080 与容器的端口 80 之间创建映射。来自容器的出站连接将使用 Docker 主机的 IP 地址进行伪装。

## 发布端口（Publishing ports）

当您使用 `docker create` 或 `docker run` 创建或运行容器时，**bridge** 网络上容器的所有端口都可以从 Docker 主机以及连接到同一网络的其他容器访问。但端口无法从主机外部访问，或者在默认配置下，无法从其他网络中的容器访问。

使用 `--publish` 或 `-p` 标志可以使端口在主机外部以及在其他 **bridge** 网络中的容器上可用。

这会在主机中创建一个防火墙规则，将容器端口映射到 Docker 主机上的端口，从而对外部世界开放。以下是一些示例：

| 标志值                          | 描述                                                                                                                                             |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `-p 8080:80`                    | 将 Docker 主机上的端口 `8080` 映射到容器中的 TCP 端口 `80`。                                                                                   |
| `-p 192.168.1.100:8080:80`      | 将 Docker 主机 IP `192.168.1.100` 上的端口 `8080` 映射到容器中的 TCP 端口 `80`。                                                                |
| `-p 8080:80/udp`                | 将 Docker 主机上的端口 `8080` 映射到容器中的 UDP 端口 `80`。                                                                                   |
| `-p 8080:80/tcp -p 8080:80/udp` | 将 Docker 主机上的 TCP 端口 `8080` 映射到容器中的 TCP 端口 `80`，并将 Docker 主机上的 UDP 端口 `8080` 映射到容器中的 UDP 端口 `80`。 |

> [!IMPORTANT]
>
> 默认情况下，发布容器端口是不安全的。这意味着，当您发布容器的端口时，它不仅对 Docker 主机可用，对外部世界也是可用的。
>
> 如果您在发布标志中包含 localhost IP 地址（`127.0.0.1` 或 `::1`），则只有 Docker 主机可以访问已发布的容器端口。
>
> ```console
> $ docker run -p 127.0.0.1:8080:80 -p '[::1]:8080:80' nginx
> ```
>
> > [!WARNING]
> >
> > 在低于 28.0.0 的版本中，同一 L2 网段内的主机（例如，连接到同一网络交换机的主机）可以访问发布到 localhost 的端口。更多信息请参阅 [moby/moby#45610](https://github.com/moby/moby/issues/45610)。

如果在端口映射中未指定主机 IP、bridge 网络仅为 IPv4 且 `--userland-proxy=true`（默认值），则主机 IPv6 地址上的端口将映射到容器的 IPv4 地址。

## 直接路由（Direct routing）

端口映射确保已发布的端口可以在主机的网络地址上被访问，这些地址很可能对于任何外部客户端都是可路由的。通常，在主机的网络中不会为容器地址设置路由。

但是，特别是在 IPv6 的情况下，您可能希望避免使用 NAT，而是安排外部路由到容器地址（“直接路由（direct routing）”）。

要从 Docker 主机外部访问 **bridge** 网络上的容器，您必须首先通过 Docker 主机上的一个地址设置到 bridge 网络的路由。这可以通过静态路由、边界网关协议（BGP）或任何适合您网络的其他方式来实现。例如，在本地二层网络中，远程主机可以通过 Docker 守护进程主机在本地网络上的地址设置到容器网络的静态路由。

### 直接路由到 **bridge** 网络中的容器

默认情况下，不允许远程主机直接访问 Docker Linux **bridge** 网络中容器的 IP 地址。它们只能访问已发布到主机 IP 地址的端口。

要允许直接访问任何 Linux **bridge** 网络中任何容器上的任何已发布端口，请在 `/etc/docker/daemon.json` 中使用守护进程选项 `"allow-direct-routing": true` 或等效的 `--allow-direct-routing`。

要允许从任何地方直接路由到特定 **bridge** 网络中的容器，请参阅[网关模式](#gateway-modes)。

或者，要允许通过特定主机接口直接路由到特定 **bridge** 网络，请在创建网络时使用以下选项：
- `com.docker.network.bridge.trusted_host_interfaces`

#### 示例

创建一个网络，允许从接口 `vxlan.1` 和 `eth3` 直接访问容器 IP 地址上已发布的端口：

```console
$ docker network create --subnet 192.0.2.0/24 --ip-range 192.0.2.0/29 -o com.docker.network.bridge.trusted_host_interfaces="vxlan.1:eth3" mynet
```

在该网络中运行一个容器，将其端口 80 发布到主机环回接口的端口 8080：

```console
$ docker run -d --ip 192.0.2.100 -p 127.0.0.1:8080:80 nginx
```

现在，可以从 Docker 主机通过 `http://127.0.0.1:8080` 访问容器端口 80 上运行的 Web 服务器，或者直接通过 `http://192.0.2.100:80` 访问。如果连接到接口 `vxlan.1` 和 `eth3` 的网络上的远程主机具有到 Docker 主机内部 `192.0.2.0/24` 网络的路由，它们也可以通过 `http://192.0.2.100:80` 访问 Web 服务器。

## 网关模式（Gateway modes）

**bridge** 网络驱动有以下选项：
- `com.docker.network.bridge.gateway_mode_ipv6`
- `com.docker.network.bridge.gateway_mode_ipv4`

每个选项都可以设置为以下网关模式之一：
- `nat`
- `nat-unprotected`
- `routed`
- `isolated`

默认值为 `nat`，会为每个已发布的容器端口设置 NAT 和伪装规则。离开主机的数据包将使用主机地址。

在 `routed` 模式下，不设置 NAT 或伪装规则，但仍会设置防火墙规则，以便只有已发布的容器端口可被访问。来自容器的出站数据包将使用容器的地址，而不是主机地址。

要访问 `routed` 网络中的已发布端口，远程主机必须具有通过 Docker 主机上的外部地址到容器网络的直接路由（direct routing）。本地二层网络上的主机可以在不需要任何额外网络配置的情况下设置直接路由。本地网络之外的主机只有配置了网络路由器以启用它时，才能使用直接路由到容器。

在 `nat` 模式网络中，将端口发布到环回接口上的地址意味着远程主机无法访问它。在 `routed` 和 `nat` 网络中，其他已发布的容器端口始终可以通过直接路由从远程主机访问，除非 Docker 主机的防火墙有额外限制。

> [!NOTE]
>
> 当端口在 `nat` 模式下发布到特定的主机地址时，如果在 Docker 主机上启用了 IP 转发，则可以通过使用直接路由到该主机地址的其他主机接口来访问已发布的端口。
>
> 例如，一个启用了 IP 转发的 Docker 主机有两个网卡，地址分别为 `192.168.100.10/24` 和 `10.0.0.10/24`。当端口发布到 `192.168.100.10` 时，`10.0.0.0/24` 子网中的主机可以通过 `10.0.0.10` 路由到 `192.168.100.10` 来访问该端口。

在 `nat-unprotected` 模式下，未发布的容器端口也可以通过直接路由访问，不设置端口过滤规则。包含此模式是为了兼容旧的默认行为。

网关模式还会影响连接到同一主机上不同 Docker 网络的容器之间的通信。
- 在 `nat` 和 `nat-unprotected` 模式下，其他 **bridge** 网络中的容器只能通过它们发布到的主机地址访问已发布的端口。不允许从其他网络直接路由。
- 在 `routed` 模式下，其他网络中的容器可以使用直接路由来访问端口，而无需经过主机地址。

在 `routed` 模式下，`-p` 或 `--publish` 端口映射中的主机端口不会被使用，主机地址仅用于决定将映射应用于 IPv4 还是 IPv6。因此，当映射仅适用于 `routed` 模式时，应仅使用地址 `0.0.0.0` 或 `::`，并且不应提供主机端口。如果提供了特定的地址或端口，它们将对已发布的端口没有影响，并且会记录警告消息。

`isolated` 模式只能在网络也使用 CLI 标志 `--internal` 或等效标志创建时使用。通常，在 `internal` 网络中，bridge 设备会被分配一个地址。因此，Docker 主机上的进程可以访问该网络，并且网络中的容器可以访问在该 bridge 地址上监听的主机服务（包括监听“任何”主机地址 `0.0.0.0` 或 `::` 的服务）。当使用网关模式 `isolated` 创建网络时，不会为 bridge 分配地址。

### 示例

创建一个适合 IPv6 直接路由的网络，同时为 IPv4 启用 NAT：
```console
$ docker network create --ipv6 --subnet 2001:db8::/64 -o com.docker.network.bridge.gateway_mode_ipv6=routed mynet
```

创建一个具有已发布端口的容器：
```console
$ docker run --network=mynet -p 8080:80 myimage
```

然后：
- 只有容器的 80 端口会开放（针对 IPv4 和 IPv6）。
- 对于 IPv6，使用 `routed` 模式，端口 80 将在容器的 IP 地址上开放。端口 8080 不会在主机的 IP 地址上开放，并且出站数据包将使用容器的 IP 地址。
- 对于 IPv4，使用默认的 `nat` 模式，容器的 80 端口可以通过主机 IP 地址上的 8080 端口访问，也可以从 Docker 主机内部直接访问。但是，无法从主机外部直接访问容器的 80 端口。从容器发起的连接将使用主机的 IP 地址进行伪装。

在 `docker inspect` 中，此端口映射将如下所示。请注意，IPv6 没有 `HostPort`，因为它使用的是 `routed` 模式：
```console
$ docker container inspect <id> --format "{{json .NetworkSettings.Ports}}"
{"80/tcp":[{"HostIp":"0.0.0.0","HostPort":"8080"},{"HostIp":"::","HostPort":""}]}
```

或者，要使映射仅适用于 IPv6，禁用对容器端口 80 的 IPv4 访问，请使用未指定的 IPv6 地址 `[::]` 并且不包含主机端口号：
```console
$ docker run --network mynet -p '[::]::80'
```

## 设置容器的默认绑定地址（Setting the default bind address for containers）

默认情况下，当容器的端口映射时未指定任何特定的主机地址，Docker 守护进程会将端口发布到所有主机地址（`0.0.0.0` 和 `[::]`）。

例如，以下命令将端口 8080 发布到主机上所有网络接口的 IPv4 和 IPv6 地址，可能会使其对外部世界可用。

```console
docker run -p 8080:80 nginx
```

您可以更改已发布容器端口的默认绑定地址，使其默认仅对 Docker 主机可访问。为此，您可以配置守护进程使用环回地址（`127.0.0.1`）。

> [!WARNING]
>
> 在低于 28.0.0 的版本中，同一 L2 网段内的主机（例如，连接到同一网络交换机的主机）可以访问发布到 localhost 的端口。更多信息请参阅 [moby/moby#45610](https://github.com/docker/desktop-feedback/issues/45610)。

要为用户定义的 **bridge** 网络配置此设置，请在创建网络时使用 `com.docker.network.bridge.host_binding_ipv4` [驱动选项](/engine/network/drivers/bridge/#default-host-binding-address)。尽管选项名称如此，但可以指定 IPv6 地址。

```console
$ docker network create mybridge \
  -o "com.docker.network.bridge.host_binding_ipv4=127.0.0.1"
```

或者，要为所有用户定义的 **bridge** 网络中的容器设置默认绑定地址，请使用守护进程配置选项 `default-network-opts`。例如：

```json
{
  "default-network-opts": {
    "bridge": {
      "com.docker.network.bridge.host_binding_ipv4": "127.0.0.1"
    }
  }
}
```

> [!NOTE]
>
> 将默认绑定地址设置为 `::` 意味着未指定主机地址的端口绑定将适用于主机上的任何 IPv6 地址。但是，`0.0.0.0` 表示任何 IPv4 或 IPv6 地址。
>
> 更改默认绑定地址对 Swarm 服务没有任何影响。Swarm 服务总是在 `0.0.0.0` 网络接口上公开。

### 出站数据包的伪装（Masquerade）或 SNAT

默认情况下，**bridge** 网络启用了 NAT，这意味着来自容器的出站数据包会被伪装。离开 Docker 主机的数据包的源地址会被更改为数据包所发送的主机接口上的地址。

可以通过在创建网络时使用 `com.docker.network.bridge.enable_ip_masquerade` 驱动选项来禁用用户定义 **bridge** 网络的伪装。例如：
```console
$ docker network create mybridge \
  -o com.docker.network.bridge.enable_ip_masquerade=false ...
```

要为用户定义网络中的出站数据包使用特定的源地址，而不是让伪装选择一个地址，请使用选项 `com.docker.network.host_ipv4` 和 `com.docker.network.host_ipv6` 来指定要使用的源 NAT (SNAT) 地址。要使这些选项生效，`com.docker.network.bridge.enable_ip_masquerade` 选项必须为 `true`（默认值）。

### 默认 bridge（Default bridge）

要为默认 **bridge** 网络设置默认绑定地址，请在 `daemon.json` 配置文件中配置 `"ip"` 键：

```json
{
  "ip": "127.0.0.1"
}
```

这将默认 bridge 网络上已发布容器端口的默认绑定地址更改为 `127.0.0.1`。重启守护进程以使此更改生效。或者，您可以在启动守护进程时使用 `dockerd --ip` 标志。