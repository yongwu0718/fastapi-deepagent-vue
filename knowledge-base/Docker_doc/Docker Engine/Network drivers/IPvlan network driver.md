# IPvlan 网络驱动（IPvlan network driver）

**IPvlan** 驱动让用户能够完全控制 IPv4 和 IPv6 的寻址。**VLAN** 驱动在此基础上构建，使运维人员能够完全控制二层 VLAN 标记，甚至为对底层网络集成感兴趣的用户提供 IPvlan L3 路由。对于抽象物理限制的 overlay 部署，请参阅[多主机 overlay](/engine/network/drivers/ipvlan/overlay/) 驱动。

**IPvlan** 是对久经考验的网络虚拟化技术的一种新变化。Linux 实现极其轻量，因为它们不使用传统的 Linux 桥接进行隔离，而是关联到一个 Linux 以太网接口或子接口，以实施网络间的隔离以及与物理网络的连接。

**IPvlan** 提供了许多独特的功能，并在各种模式下为进一步的创新留出了充足空间。这些方法的两个高层优势是：绕过 Linux 桥接带来的积极性能影响，以及减少活动部件带来的简单性。移除传统上位于 Docker 主机 NIC 和容器接口之间的桥接，留下了一个简单的设置：容器接口直接附加到 Docker 主机接口。对于面向外部的服务来说，这种结果易于访问，因为在这些场景下无需端口映射。

## 选项

下表描述了在使用 `ipvlan` 驱动创建网络时，可以传递给 `--opt` 的驱动特定选项。

| 选项           | 默认值   | 描述                                                           |
| -------------- | -------- | -------------------------------------------------------------- |
| `ipvlan_mode`  | `l2`     | 设置 IPvlan 操作模式。可以是：`l2`、`l3`、`l3s`                |
| `ipvlan_flag`  | `bridge` | 设置 IPvlan 模式标志。可以是：`bridge`、`private`、`vepa`      |
| `parent`       |          | 指定要使用的父接口。                                           |

## 示例

### 先决条件

- 本页的所有示例都是单主机的。
- 所有示例都可以在运行 Docker 的单个主机上执行。任何使用子接口（如 `eth0.10`）的示例都可以替换为 `eth0` 或 Docker 主机上任何其他有效的父接口。带点号 `.` 的子接口是动态创建的。`-o parent` 接口也可以在 `docker network create` 中完全省略，驱动将创建一个 `dummy` 接口，该接口将启用本地主机连接以执行示例。
- 内核要求：
  - IPvlan Linux 内核 v4.2+（对早期内核的支持存在但有问题）。要检查您当前的内核版本，请使用 `uname -r`

### IPvlan L2 模式使用示例

下图展示了 IPvlan `L2` 模式拓扑的示例。驱动通过 `-d driver_name` 选项指定。在本例中为 `-d ipvlan`。

![简单的 IPvlan L2 模式示例](/engine/network/drivers/ipvlan/images/ipvlan_l2_simple.png)

下一个示例中的父接口 `-o parent=eth0` 配置如下：

```console
$ ip addr show eth0
3: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    inet 192.168.1.250/24 brd 192.168.1.255 scope global eth0
```

使用主机接口的网络作为 `docker network create` 中的 `--subnet`。容器将附加到与主机接口相同的网络，该网络通过 `-o parent=` 选项设置。

创建 IPvlan 网络并运行一个附加到该网络的容器：

```console
# IPvlan（如果未指定，-o ipvlan_mode= 默认为 L2 模式）
$ docker network create -d ipvlan \
    --subnet=192.168.1.0/24 \
    --gateway=192.168.1.1 \
    -o ipvlan_mode=l2 \
    -o parent=eth0 db_net

# 在 db_net 网络上启动一个容器
$ docker run --net=db_net -it --rm alpine /bin/sh

# 注意：容器无法 ping 到底层主机接口，因为出于额外隔离的目的，Linux 有意过滤了它们。
```

IPvlan 的默认模式是 `l2`。如果未指定 `-o ipvlan_mode=`，将使用默认模式。类似地，如果 `--gateway` 留空，则网络上的第一个可用地址将被设置为网关。例如，如果在网络创建中提供的子网是 `--subnet=192.168.1.0/24`，那么容器收到的网关就是 `192.168.1.1`。

