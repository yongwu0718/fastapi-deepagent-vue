# Settings and feedback for Docker Extensions

## Settings

### 开启或关闭 extensions

Docker Extensions 默认是关闭的。要更改您的设置：

1. 导航到 **Settings**。
2. 选择 **Extensions** 选项卡。
3. 在 **Enable Docker Extensions** 旁边，选中或清除复选框以设置您所需的状态。
4. 在右下角，选择 **Apply**。

> [!NOTE]
>
> 如果您是[组织所有者（organization owner）](/admin/organization/manage/manage-a-team/#what-is-an-organization-owner)，可以为您的用户关闭 extensions。打开 `settings-store.json` 文件，并将 `"extensionsEnabled"` 设置为 `false`。
> `settings-store.json` 文件位于：
>   - Mac：`~/Library/Group Containers/group.com.docker/settings-store.json`
>   - Windows：`C:\Users\[USERNAME]\AppData\Roaming\Docker\settings-store.json`
>
> 这也可以通过 [Hardened Docker Desktop](/enterprise/security/hardened-desktop/) 完成。

### 开启或关闭不在 Marketplace 中的 extensions

您可以通过 Marketplace 或 Extensions SDK 工具安装 extensions。您可以选择只允许已发布的 extensions。这些是已经过审查并在 Extensions Marketplace 中发布的 extensions。

1. 导航到 **Settings**。
2. 选择 **Extensions** 选项卡。
3. 在 **Allow only extensions distributed through the Docker Marketplace** 旁边，选中或清除复选框以设置您所需的状态。
4. 在右下角，选择 **Apply**。

### 查看 extensions 创建的 containers

默认情况下，extensions 创建的 containers 会从 Docker Desktop Dashboard 和 Docker CLI 的容器列表中隐藏。要使它们可见，请更新您的设置：

1. 导航到 **Settings**。
2. 选择 **Extensions** 选项卡。
3. 在 **Show Docker Extensions system containers** 旁边，选中或清除复选框以设置您所需的状态。
4. 在右下角，选择 **Apply**。

> [!NOTE]
>
> 启用 extensions 本身不会消耗计算机资源（CPU / 内存）。
>
> 特定的 extensions 可能会消耗计算机资源，具体取决于每个 extension 的功能和实现，但启用 extensions 没有预留资源或使用成本。

## Submit feedback

您可以通过专门的 Slack 频道或 GitHub 向 extension 作者提供反馈。要提交关于特定 extension 的反馈：

1. 导航到 Docker Desktop Dashboard 并选择 **Manage** 选项卡。
   这将显示您已安装的 extensions 列表。
2. 选择您要提供反馈的 extension。
3. 滚动到 extension 描述底部，根据 extension 的情况，选择：
    - Support
    - Slack
    - Issues。您将被发送到 Docker Desktop 外部的页面以提交反馈。

如果某个 extension 没有提供反馈方式，请联系我们，我们将为您转达反馈。要提供反馈，请选择 **Extensions Marketplace** 右侧的 **Give feedback**。