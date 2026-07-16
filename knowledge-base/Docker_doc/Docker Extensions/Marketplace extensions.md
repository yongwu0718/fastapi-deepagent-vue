# Marketplace extensions

Marketplace 中有两种类型的扩展（extensions）：
- Docker 审查的扩展（Docker-reviewed extensions）
- 自行发布的扩展（Self-published extensions）

Docker 审查的扩展由 Docker Extensions 团队手动审查，以确保额外的信任和质量。它们在 Marketplace 中显示为 **Reviewed**。

自行发布的扩展由扩展开发者自主发布，并经过自动化验证流程。它们在 Marketplace 中显示为 **Not reviewed**。

> [!IMPORTANT]
>
> Marketplace 中的扩展由 Docker 审查，但并未经过完整的安全审计。扩展以主机级权限运行。它们可以安装二进制文件、访问 Docker Engine、调用命令以及访问您机器上的文件。请仅从您信任的发布者安装扩展。

## 安装扩展（Install an extension）

> [!NOTE]
>
> 对于某些扩展，在使用前需要单独创建一个账户。

要安装扩展：

1. 打开 Docker Desktop。
2. 在 Docker Desktop Dashboard 中，选择 **Extensions** 选项卡。
   Extensions Marketplace 会在 **Browse** 选项卡中打开。
3. 浏览可用的扩展。
   您可以按 **Recently added**、**Most installed** 或字母顺序对扩展列表进行排序。或者，使用 **Content** 或 **Categories** 下拉菜单按扩展是否已被审查或按类别进行搜索。
4. 选择一个扩展，然后选择 **Install**。

在此之后，您可以选择 **Open** 来访问该扩展，或安装其他扩展。该扩展也会出现在左侧菜单和 **Manage** 选项卡中。

## 更新扩展（Update an extension）

您可以在 Docker Desktop 版本之外更新任何扩展。要将扩展更新到最新版本，请导航到 Docker Desktop Dashboard 并选择 **Manage** 选项卡。

**Manage** 选项卡会显示您已安装的所有扩展。如果某个扩展有新版本可用，它会显示一个 **Update** 按钮。

## 卸载扩展（Uninstall an extension）

您可以随时卸载扩展。

> [!NOTE]
>
> 扩展使用并存储在 volume 中的任何数据都必须手动删除。

1. 导航到 Docker Desktop Dashboard 并选择 **Manage** 选项卡。
   这将显示您已安装的扩展列表。
2. 选择要卸载的扩展右侧的省略号（ellipsis）。
3. 选择 **Uninstall**。