# Bridge 网络驱动（Bridge network driver）

一个 Docker **bridge** 网络拥有一个 IPv4 子网，并且可选地拥有一个 IPv6 子网。连接到该 bridge 网络的每个容器都有一个带有网络子网地址的网络接口。默认情况下，它：

- 允许从主机以及从连接到同一 bridge 网络的其他容器对网络中的容器进行无限制的网络访问。
- 阻止来自其他网络中的容器以及 Docker 主机外部的访问。
- 使用伪装（masquerading）为容器提供外部网络访问。主机外部网络上的设备只能看到 Docker 主机的 IP 地址。
- 支持端口发布（port publishing），网络流量在容器端口和主机 IP 地址上的端口之间转发。已发布的端口可以从 Docker 主机外部、在其 IP 地址上进行访问。

就 Docker 而言，**bridge** 网络使用一个软件桥接器，允许连接到同一 bridge 网络的容器进行通信，同时提供与未连接到该 bridge 网络的容器的隔离。默认情况下，Docker bridge 驱动会自动在主机中安装规则，以便连接到不同 bridge 网络的容器只能使用已发布的端口相互通信。

Bridge 网络适用于运行在同一 Docker 守护进程主机上的容器。对于运行在不同 Docker 守护进程主机上的容器之间的通信，您可以在操作系统级别管理路由，或者使用 [**overlay** 网络](/engine/network/drivers/bridge/overlay/)。