为了帮助理解此模式如何与其他主机交互，下图显示了两个 Docker 主机之间的同一二层网段，该网段适用于 IPvlan L2 模式。

![多个 IPvlan 主机](/engine/network/drivers/ipvlan/images/macvlan-bridge-ipvlan-l2.webp?w=700)

以下将创建与之前创建的 `db_net` 网络完全相同的网络，使用 `--gateway=192.168.1.1` 和 `-o ipvlan_mode=l2` 的驱动默认值。

```console
# IPvlan（如果未指定，-o ipvlan_mode= 默认为 L2 模式）
$ docker network create -d ipvlan \
    --subnet=192.168.1.0/24 \
    -o parent=eth0 db_net_ipv

# 以后台模式启动一个具有显式名称的容器
$ docker run --net=db_net_ipv --name=ipv1 -itd alpine /bin/sh

# 启动第二个容器并使用容器名称 ping，以查看 Docker 包含的名称解析功能
$ docker run --net=db_net_ipv --name=ipv2 -it --rm alpine /bin/sh
$ ping -c 4 ipv1

# 注意：容器无法 ping 到底层主机接口，因为出于额外隔离的目的，Linux 有意过滤了它们。
```

这些驱动也支持 `--internal` 标志，该标志将完全隔离网络上的容器与该网络外部的任何通信。由于网络隔离与网络的父接口紧密耦合，在 `docker network create` 中省略 `-o parent=` 选项的结果与 `--internal` 选项完全相同。如果未指定父接口或使用了 `--internal` 标志，则会为用户创建一个 netlink 类型的 `dummy` 父接口，并将其用作父接口，从而完全隔离网络。

以下两个 `docker network create` 示例产生了相同的网络，您可以将容器附加到这些网络上：

```console
# 空的 '-o parent=' 创建一个隔离的网络
$ docker network create -d ipvlan \
    --subnet=192.168.10.0/24 isolated1

# 显式的 '--internal' 标志是相同的：
$ docker network create -d ipvlan \
    --subnet=192.168.11.0/24 --internal isolated2

# 即使 '--subnet=' 可以留空，并且默认的 IPAM 子网 172.18.0.0/16 将被分配
$ docker network create -d ipvlan isolated3

$ docker run --net=isolated1 --name=cid1 -it --rm alpine /bin/sh
$ docker run --net=isolated2 --name=cid2 -it --rm alpine /bin/sh
$ docker run --net=isolated3 --name=cid3 -it --rm alpine /bin/sh

# 要附加到任何容器，请使用 `docker exec` 并启动一个 shell
$ docker exec -it cid1 /bin/sh
$ docker exec -it cid2 /bin/sh
$ docker exec -it cid3 /bin/sh
```

### IPvlan 802.1Q 中继 L2 模式使用示例

在架构上，IPvlan L2 模式中继在网关和 L2 路径隔离方面与 Macvlan 相同。存在一些细微差别，可能对 ToR 交换机中的 CAM 表压力（每个端口一个 MAC 地址）、主机父 NIC 上的 MAC 耗尽等有利。802.1Q 中继场景看起来相同。两种模式都遵循标记标准，并与物理网络无缝集成，用于底层集成和硬件供应商插件集成。

同一 VLAN 上的主机通常位于同一子网，并且几乎总是根据其安全策略分组在一起。在大多数场景中，多层应用程序被划分到不同的子网，因为每个进程的安全配置文件都需要某种形式的隔离。例如，将您的信用卡处理托管在与前端 Web 服务器相同的虚拟网络上将违反法规遵从性，并且也违背了分层防御深度架构的长期最佳实践。VLAN 或在 Overlay 驱动中使用等价的 VNI（虚拟网络标识符）是隔离租户流量的第一步。

![深入的 Docker VLAN](/engine/network/drivers/ipvlan/images/vlans-deeper-look.webp)

用 VLAN 标记的 Linux 子接口可以已经存在，也可以在您调用 `docker network create` 时创建。`docker network rm` 将删除该子接口。父接口（如 `eth0`）不会被删除，只有 netlink 父索引 > 0 的子接口会被删除。

