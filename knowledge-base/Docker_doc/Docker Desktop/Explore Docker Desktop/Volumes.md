# 在 Docker Desktop 中探索 **Volumes** 视图

Docker Desktop 中的 **Volumes** 视图允许您创建（Create）、检查（Inspect）、删除（Delete）、克隆（Clone）、清空（Empty）、导出（Export）和导入（Import）[Docker 卷](/engine/storage/volumes/)。您还可以浏览卷中的文件和文件夹，并查看哪些容器正在使用它们。

## 查看您的卷

您可以查看有关卷的以下信息：

- **Name**：卷的名称。
- **Status**：卷是否正在被容器使用。
- **Created**：卷创建了多久。
- **Size**：卷的大小。
- **Scheduled exports**：是否启用了计划导出。

默认情况下，**Volumes** 视图显示所有卷的列表。

您可以通过以下方式过滤（Filter）和排序（Sort）卷，以及修改显示的列：

- 按名称过滤卷：使用 **Search** 字段。
- 按状态过滤卷：在搜索栏右侧，按 **In use**（使用中）或 **Unused**（未使用）过滤卷。
- 排序卷：选择列名称以对卷进行排序。
- 自定义列：在搜索栏右侧，选择要显示的卷信息。

## 创建卷

您可以按照以下步骤创建一个空卷。或者，如果您使用尚不存在的卷启动容器，Docker 会自动为您创建该卷。

要创建卷：

1. 在 **Volumes** 视图中，选择 **Create** 按钮。
2. 在 **New Volume** 模态框中，指定卷名称，然后选择 **Create**。

要将该卷与容器一起使用，请参阅使用卷。

## 检查卷

要探索特定卷的详细信息，请从列表中选择一个卷。这将打开详细视图。

**Container in-use** 选项卡显示使用该卷的容器名称、镜像名称、容器使用的端口号以及目标（Target）。目标（Target）是容器内部的一个路径，用于访问卷中的文件。

**Stored data** 选项卡显示卷中的文件和文件夹以及文件大小。要保存文件或文件夹，请右键单击文件或文件夹以显示选项菜单，选择 **Save as...**，然后指定下载文件的位置。

要删除卷中的文件或文件夹，请右键单击文件或文件夹以显示选项菜单，选择 **Delete**，然后再次选择 **Delete** 进行确认。

**Exports** 选项卡允许您导出卷。

## 克隆卷

克隆（Clone）卷会创建一个新卷，其中包含被克隆卷中所有数据的副本。当克隆一个正在被一个或多个正在运行的容器使用的卷时，Docker 会暂时停止这些容器，克隆数据，然后在克隆过程完成后重新启动它们。

要克隆卷：

1. 登录 Docker Desktop。您必须登录才能克隆卷。
2. 在 **Volumes** 视图中，为您要克隆的卷点击 **Actions** 列中的 **Clone** 图标。
3. 在 **Clone a volume** 模态框中，指定 **Volume name**，然后选择 **Clone**。

## 删除一个或多个卷

删除卷会删除该卷及其所有数据。当容器正在使用某个卷时，即使该容器已停止，您也无法删除该卷。您必须先停止并移除所有使用该卷的容器，然后才能删除该卷。

要删除一个卷：

1. 在 **Volumes** 视图中，为您要删除的卷点击 **Actions** 列中的 **Delete** 图标。
2. 在 **Delete volume?** 模态框中，选择 **Delete forever**。

要删除多个卷：

1. 在 **Volumes** 视图中，选中要删除的所有卷旁边的复选框。
2. 选择 **Delete**。
3. 在 **Delete volumes?** 模态框中，选择 **Delete forever**。

## 清空卷

清空（Empty）卷会删除卷的所有数据，但不会删除卷本身。当清空一个正在被一个或多个正在运行的容器使用的卷时，Docker 会暂时停止这些容器，清空数据，然后在清空过程完成后重新启动它们。

要清空卷：

1. 登录 Docker Desktop。您必须登录才能清空卷。
2. 在 **Volumes** 视图中，选择要清空的卷。
3. 在 **Import** 旁边，选择 **More volume actions** 图标，然后选择 **Empty volume**。
4. 在 **Empty a volume?** 模态框中，选择 **Empty**。

## 导出卷

您可以将卷的内容导出到本地文件（Local file）、本地镜像（Local image）、Docker Hub 中的镜像，或受支持的云提供商（Cloud provider）。当从正在被一个或多个正在运行的容器使用的卷中导出内容时，Docker 会暂时停止这些容器，导出内容，然后在导出过程完成后重新启动它们。

