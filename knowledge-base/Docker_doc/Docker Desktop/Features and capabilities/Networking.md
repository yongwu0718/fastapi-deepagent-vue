# Docker Desktop 的网络功能

本页说明 Docker Desktop 如何在容器、虚拟机和主机之间路由网络流量和文件 I/O，以及防火墙和端点防护工具如何观察到这些行为。

## 概述

Docker Desktop 在轻量级 Linux 虚拟机（VM）内运行 Docker Engine。根据您的系统配置和操作系统，Docker Desktop 使用不同的后端组件在 Docker VM 和主机之间路由网络和文件操作。

### 后端组件及其职责

后端扮演以下角色：

- **网络代理 (Network proxy)**：在主机和 Linux VM 之间转换流量。
   - 在 Windows 和 Mac 上，由 `com.docker.backend` 进程处理。
   - 在 Linux 上，由 `qemu` 进程执行此功能。
- **文件服务器 (File server)**：处理从容器到主机文件系统的文件访问。
   - 当使用 gRPC FUSE 时，后端执行文件共享。
   - 当使用 `virtiofs`、`osxfs` 或 `krun` 时，文件访问由各自对应的守护进程处理，而不是后端进程。
- **控制平面 (Control plane)**：管理 Docker API 调用、端口转发和代理配置。

下表更详细地总结了典型设置：

| 平台             | 设置                                 | 网络处理方               | 文件共享处理方                        | 备注                                                   |
| --------------- | ------------------------------------ | ------------------------ | -------------------------------------- | ------------------------------------------------------ |
| Windows         | Hyper-V                              | `com.docker.backend.exe` | `com.docker.backend.exe`               | 最简单的设置，EDR/防火墙工具具有完全可见性               |
| Windows (WSL 2) | WSL 2                                | `com.docker.backend.exe` | WSL 2 内核（主机不可见）               | 仅在需要 WSL 2 集成时推荐                              |
| Mac             | Virtualization framework + gRPC FUSE | `com.docker.backend`     | `com.docker.backend`                   | 推荐，兼顾性能和可见性                                 |
| Mac             | Virtualization framework + `virtiofs`| `com.docker.backend`     | Apple 的 Virtualization framework      | 性能更高，但主机无法看到文件访问                       |
| Mac             | Virtualization framework + `osxfs`   | `com.docker.backend`     | `osxfs`                                | 旧版设置，不推荐                                       |
| Mac             | DockerVMM + `virtiofs`               | `com.docker.backend`     | `krun`                                 | 目前处于 Beta 版                                       |
| Linux           | Native Linux VM                      | `qemu`                   | `virtiofsd`                            | Linux 上没有 `com.docker.backend` 进程                 |

## 容器如何连接到互联网

Docker Desktop 中的每个 Linux 容器都运行在由 Docker 管理的小型虚拟网络内部，每个容器都连接到一个 Docker 管理的网络并获得自己的内部 IP 地址。您可以使用 `docker network ls`、`docker network create` 和 `docker network inspect` 查看和管理这些网络。它们由 [`daemon.json`](/engine/daemon/) 管理。

当容器发起网络请求时（例如 `apt-get update` 或 `docker pull`）：

- 容器的 `eth0` 接口连接到 VM 内部的虚拟网桥（`docker0`）。
- 来自容器的出站流量通过网络地址转换（NAT）使用虚拟适配器（通常具有内部 IP，如 `192.168.65.3`）发送。您可以通过 [Docker Desktop 设置](/desktop/settings-and-maintenance/settings/#network)查看或更改此设置。
- 流量通过共享内存通道传输到主机系统，而不是通过传统的虚拟网络接口。这种方法确保了可靠的通信，并避免了与主机级网络适配器或防火墙配置的冲突。
- 在主机上，Docker Desktop 的后端进程接收流量，并使用与其他应用程序相同的网络 API 创建标准的 TCP/IP 连接。

所有出站的容器网络流量都源自 `com.docker.backend` 进程。防火墙、VPN 和安全工具（如 Crowdstrike）看到的流量来自此进程，而不是来自 VM 或未知来源，因此防火墙和端点安全软件可以直接对 `com.docker.backend` 应用规则。

## 暴露端口（Exposed ports）的工作原理

当您使用 `-p` 或 `--publish` 标志发布容器端口时，Docker Desktop 会使该容器端口可从您的主机系统或本地网络访问。

例如，使用 `docker run -p 80:80 nginx`：

- Docker Desktop 的后端进程在指定的主机端口（本例中为端口 `80`）上侦听。
- 当应用程序（例如 Web 浏览器）连接到该端口时，Docker Desktop 通过共享内存通道将连接转发到运行容器的 Linux VM 中。
- 在 VM 内部，连接被路由到容器的内部 IP 地址和端口，例如 `172.17.0.2:80`。
- 容器通过相同的路径响应，因此您可以从主机像访问任何其他本地服务一样访问它。

默认情况下，`docker run -p` 侦听所有网络接口（`0.0.0.0`），但您可以将其限制为特定地址，例如 `127.0.0.1`（localhost）或特定的网络适配器。可以在 [Docker Desktop 的网络设置](/desktop/settings-and-maintenance/settings/#network)中修改此行为，使其默认绑定到 `localhost`。

主机防火墙可以通过对 `com.docker.backend` 进行过滤来允许或拒绝入站连接。

## 将 Docker Desktop 与代理（Proxy）一起使用

Docker Desktop 可以使用系统的默认代理设置，或者您通过 [Docker Desktop 的代理设置](/desktop/settings-and-maintenance/settings/#proxies)配置的自定义设置。所有代理流量都经过 `com.docker.backend.exe`。

当启用代理时：

- 后端进程通过网络请求（例如 `docker pull`）转发到内部代理 `http.docker.internal:3128`。
- 然后，内部代理根据您的配置（并在必要时添加身份验证）直接连接到互联网或通过您的上游代理进行连接。
- 然后，Docker Desktop 照常通过代理下载请求的镜像或数据。

请注意：
- 代理遵循系统或手动代理配置。
- 在 Windows 上，支持 Basic、NTLM 和 Kerberos 身份验证。
- 对于 Mac，原生不支持 NTLM/Kerberos。解决方法是在 `localhost` 上运行本地代理。
- 直接使用 Docker API 的 CLI 插件和其他工具必须单独使用 `HTTP_PROXY`、`HTTPS_PROXY` 和 `NO_PROXY` 环境变量进行配置。

## 防火墙和端点可见性

要限制 VM 或容器网络，请将规则应用于 `com.docker.backend.exe` (Windows)、`com.docker.backend` (Mac) 或 `qemu` (Linux)，因为所有 VM 网络都通过这些进程进行。

使用 Windows Defender 防火墙或企业端点防火墙进行控制。这可以在主机级别进行流量检查和限制，而无需修改 Docker Engine。

Crowdstrike 和类似工具可以观察到通过后端进程的所有流量和文件访问。

| 操作 | 对主机 EDR 可见？ | 原因 |
|---------|----------------------|---------|
| 容器读取主机文件 | 是 | 访问由 `com.docker.backend` 处理 |
| 容器写入主机文件 | 是 | 执行写入的是同一进程 |
| 容器访问自己的文件系统层 | 否 | 仅存在于 VM 内部 |