为了让驱动添加/删除 VLAN 子接口，格式需要是 `interface_name.vlan_tag`。可以使用其他子接口命名作为指定的父接口，但当调用 `docker network rm` 时，该链路不会被自动删除。

使用现有父 VLAN 子接口或让 Docker 管理它们的选择，使用户既可以完全管理 Linux 接口和网络，也可以让 Docker 无需用户费力地创建和删除 VLAN 父子接口（netlink `ip link`）。

例如：使用 `eth0.10` 表示用 VLAN id `10` 标记的 `eth0` 子接口。等效的 `ip link` 命令将是 `ip link add link eth0 name eth0.10 type vlan id 10`。

该示例创建 VLAN 标记的网络，然后启动两个容器以测试容器之间的连通性。不同的 VLAN 无法相互 ping 通，除非有路由器在两个网络之间进行路由。根据 IPvlan 的设计，默认命名空间是不可达的，目的是将容器命名空间与底层主机隔离。

#### VLAN ID 20

在由 Docker 主机标记和隔离的第一个网络中，`eth0.20` 是用 VLAN id `20` 标记的父接口，通过 `-o parent=eth0.20` 指定。可以使用其他命名格式，但需要使用 `ip link` 或 Linux 配置文件手动添加和删除链路。只要 `-o parent` 存在，只要符合 Linux netlink 规范，任何内容都可以使用。

```console
# 现在像往常一样通过附加到已标记的主（子）接口来添加网络和主机
$ docker network create -d ipvlan \
    --subnet=192.168.20.0/24 \
    --gateway=192.168.20.1 \
    -o parent=eth0.20 ipvlan20

# 在两个单独的终端中，启动一个 Docker 容器，现在容器可以相互 ping 通。
$ docker run --net=ipvlan20 -it --name ivlan_test1 --rm alpine /bin/sh
$ docker run --net=ipvlan20 -it --name ivlan_test2 --rm alpine /bin/sh
```

#### VLAN ID 30

在由 Docker 主机标记和隔离的第二个网络中，`eth0.30` 是用 VLAN id `30` 标记的父接口，通过 `-o parent=eth0.30` 指定。`ipvlan_mode=` 默认为 l2 模式 `ipvlan_mode=l2`。也可以显式设置，结果相同，如下一个示例所示。

```console
# 现在像往常一样通过附加到已标记的主（子）接口来添加网络和主机。
$ docker network create -d ipvlan \
    --subnet=192.168.30.0/24 \
    --gateway=192.168.30.1 \
    -o parent=eth0.30 \
    -o ipvlan_mode=l2 ipvlan30

# 在两个单独的终端中，启动一个 Docker 容器，现在容器可以相互 ping 通。
$ docker run --net=ipvlan30 -it --name ivlan_test3 --rm alpine /bin/sh
$ docker run --net=ipvlan30 -it --name ivlan_test4 --rm alpine /bin/sh
```

网关在容器内部被设置为默认网关。该网关通常是网络上的外部路由器。

```console
$$ ip route
  default via 192.168.30.1 dev eth0
  192.168.30.0/24 dev eth0  src 192.168.30.2
```

示例：多子网 IPvlan L2 模式，在同一子网上启动两个容器并相互 ping 通。为了使 `192.168.114.0/24` 能够到达 `192.168.116.0/24`，在 L2 模式下需要一个外部路由器。L3 模式可以在共享相同 `-o parent=` 的子网之间进行路由。

随着地址空间的耗尽，网络路由器上的辅助地址很常见，可以为 L3 VLAN 接口（通常称为“交换虚拟接口”（SVI））添加另一个辅助地址。

```console
$ docker network create -d ipvlan \
    --subnet=192.168.114.0/24 --subnet=192.168.116.0/24 \
    --gateway=192.168.114.254 --gateway=192.168.116.254 \
    -o parent=eth0.114 \
    -o ipvlan_mode=l2 ipvlan114

$ docker run --net=ipvlan114 --ip=192.168.114.10 -it --rm alpine /bin/sh
$ docker run --net=ipvlan114 --ip=192.168.114.11 -it --rm alpine /bin/sh
```

