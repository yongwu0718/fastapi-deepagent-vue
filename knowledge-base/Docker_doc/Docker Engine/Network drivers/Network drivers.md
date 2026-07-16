# 网络驱动（Network drivers）

Docker 的网络子系统是可插拔的，通过驱动（drivers）实现。默认情况下存在几种驱动，并提供核心网络功能：

- `bridge`：默认网络驱动。如果您不指定驱动，这就是您正在创建的网络类型。当您的应用程序在容器中运行，且需要与同一主机上的其他容器通信时，通常使用 **bridge** 网络。
  请参阅 [Bridge 网络驱动](/engine/network/drivers/bridge/)。

- `host`：消除容器与 Docker 主机之间的网络隔离，直接使用主机的网络。
  请参阅 [Host 网络驱动](/engine/network/drivers/host/)。

- `overlay`：**Overlay** 网络将多个 Docker 守护进程连接在一起，并允许 Swarm 服务和容器跨节点通信。此策略消除了进行操作系统级别路由的需求。
  请参阅 [Overlay 网络驱动](/engine/network/drivers/overlay/)。

- `ipvlan`：**IPvlan** 网络让用户完全控制 IPv4 和 IPv6 寻址。VLAN 驱动在此基础上构建，使操作员能够完全控制二层 VLAN 标记，甚至为对底层网络集成感兴趣的用户提供 IPvlan L3 路由。
  请参阅 [IPvlan 网络驱动](/engine/network/drivers/ipvlan/)。

- `macvlan`：**Macvlan** 网络允许您为容器分配一个 MAC 地址，使其看起来像是网络上的一个物理设备。Docker 守护进程通过 MAC 地址将流量路由到容器。当处理期望直接连接到物理网络（而不是通过 Docker 主机的网络栈路由）的遗留应用程序时，使用 `macvlan` 驱动有时是最佳选择。
  请参阅 [Macvlan 网络驱动](/engine/network/drivers/macvlan/)。

- `none`：将容器与主机和其他容器完全隔离。`none` 不适用于 Swarm 服务。
  请参阅 [None 网络驱动](/engine/network/drivers/none/)。

- [网络插件（Network plugins）](/engine/extend/plugins_network/)：您可以安装和使用第三方网络插件与 Docker 配合使用。

### 网络驱动摘要

- 默认的 **bridge** 网络适合运行不需要特殊网络功能的容器。
- 用户定义的 **bridge** 网络使同一 Docker 主机上的容器能够相互通信。用户定义的网络通常为属于同一项目或组件的多个容器定义一个隔离网络。
- **Host** 网络将主机的网络与容器共享。使用此驱动时，容器的网络与主机没有隔离。
- 当您需要运行在不同 Docker 主机上的容器进行通信，或者多个应用程序使用 Swarm 服务协同工作时，**Overlay** 网络是最佳选择。
- 当您从虚拟机设置迁移，或者需要您的容器看起来像网络上的物理主机（每个都有唯一的 MAC 地址）时，**Macvlan** 网络是最佳选择。
- **IPvlan** 类似于 Macvlan，但不为容器分配唯一的 MAC 地址。当网络接口或端口可分配的 MAC 地址数量受限时，请考虑使用 **IPvlan**。
- 第三方网络插件允许您将 Docker 与专用网络堆栈集成。

## 下一步（Next steps）

每个驱动页面都包含详细的解释、配置选项和动手实践的使用示例，以帮助您有效地使用该驱动。