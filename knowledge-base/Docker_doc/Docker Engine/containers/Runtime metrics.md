# 运行时指标（Runtime metrics）

## Docker stats

您可以使用 `docker stats` 命令实时流式查看容器的运行时指标。该命令支持 CPU、内存使用量、内存限制以及网络 IO 指标。

以下是 `docker stats` 命令的示例输出：

```console
$ docker stats redis1 redis2

CONTAINER           CPU %               MEM USAGE / LIMIT     MEM %               NET I/O             BLOCK I/O
redis1              0.07%               796 KB / 64 MB        1.21%               788 B / 648 B       3.568 MB / 512 KB
redis2              0.07%               2.746 MB / 64 MB      4.29%               1.266 KB / 648 B    12.4 MB / 0 B
```

[`docker stats`](/reference/cli/docker/container/stats/) 参考页面提供了关于 `docker stats` 命令的更多详细信息。

## 控制组（Control groups）

Linux 容器依赖于[控制组（control groups）](https://www.kernel.org/doc/Documentation/cgroup-v1/cgroups.txt)，它不仅跟踪进程组，还公开有关 CPU、内存和块 I/O 使用情况的指标。您可以访问这些指标并获取网络使用指标。这适用于“纯”LXC 容器以及 Docker 容器。

控制组通过伪文件系统暴露。在现代发行版中，您应该在 `/sys/fs/cgroup` 下找到此文件系统。在该目录下，您会看到多个子目录，称为 `devices`、`freezer`、`blkio` 等。每个子目录实际上对应一个不同的 cgroup 层级。

在较旧的系统上，控制组可能挂载在 `/cgroup` 下，没有独立的层级。在这种情况下，您不会看到子目录，而是会看到该目录中的一堆文件，以及可能一些对应现有容器的目录。

要确定控制组的挂载位置，可以运行：

```console
$ grep cgroup /proc/mounts
```

### 枚举 cgroup（Enumerate cgroups）

cgroup v1 和 v2 的文件布局有显著差异。

如果您的系统上存在 `/sys/fs/cgroup/cgroup.controllers`，则您使用的是 v2，否则使用的是 v1。请参阅与您的 cgroup 版本相对应的子章节。

cgroup v2 在以下发行版中默认使用：

- Fedora（自 31 起）
- Debian GNU/Linux（自 11 起）
- Ubuntu（自 21.10 起）

#### cgroup v1

您可以查看 `/proc/cgroups` 以了解系统已知的不同控制组子系统、它们所属的层级以及它们包含的组数。

您还可以查看 `/proc/<pid>/cgroup` 以查看进程属于哪些控制组。控制组显示为相对于层级挂载点根目录的路径。`/` 表示进程尚未分配给任何组，而 `/lxc/pumpkin` 表示该进程是名为 `pumpkin` 的容器的成员。

#### cgroup v2

在 cgroup v2 主机上，`/proc/cgroups` 的内容没有意义。请查看 `/sys/fs/cgroup/cgroup.controllers` 以了解可用的控制器。

### 更改 cgroup 版本（Changing cgroup version）

更改 cgroup 版本需要重新启动整个系统。

在基于 systemd 的系统上，可以通过向内核命令行添加 `systemd.unified_cgroup_hierarchy=1` 来启用 cgroup v2。要将 cgroup 版本恢复为 v1，需要改为设置 `systemd.unified_cgroup_hierarchy=0`。

如果您的系统上 `grubby` 命令可用（例如在 Fedora 上），可以如下修改命令行：

```console
$ sudo grubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=1"
```

如果 `grubby` 命令不可用，请编辑 `/etc/default/grub` 中的 `GRUB_CMDLINE_LINUX` 行，然后运行 `sudo update-grub`。

### 在 cgroup v2 上运行 Docker（Running Docker on cgroup v2）

自 Docker 20.10 起，Docker 支持 cgroup v2。在 cgroup v2 上运行 Docker 还需要满足以下条件：

- containerd：v1.4 或更高版本
- runc：v1.0.0-rc91 或更高版本
- 内核：v4.15 或更高版本（建议 v5.2 或更高）

请注意，cgroup v2 模式的行为与 cgroup v1 模式略有不同：

- 默认的 cgroup 驱动（`dockerd --exec-opt native.cgroupdriver`）在 v2 上是 `systemd`，在 v1 上是 `cgroupfs`。
- 默认的 cgroup 命名空间模式（`docker run --cgroupns`）在 v2 上是 `private`，在 v1 上是 `host`。
- `docker run` 标志 `--oom-kill-disable` 在 v2 上被丢弃。

### 查找给定容器的 cgroup（Find the cgroup for a given container）

对于每个容器，在每个层级中会创建一个 cgroup。在使用旧版本 LXC 用户态工具的旧系统上，cgroup 的名称就是容器的名称。对于较新版本的 LXC 工具，cgroup 名称为 `lxc/<container_name>`。

对于使用 cgroup 的 Docker 容器，cgroup 名称是容器的完整 ID 或长 ID。如果某个容器在 `docker ps` 中显示为 `ae836c95b4c3`，其长 ID 可能类似于 `ae836c95b4c3c9e9179e0e91015512da89fdec91612f63cebae57df9a5444c79`。您可以使用 `docker inspect` 或 `docker ps --no-trunc` 查找它。

综合以上信息，要查看 Docker 容器的内存指标，可以查看以下路径：

- `/sys/fs/cgroup/memory/docker/<longid>/`（cgroup v1，`cgroupfs` 驱动）
- `/sys/fs/cgroup/memory/system.slice/docker-<longid>.scope/`（cgroup v1，`systemd` 驱动）
- `/sys/fs/cgroup/docker/<longid>/`（cgroup v2，`cgroupfs` 驱动）
- `/sys/fs/cgroup/system.slice/docker-<longid>.scope/`（cgroup v2，`systemd` 驱动）

### 来自 cgroup 的指标：内存、CPU、块 I/O（Metrics from cgroups: memory, CPU, block I/O）

> [!NOTE]
>
> 本节尚未针对 cgroup v2 进行更新。有关 cgroup v2 的更多信息，请参阅[内核文档](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)。

对于每个子系统（内存、CPU 和块 I/O），存在一个或多个伪文件并包含统计信息。

#### 内存指标：`memory.stat`

内存指标位于 `memory` cgroup 中。内存控制组会增加一点开销，因为它对主机上的内存使用进行非常精细的核算。因此，许多发行版默认不启用它。通常，要启用它，只需添加一些内核命令行参数：`cgroup_enable=memory swapaccount=1`。

指标位于伪文件 `memory.stat` 中。内容如下：

    cache 11492564992
    rss 1930993664
    mapped_file 306728960
    pgpgin 406632648
    pgpgout 403355412
    swap 0
    pgfault 728281223
    pgmajfault 1724
    inactive_anon 46608384
    active_anon 1884520448
    inactive_file 7003344896
    active_file 4489052160
    unevictable 32768
    hierarchical_memory_limit 9223372036854775807
    hierarchical_memsw_limit 9223372036854775807
    total_cache 11492564992
    total_rss 1930993664
    total_mapped_file 306728960
    total_pgpgin 406632648
    total_pgpgout 403355412
    total_swap 0
    total_pgfault 728281223
    total_pgmajfault 1724
    total_inactive_anon 46608384
    total_active_anon 1884520448
    total_inactive_file 7003344896
    total_active_file 4489052160
    total_unevictable 32768

前半部分（不带 `total_` 前缀）包含与 cgroup 内进程相关的统计信息，不包括子 cgroup。后半部分（带 `total_` 前缀）也包括子 cgroup。

有些指标是“仪表”（gauge），即可增可减的值。例如，`swap` 是 cgroup 成员使用的交换空间量。其他一些指标是“计数器”（counter），只能增加，因为它们代表特定事件的发生次数。例如，`pgfault` 表示自 cgroup 创建以来发生的页面错误次数。

`cache`
: 此控制组的进程使用的内存量，这些内存可以与块设备上的块精确关联。当您读写磁盘上的文件时，此值会增加。无论您使用“传统”I/O（`open`、`read`、`write` 系统调用）还是内存映射文件（使用 `mmap`），情况都是如此。它也计入 `tmpfs` 挂载使用的内存，尽管原因尚不清楚。

`rss`
: 不对应磁盘上任何内容的内存量：栈、堆和匿名内存映射。

`mapped_file`
: 表示控制组中进程映射的内存量。它不告诉您使用了多少内存，而是告诉您如何使用内存。

`pgfault`、`pgmajfault`
: 分别表示 cgroup 的进程触发“页面错误”（page fault）和“主页面错误”（major fault）的次数。当进程访问当前未映射到物理内存帧的虚拟内存页时，会发生页面错误。这是内存管理的正常部分。例如，当进程从已交换出去的内存区域或对应内存映射文件的区域读取时，会发生页面错误：在这种情况下，内核从磁盘加载页面并让 CPU 完成内存访问。当进程写入写时复制（copy-on-write）内存区域时也会发生页面错误：内核复制内存页，并在进程自己的页面副本上恢复写操作。“主”错误发生在内核需要从磁盘读取数据时。当内核复制现有页面或分配空页面时，这是一个普通的（或“次要”）错误。

`swap`
: 此 cgroup 中的进程当前使用的交换空间量。

`active_anon`、`inactive_anon`
: 内核标识为分别处于**活动**和**非活动**状态的匿名内存量。“匿名”内存是**不**链接到磁盘页的内存。换句话说，这相当于上面描述的 rss 计数器。实际上，rss 计数器的定义是 `active_anon` + `inactive_anon` - `tmpfs`（其中 tmpfs 是此控制组挂载的 `tmpfs` 文件系统使用的内存量）。那么，“活动”和“非活动”有什么区别？页面最初是“活动的”；内核定期扫描内存，并将一些页面标记为“非活动”。当它们再次被访问时，会立即重新标记为“活动”。当内核内存不足需要交换到磁盘时，内核会交换“非活动”页面。

`active_file`、`inactive_file`
: 缓存内存，其“活动”和“非活动”类似于上面的匿名内存。确切的公式是 `cache` = `active_file` + `inactive_file` + `tmpfs`。内核用于在活动和非活动集合之间移动内存页面的确切规则与匿名内存的规则不同，但一般原则相同。当内核需要回收内存时，从此池中回收干净的（=未修改的）页面更便宜，因为可以立即回收（而匿名页面和脏/修改页面需要先写入磁盘）。

`unevictable`
: 无法回收的内存量；通常，它算作已被 `mlock`“锁定”的内存。它通常被加密框架用来确保密钥和其他敏感材料永远不会被交换到磁盘。

`memory_limit`、`memsw_limit`
: 这些不是真正的指标，而是对此 cgroup 应用的限制的提醒。第一个表示此控制组进程可以使用的最大物理内存量；第二个表示最大 RAM+交换量。

页面缓存中的内存核算非常复杂。如果不同控制组中的两个进程都读取同一文件（最终依赖磁盘上的相同块），相应的内存费用会在控制组之间分摊。这很好，但这也意味着当某个 cgroup 终止时，可能会增加另一个 cgroup 的内存使用量，因为它们不再分摊那些内存页面的成本。

#### CPU 指标：`cpuacct.stat`

在介绍了内存指标之后，相比之下其他指标就简单了。CPU 指标位于 `cpuacct` 控制器中。

对于每个容器，伪文件 `cpuacct.stat` 包含该容器进程累积的 CPU 使用情况，分为 `user` 时间和 `system` 时间。区别在于：

- `user` 时间是进程直接控制 CPU、执行进程代码的时间。
- `system` 时间是内核代表进程执行系统调用的时间。

这些时间以 1/100 秒的滴答数表示，也称为“用户 jiffies”。每秒有 `USER_HZ` 个 _jiffies_，在 x86 系统上，`USER_HZ` 为 100。历史上，这完全映射到每秒调度器“滴答”的数量，但更高频率的调度和[无滴答内核](https://lwn.net/Articles/549580/)使滴答数变得无关紧要。

#### 块 I/O 指标（Block I/O metrics）

块 I/O 在 `blkio` 控制器中核算。不同的指标分散在不同的文件中。虽然您可以在内核文档的 [blkio-controller](https://www.kernel.org/doc/Documentation/cgroup-v1/blkio-controller.txt) 文件中找到深入的详细信息，但这里列出了最相关的几个：

`blkio.sectors`
: 包含 cgroup 成员进程按设备读写的 512 字节扇区数。读写合并为一个计数器。

`blkio.io_service_bytes`
: 表示 cgroup 读写的字节数。每个设备有 4 个计数器，因为对于每个设备，它区分同步 vs. 异步 I/O，以及读取 vs. 写入。

`blkio.io_serviced`
: 执行的 I/O 操作数，无论其大小。每个设备也有 4 个计数器。

`blkio.io_queued`
: 表示此 cgroup 当前排队等待的 I/O 操作数。换句话说，如果 cgroup 没有执行任何 I/O，则此值为零。反之则不成立。换句话说，如果没有 I/O 排队，并不表示 cgroup 空闲（从 I/O 角度）。它可能只是在其他方面静止的设备上执行纯同步读取，因此可以立即处理它们而无需排队。此外，虽然它有助于找出哪个 cgroup 给 I/O 子系统带来压力，但请记住这是一个相对量。即使一个进程组没有执行更多 I/O，其队列大小也可能仅仅因为设备负载因其他设备而增加。

### 网络指标（Network metrics）

网络指标不直接由控制组暴露。有一个很好的解释：网络接口存在于**网络命名空间**的上下文中。内核可能可以累积一组进程发送和接收的数据包和字节的指标，但这些指标可能不是很有用。您需要的是按接口的指标（因为本地 `lo` 接口上的流量并不真正算数）。但由于单个 cgroup 中的进程可能属于多个网络命名空间，这些指标将更难解释：多个网络命名空间意味着多个 `lo` 接口，可能多个 `eth0` 接口等；这就是为什么没有简单的方法用控制组收集网络指标的原因。

相反，您可以从其他来源收集网络指标。

#### iptables

iptables（或者更确切地说是 netfilter 框架，iptables 只是其一个接口）可以进行一些严肃的核算。

例如，您可以设置一条规则来核算 Web 服务器上的出站 HTTP 流量：

```console
$ iptables -I OUTPUT -p tcp --sport 80
```

没有 `-j` 或 `-g` 标志，因此该规则仅计算匹配的数据包并转到下一条规则。

之后，您可以使用以下命令检查计数器的值：

```console
$ iptables -nxvL OUTPUT
```

从技术上讲，`-n` 不是必需的，但它可以防止 iptables 进行 DNS 反向查找，这在此场景中可能毫无用处。

计数器包括数据包和字节。如果您想为此类容器流量设置指标，可以执行一个 `for` 循环，在 `FORWARD` 链中为每个容器 IP 地址添加两条 iptables 规则（每个方向一条）。这仅度量经过 NAT 层的流量；您还需要添加经过用户态代理的流量。

然后，您需要定期检查这些计数器。如果您碰巧使用 `collectd`，有一个[不错的插件](https://collectd.org/wiki/index.php/Table_of_Plugins)可以自动收集 iptables 计数器。

#### 接口级计数器（Interface-level counters）

由于每个容器都有一个虚拟以太网接口，您可能希望直接检查该接口的 TX 和 RX 计数器。每个容器都与您主机中的一个虚拟以太网接口相关联，名称类似于 `vethKk8Zqi`。不幸的是，找出哪个接口对应哪个容器是困难的。

但目前，最好的方法是**从容器内部**检查指标。要实现这一点，您可以使用 **ip-netns 魔法**，从主机环境中在容器的网络命名空间内运行一个可执行文件。

`ip-netns exec` 命令允许您在当前进程可见的任何网络命名空间中执行任何（存在于主机系统中的）程序。这意味着您的主机可以进入容器的网络命名空间，但容器不能访问主机或其他对等容器。不过，容器可以与其子容器交互。

命令的确切格式是：

```console
$ ip netns exec <nsname> <command...>
```

例如：

```console
$ ip netns exec mycontainer netstat -i
```

`ip netns` 通过使用命名空间伪文件来查找 `mycontainer` 容器。每个进程都属于一个网络命名空间、一个 PID 命名空间、一个 `mnt` 命名空间等，这些命名空间在 `/proc/<pid>/ns/` 下具体化。例如，PID 42 的网络命名空间由伪文件 `/proc/42/ns/net` 具体化。

当您运行 `ip netns exec mycontainer ...` 时，它期望 `/var/run/netns/mycontainer` 是这些伪文件之一（接受符号链接）。

换句话说，要在容器的网络命名空间内执行命令，我们需要：

- 找到要调查的容器内任何进程的 PID；
- 创建从 `/var/run/netns/<somename>` 到 `/proc/<thepid>/ns/net` 的符号链接；
- 执行 `ip netns exec <somename> ....`

回顾[枚举 cgroup](#enumerate-cgroups) 以了解如何找到要测量其网络使用情况的容器内进程的 cgroup。从那里，您可以检查名为 `tasks` 的伪文件，其中包含 cgroup 中的所有 PID（因此也包含容器中的 PID）。选择其中任何一个 PID。

综合起来，如果容器的“短 ID”保存在环境变量 `$CID` 中，那么可以这样做：

```console
$ TASKS=/sys/fs/cgroup/devices/docker/$CID*/tasks
$ PID=$(head -n 1 $TASKS)
$ mkdir -p /var/run/netns
$ ln -sf /proc/$PID/ns/net /var/run/netns/$CID
$ ip netns exec $CID netstat -i
```

## 高性能指标收集的技巧（Tips for high-performance metric collection）

每次要更新指标时运行一个新进程是（相对）昂贵的。如果您想以高分辨率收集指标，并且/或者针对大量容器（设想单个主机上有 1000 个容器），您不希望每次分叉一个新进程。

以下是如何从单个进程收集指标。您需要用 C（或任何允许您进行低级系统调用的语言）编写指标收集器。您需要使用特殊的系统调用 `setns()`，它允许当前进程进入任意命名空间。但是，它需要打开命名空间伪文件的文件描述符（记住：那是 `/proc/<pid>/ns/net` 中的伪文件）。

然而，有一个问题：您不能保持此文件描述符打开。如果您这样做，当控制组的最后一个进程退出时，命名空间不会被销毁，其网络资源（如容器的虚拟接口）将永远保留（或直到您关闭该文件描述符）。

正确的方法是跟踪每个容器的第一个 PID，并在每次需要时重新打开命名空间伪文件。

## 在容器退出时收集指标（Collect metrics when a container exits）

有时您不关心实时指标收集，但当容器退出时，您想知道它使用了多少 CPU、内存等。

Docker 使这变得困难，因为它依赖 `lxc-start`，它会仔细清理自身。通常，定期收集指标更容易，这就是 `collectd` LXC 插件的工作方式。

但是，如果您仍然希望在容器停止时收集统计信息，可以这样做：

对于每个容器，启动一个收集进程，并将其 PID 写入 cgroup 的 `tasks` 文件，从而将其移动到要监控的控制组中。收集进程应定期重新读取 `tasks` 文件，以检查它是否是控制组的最后一个进程。（如果您还想收集上一节中说明的网络统计信息，您还应将该进程移动到适当的网络命名空间。）

当容器退出时，`lxc-start` 会尝试删除控制组。由于控制组仍在使用中，它会失败，但这没问题。您的进程现在应该检测到它是组中唯一剩下的进程。现在是收集所有所需指标的正确时机！

最后，您的进程应将自己移回根控制组，并删除容器控制组。要删除控制组，只需 `rmdir` 其目录。对一个仍包含文件的目录执行 `rmdir` 是违反直觉的，但请记住这是一个伪文件系统，因此通常的规则不适用。清理完成后，收集进程可以安全退出。