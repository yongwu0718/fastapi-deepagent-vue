# 在 Docker Desktop 中探索 **Images** 视图

**Images** 视图会显示您的 Docker 镜像列表，并允许您将镜像作为容器运行、从 Docker Hub 拉取最新版本的镜像以及检查镜像。它还会显示镜像漏洞的摘要信息。此外，**Images** 视图还包含清理选项，可以从磁盘中移除不需要的镜像以释放空间。如果您已登录，还可以查看您和您的组织在 Docker Hub 上共享的镜像。更多信息，请参阅探索您的镜像。

**Images** 视图让您无需使用 CLI 即可管理 Docker 镜像。默认情况下，它会显示您本地磁盘上所有 Docker 镜像的列表。

登录 Docker Hub 后，您还可以查看 Hub 镜像。这使您能够与团队协作，并直接通过 Docker Desktop 管理您的镜像。

通过 **Images** 视图，您可以执行核心操作，例如将镜像作为容器运行（Run）、从 Docker Hub 拉取（Pull）最新版本的镜像、将镜像推送到 Docker Hub（Push）以及检查（Inspect）镜像。

它还会显示镜像的元数据，例如：
- 标签（Tag）
- 镜像 ID（Image ID）
- 创建日期（Date created）
- 镜像大小（Size of the image）

**In Use** 标签会显示在正在运行或已停止的容器所使用的镜像旁边。您可以通过选择搜索栏右侧的 **More options** 菜单，然后根据偏好使用切换开关，来选择要显示的信息。

**Images on disk** 状态栏会显示镜像数量、这些镜像占用的总磁盘空间，以及该信息上次刷新的时间。

## 管理您的镜像

使用 **Search** 字段搜索特定镜像。

您可以按以下方式对镜像进行排序：
- In use（使用中）
- Unused（未使用）
- Dangling（悬挂）

## 将镜像作为容器运行

在 **Images view** 中，将鼠标悬停在一个镜像上，然后选择 **Run**。

在提示时，您可以：
- 选择 **Optional settings** 下拉菜单来指定名称、端口、卷、环境变量，然后选择 **Run**
- 直接选择 **Run**，不指定任何可选设置。

## 检查镜像

要检查镜像，请选择该镜像所在的行。检查镜像会显示有关该镜像的详细信息，例如：
- 镜像历史（Image history）
- 镜像 ID（Image ID）
- 镜像创建日期
- 镜像大小
- 构成镜像的层（Layers）
- 使用的基础镜像（Base images）
- 发现的漏洞（Vulnerabilities）
- 镜像内的软件包（Packages）

Docker Scout 提供这些漏洞信息。
有关该视图的更多信息，请参阅镜像详细信息视图。

## 从 Docker Hub 拉取最新镜像

从列表中选择镜像，选择 **More options** 按钮，然后选择 **Pull**。

> [!NOTE]
>
> 必须先在 Docker Hub 上存在该仓库，才能拉取镜像的最新版本。您必须登录才能拉取私有镜像。

## 将镜像推送到 Docker Hub

从列表中选择镜像，选择 **More options** 按钮，然后选择 **Push to Hub**。

> [!NOTE]
>
> 只有当镜像属于您的 Docker ID 或您的组织时，才能将其推送到 Docker Hub。也就是说，镜像的标签中必须包含正确的用户名/组织名称，才能推送到 Docker Hub。

## 移除镜像

> [!NOTE]
>
> 要移除正在运行或已停止容器所使用的镜像，您必须首先移除关联的容器。

未使用的镜像（Unused image）是指未被任何正在运行或已停止容器使用的镜像。当您用相同的标签构建镜像的新版本时，旧镜像会变为悬挂镜像（Dangling image）。

要移除单个镜像，请选择垃圾桶图标。

## Docker Hub 仓库

**Images** 视图还允许您管理和交互 Docker Hub 仓库中的镜像。
默认情况下，当您转到 Docker Desktop 中的 **Images** 时，您会看到本地镜像存储中的镜像列表。
顶部的 **Local** 和 **Docker Hub repositories** 选项卡可在查看本地镜像存储中的镜像和查看您有权访问的远程 Docker Hub 仓库中的镜像之间切换。

切换到 **Docker Hub repositories** 选项卡会提示您登录 Docker Hub 账户（如果尚未登录）。
登录后，它会显示您有权访问的 Docker Hub 组织和仓库中的镜像列表。

从下拉菜单中选择一个组织，以查看该组织的仓库列表。

如果您已在仓库上启用 [Docker Scout](/scout/)，则镜像标签旁边会显示镜像分析结果（以及健康评分（health scores），如果您的 Docker 组织有资格的话）。

将鼠标悬停在镜像标签上会显示两个选项：
- **Pull**：从 Docker Hub 拉取镜像的最新版本。
- **View in Hub**：打开 Docker Hub 页面并显示有关镜像的详细信息。

## 附加资源

- [什么是镜像？](/get-started/docker-concepts/the-basics/what-is-an-image/)