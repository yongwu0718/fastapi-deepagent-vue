# Macvlan 网络驱动（Macvlan network driver）

某些应用程序，特别是遗留应用程序或监控网络流量的应用程序，期望直接连接到物理网络。在这种情况下，您可以使用 `macvlan` 网络驱动为每个容器的虚拟网络接口分配一个 MAC 地址，使其看起来像是直接连接到物理网络的物理网络接口。此时，您需要指定 Docker 主机上的一个物理接口用于 Macvlan，以及网络的子网和网关。您甚至可以使用不同的物理网络接口来隔离您的 Macvlan 网络。

## 平台支持与要求

- `macvlan` 驱动仅在 Linux 主机上工作。在 Docker Desktop for Mac 或 Windows 上，或 Windows 上的 Docker Engine 上不受支持。
- 大多数云提供商阻止 `macvlan` 网络。您可能需要物理访问您的网络设备。
- 至少需要 Linux 内核版本 3.9（建议使用 4.0 或更高版本）。
- `macvlan` 驱动在 rootless 模式下不受支持。

## 注意事项

- 由于 IP 地址耗尽或“VLAN 传播”（当网络中存在过多唯一 MAC 地址时发生的情况），您可能会无意中降低网络性能。

- 您的网络设备需要能够处理“混杂模式”（promiscuous mode），即一个物理接口可以分配多个 MAC 地址。

- 如果您的应用程序可以使用桥接（在单个 Docker 主机上）或 overlay（跨多个 Docker 主机通信）工作，从长远来看，这些解决方案可能更好。

- 附加到 `macvlan` 网络的容器无法直接与主机通信，这是 Linux 内核的一个限制。如果您需要主机和容器之间的通信，可以将容器同时连接到 bridge 网络和 `macvlan` 网络。也可以在主机上使用相同的父接口创建一个 `macvlan` 接口，并在 Docker 网络的子网中为其分配一个 IP 地址。

## 选项

下表描述了在使用 `macvlan` 驱动创建网络时，可以传递给 `--opt` 的驱动特定选项。

| 选项           | 默认值   | 描述                                                           |
| -------------- | -------- | -------------------------------------------------------------- |
| `macvlan_mode` | `bridge` | 设置 Macvlan 模式。可以是：`bridge`、`vepa`、`passthru`、`private` |
| `parent`       |          | 指定要使用的父接口。                                           |

## 创建 Macvlan 网络

当您创建一个 Macvlan 网络时，它可以是桥接模式或 802.1Q 中继桥接模式。

- 在桥接模式下，Macvlan 流量通过主机上的物理设备传输。

- 在 802.1Q 中继桥接模式下，流量通过 Docker 动态创建的 802.1Q 子接口传输。这允许您以更细粒度控制路由和过滤。

### 桥接模式

要创建一个与给定物理网络接口桥接的 `macvlan` 网络，请在 `docker network create` 命令中使用 `--driver macvlan`。您还需要指定 `parent`，即流量在 Docker 主机上实际通过的接口。

```console
$ docker network create -d macvlan \
  --subnet=172.16.86.0/24 \
  --gateway=172.16.86.1 \
  -o parent=eth0 pub_net
```

如果您需要排除某些 IP 地址在 `macvlan` 网络中使用（例如当某个 IP 地址已被使用时），请使用 `--aux-addresses`：

```console
$ docker network create -d macvlan \
  --subnet=192.168.32.0/24 \
  --ip-range=192.168.32.128/25 \
  --gateway=192.168.32.254 \
  --aux-address="my-router=192.168.32.129" \
  -o parent=eth0 macnet32
```

### 802.1Q 中继桥接模式

如果您指定的 `parent` 接口名称包含点号（例如 `eth0.50`），Docker 会将其解释为 `eth0` 的子接口，并自动创建该子接口。

```console
$ docker network create -d macvlan \
    --subnet=192.168.50.0/24 \
    --gateway=192.168.50.1 \
    -o parent=eth0.50 macvlan50
```

### 使用 IPvlan 替代 Macvlan

使用选项 `-o ipvlan_mode=l2` 创建的 `ipvlan` 网络类似于 `macvlan` 网络。主要区别在于 `ipvlan` 驱动不会为每个容器分配 MAC 地址，而是让 ipvlan 网络中的设备共享二层网络栈。因此，容器使用父接口的 MAC 地址。

网络将看到更少的 MAC 地址，并且主机的 MAC 地址将与每个容器的 IP 地址关联。