一个关键要点是，运维人员能够将他们的物理网络映射到虚拟网络中，以便将容器集成到他们的环境中，而无需进行运营大修。NetOps 将 802.1Q 中继接入 Docker 主机。该虚拟链路将是网络创建中传递的 `-o parent=`。对于未标记（非 VLAN）链路，就像 `-o parent=eth0` 一样简单；对于 802.1Q 中继，每个具有 VLAN ID 的网络都会映射到网络中的相应 VLAN/子网。

一个例子是：NetOps 提供 VLAN ID 以及通过以太网链路传递到 Docker 主机服务器的 VLAN 相关联的子网。这些值在配置 Docker 网络时被填入 `docker network create` 命令。这些是每次 Docker 引擎启动时都会应用的持久配置，从而减轻了管理通常复杂的配置文件的需求。也可以通过预先创建网络接口来手动管理，Docker 网络将永远不会修改它们，并将它们用作父接口。从 NetOps 到 Docker 网络命令的示例映射如下：

- VLAN：10，子网：172.16.80.0/24，网关：172.16.80.1
  - `--subnet=172.16.80.0/24 --gateway=172.16.80.1 -o parent=eth0.10`
- VLAN：20，IP 子网：172.16.50.0/22，网关：172.16.50.1
  - `--subnet=172.16.50.0/22 --gateway=172.16.50.1 -o parent=eth0.20`
- VLAN：30，子网：10.1.100.0/16，网关：10.1.100.1
  - `--subnet=10.1.100.0/16 --gateway=10.1.100.1 -o parent=eth0.30`

### IPvlan L3 模式示例

IPvlan 需要将路由分发到每个端点。该驱动仅构建 IPvlan L3 模式端口并将容器附加到接口。整个集群中的路由分发超出了这个单主机范围驱动的初始实现范围。在 L3 模式下，Docker 主机非常类似于在容器中启动新网络的路由器。如果没有路由分发，上游网络将不知道这些网络。对于那些好奇 IPvlan L3 将如何适应容器网络的人，请参阅以下示例。

![Docker IPvlan L2 模式](/engine/network/drivers/ipvlan/images/ipvlan-l3.webp?w=500)

IPvlan L3 模式会丢弃所有广播和多播流量。仅凭这个原因，就使 IPvlan L3 模式成为那些寻求大规模和可预测网络集成的人的主要候选方案。它是可预测的，因此将带来更高的正常运行时间，因为不涉及桥接。桥接环路一直是造成严重中断的原因，根据故障域的大小，可能难以确定问题所在。这是由于 BPDU（桥接协议数据单元）的级联性质，它们在广播域（VLAN）中泛滥以查找和阻止拓扑环路。消除桥接域，或者至少将它们隔离到一对 ToR（机架顶部交换机）将减少难以排查的桥接不稳定性。IPvlan L2 模式非常适合仅中继到一对 ToR 的隔离 VLAN，这些 ToR 可以提供无环路、无阻塞的结构。下一步是通过 IPvlan L3 模式在边缘进行路由，将故障域缩小到仅本地主机。

- L3 模式需要位于与默认命名空间不同的子网上，因为它需要在默认命名空间中有一个指向 IPvlan 父接口的 netlink 路由。
- 本示例中使用的父接口是 `eth0`，它位于子网 `192.168.1.0/24` 上。请注意 `docker network` 与 `eth0` 不在同一子网上。
- 与 IPvlan l2 模式不同，只要它们共享相同的父接口 `-o parent=`，不同子网/网络就可以相互 ping 通。

```console
$$ ip a show eth0
3: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether 00:50:56:39:45:2e brd ff:ff:ff:ff:ff:ff
    inet 192.168.1.250/24 brd 192.168.1.255 scope global eth0
```

- 对于 L3 模式的 IPvlan 接口，传统网关意义不大，因为不允许广播流量。因此，容器的默认网关指向容器的 `eth0` 设备。有关详细信息，请参阅下面来自 L3 容器内部的 `ip route` 或 `ip -6 route` 的 CLI 输出。

