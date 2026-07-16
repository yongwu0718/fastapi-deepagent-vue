# 使用 nftables 的 Docker

> [!WARNING]
>
> Docker 29.0.0 中引入的对 nftables 的支持是实验性的，配置选项、行为和实现都可能在未来版本中发生变化。
> overlay 网络的规则尚未从 iptables 迁移过来。因此，当 Docker 守护进程以 Swarm 模式运行时，无法启用 nftables。

要使用 nftables 替代 iptables，可以在 Docker Engine 命令行中使用选项 `--firewall-backend=nftables`，或者在配置文件中使用 `"firewall-backend": "nftables"`。您可能还需要修改主机上的 IP 转发配置，并将规则从 iptables 的 `DOCKER-USER` 链迁移过来，请参阅[从 iptables 迁移到 nftables](#migrating-from-iptables-to-nftables)。

对于 **bridge** 网络，Docker 会在主机的网络命名空间中创建 nftables 规则。对于 bridge 和其他网络类型，DNS 的 nftables 规则也会在容器的网络命名空间中创建。

可以使用守护进程选项 `iptables` 和 `ip6tables` 来禁用 nftables 规则的创建。*这些选项同时适用于 iptables 和 nftables。* 请参阅[阻止 Docker 操纵防火墙规则](/engine/network/firewall-nftables/packet-filtering-firewalls/#prevent-docker-from-manipulating-firewall-rules)。然而，对于大多数用户来说，不建议这样做，因为它很可能会破坏容器网络。

## Docker 的 nftables 表

对于 **bridge** 网络，Docker 会创建两个表：`ip docker-bridges` 和 `ip6 docker-bridges`。

每个表包含多个[基链](https://wiki.nftables.org/wiki-nftables/index.php/Configuring_chains#Adding_base_chains)，并为每个 bridge 网络添加更多链。moby 项目有一些[内部文档](https://github.com/moby/moby/blob/master/integration/network/bridge/nftablesdoc.md)描述了其 nftables 规则，以及它们如何依赖于网络和容器配置。然而，这些表及其规则可能会在 Docker Engine 版本之间发生变化。

> [!NOTE]
>
> 不要直接修改 Docker 的表，因为这些修改很可能会丢失，Docker 期望完全拥有其表的所有权。

> [!NOTE]
>
> 由于 iptables 具有一组固定的链（相当于 nftables 的基链），所有规则都包含在这些链中。`DOCKER-USER` 链作为一种将规则插入到 `filter` 表的 `FORWARD` 链中、并在 Docker 规则之前运行的方式提供。
> 在 Docker 的 nftables 实现中，没有 `DOCKER-USER` 链。相反，可以在单独的表（tables）中添加规则，这些表具有与 Docker 基链相同类型（types）和钩子点（hook points）的基链。如有必要，可以使用[基链优先级](https://wiki.nftables.org/wiki-nftables/index.php/Configuring_chains#Base_chain_priority)来告诉 nftables 调用链的顺序。
> Docker 为其每个基链使用众所周知的[优先级值](https://wiki.nftables.org/wiki-nftables/index.php/Netfilter_hooks#Priority_within_hook)。

## 从 iptables 迁移到 nftables

如果 Docker 守护进程一直以 iptables 防火墙后端运行，则使用 nftables 后端重启它将删除大多数 Docker 的 iptables 链和规则，并转而创建 nftables 规则。

如果未启用 IP 转发，Docker 在创建需要它的 bridge 网络时会报告错误。由于默认 bridge 的存在，如果 IPv4 转发被禁用，该错误将在守护进程启动期间报告。请参阅 [IP 转发](#ip-forwarding)。

如果您在 `DOCKER-USER` 链中有规则，请参阅[迁移 `DOCKER-USER`](#migrating-docker-user)。

如果 iptables `FORWARD` 策略已被 Docker 通过 iptables 设置或作为主机防火墙配置的一部分设置为 `DROP`，您可能需要手动更新该策略。请参阅 [iptables 中的 FORWARD 策略](#forward-policy-in-iptables)。

### IP 转发

Docker 主机上的 IP 转发启用了 Docker 的多种功能，包括端口发布、bridge 网络之间的通信，以及从主机外部直接路由到 bridge 网络中的容器。

当使用 iptables 运行时，根据网络和守护进程的配置，Docker 可能会在主机上启用 IPv4 和 IPv6 转发。

当启用其 nftables 防火墙后端时，Docker 本身不会启用 IP 转发。如果需要转发但尚未启用，它将报告错误。要禁用 Docker 对 IP 转发的检查，使其在确定转发被禁用时仍然启动并创建网络，请使用守护进程选项 `--ip-forward=false`，或在配置文件中使用 `"ip-forward": false`。

> [!WARNING]
>
> 启用 IP 转发时，请确保拥有防火墙规则来阻止非 Docker 接口之间不必要的转发。

> [!NOTE]
>
> 如果您停止 Docker 以迁移到 nftables，Docker 可能已经在您的系统上启用了 IP 转发。重启后，如果没有其他服务重新启用转发，Docker 将无法启动。

如果 Docker 位于具有单个网络接口且没有其他软件运行的虚拟机中，则可能没有需要阻止的不必要转发。但是，在具有多个网络接口的物理主机上，除非主机充当路由器，否则可能应使用 nftables 规则阻止这些接口之间的转发。

要在主机上启用 IP 转发，请设置以下 sysctl 参数：

- `net.ipv4.ip_forward=1`
- `net.ipv6.conf.all.forwarding=1`

如果您的主机使用 `systemd`，则可以使用 `systemd-sysctl`。例如，通过编辑 `/etc/sysctl.d/99-sysctl.conf`。

如果主机运行 `firewalld`，则可以使用它来阻止不必要的转发。Docker 的 bridge 位于名为 `docker` 的 firewalld 区域中，它会创建一个名为 `docker-forwarding` 的转发策略，该策略接受从 `ANY` 区域到 `docker` 区域的转发。

例如，要使用 nftables 阻止接口 `eth0` 和 `eth1` 之间的转发，可以使用：

```console
table inet no-ext-forwarding {
	chain no-ext-forwarding {
		type filter hook forward priority filter; policy accept;
		iifname "eth0" oifname "eth1" drop
		iifname "eth1" oifname "eth0" drop
	}
}
```

### iptables 中的 FORWARD 策略

具有 `FORWARD` 策略 `DROP` 的 iptables 链将丢弃已被 Docker 的 nftables 规则接受的包，因为该包将同时被 iptables 链和 Docker 的 nftables 链处理。

除非移除 `DROP` 策略，或向 iptables `FORWARD` 链添加额外的 iptables 规则以接受与 Docker 相关的流量，否则某些功能（包括端口发布）将无法工作。

当 Docker 使用 iptables 并在主机上启用 IP 转发时，它会将 iptables `FORWARD` 链的默认策略设置为 `DROP`。因此，如果您停止 Docker 以迁移到 nftables，它可能已设置了一个您需要移除的 `DROP` 策略。该策略在重启后也会被移除。

为了继续使用 `DOCKER-USER` 中依赖于该链具有 `DROP` 策略的规则，您必须为与 Docker 相关的流量添加显式的 `ACCEPT` 规则。

要检查当前的 iptables `FORWARD` 策略，请使用：

```console
$ iptables -L FORWARD
Chain FORWARD (policy DROP)
target     prot opt source               destination
$ ip6tables -L FORWARD
Chain FORWARD (policy ACCEPT)
target     prot opt source               destination
```

要将 IPv4 和 IPv6 的 iptables 策略设置为 `ACCEPT`：

```console
$ iptables -P FORWARD ACCEPT
$ ip6tables -P FORWARD ACCEPT
```

### 迁移 `DOCKER-USER`

对于防火墙后端 "iptables"，添加到 iptables `DOCKER-USER` 的规则会在 `filter` 表的 `FORWARD` 链中、Docker 规则之前被处理。

当在使用 iptables 后以 nftables 启动守护进程时，Docker 不会移除从 `FORWARD` 链到 `DOCKER-USER` 的跳转。因此，在 `DOCKER-USER` 中创建的规则将继续运行，直到该跳转被移除或主机被重启。

当以 nftables 启动时，守护进程不会添加该跳转。因此，除非已存在跳转，否则 `DOCKER-USER` 中的规则将被忽略。

#### 迁移 `ACCEPT` 规则

`DOCKER-USER` 链中的某些规则将继续工作。例如，如果一个包被丢弃，它会在 Docker 的 `filter-FORWARD` 链中的 nftables 规则之前或之后被丢弃。但其他规则，特别是覆盖 Docker 的 `DROP` 规则的 `ACCEPT` 规则，将无法工作。

在 nftables 中，"accept" 规则不是终局的。它会终止其基链的处理，但被接受的包仍将被其他基链处理，而其他基链可能会丢弃它。

要覆盖 Docker 的 `drop` 规则，您必须使用防火墙标记（firewall mark）。选择一个主机上尚未使用的标记，并使用 Docker Engine 选项 `--bridge-accept-fwmark`。

例如，`--bridge-accept-fwmark=1` 告诉守护进程接受任何 `fwmark` 值为 `1` 的包。您可以选择提供一个掩码来匹配标记中的特定位：`--bridge-accept-fwmark=0x1/0x3`。

然后，不要在 `DOCKER-USER` 中接受该包，而是添加您选择的防火墙标记，Docker 就不会丢弃它。

防火墙标记必须在 Docker 的规则运行之前添加。因此，如果标记是在类型为 `filter`、钩子为 `forward` 的链中添加的，则其优先级必须为 `filter - 1` 或更低。

#### 使用 nftables 表替换 `DOCKER-USER`

由于 nftables 没有预定义的链，要替换 `DOCKER-USER` 链，您可以创建自己的表（table），并向其中添加链和规则。

`DOCKER-USER` 链的类型为 `filter`，钩子为 `forward`，因此它只能包含过滤 forward 链中的规则。您表（table）中的基链可以具有任何 `type` 或 `hook`。如果您的规则需要在 Docker 的规则之前运行，请为基链设置一个比 Docker 链更低的 `priority` 数字。或者，设置更高的优先级以确保它们在 Docker 的规则之后运行。

Docker 的基链使用 [priority values](https://wiki.nftables.org/wiki-nftables/index.php/Netfilter_hooks#Priority_within_hook) 中定义的优先级值。

#### 示例：限制对容器的外部连接

默认情况下，任何远程主机都可以连接到发布到 Docker 主机外部地址的端口。

为了只允许特定的 IP 或网络访问容器，请创建一个带有具有丢弃规则（drop rule）的基链的表（table）。例如，以下表丢弃除 `192.0.2.2` 之外的所有 IP 地址的包：

```console
table ip my-table {
	chain my-filter-forward {
		type filter hook forward priority filter; policy accept;
		iifname "ext_if" ip saddr != 192.0.2.2 counter drop
	}
}
```

您需要将 `ext_if` 更改为主机的外部接口名称。

您也可以接受来自源子网的连接。以下表仅接受来自子网 `192.0.2.0/24` 的访问：

```console
table ip my-table {
	chain my-filter-forward {
		type filter hook forward priority filter; policy accept;
		iifname "ext_if" ip saddr != 192.0.2.0/24 counter drop
	}
}
```

如果您在主机上运行其他使用 IP 转发且需要被不同外部主机访问的服务，则需要更具体的过滤器。例如，要匹配属于 Docker 用户定义 bridge 网络的 bridge 设备的默认前缀 `br-`：

```console
table ip my-table {
	chain my-filter-forward {
		type filter hook forward priority filter; policy accept;
		iifname "ext_if" oifname "br-*" ip saddr != 192.0.2.0/24 counter drop
	}
}
```

有关 nftables 配置和高级用法的更多信息，请参阅 [nftables 维基](https://wiki.nftables.org/wiki-nftables/index.php/Main_Page)。
