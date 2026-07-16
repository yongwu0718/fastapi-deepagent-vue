# 排查 Docker 守护进程故障（Troubleshooting the Docker daemon）

本页介绍在遇到问题时如何对守护进程进行故障排查和调试。

您可以在守护进程上开启调试功能，以了解守护进程的运行时活动并帮助排查问题。如果守护进程无响应，您还可以通过向 Docker 守护进程发送 `SIGUSR1` 信号来[强制将所有线程的完整堆栈跟踪添加到守护进程日志中](/engine/daemon/troubleshoot/logs/#force-a-stack-trace-to-be-logged)。

## 守护进程（Daemon）

### 无法连接到 Docker 守护进程（Unable to connect to the Docker daemon）

```text
Cannot connect to the Docker daemon. Is 'docker daemon' running on this host?
```

此错误可能表示：

- Docker 守护进程未在您的系统上运行。请启动守护进程，然后再次尝试运行命令。
- 您的 Docker 客户端正在尝试连接到不同主机上的 Docker 守护进程，并且该主机不可达。

### 检查 Docker 是否正在运行（Check whether Docker is running）

检查 Docker 是否正在运行的与操作系统无关的方法是使用 `docker info` 命令询问 Docker。

您也可以使用操作系统工具，例如 `sudo systemctl is-active docker`、`sudo status docker`、`sudo service docker status`，或使用 Windows 工具检查服务状态。

最后，您可以使用 `ps` 或 `top` 等命令在进程列表中检查 `dockerd` 进程。

#### 检查客户端连接到哪个主机（Check which host your client is connecting to）

要查看您的客户端连接到哪个主机，请检查环境中的 `DOCKER_HOST` 变量。

```console
$ env | grep DOCKER_HOST
```

如果此命令返回值，则 Docker 客户端被设置为连接到该主机上运行的 Docker 守护进程。如果未设置，则 Docker 客户端被设置为连接到本地主机上运行的 Docker 守护进程。如果设置错误，请使用以下命令取消设置：

```console
$ unset DOCKER_HOST
```

您可能需要编辑 `~/.bashrc` 或 `~/.profile` 等文件中的环境，以防止 `DOCKER_HOST` 变量被错误设置。

如果 `DOCKER_HOST` 按预期设置，请验证远程主机上的 Docker 守护进程正在运行，并且防火墙或网络故障没有阻止您的连接。

### 排查 `daemon.json` 与启动脚本之间的冲突（Troubleshoot conflicts between the `daemon.json` and startup scripts）

如果您使用 `daemon.json` 文件，并且同时手动或使用启动脚本向 `dockerd` 命令传递选项，而这些选项发生冲突，Docker 将无法启动并显示如下错误：

```text
unable to configure the Docker daemon with file /etc/docker/daemon.json:
the following directives are specified both as a flag and in the configuration
file: hosts: (from flag: [unix:///var/run/docker.sock], from file: [tcp://127.0.0.1:2376])
```

如果您看到类似错误并且您正在手动使用标志启动守护进程，则可能需要调整您的标志或 `daemon.json` 以消除冲突。

> [!NOTE]
>
> 如果您看到关于 `hosts` 的具体错误消息，请继续阅读[下一节](#configure-the-daemon-host-with-systemd)以获取解决方法。

如果您使用操作系统的 init 脚本启动 Docker，则可能需要以特定于操作系统的方式覆盖这些脚本中的默认设置。

#### 使用 systemd 配置守护进程主机（Configure the daemon host with systemd）

一个难以排查的配置冲突的显著示例是当您希望指定一个不同于默认地址的守护进程地址时。Docker 默认监听一个 socket。在使用 `systemd` 的 Debian 和 Ubuntu 系统上，这意味着在启动 `dockerd` 时总是使用主机标志 `-H`。如果您在 `daemon.json` 中指定了 `hosts` 条目，则会导致配置冲突，并使 Docker 守护进程无法启动。

要解决此问题，请创建一个新文件 `/etc/systemd/system/docker.service.d/docker.conf`，内容如下，以移除默认启动守护进程时使用的 `-H` 参数。

```systemd
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
```

还有其他情况您可能需要使用 Docker 配置 `systemd`，例如[配置 HTTP 或 HTTPS 代理](/engine/daemon/proxy/)。

> [!NOTE]
>
> 如果您覆盖此选项，但未在 `daemon.json` 中指定 `hosts` 条目，也未在手动启动 Docker 时指定 `-H` 标志，Docker 将无法启动。

在尝试启动 Docker 之前，运行 `sudo systemctl daemon-reload`。如果 Docker 成功启动，它将监听在 `daemon.json` 的 `hosts` 键中指定的 IP 地址上，而不是 socket 上。

> [!IMPORTANT]
>
> 在 Docker Desktop for Windows 或 Docker Desktop for Mac 上，不支持在 `daemon.json` 中设置 `hosts`。

### 内存不足问题（Out of memory issues）

如果您的容器尝试使用的内存超过系统可用内存，您可能会遇到内存不足（OOM）异常，并且容器或 Docker 守护进程可能会被内核 OOM killer 停止。为防止这种情况发生，请确保您的应用程序在具有足够内存的主机上运行，并参阅[了解内存不足的风险](/engine/containers/resource_constraints/#understand-the-risks-of-running-out-of-memory)。

### 内核兼容性（Kernel compatibility）

如果您的内核版本低于 3.10，或者缺少内核模块，Docker 无法正常运行。要检查内核兼容性，您可以下载并运行 [`check-config.sh`](https://raw.githubusercontent.com/docker/docker/master/contrib/check-config.sh) 脚本。

```console
$ curl https://raw.githubusercontent.com/docker/docker/master/contrib/check-config.sh > check-config.sh

$ bash ./check-config.sh
```

该脚本仅在 Linux 上工作。

### 内核 cgroup swap 限制能力（Kernel cgroup swap limit capabilities）

在 Ubuntu 或 Debian 主机上，处理镜像时您可能会看到类似以下的消息。

```text
WARNING: Your kernel does not support swap limit capabilities. Limitation discarded.
```

如果您不需要这些能力，可以忽略此警告。

您可以按照以下说明在 Ubuntu 或 Debian 上启用这些能力。即使没有运行 Docker，内存和交换核算也会产生约总可用内存 1% 的开销和 10% 的整体性能下降。

1. 以具有 `sudo` 权限的用户身份登录 Ubuntu 或 Debian 主机。

2. 编辑 `/etc/default/grub` 文件。添加或编辑 `GRUB_CMDLINE_LINUX` 行，添加以下两个键值对：

   ```text
   GRUB_CMDLINE_LINUX="cgroup_enable=memory swapaccount=1"
   ```

   保存并关闭文件。

3. 更新 GRUB 引导加载程序。

   ```console
   $ sudo update-grub
   ```

   如果您的 GRUB 配置文件语法不正确，则会发生错误。在这种情况下，请重复步骤 2 和 3。

   更改在系统重新启动后生效。

## 网络（Networking）

### IP 转发问题（IP forwarding problems）

如果您使用 systemd 版本 219 或更高版本的 `systemd-network` 手动配置网络，Docker 容器可能无法访问您的网络。从 systemd 220 版本开始，给定网络（`net.ipv4.conf.<interface>.forwarding`）的转发设置默认为关闭。此设置阻止 IP 转发。它还与 Docker 在容器内启用 `net.ipv4.conf.all.forwarding` 设置的行为冲突。

要在 RHEL、CentOS 或 Fedora 上解决此问题，请在 Docker 主机上的 `/usr/lib/systemd/network/` 中编辑 `<interface>.network` 文件，例如 `/usr/lib/systemd/network/80-container-host0.network`。

在 `[Network]` 部分中添加以下块。

```systemd
[Network]
...
IPForward=kernel
# OR
IPForward=true
```

此配置允许按预期从容器进行 IP 转发。

### DNS 解析器问题（DNS resolver issues）

```console
DNS resolver found in resolv.conf and containers can't use it
```

Linux 桌面环境通常运行一个网络管理器程序，该程序使用 `dnsmasq` 通过将 DNS 请求添加到 `/etc/resolv.conf` 来缓存它们。`dnsmasq` 实例运行在回环地址上，如 `127.0.0.1` 或 `127.0.1.1`。它可以加速 DNS 查找并提供 DHCP 服务。这种配置在 Docker 容器内不起作用。Docker 容器使用自己的网络命名空间，并将 `127.0.0.1` 等回环地址解析到自身，而且它不太可能在自己的回环地址上运行 DNS 服务器。

如果 Docker 检测到 `/etc/resolv.conf` 中引用的 DNS 服务器都不是功能完全的 DNS 服务器，则会出现以下警告：

```text
WARNING: Local (127.0.0.1) DNS resolver found in resolv.conf and containers
can't use it. Using default external servers : [8.8.8.8 8.8.4.4]
```

如果您看到此警告，请首先检查是否使用了 `dnsmasq`：

```console
$ ps aux | grep dnsmasq
```

如果您的容器需要解析网络内部的主机，公共名称服务器是不够的。您有两个选择：

- 为 Docker 指定要使用的 DNS 服务器。
- 关闭 `dnsmasq`。

  关闭 `dnsmasq` 会将实际 DNS 名称服务器的 IP 地址添加到 `/etc/resolv.conf` 中，但您会失去 `dnsmasq` 的好处。

您只需使用其中一种方法。

### 为 Docker 指定 DNS 服务器（Specify DNS servers for Docker）

配置文件的默认位置是 `/etc/docker/daemon.json`。您可以使用 `--config-file` 守护进程标志更改配置文件的位置。以下说明假定配置文件的位置为 `/etc/docker/daemon.json`。

1. 创建或编辑 Docker 守护进程配置文件，默认为 `/etc/docker/daemon.json` 文件，该文件控制 Docker 守护进程配置。

   ```console
   $ sudo nano /etc/docker/daemon.json
   ```

2. 添加一个 `dns` 键，其值为一个或多个 DNS 服务器 IP 地址。

   ```json
   {
     "dns": ["8.8.8.8", "8.8.4.4"]
   }
   ```

   如果文件已有内容，您只需添加或编辑 `dns` 行。如果您的内部 DNS 服务器无法解析公共 IP 地址，请至少包含一个可以解析的 DNS 服务器。这样做可以允许您连接到 Docker Hub，并允许您的容器解析互联网域名。

   保存并关闭文件。

3. 重启 Docker 守护进程。

   ```console
   $ sudo service docker restart
   ```

4. 尝试拉取镜像以验证 Docker 可以解析外部 IP 地址：

   ```console
   $ docker pull hello-world
   ```

5. 如有必要，通过 ping 内部主机名来验证 Docker 容器可以解析内部主机名。

   ```console
   $ docker run --rm -it alpine ping -c4 <my_internal_host>

   PING google.com (192.168.1.2): 56 data bytes
   64 bytes from 192.168.1.2: seq=0 ttl=41 time=7.597 ms
   64 bytes from 192.168.1.2: seq=1 ttl=41 time=7.635 ms
   64 bytes from 192.168.1.2: seq=2 ttl=41 time=7.660 ms
   64 bytes from 192.168.1.2: seq=3 ttl=41 time=7.677 ms
   ```

### 关闭 `dnsmasq`（Turn off `dnsmasq`）

**Ubuntu**

如果您不想更改 Docker 守护进程的配置以使用特定 IP 地址，请按照以下说明在 NetworkManager 中关闭 `dnsmasq`。

1. 编辑 `/etc/NetworkManager/NetworkManager.conf` 文件。

2. 通过在行首添加 `#` 字符来注释掉 `dns=dnsmasq` 行。

   ```text
   # dns=dnsmasq
   ```

   保存并关闭文件。

3. 重启 NetworkManager 和 Docker。或者，您可以重新启动系统。

   ```console
   $ sudo systemctl restart network-manager
   $ sudo systemctl restart docker
   ```

**RHEL、CentOS 或 Fedora**

在 RHEL、CentOS 或 Fedora 上关闭 `dnsmasq`：

1. 关闭 `dnsmasq` 服务：

   ```console
   $ sudo systemctl stop dnsmasq
   $ sudo systemctl disable dnsmasq
   ```

2. 使用 [Red Hat 文档](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/configuring_and_managing_networking/configuring-the-order-of-dns-servers_configuring-and-managing-networking) 手动配置 DNS 服务器。

### Docker 网络消失（Docker networks disappearing）

如果 Docker 网络（例如 `docker0` 桥接或自定义网络）随机消失或以其他方式似乎工作不正常，可能是因为其他服务干扰或修改了 Docker 接口。已知一些管理主机上网络接口的工具有时也会不适当地修改 Docker 接口。

请根据主机上存在的网络管理工具，参考以下部分了解如何配置网络管理器将 Docker 接口设置为不受管理（unmanaged）：

- 如果安装了 `netscript`，请考虑[卸载它](#uninstall-netscript)
- 配置网络管理器[将 Docker 接口视为不受管理](#un-manage-docker-interfaces)
- 如果您使用 Netplan，可能需要[应用自定义 Netplan 配置](#prevent-netplan-from-overriding-network-configuration)

#### 卸载 `netscript`（Uninstall `netscript`）

如果您的系统上安装了 `netscript`，通常可以通过卸载它来解决问题。例如，在基于 Debian 的系统上：

```console
$ sudo apt-get remove netscript-2.4
```

#### 取消管理 Docker 接口（Un-manage Docker interfaces）

在某些情况下，网络管理器会默认尝试管理 Docker 接口。您可以通过编辑系统的网络配置设置，尝试将 Docker 网络显式标记为不受管理。

**NetworkManager**

如果您使用 `NetworkManager`，请在 `/etc/network/interfaces` 下编辑系统网络配置。

1. 在 `/etc/network/interfaces.d/20-docker0` 创建一个文件，内容如下：

   ```text
   iface docker0 inet manual
   ```

   请注意，此示例配置仅“取消管理”默认的 `docker0` 桥接，而不是自定义网络。

2. 重启 `NetworkManager` 以使配置更改生效。

   ```console
   $ systemctl restart NetworkManager
   ```

3. 验证 `docker0` 接口是否具有 `unmanaged` 状态。

   ```console
   $ nmcli device
   ```

**systemd-networkd**

如果您在将 `systemd-networkd` 作为网络守护进程的系统上运行 Docker，请通过在 `/etc/systemd/network` 下创建配置文件来将 Docker 接口配置为不受管理：

1. 创建 `/etc/systemd/network/docker.network`，内容如下：

   ```ini
   # 确保 Docker 接口不受管理

   [Match]
   Name=docker0 br-* veth*

   [Link]
   Unmanaged=yes

   ```

2. 重新加载配置。

   ```console
   $ sudo systemctl restart systemd-networkd
   ```

3. 重启 Docker 守护进程。

   ```console
   $ sudo systemctl restart docker
   ```

4. 验证 Docker 接口是否具有 `unmanaged` 状态。

   ```console
   $ networkctl
   ```

### 防止 Netplan 覆盖网络配置（Prevent Netplan from overriding network configuration）

在使用 [`cloud-init`](https://cloudinit.readthedocs.io/en/latest/index.html) 通过 [Netplan](https://netplan.io/) 的系统上，您可能需要应用自定义配置以防止 `netplan` 覆盖网络管理器配置：

1. 按照[取消管理 Docker 接口](#un-manage-docker-interfaces)中的步骤创建网络管理器配置。
2. 在 `/etc/netplan/50-cloud-init.yml` 下创建一个 `netplan` 配置文件。

   以下示例配置文件是一个起点。请根据您要取消管理的接口进行调整。不正确的配置可能导致网络连接问题。

   ```yaml {title="/etc/netplan/50-cloud-init.yml"}
   network:
     ethernets:
       all:
         dhcp4: true
         dhcp6: true
         match:
           # 编辑此过滤器以匹配适合您系统的任何内容
           name: en*
     renderer: networkd
     version: 2
   ```

3. 应用新的 Netplan 配置。

   ```console
   $ sudo netplan apply
   ```

4. 重启 Docker 守护进程：

   ```console
   $ sudo systemctl restart docker
   ```

5. 验证 Docker 接口是否具有 `unmanaged` 状态。

   ```console
   $ networkctl
   ```

## 卷（Volumes）

### 无法移除文件系统（Unable to remove filesystem）

```text
Error: Unable to remove filesystem
```

某些基于容器的工具（例如 [Google cAdvisor](https://github.com/google/cadvisor)）会将 Docker 系统目录（如 `/var/lib/docker/`）挂载到容器中。例如，`cadvisor` 的文档指示您按如下方式运行 `cadvisor` 容器：

```console
$ sudo docker run \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:rw \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --publish=8080:8080 \
  --detach=true \
  --name=cadvisor \
  google/cadvisor:latest
```

当您绑定挂载 `/var/lib/docker/` 时，这实际上将所有其他运行中容器的所有资源作为文件系统挂载到挂载 `/var/lib/docker/` 的容器中。当您尝试移除其中任何一个容器时，移除操作可能会失败，并出现如下错误：

```text
Error: Unable to remove filesystem for
74bef250361c7817bee19349c93139621b272bc8f654ae112dd4eb9652af9515:
remove /var/lib/docker/containers/74bef250361c7817bee19349c93139621b272bc8f654ae112dd4eb9652af9515/shm:
Device or resource busy
```

如果绑定挂载 `/var/lib/docker/` 的容器对 `/var/lib/docker/` 内的文件系统句柄使用了 `statfs` 或 `fstatfs` 并且没有关闭它们，则会出现此问题。

通常，我们建议不要以这种方式绑定挂载 `/var/lib/docker`。但是，`cAdvisor` 的核心功能需要此绑定挂载。

如果您不确定是哪个进程导致错误中提到的路径繁忙并阻止其被移除，您可以使用 `lsof` 命令找到其进程。例如，对于上面的错误：

```console
$ sudo lsof /var/lib/docker/containers/74bef250361c7817bee19349c93139621b272bc8f654ae112dd4eb9652af9515/shm
```

要解决此问题，请停止绑定挂载 `/var/lib/docker/` 的容器，然后再次尝试移除另一个容器。