必须显式指定模式 `-o ipvlan_mode=l3`，因为默认的 IPvlan 模式是 `l2`。

以下示例未指定父接口。网络驱动将为用户创建一个 dummy 类型的链路，而不是拒绝网络创建，并将容器隔离，使它们只能相互通信。

```console
# 创建 IPvlan L3 网络
$ docker network create -d ipvlan \
    --subnet=192.168.214.0/24 \
    --subnet=10.1.214.0/24 \
    -o ipvlan_mode=l3 ipnet210

# 测试 192.168.214.0/24 的连通性
$ docker run --net=ipnet210 --ip=192.168.214.10 -itd alpine /bin/sh
$ docker run --net=ipnet210 --ip=10.1.214.10 -itd alpine /bin/sh

# 测试从 10.1.214.0/24 到 192.168.214.0/24 的 L3 连通性
$ docker run --net=ipnet210 --ip=192.168.214.9 -it --rm alpine ping -c 2 10.1.214.10

# 测试从 192.168.214.0/24 到 10.1.214.0/24 的 L3 连通性
$ docker run --net=ipnet210 --ip=10.1.214.9 -it --rm alpine ping -c 2 192.168.214.10
```

> [!NOTE]
>
> 请注意，在网络创建中没有 `--gateway=` 选项。如果在 `l3` 模式下指定了该字段，它将被忽略。查看容器内部的容器路由表：
>
> ```console
> # 在 L3 模式容器内部
> $$ ip route
>  default dev eth0
>   192.168.214.0/24 dev eth0  src 192.168.214.10
> ```

为了能够从远程 Docker 主机 ping 容器，或者容器能够 ping 远程主机，远程主机或中间的物理网络需要有一条指向容器 Docker 主机 eth 接口的主机 IP 地址的路由。

### 双栈 IPv4 IPv6 IPvlan L2 模式

- Libnetwork 不仅让您完全控制 IPv4 寻址，还让您完全控制 IPv6 寻址，并在两个地址族之间实现功能对等。

- 下一个示例将从仅 IPv6 开始。在同一 VLAN `139` 上启动两个容器并相互 ping 通。由于未指定 IPv4 子网，默认 IPAM 将提供一个默认的 IPv4 子网。除非上游网络在 VLAN `139` 上明确路由它，否则该子网是隔离的。

```console
# 创建一个 v6 网络
$ docker network create -d ipvlan \
    --ipv6 --subnet=2001:db8:abc2::/64 --gateway=2001:db8:abc2::22 \
    -o parent=eth0.139 v6ipvlan139

# 在网络中启动一个容器
$ docker run --net=v6ipvlan139 -it --rm alpine /bin/sh
```

查看容器 eth0 接口和 v6 路由表：

```console
# 在 IPv6 容器内部
$$ ip a show eth0
75: eth0@if55: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default
    link/ether 00:50:56:2b:29:40 brd ff:ff:ff:ff:ff:ff
    inet 172.18.0.2/16 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 2001:db8:abc4::250:56ff:fe2b:2940/64 scope link
       valid_lft forever preferred_lft forever
    inet6 2001:db8:abc2::1/64 scope link nodad
       valid_lft forever preferred_lft forever

$$ ip -6 route
2001:db8:abc4::/64 dev eth0  proto kernel  metric 256
2001:db8:abc2::/64 dev eth0  proto kernel  metric 256
default via 2001:db8:abc2::22 dev eth0  metric 1024
```

启动第二个容器并 ping 第一个容器的 v6 地址。

```console
# 通过 IPv6 测试 L2 连通性
$ docker run --net=v6ipvlan139 -it --rm alpine /bin/sh

# 在第二个 IPv6 容器内部
$$ ip a show eth0
75: eth0@if55: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default
    link/ether 00:50:56:2b:29:40 brd ff:ff:ff:ff:ff:ff
    inet 172.18.0.3/16 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 2001:db8:abc4::250:56ff:fe2b:2940/64 scope link tentative dadfailed
       valid_lft forever preferred_lft forever
    inet6 2001:db8:abc2::2/64 scope link nodad
       valid_lft forever preferred_lft forever

$$ ping6 2001:db8:abc2::1
PING 2001:db8:abc2::1 (2001:db8:abc2::1): 56 data bytes
64 bytes from 2001:db8:abc2::1%eth0: icmp_seq=0 ttl=64 time=0.044 ms
64 bytes from 2001:db8:abc2::1%eth0: icmp_seq=1 ttl=64 time=0.058 ms

2 packets transmitted, 2 packets received, 0% packet loss
round-trip min/avg/max/stddev = 0.044/0.051/0.058/0.000 ms
```

