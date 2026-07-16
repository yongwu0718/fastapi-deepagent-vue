# 在 Docker Desktop 中探索 **Builds** 视图

Docker Desktop 中的 **Builds** 视图提供了一个交互式界面，用于直接在 Docker Desktop 中检查构建历史、监控活动构建以及管理构建器（builder）。

默认情况下，**Build history** 选项卡显示已完成构建的列表，按日期排序（最新的在前）。切换到 **Active builds** 选项卡可以查看正在进行的构建。

如果您通过 [Docker Build Cloud](/build-cloud/) 连接到云构建器（cloud builder），**Builds** 视图还会列出连接到同一云构建器的其他团队成员的任何活动或已完成云构建。

> [!NOTE]
>
> Windows 容器镜像构建使用的是旧版构建器（legacy builder），不会出现在 **Builds** 视图中。此处仅显示由 BuildKit 驱动的构建。

## 显示构建列表

从 Docker Dashboard 打开 **Builds** 视图可以访问：

- **Build history**：已完成构建，可访问日志、依赖项、跟踪信息等
- **Active builds**：当前正在进行的构建

仅列出来自活动、正在运行的构建器的构建。已移除或已停止的构建器的构建不会显示。

### 构建器设置（Builder settings）

右上角显示您当前选择的构建器名称，**Builder settings** 按钮允许您在 Docker Desktop 设置中管理构建器。

### 导入构建（Import builds）

**Import builds** 按钮允许您导入由其他人或在 CI 环境中执行的构建记录。导入构建记录后，您可以直接在 Docker Desktop 中完全访问该构建的日志、跟踪信息和其他数据。

`docker/build-push-action` 和 `docker/bake-action` GitHub Actions 的 构建摘要（build summary）包含一个用于下载构建记录的链接，以便使用 Docker Desktop 检查 CI 作业。

## 检查构建（Inspect builds）

要检查构建，请从列表中选择您想要查看的构建。检查视图包含多个选项卡。

**Info** 选项卡显示构建的详细信息。

如果您正在检查多平台构建（multi-platform build），此选项卡右上角的下拉菜单允许您将信息过滤到特定平台：

**Source details** 部分显示有关前端（frontend）的信息，以及可用的用于构建的源代码仓库。

### 构建计时（Build timing）

**Info** 选项卡的 **Build timing** 部分包含图表，从不同角度展示构建执行的分解情况。

- **Real time** 指的是完成构建所经过的实际时间。
- **Accumulated time** 显示所有步骤的总 CPU 时间。
- **Cache usage** 显示构建操作被缓存的程度。
- **Parallel execution** 显示构建执行时间中有多少时间用于并行运行步骤。

图表的颜色和图例键描述了不同的构建操作。构建操作定义如下：

| 构建操作（Build operation） | 描述 |
| :------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Local file transfers | 将本地文件从客户端传输到构建器所花费的时间。 |
| File operations      | 任何涉及在构建中创建和复制文件的操作。例如，Dockerfile 前端中的 `COPY`、`WORKDIR`、`ADD` 指令都会产生文件操作。 |
| Image pulls          | 拉取镜像所花费的时间。 |
| Executions           | 容器执行，例如在 Dockerfile 前端中定义为 `RUN` 指令的命令。 |
| HTTP                 | 使用 `ADD` 下载远程工件。 |
| Git                  | 与 **HTTP** 相同，但针对 Git URL。 |
| Result exports       | 导出构建结果所花费的时间。 |
| SBOM                 | 生成 [SBOM 证明（SBOM attestation）](/build/metadata/attestations/sbom/)所花费的时间。 |
| Idle                 | 构建工作器的空闲时间，如果您配置了[最大并行限制（max parallelism limit）](/build/buildkit/configure/#max-parallelism)，则可能发生这种情况。 |

### 构建依赖项（Build dependencies）

**Dependencies** 部分显示构建期间使用的镜像和远程资源。此处列出的资源包括：

- 构建期间使用的容器镜像
- 使用 `ADD` Dockerfile 指令包含的 Git 仓库
- 使用 `ADD` Dockerfile 指令包含的远程 HTTPS 资源

### 参数、密钥和其他设置（Arguments, secrets, and other parameters）

**Info** 选项卡的 **Configuration** 部分显示传递给构建的参数：

- 构建参数，包括解析后的值
- 密钥（secret），包括其 ID（但不包括值）
- SSH 套接字
- 标签（Label）
- 附加上下文（Additional contexts）]

### 输出与工件（Outputs and artifacts）

**Build results** 部分显示生成的构建工件的摘要，包括镜像清单详细信息、证明（attestation）和构建跟踪信息（build trace）。

证明是附加到容器镜像的元数据记录。该元数据描述了有关镜像的某些信息，例如它是如何构建的或它包含哪些软件包。有关证明的更多信息，请参阅构建证明（Build attestations）。

构建跟踪信息捕获 Buildx 和 BuildKit 中构建执行步骤的信息。跟踪信息有两种格式：OTLP 和 Jaeger。您可以通过打开操作菜单并选择要下载的格式，从 Docker Desktop 下载构建跟踪信息。

#### 使用 Jaeger 检查构建跟踪信息

使用 Jaeger 客户端，您可以导入并检查来自 Docker Desktop 的构建跟踪信息。以下步骤向您展示如何从 Docker Desktop 导出跟踪信息并在 Jaeger 中查看：

1. 启动 Jaeger UI：

   ```console
   $ docker run -d --name jaeger -p "16686:16686" jaegertracing/all-in-one
   ```

2. 在 Docker Desktop 中打开 **Builds** 视图，然后选择一个已完成的构建。

3. 导航到 **Build results** 部分，打开操作菜单并选择 **Download as Jaeger format**。

4. 在浏览器中访问 <http://localhost:16686> 以打开 Jaeger UI。

5. 选择 **Upload** 选项卡并打开您刚刚导出的 Jaeger 构建跟踪信息。

现在您可以使用 Jaeger UI 分析构建跟踪信息：

### Dockerfile 源与错误

当检查成功完成的构建或正在进行的活动构建时，**Source** 选项卡显示用于创建构建的前端（frontend）。

如果构建失败，则会显示 **Error** 选项卡而不是 **Source** 选项卡。错误信息内嵌在 Dockerfile 源码中，指示失败发生的位置和原因。

### 构建日志（Build logs）

**Logs** 选项卡显示构建日志。对于活动构建，日志会实时更新。

您可以在构建日志的 **List view** 和 **Plain-text view** 之间切换。

- **List view** 以可折叠格式呈现所有构建步骤，并提供时间轴以便沿着时间轴导航日志。
- **Plain-text view** 将日志显示为纯文本。

**Copy** 按钮允许您将日志的纯文本版本复制到剪贴板。

### 构建历史（Build history）

**History** 选项卡显示有关已完成构建的统计数据。

时间序列图表展示了相关构建在持续时间、构建步骤和缓存使用方面的趋势，帮助您识别构建操作随时间变化的模式和变化。例如，构建持续时间的显著峰值或大量缓存未命中可能表明存在优化 Dockerfile 的机会。

您可以通过在图表中选择相关构建，或使用图表下方的 **Past builds** 列表，来导航到并检查该构建。

## 管理构建器（Manage builders）

**Settings** 中的 **Builder** 选项卡允许您：

- 检查活动构建器的状态和配置
- 启动和停止构建器
- 删除构建历史
- 添加或移除构建器（对于云构建器，则为连接或断开连接）

有关管理构建器的更多信息，请参阅更改设置（Change settings）