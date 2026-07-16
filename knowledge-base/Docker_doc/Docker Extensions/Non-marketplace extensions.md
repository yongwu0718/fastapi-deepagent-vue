# 非 Marketplace 扩展

## 安装不在 Marketplace 中的扩展

> [!WARNING]
>
> 在 Marketplace 之外安装的扩展未经过 Docker 的审查流程。与所有 Docker 扩展一样，它们以主机级权限运行。它们可以安装二进制文件、访问 Docker Engine、调用命令以及访问您机器上的文件。仅在您信任发布者并已验证来源的情况下安装。

Extensions Marketplace 是从 Docker Desktop 内部安装扩展的可信且官方的位置。这些扩展已经过 Docker 的审查流程。然而，如果您信任扩展作者，也可以在 Docker Desktop 中安装其他扩展。

鉴于 Docker Extension 的性质（即一个 Docker image），您可以在其他地方找到用户发布其扩展源代码的位置。例如 GitHub、GitLab，甚至托管在 DockerHub 或 GHCR 等镜像 registry 中。您可以安装由社区开发的扩展，或者从同事那里安装您公司内部的扩展。您不仅限于从 Marketplace 安装扩展。

> [!NOTE]
>
> 请确保 **Allow only extensions distributed through the Docker Marketplace** 选项已禁用。否则，这将阻止任何未在 Marketplace 中列出的扩展（通过 Extension SDK 工具）被安装。
> 您可以在 **Settings** 中更改此选项。

要安装不在 Marketplace 中的扩展，您可以使用 Docker Desktop 自带的 Extensions CLI。

在终端中，键入 `docker extension install IMAGE[:TAG]` 通过其 image 引用（可选 tag）来安装扩展。使用 `-f` 或 `--force` 标志可避免交互式确认。

转到 Docker Desktop Dashboard 以查看已安装的新扩展。

## 列出已安装的扩展

无论扩展是从 Marketplace 安装还是通过 Extensions CLI 手动安装，您都可以使用 `docker extension ls` 命令来显示已安装扩展的列表。在输出中，您将看到扩展 ID、提供者、版本、标题以及它是否运行后端容器或已向主机部署二进制文件，例如：

```console
$ docker extension ls
ID                  PROVIDER            VERSION             UI                    VM                  HOST
john/my-extension   John                latest              1 tab(My-Extension)   Running(1)          -
```

转到 Docker Desktop Dashboard，选择 **Add Extensions** 并在 **Managed** 选项卡中查看已安装的新扩展。注意会显示一个 `UNPUBLISHED` 标签，表示该扩展并非从 Marketplace 安装。

## 更新扩展

要更新不在 Marketplace 中的扩展，请在终端中键入 `docker extension update IMAGE[:TAG]`，其中 `TAG` 应与已安装的扩展不同。

例如，如果您使用 `docker extension install john/my-extension:0.0.1` 安装了一个扩展，您可以通过运行 `docker extension update john/my-extension:0.0.2` 来更新它。转到 Docker Desktop Dashboard 以查看已更新的新扩展。

> [!NOTE]
>
> 非通过 Marketplace 安装的扩展不会从 Docker Desktop 接收更新通知。

## 卸载扩展

要卸载不在 Marketplace 中的扩展，您可以导航到 Marketplace 中的 **Managed** 选项卡并选择 **Uninstall** 按钮，或者从终端键入 `docker extension uninstall IMAGE[:TAG]`。