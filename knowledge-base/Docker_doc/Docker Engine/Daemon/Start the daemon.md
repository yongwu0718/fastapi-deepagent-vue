# Start the daemon（启动守护进程）

本页介绍如何手动或使用操作系统工具启动守护进程（daemon）。

## 使用操作系统工具启动守护进程（Start the daemon using operating system utilities）

在典型安装中，Docker 守护进程由系统工具启动，而非用户手动启动。这使得在机器重启时自动启动 Docker 更加容易。

启动 Docker 的命令取决于你的操作系统。请查阅[安装 Docker](/engine/install/) 下的相应页面。

### 使用 systemd 启动（Start with systemd）

在某些操作系统上（如 Ubuntu 和 Debian），Docker 守护进程服务会自动启动。使用以下命令手动启动它：

```console
$ sudo systemctl start docker
```

如果你希望 Docker 在启动时自动运行，请参阅[配置 Docker 在启动时启动](/engine/install/linux-postinstall/#configure-docker-to-start-on-boot-with-systemd)。

## 手动启动守护进程（Start the daemon manually）

如果你不想使用系统工具来管理 Docker 守护进程，或者只是想测试一下，你可以直接使用 `dockerd` 命令手动运行它。根据你的操作系统配置，你可能需要使用 `sudo`。

当你以这种方式启动 Docker 时，它会在前台运行，并将其日志直接发送到你的终端。

```console
$ dockerd

INFO[0000] +job init_networkdriver()
INFO[0000] +job serveapi(unix:///var/run/docker.sock)
INFO[0000] Listening for HTTP on unix (/var/run/docker.sock)
```

要停止你手动启动的 Docker，请在终端中按下 `Ctrl+C`。