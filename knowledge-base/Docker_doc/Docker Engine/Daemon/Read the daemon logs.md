# 读取守护进程日志（Read the daemon logs）

守护进程日志有助于诊断问题。根据操作系统配置和日志记录子系统的不同，日志可能保存在以下几个位置之一：

| 操作系统                     | 位置                                                                                                                                 |
| :--------------------------- | :----------------------------------------------------------------------------------------------------------------------------------- |
| Linux                        | 使用命令 `journalctl -xu docker.service`（或根据您的 Linux 发行版读取 `/var/log/syslog` 或 `/var/log/messages`） |
| macOS（Docker Desktop）       | `~/Library/Containers/com.docker.docker/Data/log/vm/init.log`                                                                            |
| Windows（WSL2）               | `%LOCALAPPDATA%\Docker\log\vm\init.log`                                                                                                  |
| Windows（Windows 容器） | 日志位于 Windows 事件日志中                                                                                                        |

在 macOS 和 Windows（WSL2）上，Docker Desktop 将守护进程日志（`dockerd`、`containerd` 和其他 VM 服务）写入一个多路复用的 `init.log` 文件（JSON 格式）。每一行包含一个 `"component"` 字段，用于标识服务。要跟踪日志，打开终端并使用带有 `-f` 标志的 `tail` 命令。日志会持续打印，直到你使用 `CTRL+c` 终止命令：

```console
$ tail -f ~/Library/Containers/com.docker.docker/Data/log/vm/init.log
{"component":"dockerd","level":"debug","msg":"attach: stdout: begin","time":"2021-07-28T10:21:21.497642089Z"}
{"component":"dockerd","level":"debug","msg":"attach: stderr: begin","time":"2021-07-28T10:21:21.497714291Z"}
...
^C
```

仅过滤 `dockerd` 输出：

```console
$ grep '"component":"dockerd"' ~/Library/Containers/com.docker.docker/Data/log/vm/init.log
```

## 启用调试（Enable debugging）

有两种启用调试的方法。推荐的方法是在 `daemon.json` 文件中将 `debug` 键设置为 `true`。此方法适用于所有 Docker 平台。

1. 编辑 `daemon.json` 文件，该文件通常位于 `/etc/docker/`。如果文件不存在，可能需要创建它。在 macOS 或 Windows 上，不要直接编辑该文件，而是通过 Docker Desktop 设置来编辑。

2. 如果文件为空，添加以下内容：

   ```json
   {
     "debug": true
   }
   ```

   如果文件中已包含 JSON，只需添加键 `"debug": true`，注意如果该行不是右括号之前的最后一行，则需要在行末添加逗号。同时验证如果设置了 `log-level` 键，它应设置为 `info` 或 `debug`。`info` 是默认值，可选值为 `debug`、`info`、`warn`、`error`、`fatal`。

3. 向守护进程发送 `HUP` 信号，使其重新加载配置。在 Linux 主机上，使用以下命令：

   ```console
   $ sudo kill -SIGHUP $(pidof dockerd)
   ```

   在 Windows 主机上，重启 Docker。

除了此过程，您也可以停止 Docker 守护进程并使用调试标志 `-D` 手动重启。但是，这可能导致 Docker 在不同于主机启动脚本创建的环境下重启，这可能会使调试更加困难。

## 强制记录堆栈跟踪（Force a stack trace to be logged）

如果守护进程无响应，可以通过向守护进程发送 `SIGUSR1` 信号来强制将完整的堆栈跟踪记录到日志中。

- **Linux**：

  ```console
  $ sudo kill -SIGUSR1 $(pidof dockerd)
  ```

- **Windows Server**：

  下载 [docker-signal](https://github.com/moby/docker-signal)。

  获取 dockerd 的进程 ID：`Get-Process dockerd`。

  使用标志 `--pid=<守护进程的 PID>` 运行可执行文件。

这会强制记录堆栈跟踪，但不会停止守护进程。守护进程日志会显示堆栈跟踪，或者如果堆栈跟踪记录到文件中，则显示包含堆栈跟踪的文件路径。

守护进程在处理 `SIGUSR1` 信号并将堆栈跟踪转储到日志后继续运行。堆栈跟踪可用于确定守护进程内所有 goroutine 和线程的状态。

## 查看堆栈跟踪（View stack traces）

可以通过以下方法之一查看 Docker 守护进程日志：

- 在 Linux 系统上使用 `systemctl` 运行 `journalctl -u docker.service`
- 在较旧的 Linux 系统上查看 `/var/log/messages`、`/var/log/daemon.log` 或 `/var/log/docker.log`

> [!NOTE]
>
> 在 Docker Desktop for Mac 或 Docker Desktop for Windows 上无法手动生成堆栈跟踪。但是，如果您遇到问题，可以单击 Docker 任务栏图标并选择 **Troubleshoot** 将信息发送给 Docker。

在 Docker 日志中查找类似以下内容的消息：

```text
...goroutine stacks written to /var/run/docker/goroutine-stacks-2017-06-02T193336z.log
```

Docker 保存这些堆栈跟踪和转储的位置取决于您的操作系统和配置。有时可以从堆栈跟踪和转储中直接获得有用的诊断信息。否则，您可以将此信息提供给 Docker 以帮助诊断问题。