您可以立即导出卷，也可以计划定期导出。

### 立即导出卷

1. 登录 Docker Desktop。您必须登录才能导出卷。
2. 在 **Volumes** 视图中，选择要导出的卷。
3. 选择 **Exports** 选项卡。
4. 选择 **Quick export**。
5. 选择是将卷导出到 **Local or Hub storage**（本地或 Hub 存储）还是 **External cloud storage**（外部云存储），然后根据您的选择指定以下附加详细信息。

   **Local or Hub storage**

   - **Local file**：指定文件名并选择一个文件夹。
   - **Local image**：选择要将内容导出到的本地镜像。镜像中的任何现有数据都将被导出的内容替换。
   - **New image**：为新镜像指定一个名称。
   - **Registry**：指定一个 Docker Hub 仓库。

   **External cloud storage**

   要导出到外部云提供商，您必须拥有 Docker Business 订阅。

   选择您的云提供商，然后指定要上传到的存储 URL。请参考以下云提供商文档，了解如何获取 URL。

   - Amazon Web Services：[使用 AWS SDK 创建 Amazon S3 的预签名 URL](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example_s3_Scenario_PresignedUrl_section.html)
   - Microsoft Azure：[生成 SAS 令牌和 URL](https://learn.microsoft.com/en-us/azure/data-explorer/kusto/api/connection-strings/generate-sas-token)
   - Google Cloud：[创建用于上传对象的签名 URL](https://cloud.google.com/storage/docs/access-control/signing-urls-with-helpers#upload-object)

6. 选择 **Save**。

### 计划卷导出

1. 登录 Docker Desktop。您必须登录并拥有付费的 Docker 订阅才能计划卷导出。
2. 在 **Volumes** 视图中，选择要导出的卷。
3. 选择 **Exports** 选项卡。
4. 选择 **Schedule export**。
5. 在 **Recurrence**（重复频率）中，选择导出的发生频率，然后根据您的选择指定以下附加详细信息：

   - **Daily**：指定每天备份发生的时间。
   - **Weekly**：指定一周中的一天或多天，以及每周备份发生的时间。
   - **Monthly**：指定每月的第几天以及每月备份发生的时间。

6. 选择是将卷导出到 **Local or Hub storage** 还是 **External cloud storage**，然后根据您的选择指定以下附加详细信息。

   **Local or Hub storage**

   - **Local file**：指定文件名并选择一个文件夹。
   - **Local image**：选择要将内容导出到的本地镜像。镜像中的任何现有数据都将被导出的内容替换。
   - **New image**：为新镜像指定一个名称。
   - **Registry**：指定一个 Docker Hub 仓库。

   **External cloud storage**

   要导出到外部云提供商，您必须拥有 [Docker Business 订阅](https://www.docker.com/pricing?ref=Docs&refAction=DocsDesktopVolumes)。

   选择您的云提供商，然后指定要上传到的存储 URL。请参考以下云提供商文档，了解如何获取 URL。

   - Amazon Web Services：[使用 AWS SDK 创建 Amazon S3 的预签名 URL](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example_s3_Scenario_PresignedUrl_section.html)
   - Microsoft Azure：[生成 SAS 令牌和 URL](https://learn.microsoft.com/en-us/azure/data-explorer/kusto/api/connection-strings/generate-sas-token)
   - Google Cloud：[创建用于上传对象的签名 URL](https://cloud.google.com/storage/docs/access-control/signing-urls-with-helpers#upload-object)

7. 选择 **Save**。

## 导入卷

您可以导入本地文件（Local file）、本地镜像（Local image）或来自 Docker Hub 的镜像。卷中的任何现有数据都将被导入的内容替换。当将内容导入到正在被一个或多个正在运行的容器使用的卷时，Docker 会暂时停止这些容器，导入内容，然后在导入过程完成后重新启动它们。

要导入卷：

1. 登录 Docker Desktop。您必须登录才能导入卷。
2. 可选地，[创建](#create-a-volume)一个新卷以将内容导入其中。
3. 选择要导入内容的卷。
4. 选择 **Import**。
5. 选择内容的来源，然后根据您的选择指定以下附加详细信息：

   - **Local file**：选择包含内容的文件。
   - **Local image**：选择包含内容的本地镜像。
   - **Registry**：指定包含内容的 Docker Hub 镜像。

6. 选择 **Import**。

## 附加资源

- [持久化容器数据](/get-started/docker-concepts/running-containers/persisting-container-data/)
- [使用卷](/engine/storage/volumes/)