选择网络类型取决于您的环境和需求。关于权衡的一些说明请参阅 [Linux 内核文档](https://docs.kernel.org/networking/ipvlan.html#what-to-choose-macvlan-vs-ipvlan)。

```console
$ docker network create -d ipvlan \
    --subnet=192.168.210.0/24 \
    --gateway=192.168.210.254 \
     -o ipvlan_mode=l2 -o parent=eth0 ipvlan210
```

## 使用 IPv6

如果您已[配置 Docker 守护进程启用 IPv6](/engine/daemon/ipv6/)，则可以使用双栈 IPv4/IPv6 `macvlan` 网络。

```console
$ docker network create -d macvlan \
    --subnet=192.168.216.0/24 --subnet=192.168.218.0/24 \
    --gateway=192.168.216.1 --gateway=192.168.218.1 \
    --subnet=2001:db8:abc8::/64 --gateway=2001:db8:abc8::10 \
     -o parent=eth0.218 \
     -o macvlan_mode=bridge macvlan216
```

## 使用示例

本节提供了使用 `macvlan` 网络的动手实践示例，包括桥接模式和 802.1Q 中继桥接模式。

> [!NOTE]
> 这些示例假设您的以太网接口是 `eth0`。如果您的设备名称不同，请使用相应的名称。

### 桥接模式示例

在桥接模式下，您的流量通过 `eth0` 传输，Docker 使用容器的 MAC 地址将流量路由到容器。对于网络上的网络设备而言，您的容器看起来像是物理连接到网络。

1. 创建一个名为 `my-macvlan-net` 的 `macvlan` 网络。修改 `subnet`、`gateway` 和 `parent` 值以匹配您的环境：

   ```console
   $ docker network create -d macvlan \
     --subnet=172.16.86.0/24 \
     --gateway=172.16.86.1 \
     -o parent=eth0 \
     my-macvlan-net
   ```

   验证网络已创建：

   ```console
   $ docker network ls
   $ docker network inspect my-macvlan-net
   ```

2. 启动一个 `alpine` 容器并将其附加到 `my-macvlan-net` 网络。`-dit` 标志在后台启动容器。`--rm` 标志在容器停止时将其移除：

   ```console
   $ docker run --rm -dit \
     --network my-macvlan-net \
     --name my-macvlan-alpine \
     alpine:latest \
     ash
   ```

3. 检查容器，注意 `Networks` 部分中的 `MacAddress` 键：

   ```console
   $ docker container inspect my-macvlan-alpine
   ```

   查找类似以下的输出：

   ```json
   "Networks": {
     "my-macvlan-net": {
       "Gateway": "172.16.86.1",
       "IPAddress": "172.16.86.2",
       "IPPrefixLen": 24,
       "MacAddress": "02:42:ac:10:56:02",
       ...
     }
   }
   ```

4. 检查容器如何看待自己的网络接口：

   ```console
   $ docker exec my-macvlan-alpine ip addr show eth0

   9: eth0@tunl0: <BROADCAST,MULTICAST,UP,LOWER_UP,M-DOWN> mtu 1500 qdisc noqueue state UP
   link/ether 02:42:ac:10:56:02 brd ff:ff:ff:ff:ff:ff
   inet 172.16.86.2/24 brd 172.16.86.255 scope global eth0
      valid_lft forever preferred_lft forever
   ```

   检查路由表：

   ```console
   $ docker exec my-macvlan-alpine ip route

   default via 172.16.86.1 dev eth0
   172.16.86.0/24 dev eth0 scope link  src 172.16.86.2
   ```

5. 停止容器（Docker 会自动移除它）并删除网络：

   ```console
   $ docker container stop my-macvlan-alpine
   $ docker network rm my-macvlan-net
   ```

### 802.1Q 中继桥接模式示例

在 802.1Q 中继桥接模式下，您的流量通过 `eth0` 的子接口（称为 `eth0.10`）传输，Docker 使用容器的 MAC 地址将流量路由到容器。对于网络上的网络设备而言，您的容器看起来像是物理连接到网络。

1. 创建一个名为 `my-8021q-macvlan-net` 的 `macvlan` 网络。修改 `subnet`、`gateway` 和 `parent` 值以匹配您的环境：

   ```console
   $ docker network create -d macvlan \
     --subnet=172.16.86.0/24 \
     --gateway=172.16.86.1 \
     -o parent=eth0.10 \
     my-8021q-macvlan-net
   ```

   验证网络已创建并且父接口为 `eth0.10`。您可以在 Docker 主机上使用 `ip addr show` 验证接口 `eth0.10` 是否存在：

   ```console
   $ docker network ls
   $ docker network inspect my-8021q-macvlan-net
   ```

2. 启动一个 `alpine` 容器并将其附加到 `my-8021q-macvlan-net` 网络：

   ```console
   $ docker run --rm -itd \
     --network my-8021q-macvlan-net \
     --name my-second-macvlan-alpine \
     alpine:latest \
     ash
   ```

3. 检查容器，注意 `MacAddress` 键：

   ```console
   $ docker container inspect my-second-macvlan-alpine
   ```

   查找包含 MAC 地址的 `Networks` 部分。

4. 检查容器如何看待自己的网络接口：

   ```console
   $ docker exec my-second-macvlan-alpine ip addr show eth0

   11: eth0@if10: <BROADCAST,MULTICAST,UP,LOWER_UP,M-DOWN> mtu 1500 qdisc noqueue state UP
   link/ether 02:42:ac:10:56:02 brd ff:ff:ff:ff:ff:ff
   inet 172.16.86.2/24 brd 172.16.86.255 scope global eth0
      valid_lft forever preferred_lft forever
   ```

   检查路由表：

   ```console
   $ docker exec my-second-macvlan-alpine ip route

   default via 172.16.86.1 dev eth0
   172.16.86.0/24 dev eth0 scope link  src 172.16.86.2
   ```

5. 停止容器并删除网络：

   ```console
   $ docker container stop my-second-macvlan-alpine
   $ docker network rm my-8021q-macvlan-net
   ```
   