下一个示例将设置一个双栈 IPv4/IPv6 网络，使用示例 VLAN ID `140`。

接下来创建一个包含两个 IPv4 子网和一个 IPv6 子网的网络，所有这些子网都有显式的网关：

```console
$ docker network create -d ipvlan \
    --subnet=192.168.140.0/24 --subnet=192.168.142.0/24 \
    --gateway=192.168.140.1 --gateway=192.168.142.1 \
    --subnet=2001:db8:abc9::/64 --gateway=2001:db8:abc9::22 \
    -o parent=eth0.140 \
    -o ipvlan_mode=l2 ipvlan140
```

启动一个容器并查看 eth0 以及 v4 和 v6 路由表：

```console
$ docker run --net=ipvlan140 --ip6=2001:db8:abc2::51 -it --rm alpine /bin/sh

$ ip a show eth0
78: eth0@if77: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default
    link/ether 00:50:56:2b:29:40 brd ff:ff:ff:ff:ff:ff
    inet 192.168.140.2/24 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 2001:db8:abc4::250:56ff:fe2b:2940/64 scope link
       valid_lft forever preferred_lft forever
    inet6 2001:db8:abc9::1/64 scope link nodad
       valid_lft forever preferred_lft forever

$$ ip route
default via 192.168.140.1 dev eth0
192.168.140.0/24 dev eth0  proto kernel  scope link  src 192.168.140.2

$$ ip -6 route
2001:db8:abc4::/64 dev eth0  proto kernel  metric 256
2001:db8:abc9::/64 dev eth0  proto kernel  metric 256
default via 2001:db8:abc9::22 dev eth0  metric 1024
```

启动第二个容器，指定一个 `--ip4` 地址，并使用 IPv4 数据包 ping 第一个主机：

```console
$ docker run --net=ipvlan140 --ip=192.168.140.10 -it --rm alpine /bin/sh
```

> [!NOTE]
>
> 在 IPvlan `L2` 模式下，同一父接口上的不同子网无法相互 ping 通。这需要一个路由器使用辅助子网对请求进行代理 ARP。但是，只要它们共享相同的 `-o parent` 父链路，IPvlan `L3` 模式就会在不同子网之间路由单播流量。

### 双栈 IPv4 IPv6 IPvlan L3 模式

示例：IPvlan L3 模式双栈 IPv4/IPv6，多子网 w/ 802.1Q VLAN 标记：118

与所有示例中一样，不一定必须使用标记的 VLAN 接口。子接口可以替换为 `eth0`、`eth1`、`bond0` 或主机上除 `lo` 环回之外的任何其他有效接口。

您将看到的主要区别是，L3 模式不会创建具有下一跳的默认路由，而是设置一个仅指向 `dev eth` 的默认路由，因为根据设计，ARP/广播/多播都被 Linux 过滤了。由于父接口本质上充当路由器，因此父接口 IP 和子网需要与容器网络不同。这与 bridge 和 L2 模式相反，后者需要位于同一子网（广播域）上才能转发广播和多播数据包。

