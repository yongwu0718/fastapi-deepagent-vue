# 更改您的 Docker Desktop 设置

通过 Docker Desktop 的设置（Settings），您可以自定义 Docker Desktop 的行为，并优化性能和资源使用。

要打开 **Settings**，可以：

- 选择 Docker 菜单

 然后选择 **Settings**
- 或者从 Docker Desktop Dashboard 中选择 **Settings** 图标。

您也可以在以下位置找到 `settings-store.json` 文件：
 - Mac：`~/Library/Group\ Containers/group.com.docker/settings-store.json`
 - Windows：`C:\Users\[USERNAME]\AppData\Roaming\Docker\settings-store.json`
 - Linux：`~/.docker/desktop/settings-store.json`

有关在组织级别强制设置的信息，请参阅[设置管理（Settings Management）](/enterprise/security/hardened-desktop/settings-management/settings-reference/)。

## General（通用）

配置 Docker Desktop 的启动行为、UI 外观、终端偏好以及功能默认值。

| Setting                                                     | Description                                                                                                                                                                                                               | Default                 | Platform                | Notes                                                                                                                                                                              |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Start Docker Desktop when you sign in to your computer**  | 登录计算机时自动启动 Docker Desktop。                                                                                                                                                                                                | Disabled                | All                     | 推荐给频繁使用 Docker 的用户。                                                                                                                                                                |
| **Open Docker Dashboard when Docker Desktop starts**        | 启动 Docker Desktop 时自动打开仪表板。                                                                                                                                                                                               | Disabled                | All                     |                                                                                                                                                                                    |
| **Choose theme for Docker Desktop**                         | 为 Docker Desktop 应用**Light**（亮色）或**Dark**（暗色）主题。                                                                                                                                                                          | **Use system settings** | All                     |                                                                                                                                                                                    |
| **Configure shell completions**                             | 编辑您的 shell 配置，以便在终端中按 `<Tab>` 时启用命令、标志和 Docker 对象的单词补全。更多信息请参阅[补全（Completion）](/engine/cli/completion/)。                                                                                                                  | Disabled                | All                     |                                                                                                                                                                                    |
| **Choose container terminal**                               | 设置当您选择容器终端时打开哪个终端。使用集成终端从 Dashboard 在运行中的容器内执行命令。更多信息请参阅[探索容器（Explore containers）](/desktop/use-desktop/container/)。                                                                                                      | Disabled                | All                     |                                                                                                                                                                                    |
| **Enable Docker terminal**                                  | 与您的主机交互并直接从 Docker Desktop 执行命令。                                                                                                                                                                                          | Disabled                | All                     |                                                                                                                                                                                    |
| **Enable Docker Debug by default**                          | 默认情况下在打开集成终端时使用 Docker Debug。更多信息请参阅[探索容器（Explore containers）](/desktop/use-desktop/container/#integrated-terminal)。                                                                                                      | Disabled                | All                     |                                                                                                                                                                                    |
| **Include VM in Time Machine backups**                      | 备份 Docker Desktop 虚拟机。                                                                                                                                                                                                    | Disabled                | Mac                     |                                                                                                                                                                                    |
| **Use containerd for pulling and storing images**           | 使用 **containerd image store** 而不是经典镜像存储。更多信息请参阅 [containerd image store](/desktop/features/containerd/)。                                                                                                                  | Enabled                 | All                     |                                                                                                                                                                                    |
| **Expose daemon on tcp://localhost:2375 without TLS**       | 允许旧版客户端连接到 Docker 守护进程。请谨慎使用，因为暴露未启用 TLS 的守护进程可能导致远程代码执行攻击。                                                                                                                                                               | Disabled                | Windows (仅限 Hyper-V 后端) |                                                                                                                                                                                    |
| **Use the WSL 2 based engine**                              | **WSL 2** 提供比 Hyper-V 后端更好的性能。更多信息请参阅 [Docker Desktop WSL 2 backend](/desktop/features/wsl/)。                                                                                                                             | Disabled                | Windows                 |                                                                                                                                                                                    |
| **Add \*.docker.internal to host file**                     | 添加内部 DNS 条目。                                                                                                                                                                                                              | Enabled                 | Windows                 | 有助于解析 Docker 内部域名                                                                                                                                                                  |
| **Choose Virtual Machine Manager (VMM)**                    | 选择用于创建和管理 Docker Desktop Linux 虚拟机的 VMM。更多信息请参阅[虚拟机管理器（Virtual Machine Manager）](/desktop/features/vmm/)。                                                                                                                 |                         | Mac                     | 选择 **Docker VMM** 可获得最新、性能最佳的 Hypervisor/VMM。此选项仅在 Apple Silicon Mac 上可用，且处于 Beta 阶段。                                                                                              |
| **Choose file sharing implementation for your containers**  | 选择使用 **VirtioFS**、**gRPC FUSE** 还是 **osxfs (Legacy)** 来共享文件。                                                                                                                                                              | **VirtioFS**            | Mac                     | 使用 VirtioFS 可实现快速文件共享。VirtioFS 已将完成文件系统操作的时间[减少多达 98%](https://github.com/docker/roadmap/issues/7#issuecomment-1044452206)。它是 **Docker VMM** 支持的唯一文件共享实现。                          |
| **Use Rosetta for x86_64/amd64 emulation on Apple Silicon** | 在 Apple Silicon 上加速 x86/AMD64 二进制模拟。仅当您选择 **Apple Virtualization framework** 作为虚拟机管理器时，此选项才可用。                                                                                                                            | Disabled                | Mac                     |                                                                                                                                                                                    |
| **Send usage statistics**                                   | 向 Docker 发送诊断、崩溃报告和使用数据，以改进和排查应用程序问题。Docker 可能会定期提示您提供更多信息。                                                                                                                                                               | Enabled                 | All                     |                                                                                                                                                                                    |
| **Use Enhanced Container Isolation**                        | 防止容器破坏 Linux 虚拟机。更多信息请参阅[增强型容器隔离（Enhanced Container Isolation）](/enterprise/security/hardened-desktop/enhanced-container-isolation/)。                                                                                     | Disabled                | All                     | 必须登录并拥有 Docker Business 订阅。                                                                                                                                                        |
| **Show CLI hints**                                          | 在终端中显示有用的 CLI 建议。                                                                                                                                                                                                         | Enabled                 | All                     | 提高可发现性                                                                                                                                                                             |
| **Enable Docker Scout image analysis**                      | 在检查镜像时显示 **Start analysis** 按钮，以便使用 Docker Scout 分析镜像。                                                                                                                                                                    | Enabled                 | All                     |                                                                                                                                                                                    |
| **Enable background SBOM indexing**                         | 自动分析您构建或拉取的镜像。                                                                                                                                                                                                            | Disabled                | All                     |                                                                                                                                                                                    |
| **Automatically check configuration**                       | 定期检查您的配置，确保没有其他应用程序进行了意外更改。如果发现更改，会通知您，并可直接从通知中恢复配置。更多信息请参阅 [FAQs](/desktop/troubleshoot-and-support/faqs/macfaqs/#why-do-i-keep-getting-a-notification-telling-me-an-application-has-changed-my-desktop-configurations)。 | Enabled                 | Mac                     | Docker Desktop 会检查安装期间配置的设置是否已被 Orbstack 等外部应用更改。Docker Desktop 会检查 Docker 二进制文件到 `/usr/local/bin` 的符号链接以及默认 Docker socket 的符号链接。此外，Docker Desktop 会确保在启动时将上下文切换到 `desktop-linux`。 |

## Resources（资源）

控制 Docker Desktop 可用的 CPU、内存、磁盘、文件共享、代理和网络资源。

### Advanced（高级）

| Setting                 | Description                                                                                                                    | Platform                    | Notes                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------- | --------------------------------------------------------- |
| **CPU limit**           | 指定 Docker Desktop 可使用的最大 CPU 核心数。                                                                                              | Mac, Linux, Windows Hyper-V |                                                           |
| **Memory limit**        | 分配给 Docker 虚拟机的 RAM                                                                                                            | Mac, Linux, Windows Hyper-V | 默认为主机内存的 50%。                                             |
| **Swap**                | 根据需要配置 swap 文件大小。                                                                                                              | Mac, Linux, Windows Hyper-V | 默认 1 GB。                                                  |
| **Disk usage limit**    | 指定引擎可以使用的最大磁盘空间。                                                                                                               | Mac, Linux, Windows Hyper-V |                                                           |
| **Disk image location** | 指定存储容器和镜像的 Linux 卷的位置。在 **Advanced** 选项卡上，您可以限制 Docker Linux 虚拟机的可用资源。                                                         | Mac, Linux, Windows Hyper-V | 您还可以将磁盘镜像移动到其他位置。如果您尝试将磁盘镜像移动到已有镜像的位置，系统会询问您是使用现有镜像还是替换它。 |
| **Resource Saver**      | 启用或禁用 [Resource Saver mode](/desktop/use-desktop/resource-saver/)，该模式在 Docker Desktop 空闲时自动关闭 Linux 虚拟机，从而显著降低主机上的 CPU 和内存利用率。 | Mac, Linux, Windows Hyper-V | 当需要运行容器时会自动重启。重启可能需要 3–10 秒。                              |

在 WSL 2 模式下，请在 [WSL 2 utility VM](https://docs.microsoft.com/en-us/windows/wsl/wsl-config#configure-global-options-with-wslconfig) 上配置内存、CPU 和 swap 限制。

> [!TIP]
>
> 如果您感觉 Docker Desktop 开始变慢，或者正在运行多容器工作负载，请增加内存和磁盘镜像空间分配。

### File sharing（文件共享）

使用 **File sharing** 允许将您机器上的本地目录与 Linux 容器共享。这在主机上使用 IDE 编辑源代码，同时在容器中运行和测试代码时特别有用。

| Setting             | Description                               | Platform | Notes                                 |
| ------------------- | ----------------------------------------- | -------- | ------------------------------------- |
| **Synchronized file shares** | 快速灵活的主机到虚拟机文件共享，通过使用同步文件系统缓存增强绑定挂载性能。更多信息请参阅[同步文件共享（Synchronized file share）](/desktop/features/synchronized-file-sharing/)。 | Mac, Linux, Windows Hyper-V | 适用于 Pro、Team 和 Business 订阅。 |
| **Virtual file shares** | 将本地目录与 Linux 容器共享。默认情况下，`/Users`、`/Volumes`、`/private`、`/tmp` 和 `/var/folders` 目录是共享的。如果您的项目不在这些目录下，则必须将其添加到列表中，否则运行时可能会遇到 `Mounts denied` 或 `cannot start service` 错误。 | Mac, Linux, Windows Hyper-V | |

- 仅与容器共享您需要的目录。文件共享会带来开销，因为主机上文件的任何更改都需要通知 Linux 虚拟机。共享过多文件可能导致 CPU 负载过高和文件系统性能下降。
- 共享文件夹旨在允许在主机上编辑应用程序代码，同时在容器中执行代码。对于非代码项目（如缓存目录或数据库），如果它们存储在 Linux 虚拟机中（使用[数据卷（data volume）](/engine/storage/volumes/)（命名卷）或[数据容器（data container）](/engine/storage/volumes/)），性能会好得多。
- 如果您将整个主目录共享到容器中，Mac 可能会提示您授予 Docker 访问主目录中个人区域（如提醒事项或下载）的权限。
- 默认情况下，Mac 文件系统不区分大小写，而 Linux 区分大小写。在 Linux 上，可以创建两个不同的文件：`test` 和 `Test`，而在 Mac 上，这些文件名实际上指向同一个底层文件。这可能导致应用程序在开发人员机器（文件内容共享）上正常工作，但在生产环境 Linux（文件内容不同）中失败。为避免此问题，Docker Desktop 要求所有共享文件按其原始大小写访问。因此，如果创建了一个名为 `test` 的文件，则必须作为 `test` 打开。尝试打开 `Test` 将失败，并显示错误“No such file or directory”。类似地，一旦创建了名为 `test` 的文件，尝试创建第二个名为 `Test` 的文件将失败。

更多信息请参阅[卷挂载需要对 `/Users` 之外的任何项目目录进行文件共享](/desktop/troubleshoot-and-support/troubleshoot/topics/)。

### Proxies（代理）

Docker Desktop 支持 HTTP/HTTPS 和 SOCKS5 代理。SOCKS5 需要 Business 订阅。

为防止开发人员意外更改代理设置，请参阅[设置管理（Settings Management）](/enterprise/security/hardened-desktop/settings-management/#what-features-can-i-configure-with-settings-management)。

#### Docker Desktop proxy（Docker Desktop 代理）

用于登录 Docker、拉取和推送镜像、在镜像构建期间获取工件以及报告错误诊断。

| Proxy mode | Description |
|------------|-------------|
| **System proxy** | 使用主机上配置的代理（静态或代理自动配置 PAC）。Docker Desktop 会自动读取。 |
| **No proxy** | 直接连接，不使用代理。 |
| **Manual configuration** | 手动输入 **Web Server (HTTP)** 和 **Secure Web Server (HTTPS)** URL。使用格式 `http://proxy:port` 或 `https://proxy:port`。您还可以指定应绕过代理的主机和域，例如：`registry-1.docker.com,*.docker.com,10.0.0.0/8`。 |

> [!NOTE]
>
> 如果您使用托管在 Web 服务器上的 PAC 文件，请为 `.pac` 扩展添加 MIME 类型 `application/x-ns-proxy-autoconfig`。否则，PAC 文件可能无法正确解析。请参阅[加固型 Docker Desktop（Hardened Docker Desktop）](/enterprise/security/hardened-desktop/air-gapped-containers/#proxy-auto-configuration-files)。

#### Containers proxy（容器代理）

用于来自运行中容器的出站流量。

| Proxy mode | Description |
|------------|-------------|
| **Same as host proxy** | 使用与 Docker Desktop 代理相同的代理配置。 |
| **System proxy** | 使用主机上配置的代理。 |
| **No proxy** | 直接连接，不使用代理。 |
| **Manual configuration** | 手动输入 **Web Server (HTTP)** 和 **Secure Web Server (HTTPS)** URL。使用格式 `http://proxy:port` 或 `https://proxy:port`。您还可以指定应绕过代理的主机和域，例如：`registry-1.docker.com,*.docker.com,10.0.0.0/8`。 |

> [!NOTE]
>
> 用于镜像扫描的 HTTPS 代理使用 `HTTPS_PROXY` 环境变量进行配置。

#### Proxy authentication（代理身份验证）

| Method |  Behavior | Notes |
|--------|-----------| ----- |
| **Basic** | Docker Desktop 提示输入凭据并将其缓存在操作系统凭据存储中。 | 使用 `https://` 代理 URL 可保护传输中的密码。支持 TLS 1.3。 |
| **Kerberos / NTLM** | 集中身份验证——不会提示开发人员输入凭据，从而降低账户被锁定的风险。如果代理在 407 响应中返回多个方案，Docker Desktop 默认使用 Basic。 | 需要 Business 订阅。要启用 Kerberos 或 NTLM 代理身份验证，您必须在安装期间通过命令行传递 `--proxy-enable-kerberosntlm` 安装程序标志，并确保您的代理服务器已正确配置 Kerberos 或 NTLM 身份验证。 |

### Network（网络）

> [!NOTE]
>
> 在 Windows 上，**Network** 选项卡在 Windows 容器模式下不可用，因为 Windows 管理网络。

| Setting | Description | Platform |
|---------|-------------|----------|
| **Docker subnet** | 设置自定义子网以避免与环境中的 IP 冲突。Docker Desktop 为内部服务（包括 DNS 服务器和 HTTP 代理）使用专用 IPv4 网络。默认值：`192.168.65.0/24`。 | All |
| **Use kernel networking for UDP** | 为 UDP 流量使用更高效的内核网络路径。可能与 VPN 软件不兼容。 | Mac |
| **Enable host networking** | 允许使用 `--net=host` 启动的容器使用 `localhost` 连接到主机上的 TCP 和 UDP 服务。同时允许主机上的软件使用 `localhost` 连接到容器中的 TCP 和 UDP 服务。 | Mac |

在 Windows 和 Mac 上，您还可以设置默认网络模式和 DNS 解析行为。更多信息请参阅[网络（Networking）](/desktop/features/networking/networking-how-tos/#network-how-tos-for-mac-and-windows)。

### WSL integration（仅限 Windows）

| Setting             | Description                               | Notes                               |
| ------------------- | ----------------------------------------- | ------------------------------------- |
| WSL distribution integration| 选择哪些 WSL 2 发行版启用了 Docker WSL 集成。 | 默认情况下，集成在您的默认 WSL 发行版上启用。要更改默认发行版，请运行 `wsl --set-default <distribution name>`。 |

有关配置 Docker Desktop 以使用 WSL 2 的更多详细信息，请参阅 [Docker Desktop WSL 2 backend](/desktop/features/wsl/)。

## Docker Engine（Docker 引擎）

使用 JSON 配置文件配置 Docker 守护进程（daemon）。

该文件位于 `$HOME/.docker/daemon.json`。您可以直接在 Docker Desktop Dashboard 中或使用文本编辑器进行编辑。

要查看完整的可用配置选项列表，请参阅 [dockerd 命令参考](/reference/cli/dockerd/)。

## Builders（构建器）

使用 **Builders** 选项卡在 Docker Desktop 设置中检查和管理构建器。

### Inspect（检查）

要检查构建器，请找到您要检查的构建器并展开。您只能检查活动构建器。

检查活动构建器会显示：

- BuildKit 版本
- 状态（Status）
- 驱动类型（Driver type）
- 支持的能力和平台（Supported capabilities and platforms）
- 磁盘使用情况（Disk usage）
- 端点地址（Endpoint address）

### Select a different builder（选择不同的构建器）

**Selected builder** 部分显示当前选中的构建器。
要选择其他构建器：

1. 在 **Available builders** 下找到您要使用的构建器
2. 打开构建器名称旁边的下拉菜单。
3. 选择 **Use** 切换到该构建器。

现在，您的构建命令将默认使用所选构建器。

### Create a builder（创建构建器）

要创建构建器，请使用 Docker CLI。请参阅[创建新构建器（Create a new builder）](/build/builders/manage/#create-a-new-builder)

### Remove a builder（移除构建器）

如果满足以下条件，您可以移除构建器：

- 该构建器不是您的[所选构建器（selected builder）](/build/builders/#selected-builder)
- 该构建器未[与 Docker 上下文关联（associated with a Docker context）](/build/builders/#default-builder)。

要移除与 Docker 上下文关联的构建器，请使用 `docker context rm` 命令移除上下文。

要移除构建器：

1. 在 **Available builders** 下找到您要移除的构建器
2. 打开下拉菜单。
3. 选择 **Remove** 以移除此构建器。

如果构建器使用 `docker-container` 或 `kubernetes` 驱动，构建缓存将与构建器一起被移除。

### Stop and start a builder（停止和启动构建器）

使用 [`docker-container` driver](/build/builders/drivers/docker-container/) 的构建器在容器中运行 BuildKit 守护进程。您可以使用下拉菜单启动和停止 BuildKit 容器。

如果容器已停止，运行构建会自动启动它。

您只能使用 `docker-container` 驱动来启动和停止构建器。

## AI（人工智能）

从 **AI** 选项卡，您可以配置以下功能的设置：

- [Gordon](/ai/gordon/)，一个 AI 驱动的助手，可对您的 Docker 工作流采取行动。
- [Docker Model Runner](/ai/model-runner/)，它简化了使用 Docker 管理、运行和部署 AI 模型的过程。

## Kubernetes

> [!NOTE]
>
> 在 Windows 上，**Kubernetes** 选项卡在 Windows 容器模式下不可用。

启用并配置内置的独立 Kubernetes 集群，用于测试容器部署。

| Setting             | Description                               |
| ------------------- | ----------------------------------------- |
| **Enable Kubernetes** | 安装并运行一个独立的 Kubernetes 服务器作为 Docker 容器，用于测试部署。 |
| **Cluster provisioning method** | 选择 **Kubeadm**（由 Docker Desktop 设置版本的单节点集群）或 **Kind**（您可以设置版本和节点数的多节点集群）。 |
| **Show system containers (advanced)** | 在使用 Docker 命令时显示内部容器。 |
| **Reset Kubernetes cluster** | 删除所有 stacks 和 Kubernetes 资源。 |

有关将 Kubernetes 集成与 Docker Desktop 一起使用的更多信息，请参阅[探索 Kubernetes 视图（Explore the Kubernetes view）](/desktop/use-desktop/kubernetes/)。

## Software updates（软件更新）

管理 Docker Desktop 检查及下载更新的方式和时间。

| Setting                             | Description                                                                | Default  |
| ----------------------------------- | -------------------------------------------------------------------------- | -------- |
| **Automatically check for updates** | 在 Docker 菜单和 Dashboard 底部通知您有可用更新。                                         | Enabled  |
| **Always download updates**         | 自动在后台下载新版本的 Docker Desktop。                                                | Disabled |
| **Automatically update components** | 独立更新 Docker Desktop 组件（如 Docker Compose、Docker Scout 和 Docker CLI），无需完全重启。 | Enabled  |

## Extensions（扩展）

启用 Docker Extensions 并控制哪些扩展可供安装和运行。

| Setting                                                              | Description                   |
| -------------------------------------------------------------------- | ----------------------------- |
| **Enable Docker Extensions**                                         | 打开或关闭 Docker Extensions。默认关闭。 |
| **Allow only extensions distributed through the Docker Marketplace** | 仅允许来自 Marketplace 批准的来源的扩展。   |
| **Show Docker Extensions system containers**                         | 显示 Docker Extensions 使用的容器。   |

有关 Docker 扩展的更多信息，请参阅 [Docker Extensions](/extensions/)。

## Beta features（Beta 功能）

Beta 功能允许访问未来的产品功能。这些功能仅用于测试和反馈，因为它们可能在版本之间无警告地更改，或在未来版本中完全移除。Beta 功能不得在生产环境中使用。Docker 不为 Beta 功能提供支持。

您还可以从 **Beta features** 选项卡注册[开发者预览计划（Developer Preview program）](https://www.docker.com/community/get-involved/developer-preview/)。

有关 Docker CLI 中当前实验性功能的列表，请参阅 [Docker CLI Experimental features](https://github.com/docker/cli/blob/master/experimental/README.md)。

## Notifications（通知）

选择您希望接收的 Docker Desktop 通知类型。

| Notification type | Default|
| ----------------- | ------ |
| Status updates on tasks and processes | Enabled |
| Recommendations from Docker | Enabled |
| Docker announcements | Enabled |
| Docker surveys | Enabled |
| Error notifications | Always Enabled（不可更改） |
| New releases | Always Enabled（不可更改） |

通知会短暂出现在 Docker Desktop Dashboard 的右下角，然后移动到 **Notifications** 抽屉，可从 Dashboard 右上角访问。

## Advanced（仅限 Mac）

重新配置初始安装期间设置的 CLI 工具安装路径和特权系统权限。

| Setting                                        | Description                                                                                                                                                | Notes                                                                                                         |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| CLI tools installation — **System**            | 将 Docker CLI 工具安装到 `/usr/local/bin`。                                                                                                                       |                                                                                                               |
| CLI tools installation — **User**              | 将 Docker CLI 工具安装到 `$HOME/.docker/bin`                                                                                                                     | 通过将 `export PATH=$PATH:~/.docker/bin` 追加到 `~/.bashrc` 或 `~/.zshrc`，然后重启 shell，将 `$HOME/.docker/bin` 添加到 PATH。 |
| **Allow the default Docker socket to be used** | 创建 `/var/run/docker.sock`，某些第三方客户端可能使用它与 Docker Desktop 通信。更多信息请参阅 [macOS 的权限要求](/desktop/setup/install/mac-permission-requirements/#installing-symlinks)。 | 需要密码                                                                                                          |
| **Allow privileged port mapping**              | 启动特权辅助进程，绑定 1 到 1024 之间的端口。更多信息请参阅 [macOS 的权限要求](/desktop/setup/install/mac-permission-requirements/#binding-privileged-ports)。                            | 需要密码                                                                                                          |

## Docker Offload

启用 Docker Offload 并配置基于云的工作负载的空闲超时和 GPU 支持。

| Setting             | Description                               | Notes                                 |
| ------------------- | ----------------------------------------- | ------------------------------------- |
| **Enable Docker Offload** | 在云中运行您的容器。  | 需要登录和 Offload 订阅 |
| **Idle timeout** | 设置从无活动到 Docker Offload 进入空闲模式之间的持续时间。有关空闲超时的详细信息，请参阅[活动与空闲状态（Active and idle states）](/offload/configuration/#understand-active-and-idle-states)。 | |
| **Enable GPU support** | 让您的工作负载使用云 GPU（如果可用）。 | |