当您启动 Docker 时，会自动创建一个[默认 bridge 网络](#use-the-default-bridge-network)（也称为 `bridge`），并且新启动的容器默认会连接到它，除非另有指定。您也可以创建用户定义的自定义 bridge 网络。**用户定义的 bridge 网络优于默认的 `bridge` 网络。**

## 用户定义 bridge 与默认 bridge 之间的区别

- **用户定义的 bridge 提供容器之间的自动 DNS 解析**。

  默认 bridge 网络上的容器只能通过 IP 地址相互访问，除非您使用 [`--link` 选项](/engine/network/links/)，该选项被视为遗留方式。在用户定义的 bridge 网络上，容器可以通过名称或别名相互解析。

  设想一个具有 Web 前端和数据库后端的应用程序。如果您将容器命名为 `web` 和 `db`，那么无论应用程序栈在哪个 Docker 主机上运行，web 容器都可以在 `db` 上连接到 db 容器。

  如果您在默认 bridge 网络上运行相同的应用程序栈，则需要手动在容器之间创建链接（使用遗留的 `--link` 标志）。这些链接需要双向创建，因此当有两个以上需要通信的容器时，这就会变得复杂。或者，您可以操作容器内的 `/etc/hosts` 文件，但这会产生难以调试的问题。

- **用户定义的 bridge 提供更好的隔离性**。

  所有未指定 `--network` 的容器都会附加到默认 bridge 网络。这可能带来风险，因为不相关的堆栈/服务/容器可以相互通信。

  使用用户定义的网络提供了一个有范围的网络，只有附加到该网络的容器才能进行通信。

- **容器可以动态地附加到用户定义的网络或从中分离**。

  在容器的生命周期内，您可以动态地将它连接到用户定义的网络或从中断开。要将容器从默认 bridge 网络中移除，您需要停止容器并使用不同的网络选项重新创建它。

- **每个用户定义的网络创建一个可配置的 bridge**。

  如果您的容器使用默认 bridge 网络，您可以配置它，但所有容器都使用相同的设置，例如 MTU 和 `iptables` 规则。此外，配置默认 bridge 网络是在 Docker 本身之外进行的，并且需要重启 Docker。

  用户定义的 bridge 网络是使用 `docker network create` 创建和配置的。如果不同的应用程序组有不同的网络需求，您可以在创建每个用户定义的 bridge 时单独配置它。

- **默认 bridge 网络上的链接容器共享环境变量**。

  最初，在两个容器之间共享环境变量的唯一方法是使用 [`--link` 标志](/engine/network/links/) 将它们链接起来。这种变量共享方式在用户定义的网络上是不可能的。但是，有更好的方法来共享环境变量。一些想法：
  - 多个容器可以使用 Docker 卷挂载一个包含共享信息的文件或目录。
  - 多个容器可以使用 `docker-compose` 一起启动，并且 compose 文件可以定义共享变量。
  - 您可以使用 Swarm 服务而不是独立容器，并利用共享的 [secrets](/engine/swarm/secrets/) 和 [configs](/engine/swarm/configs/)。

连接到同一用户定义 bridge 网络的容器有效地相互暴露所有端口。要使端口能够被不同网络上的容器或非 Docker 主机访问，必须使用 `-p` 或 `--publish` 标志 _发布（publish）_ 该端口。

## 选项

下表描述了在使用 `bridge` 驱动创建自定义网络时，可以传递给 `--opt` 的驱动特定选项。

| 选项                                                                                          | 默认值                      | 描述                                                                                         |
| ----------------------------------------------------------------------------------------------- | --------------------------- | --------------------------------------------------------------------------------------------------- |
| `com.docker.network.bridge.name`                                                                |                             | 创建 Linux bridge 时使用的接口名称。                                               |
| `com.docker.network.bridge.enable_ip_masquerade`                                                | `true`                      | 启用 IP 伪装。                                                                             |
| `com.docker.network.host_ipv4`<br/>`com.docker.network.host_ipv6`                               |                             | 用于源 NAT 的地址。请参阅[包过滤与防火墙](/engine/network/drivers/bridge/packet-filtering-firewalls/)。 |
| `com.docker.network.bridge.gateway_mode_ipv4`<br/>`com.docker.network.bridge.gateway_mode_ipv6` | `nat`                       | 控制外部连接。请参阅[包过滤与防火墙](/engine/network/drivers/bridge/packet-filtering-firewalls/)。 |
| `com.docker.network.bridge.enable_icc`                                                          | `true`                      | 启用或禁用容器间连接。                                                     |
| `com.docker.network.bridge.host_binding_ipv4`                                                   | 所有 IPv4 和 IPv6 地址 | 绑定容器端口时的默认 IP。                                                            |
| `com.docker.network.driver.mtu`                                                                 | `0`（无限制）              | 设置容器的网络最大传输单元（MTU）。                                         |
| `com.docker.network.container_iface_prefix`                                                     | `eth`                       | 为容器接口设置自定义前缀。                                                       |
| `com.docker.network.bridge.inhibit_ipv4`                                                        | `false`                     | 阻止 Docker [为 bridge 分配 IP 地址](#skip-bridge-ip-address-configuration)。 |

其中一些选项也可作为 `dockerd` CLI 的标志使用，您可以在启动 Docker 守护进程时使用它们来配置默认的 `docker0` bridge。下表显示了哪些选项在 `dockerd` CLI 中有等效的标志。

| 选项                                           | 标志        |
| ------------------------------------------------ | ----------- |
| `com.docker.network.bridge.name`                 | -           |
| `com.docker.network.bridge.enable_ip_masquerade` | `--ip-masq` |
| `com.docker.network.bridge.enable_icc`           | `--icc`     |
| `com.docker.network.bridge.host_binding_ipv4`    | `--ip`      |
| `com.docker.network.driver.mtu`                  | `--mtu`     |
| `com.docker.network.container_iface_prefix`      | -           |

Docker 守护进程支持 `--bridge` 标志，您可以使用它来定义自己的 `docker0` bridge。如果您想在同一主机上运行多个守护进程实例，请使用此选项。有关详细信息，请参阅[运行多个守护进程](/reference/cli/dockerd/#run-multiple-daemons)。

### 默认主机绑定地址

当在端口发布选项（如 `-p 80` 或 `-p 8080:80`）中未指定主机地址时，默认将容器的端口 80 在所有主机地址（IPv4 和 IPv6）上可用。

bridge 网络驱动选项 `com.docker.network.bridge.host_binding_ipv4` 可用于修改已发布端口的默认地址。

尽管选项名称如此，但可以指定 IPv6 地址。

当默认绑定地址是指定给特定接口的地址时，容器的端口只能通过该地址访问。

将默认绑定地址设置为 `::` 意味着已发布的端口将仅在主机的 IPv6 地址上可用。但是，将其设置为 `0.0.0.0` 意味着它将同时在主机的 IPv4 和 IPv6 地址上可用。

要将已发布的端口限制为仅 IPv4，必须在容器的发布选项中包含该地址。例如，`-p 0.0.0.0:8080:80`。

## 管理用户定义的 bridge

使用 `docker network create` 命令创建用户定义的 bridge 网络。

```console
$ docker network create my-net
```

您可以指定子网、IP 地址范围、网关和其他选项。有关详细信息，请参阅 [docker network create](/reference/cli/docker/network/create/#specify-advanced-options) 参考或 `docker network create --help` 的输出。

使用 `docker network rm` 命令删除用户定义的 bridge 网络。如果当前有容器连接到该网络，请先[断开它们](#disconnect-a-container-from-a-user-defined-bridge)。

```console
$ docker network rm my-net
```

> **实际发生了什么？**
>
> 当您创建或删除用户定义的 bridge，或者将容器连接到用户定义的 bridge 或从用户定义的 bridge 断开连接时，Docker 使用操作系统特定的工具来管理底层网络基础设施（例如，添加或删除 bridge 设备，或在 Linux 上配置 `iptables` 规则）。这些细节应视为实现细节。让 Docker 为您管理用户定义的网络。

## 将容器连接到用户定义的 bridge

当您创建一个新容器时，可以指定一个或多个 `--network` 标志。此示例将一个 Nginx 容器连接到 `my-net` 网络。它还将容器中的端口 80 发布到 Docker 主机上的端口 8080，以便外部客户端可以访问该端口。连接到 `my-net` 网络的任何其他容器都可以访问 `my-nginx` 容器上的所有端口，反之亦然。

```console
$ docker create --name my-nginx \
  --network my-net \
  --publish 8080:80 \
  nginx:latest
```

要将**正在运行的**容器连接到现有的用户定义 bridge，请使用 `docker network connect` 命令。以下命令将一个已经运行的 `my-nginx` 容器连接到一个已经存在的 `my-net` 网络：

```console
$ docker network connect my-net my-nginx
```

## 将容器从用户定义的 bridge 断开连接

要将正在运行的容器从用户定义的 bridge 断开连接，请使用 `docker network disconnect` 命令。以下命令将 `my-nginx` 容器从 `my-net` 网络断开。

```console
$ docker network disconnect my-net my-nginx
```

## 在用户定义的 bridge 网络中使用 IPv6

创建网络时，可以指定 `--ipv6` 标志以启用 IPv6。

```console
$ docker network create --ipv6 --subnet 2001:db8:1234::/64 my-net
```

如果您不提供 `--subnet` 选项，则会自动选择一个唯一本地地址（ULA）前缀。

## 仅 IPv6 的 bridge 网络

要跳过 bridge 及其容器中的 IPv4 地址配置，请使用选项 `--ipv4=false` 创建网络，并使用 `--ipv6` 启用 IPv6。

```console
$ docker network create --ipv6 --ipv4=false v6net
```

在默认 bridge 网络中无法禁用 IPv4 地址配置。

## 使用默认 bridge 网络

默认的 `bridge` 网络被视为 Docker 的遗留细节，不建议用于生产。配置它是手动操作，并且它存在[技术缺陷](#differences-between-user-defined-bridges-and-the-default-bridge)。

### 将容器连接到默认 bridge 网络

如果您没有使用 `--network` 标志指定网络，并且也没有指定网络驱动，您的容器默认会连接到默认的 `bridge` 网络。连接到默认 `bridge` 网络的容器可以通信，但只能通过 IP 地址，除非它们使用[遗留的 `--link` 标志](/engine/network/links/) 进行链接。

### 配置默认 bridge 网络

要配置默认的 `bridge` 网络，您需要在 `daemon.json` 中指定选项。以下是一个带有多个选项的 `daemon.json` 示例。仅指定您需要自定义的设置。

```json
{
  "bip": "192.168.1.1/24",
  "fixed-cidr": "192.168.1.0/25",
  "mtu": 1500,
  "default-gateway": "192.168.1.254",
  "dns": ["10.20.1.2", "10.20.1.3"]
}
```

在此示例中：

- bridge 的地址是 "192.168.1.1/24"（来自 `bip`）。
- bridge 网络的子网是 "192.168.1.0/24"（来自 `bip`）。
- 容器的地址将从 "192.168.1.0/25"（来自 `fixed-cidr`）中分配。

### 在默认 bridge 网络中使用 IPv6

可以使用 `daemon.json` 中的以下选项（或其命令行等效项）为默认 bridge 启用 IPv6。

这三个选项仅影响默认 bridge，用户定义的网络不使用它们。下面的地址是来自 IPv6 文档范围的示例。

- 选项 `ipv6` 是必需的。
- 选项 `bip6` 是可选的，它指定默认 bridge 的地址，该地址将用作容器的默认网关。它还指定了 bridge 网络的子网。
- 选项 `fixed-cidr-v6` 是可选的，它指定 Docker 可以自动分配给容器的地址范围。
  - 前缀通常应为 `/64` 或更短。
  - 在本地网络上进行实验时，使用唯一本地地址（ULA）前缀（匹配 `fd00::/8`）比使用链路本地前缀（匹配 `fe80::/10`）更好。
- 选项 `default-gateway-v6` 是可选的。如果未指定，默认为 `fixed-cidr-v6` 子网中的第一个地址。

```json
{
  "ipv6": true,
  "bip6": "2001:db8::1111/64",
  "fixed-cidr-v6": "2001:db8::/64",
  "default-gateway-v6": "2001:db8:abcd::89"
}
```

如果未指定 `bip6`，则 `fixed-cidr-v6` 定义 bridge 网络的子网。如果未指定 `bip6` 或 `fixed-cidr-v6`，则会选择一个 ULA 前缀。

重启 Docker 以使更改生效。

## Bridge 网络的连接限制

由于 Linux 内核的限制，当 1000 个或更多容器连接到一个网络时，bridge 网络会变得不稳定，并且容器间的通信可能会中断。

有关此限制的更多信息，请参阅 [moby/moby#44973](https://github.com/moby/moby/issues/44973#issuecomment-1543747718)。

## 跳过 Bridge IP 地址配置

bridge 通常被分配网络的 `--gateway` 地址，该地址用作从 bridge 网络到其他网络的默认路由。

选项 `com.docker.network.bridge.inhibit_ipv4` 允许您创建一个不为 bridge 分配 IPv4 网关地址的网络。如果您想手动配置 bridge 的网关 IP 地址，这很有用。例如，如果您将物理接口添加到 bridge，并且需要它拥有网关地址。

使用此配置，除非您已在 bridge 或其附加的设备上手动配置了网关地址，否则南北向流量（进出 bridge 网络）将无法工作。

此选项只能与用户定义的 bridge 网络一起使用。

## 使用示例

本节提供了使用 bridge 网络的动手实践示例。

### 使用默认 bridge 网络

此示例展示了默认 `bridge` 网络的工作原理。您在默认 bridge 上启动两个 `alpine` 容器，并测试它们如何通信。

> [!NOTE]
> 默认 `bridge` 网络不推荐用于生产。请改用用户定义的 bridge 网络。

1. 列出当前网络：

   ```console
   $ docker network ls

   NETWORK ID          NAME                DRIVER              SCOPE
   17e324f45964        bridge              bridge              local
   6ed54d316334        host                host                local
   7092879f2cc8        none                null                local
   ```

   列出了默认的 `bridge` 网络，以及 `host` 和 `none`。

2. 启动两个运行 `ash` 的 `alpine` 容器。`-dit` 标志表示后台运行、交互式并分配 TTY。由于您没有指定 `--network` 标志，容器将连接到默认的 `bridge` 网络。

   ```console
   $ docker run -dit --name alpine1 alpine ash
   $ docker run -dit --name alpine2 alpine ash
   ```

   验证两个容器都在运行：

   ```console
   $ docker container ls

   CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES
   602dbf1edc81        alpine              "ash"               4 seconds ago       Up 3 seconds                            alpine2
   da33b7aa74b0        alpine              "ash"               17 seconds ago      Up 16 seconds                           alpine1
   ```

3. 检查 `bridge` 网络以查看已连接的容器：

   ```console
   $ docker network inspect bridge
   ```

   输出显示两个容器都已连接，并显示了它们分配的 IP 地址（`alpine1` 为 `172.17.0.2`，`alpine2` 为 `172.17.0.3`）。

4. 连接到 `alpine1`：

   ```console
   $ docker attach alpine1

   / #
   ```

   从容器内部显示 `alpine1` 的网络接口：

   ```console
   # ip addr show

   1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN qlen 1
       link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
       inet 127.0.0.1/8 scope host lo
          valid_lft forever preferred_lft forever
       inet6 ::1/128 scope host
          valid_lft forever preferred_lft forever
   27: eth0@if28: <BROADCAST,MULTICAST,UP,LOWER_UP,M-DOWN> mtu 1500 qdisc noqueue state UP
       link/ether 02:42:ac:11:00:02 brd ff:ff:ff:ff:ff:ff
       inet 172.17.0.2/16 scope global eth0
          valid_lft forever preferred_lft forever
   ```

在此示例中，`eth0` 接口的 IP 地址为 `172.17.0.2`。

5. 从 `alpine1` 内部，验证您可以连接到互联网：

   ```console
   # ping -c 2 google.com

   PING google.com (172.217.3.174): 56 data bytes
   64 bytes from 172.217.3.174: seq=0 ttl=41 time=9.841 ms
   64 bytes from 172.217.3.174: seq=1 ttl=41 time=9.897 ms

   --- google.com ping statistics ---
   2 packets transmitted, 2 packets received, 0% packet loss
   round-trip min/avg/max = 9.841/9.869/9.897 ms
   ```

6. 通过 IP 地址 ping 第二个容器：

   ```console
   # ping -c 2 172.17.0.3

   PING 172.17.0.3 (172.17.0.3): 56 data bytes
   64 bytes from 172.17.0.3: seq=0 ttl=64 time=0.086 ms
   64 bytes from 172.17.0.3: seq=1 ttl=64 time=0.094 ms

   --- 172.17.0.3 ping statistics ---
   2 packets transmitted, 2 packets received, 0% packet loss
   round-trip min/avg/max = 0.086/0.090/0.094 ms
   ```

这成功了。现在尝试通过容器名称 ping：

   ```console
   # ping -c 2 alpine2

   ping: bad address 'alpine2'
   ```

   在默认 bridge 网络上，容器无法通过名称相互解析。

7. 使用 `CTRL+p CTRL+q` 从 `alpine1` 分离而不停止它。

8. 清理：停止容器并删除它们。

   ```console
   $ docker container stop alpine1 alpine2
   $ docker container rm alpine1 alpine2
   ```

   停止的容器会丢失其 IP 地址。

### 使用用户定义的 bridge 网络

此示例展示了用户定义的 bridge 网络如何在容器之间提供更好的隔离和自动 DNS 解析。

1. 创建 `alpine-net` 网络：

   ```console
   $ docker network create --driver bridge alpine-net
   ```

2. 列出 Docker 的网络：

   ```console
   $ docker network ls

   NETWORK ID          NAME                DRIVER              SCOPE
   e9261a8c9a19        alpine-net          bridge              local
   17e324f45964        bridge              bridge              local
   6ed54d316334        host                host                local
   7092879f2cc8        none                null                local
   ```

   检查 `alpine-net` 网络：

   ```console
   $ docker network inspect alpine-net
   ```

   这显示了网络的网关（例如 `172.18.0.1`），并且目前没有容器连接。

3. 创建四个容器。三个连接到 `alpine-net`，一个连接到默认的 `bridge`。然后将一个容器连接到两个网络：

   ```console
   $ docker run -dit --name alpine1 --network alpine-net alpine ash
   $ docker run -dit --name alpine2 --network alpine-net alpine ash
   $ docker run -dit --name alpine3 alpine ash
   $ docker run -dit --name alpine4 --network alpine-net alpine ash
   $ docker network connect bridge alpine4
   ```

   验证所有容器都在运行：

   ```console
   $ docker container ls

   CONTAINER ID        IMAGE               COMMAND             CREATED              STATUS              PORTS               NAMES
   156849ccd902        alpine              "ash"               41 seconds ago       Up 41 seconds                           alpine4
   fa1340b8d83e        alpine              "ash"               51 seconds ago       Up 51 seconds                           alpine3
   a535d969081e        alpine              "ash"               About a minute ago   Up About a minute                       alpine2
   0a02c449a6e9        alpine              "ash"               About a minute ago   Up About a minute                       alpine1
   ```

4. 再次检查两个网络以查看哪些容器已连接：

   ```console
   $ docker network inspect bridge
   ```

   容器 `alpine3` 和 `alpine4` 连接到 `bridge` 网络。

   ```console
   $ docker network inspect alpine-net
   ```

   容器 `alpine1`、`alpine2` 和 `alpine4` 连接到 `alpine-net`。

5. 在用户定义的网络上，容器可以通过名称相互解析。连接到 `alpine1` 并测试：

   > [!NOTE]
   > 自动服务发现仅解析自定义容器名称，而不解析默认自动生成的名称。

   ```console
   $ docker container attach alpine1

   # ping -c 2 alpine2

   PING alpine2 (172.18.0.3): 56 data bytes
   64 bytes from 172.18.0.3: seq=0 ttl=64 time=0.085 ms
   64 bytes from 172.18.0.3: seq=1 ttl=64 time=0.090 ms

   --- alpine2 ping statistics ---
   2 packets transmitted, 2 packets received, 0% packet loss
   round-trip min/avg/max = 0.085/0.087/0.090 ms

   # ping -c 2 alpine4

   PING alpine4 (172.18.0.4): 56 data bytes
   64 bytes from 172.18.0.4: seq=0 ttl=64 time=0.076 ms
   64 bytes from 172.18.0.4: seq=1 ttl=64 time=0.091 ms

   --- alpine4 ping statistics ---
   2 packets transmitted, 2 packets received, 0% packet loss
   round-trip min/avg/max = 0.076/0.083/0.091 ms
   ```

6. 从 `alpine1`，您无法连接到 `alpine3`，因为它位于不同的网络上：

   ```console
   # ping -c 2 alpine3

   ping: bad address 'alpine3'
   ```

   您也无法通过 IP 地址连接。如果 `alpine3` 的 IP 是 `172.17.0.2`：

   ```console
   # ping -c 2 172.17.0.2

   PING 172.17.0.2 (172.17.0.2): 56 data bytes

   --- 172.17.0.2 ping statistics ---
   2 packets transmitted, 0 packets received, 100% packet loss
   ```

   使用 `CTRL+p CTRL+q` 从 `alpine1` 分离。

7. 由于 `alpine4` 连接到两个网络，它可以到达所有容器。但是，您需要使用 `alpine3` 的 IP 地址：

   ```console
   $ docker container attach alpine4

   # ping -c 2 alpine1

   PING alpine1 (172.18.0.2): 56 data bytes
   64 bytes from 172.18.0.2: seq=0 ttl=64 time=0.074 ms
   64 bytes from 172.18.0.2: seq=1 ttl=64 time=0.082 ms

   --- alpine1 ping statistics ---
   2 packets transmitted, 2 packets received, 0% packet loss
   round-trip min/avg/max = 0.074/0.078/0.082 ms

   # ping -c 2 alpine2

   PING alpine2 (172.18.0.3): 56 data bytes
   64 bytes from 172.18.0.3: seq=0 ttl=64 time=0.075 ms
   64 bytes from 172.18.0.3: seq=1 ttl=64 time=0.080 ms

   --- alpine2 ping statistics ---
   2 packets transmitted, 2 packets received, 0% packet loss
   round-trip min/avg/max = 0.075/0.077/0.080 ms

   # ping -c 2 alpine3
   ping: bad address 'alpine3'

   # ping -c 2 172.17.0.2

   PING 172.17.0.2 (172.17.0.2): 56 data bytes
   64 bytes from 172.17.0.2: seq=0 ttl=64 time=0.089 ms
   64 bytes from 172.17.0.2: seq=1 ttl=64 time=0.075 ms

   --- 172.17.0.2 ping statistics ---
   2 packets transmitted, 2 packets received, 0% packet loss
   round-trip min/avg/max = 0.075/0.082/0.089 ms
   ```

8. 验证所有容器都可以连接到互联网：

   ```console
   # ping -c 2 google.com

   PING google.com (172.217.3.174): 56 data bytes
   64 bytes from 172.217.3.174: seq=0 ttl=41 time=9.778 ms
   64 bytes from 172.217.3.174: seq=1 ttl=41 time=9.634 ms

   --- google.com ping statistics ---
   2 packets transmitted, 2 packets received, 0% packet loss
   round-trip min/avg/max = 9.634/9.706/9.778 ms
   ```

   使用 `CTRL+p CTRL+q` 分离，如果需要，可以对 `alpine3` 和 `alpine1` 重复此操作。

9. 清理：

   ```console
   $ docker container stop alpine1 alpine2 alpine3 alpine4
   $ docker container rm alpine1 alpine2 alpine3 alpine4
   $ docker network rm alpine-net
   ```

## 下一步

- 了解[从容器角度的网络](/engine/drivers/)
- 了解 [overlay 网络](/engine/network/drivers/overlay/)
- 了解 [Macvlan 网络](/engine/network/drivers/macvlan/)