```console
# 创建一个 IPv6+IPv4 双栈 IPvlan L3 网络
# v4 和 v6 的网关都设置为 dev，例如 'default dev eth0'
$ docker network create -d ipvlan \
    --subnet=192.168.110.0/24 \
    --subnet=192.168.112.0/24 \
    --ipv6 --subnet=2001:db8:abc6::/64 \
    -o parent=eth0 \
    -o ipvlan_mode=l3 ipnet110

# 在网络上（ipnet110）启动几个容器
# 在不同的终端中并检查连通性
$ docker run --net=ipnet110 -it --rm alpine /bin/sh
# 启动第二个容器，指定 v6 地址
$ docker run --net=ipnet110 --ip6=2001:db8:abc6::10 -it --rm alpine /bin/sh
# 启动第三个容器，指定 IPv4 地址
$ docker run --net=ipnet110 --ip=192.168.112.30 -it --rm alpine /bin/sh
# 启动第四个容器，同时指定 IPv4 和 IPv6 地址
$ docker run --net=ipnet110 --ip6=2001:db8:abc6::50 --ip=192.168.112.50 -it --rm alpine /bin/sh
```

接口和路由表输出如下：

```console
$$ ip a show eth0
63: eth0@if59: <BROADCAST,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default
    link/ether 00:50:56:2b:29:40 brd ff:ff:ff:ff:ff:ff
    inet 192.168.112.2/24 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 2001:db8:abc4::250:56ff:fe2b:2940/64 scope link
       valid_lft forever preferred_lft forever
    inet6 2001:db8:abc6::10/64 scope link nodad
       valid_lft forever preferred_lft forever

# 注意默认路由是 eth 设备，因为 ARP 被过滤了。
$$ ip route
  default dev eth0  scope link
  192.168.112.0/24 dev eth0  proto kernel  scope link  src 192.168.112.2

$$ ip -6 route
2001:db8:abc4::/64 dev eth0  proto kernel  metric 256
2001:db8:abc6::/64 dev eth0  proto kernel  metric 256
default dev eth0  metric 1024
```

> [!NOTE]
>
> 当指定 `--ip6=` 地址时可能存在一个错误：当您删除一个指定了 v6 地址的容器，然后启动一个具有相同 v6 地址的新容器时，它会抛出类似“地址未正确释放回 v6 池”的错误。它将无法卸载容器并保持死亡状态。

```console
docker: Error response from daemon: Address already in use.
```

### 手动创建 802.1Q 链路

#### VLAN ID 40

如果用户不希望驱动创建 VLAN 子接口，则需要在运行 `docker network create` 之前存在该子接口。只要接口存在并已启动，即使子接口命名不是 `interface.vlan_id`，它也会在 `-o parent=` 选项中被接受。

手动创建的链路在创建网络时可以任意命名，只要它们存在即可。当使用 `docker network rm` 删除网络时，无论名称如何，手动创建的链路都不会被删除。

```console
# 创建一个绑定到 dot1q vlan 40 的新子接口
$ ip link add link eth0 name eth0.40 type vlan id 40

# 启用新的子接口
$ ip link set eth0.40 up

# 现在像往常一样通过附加到已标记的主（子）接口来添加网络和主机
$ docker network create -d ipvlan \
    --subnet=192.168.40.0/24 \
    --gateway=192.168.40.1 \
    -o parent=eth0.40 ipvlan40

# 在两个单独的终端中，启动一个 Docker 容器，现在容器可以相互 ping 通。
$ docker run --net=ipvlan40 -it --name ivlan_test5 --rm alpine /bin/sh
$ docker run --net=ipvlan40 -it --name ivlan_test6 --rm alpine /bin/sh
```

示例：手动创建任意名称的 VLAN 子接口：

```console
# 创建一个绑定到 dot1q vlan 40 的新子接口
$ ip link add link eth0 name foo type vlan id 40

# 启用新的子接口
$ ip link set foo up

# 现在像往常一样通过附加到已标记的主（子）接口来添加网络和主机
$ docker network create -d ipvlan \
    --subnet=192.168.40.0/24 --gateway=192.168.40.1 \
    -o parent=foo ipvlan40

# 在两个单独的终端中，启动一个 Docker 容器，现在容器可以相互 ping 通。
$ docker run --net=ipvlan40 -it --name ivlan_test5 --rm alpine /bin/sh
$ docker run --net=ipvlan40 -it --name ivlan_test6 --rm alpine /bin/sh
```

手动创建的链路可以通过以下方式清理：

```console
$ ip link del foo
```

与所有 Libnetwork 驱动一样，它们可以混合搭配，甚至可以并行运行第三方生态系统驱动，以便为 Docker 用户提供最大的灵活性。