# 包过滤与防火墙（Packet filtering and firewalls）

在 Linux 上，Docker 会创建防火墙规则以实现网络隔离、[端口发布（port publishing）](/engine/network/port-publishing/) 和过滤。

由于这些规则对于 Docker **bridge networks** 的正常运行是必需的，您不应修改 Docker 创建的规则。

本页描述了控制 Docker 防火墙规则的选项，以实现包括端口发布和 NAT/伪装（masquerading）在内的功能。

> [!NOTE]
> 
> Docker 会为 **bridge networks** 创建防火墙规则。
> 
> 对于 `ipvlan`、`macvlan` 或 `host` 网络，不会创建规则。

## 防火墙后端（Firewall backend）

默认情况下，Docker Engine 使用 **iptables** 创建其防火墙规则，请参阅[使用 iptables 的 Docker](/engine/network/firewall-iptables/)。它也支持 **nftables**，请参阅[使用 nftables 的 Docker](/engine/network/firewall-nftables/)。

对于 **bridge networks**，**iptables** 和 **nftables** 具有相同的功能。

Docker Engine 选项 `firewall-backend` 可用于选择使用 **iptables** 还是 **nftables**。请参阅[守护进程配置（daemon configuration）](https://docs.docker.com/reference/cli/dockerd/)。

## 在路由器上运行 Docker

在 Linux 上，Docker 需要在主机上启用“IP 转发（IP Forwarding）”。因此，如果启动时尚未启用 `sysctl` 设置 `net.ipv4.ip_forward` 和 `net.ipv6.conf.all.forwarding`，Docker 会启用它们。当它这样做时，它还会配置防火墙丢弃转发的数据包，除非它们被明确接受。

当 Docker 将默认转发策略设置为“drop”时，它会阻止您的 Docker 主机充当路由器。当启用 IP 转发时，这是推荐的设置，除非需要路由器功能。

要阻止 Docker 将转发策略设置为“drop”，请在 `/etc/docker/daemon.json` 中包含 `"ip-forward-no-drop": true`，或向 `dockerd` 命令行添加选项 `--ip-forward-no-drop`。

> [!NOTE]
>
> 对于实验性的 **nftables** 后端，Docker 不会自行启用 IP 转发，也不会创建默认的“drop” nftables 策略。请参阅[从 iptables 迁移到 nftables](/engine/network/firewall-nftables/#migrating-from-iptables-to-nftables)。

## 阻止 Docker 操作防火墙规则

在[守护进程配置（daemon configuration）](https://docs.docker.com/reference/cli/dockerd/)中将 `iptables` 或 `ip6tables` 键设置为 `false`，将阻止 Docker 创建其大部分的 **iptables** 或 **nftables** 规则。但是，此选项对大多数用户并不合适，因为它很可能会破坏 Docker Engine 的容器网络。

例如，如果禁用了 Docker 的防火墙且没有替换规则，则 **bridge networks** 中的容器将无法通过伪装访问互联网主机，但它们的所有端口将对本地网络上的主机开放。

完全阻止 Docker 创建防火墙规则是不可能的，并且事后创建规则非常复杂，超出了这些说明的范围。

## 与 **firewalld** 集成

如果您在将 `iptables` 或 `ip6tables` 选项设置为 `true` 的情况下运行 Docker，并且您的系统上启用了 [**firewalld**](https://firewalld.org)，则除了其通常的 **iptables** 或 **nftables** 规则外，Docker 还会创建一个名为 `docker` 的 **firewalld** 区域（zone），其目标（target）为 `ACCEPT`。

Docker 创建的所有 **bridge** 网络接口（例如 `docker0`）都会被插入到 `docker` 区域中。

Docker 还会创建一个名为 `docker-forwarding` 的转发策略，允许从 `ANY` 区域转发到 `docker` 区域。

## Docker 与 **ufw**

[Uncomplicated Firewall (ufw)](https://launchpad.net/ufw) 是一个随 Debian 和 Ubuntu 一起提供的前端，它允许您管理防火墙规则。Docker 和 **ufw** 使用防火墙规则的方式使它们彼此不兼容。

当您使用 Docker 发布容器的端口时，进出该容器的流量会在经过 **ufw** 防火墙设置之前被分流。Docker 在 `nat` 表中路由容器流量，这意味着数据包在到达 **ufw** 使用的 `INPUT` 和 `OUTPUT` 链之前就被分流了。数据包在防火墙规则应用之前就被路由了，实际上会忽略您的防火墙配置。