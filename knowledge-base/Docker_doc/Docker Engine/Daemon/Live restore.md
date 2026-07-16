# Live restore（实时恢复）

默认情况下，当 Docker 守护进程终止时，它会关闭正在运行的容器。你可以将守护进程配置为在守护进程不可用时让容器继续运行。此功能称为 **live restore**（实时恢复）。live restore 选项有助于减少因守护进程崩溃、计划性停机或升级而导致的容器停机时间。

> [!NOTE]
>
> Windows 容器不支持 live restore，但它适用于在 Docker Desktop for Windows 上运行的 Linux 容器。

## 启用 live restore

有两种方法可以启用 live restore 设置，以便在守护进程不可用时保持容器存活。**请仅执行以下操作之一**。

- 将配置添加到守护进程配置文件中。在 Linux 上，默认路径为 `/etc/docker/daemon.json`。在 Docker Desktop for Mac 或 Docker Desktop for Windows 上，从任务栏选择 Docker 图标，然后单击 **Settings** -> **Docker Engine**。

  - 使用以下 JSON 启用 `live-restore`。

    ```json
    {
      "live-restore": true
    }
    ```

  - 重启 Docker 守护进程。在 Linux 上，你可以通过重新加载 Docker 守护进程来避免重启（并避免容器的任何停机时间）。如果你使用 `systemd`，则使用命令 `systemctl reload docker`。否则，向 `dockerd` 进程发送 `SIGHUP` 信号。

- 如果你愿意，可以使用 `--live-restore` 标志手动启动 `dockerd` 进程。这种方法不推荐，因为它不会设置 `systemd` 或其他进程管理器在启动 Docker 进程时使用的环境。这可能导致意外行为。

## 升级期间的 live restore

Live restore 允许你在 Docker 守护进程更新期间让容器保持运行，但仅支持安装补丁版本（`YY.MM.x`）时，不支持主要版本（`YY.MM`）的守护进程升级。

如果在升级过程中跳过了版本，守护进程可能无法恢复与容器的连接。如果守护进程无法恢复连接，它就无法管理正在运行的容器，你必须手动停止它们。

## 重启时的 live restore

只有在守护进程选项（如 bridge IP 地址和 graph 驱动）没有改变的情况下，live restore 选项才能恢复容器。如果这些守护进程级别的配置选项有任何更改，live restore 可能无法工作，你可能需要手动停止容器。

## Live restore 对运行中容器的影响

如果守护进程长时间宕机，正在运行的容器可能会填满守护进程正常读取的 FIFO 日志。日志填满会阻止容器记录更多数据。默认缓冲区大小为 64K。如果缓冲区填满，你必须重启 Docker 守护进程以刷新它们。

在 Linux 上，你可以通过更改 `/proc/sys/fs/pipe-max-size` 来修改内核的缓冲区大小。在 Docker Desktop for Mac 或 Docker Desktop for Windows 上，你无法修改缓冲区大小。

## Live restore 与 Swarm 模式

live restore 选项仅适用于独立容器，不适用于 Swarm 服务。Swarm 服务由 Swarm 管理者管理。如果 Swarm 管理者不可用，Swarm 服务会继续在工作节点上运行，但无法进行管理，直到有足够多的 Swarm 管理者可用以维持法定人数。