# Docker Desktop 的 **Resource Saver** 模式

**Resource Saver** 模式通过在一段时间内没有容器运行时自动停止 Docker Desktop Linux 虚拟机，从而显著降低 Docker Desktop 在主机上的 CPU 和内存使用量（减少 2 GB 或更多）。默认时间设置为 5 分钟，但可以根据您的需求进行调整。

在 **Resource Saver** 模式下，Docker Desktop 在空闲时使用最少的系统资源，从而延长笔记本电脑的电池续航时间并改善多任务处理体验。

## 配置 **Resource Saver**

**Resource Saver** 默认启用，但可以通过导航到 **Settings** 中的 **Resources** 选项卡来禁用。您还可以按如下所示配置空闲计时器。

![Resource Saver Settings](/desktop/images/resource-saver-settings.webp) 

如果提供的数值无法满足您的需求，您可以通过修改 Docker Desktop 的 `settings-store.json` 文件（Docker Desktop 4.34 及更早版本为 `settings.json`）中的 `autoPauseTimeoutSeconds` 将其重新配置为任意值（只要该值大于 30 秒即可）：

  - Mac：`~/Library/Group Containers/group.com.docker/settings-store.json`
  - Windows：`C:\Users\[USERNAME]\AppData\Roaming\Docker\settings-store.json`
  - Linux：`~/.docker/desktop/settings-store.json`

重新配置后无需重启 Docker Desktop。

当 Docker Desktop 进入 **Resource Saver** 模式时：
- Docker Desktop 状态栏以及系统托盘中的 Docker 图标上会显示一个月亮图标。
- 不运行容器的 Docker 命令（例如列出容器镜像或卷）不一定触发退出 **Resource Saver** 模式，因为 Docker Desktop 可以在不必要地唤醒 Linux VM 的情况下提供此类命令服务。

> [!NOTE]
>
> Docker Desktop 会在需要时自动退出 **Resource Saver** 模式。
> 导致退出 **Resource Saver** 的命令执行时间稍长（约 3 到 10 秒），因为 Docker Desktop 需要重新启动 Linux VM。
> 在 Mac 和 Linux 上通常更快，在装有 Hyper-V 的 Windows 上较慢。
> Linux VM 重新启动后，后续容器运行将像往常一样立即执行。

## **Resource Saver** 模式与暂停（Pause）的对比

**Resource Saver** 的优先级高于较旧的 [Pause](/desktop/use-desktop/resource-saver/pause/) 功能，这意味着当 Docker Desktop 处于 **Resource Saver** 模式时，无法手动暂停 Docker Desktop（也没有意义，因为 **Resource Saver** 实际上停止了 Docker Desktop Linux VM）。通常，我们建议保持启用 **Resource Saver**，而不是禁用它并使用手动暂停功能，因为它可以带来更好的 CPU 和内存节省效果。

## Windows 上的 **Resource Saver** 模式

**Resource Saver** 在 Windows 上使用 WSL 时的工作方式略有不同。它不是停止 WSL 虚拟机，而只是暂停 `docker-desktop` WSL 发行版中的 Docker Engine。这是因为在 WSL 中，所有 WSL 发行版共享一个 Linux VM，因此 Docker Desktop 无法停止 Linux VM（即 WSL Linux VM 不属于 Docker Desktop）。因此，**Resource Saver** 可以降低 WSL 上的 CPU 利用率，但不会减少 Docker 的内存利用率。

为了减少 WSL 上的内存利用率，我们建议用户按照 [Docker Desktop WSL 文档](/desktop/features/wsl/)中的说明启用 WSL 的 `autoMemoryReclaim` 功能。最后，由于 Docker Desktop 不会在 WSL 上停止 Linux VM，因此退出 **Resource Saver** 模式是立即的（没有退出延迟）。