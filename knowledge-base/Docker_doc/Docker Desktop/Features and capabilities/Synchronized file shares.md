# 同步文件共享（Synchronized file shares）

**同步文件共享（Synchronized file shares）** 是一种替代性的文件共享机制，可提供快速且灵活的主机到虚拟机文件共享，通过使用同步文件系统缓存来提升绑定挂载（bind mount）的性能。

## 适用人群

**同步文件共享（Synchronized file shares）** 非常适合以下开发者：
- 拥有大型仓库或单体仓库（monorepo），包含 10 万个或更多文件，总大小达数百兆字节甚至千兆字节。
- 正在使用虚拟文件系统（如 VirtioFS、gRPC FUSE 和 osxfs），但这些文件系统已无法随代码库规模良好扩展。
- 经常遇到性能限制。
- 不想担心文件所有权问题，也不希望在修改多个容器时花费时间解决冲突的文件所有权信息。

## 同步文件共享（Synchronized file shares）的工作原理？

**同步文件共享（Synchronized file share）** 的行为类似于虚拟文件共享，但利用高性能、低延迟的代码同步引擎，在 Docker Desktop 虚拟机内的 ext4 文件系统上创建主机文件的同步缓存。如果您在主机上或虚拟机的容器中更改文件系统，这些更改会通过双向同步进行传播。

创建文件共享实例后，任何使用绑定挂载（bind mount）且该绑定挂载指向与指定同步文件共享位置相匹配的主机文件系统位置（或其子目录）的容器，都将使用 **同步文件共享（Synchronized File Shares）** 功能。不满足此条件的绑定挂载将传递给正常的虚拟文件系统[绑定挂载机制](/engine/storage/bind-mounts/)，例如 VirtioFS 或 gRPC-FUSE。

> [!NOTE]
>
> Docker Desktop 中的 Kubernetes `hostPath` 卷不会使用**同步文件共享（Synchronized file shares）**。

> [!IMPORTANT]
>
> **同步文件共享（Synchronized file shares）** 在 WSL 上或使用 Windows 容器时不可用。

## 创建文件共享实例

要创建文件共享实例：
1. 登录 Docker Desktop。
2. 在 **Settings** 中，导航到 **Resources** 部分下的 **File sharing** 选项卡。
3. 在 **Synchronized file shares** 部分，选择 **Create share**。
4. 选择要共享的主机文件夹。同步文件共享应会初始化并可供使用。

文件共享需要几秒钟来初始化，因为文件会被复制到 Docker Desktop 虚拟机中。在此期间，状态指示器会显示 **Preparing**。Docker Desktop Dashboard 的底部还有一个状态图标，让您随时了解最新状态。

当状态指示器显示 **Watching for filesystem changes** 时，您的文件已可通过所有标准绑定挂载机制（无论是命令行的 `-v` 还是在 `compose.yml` 文件中指定）供虚拟机使用。

> [!NOTE]
>
> 当您创建新服务时，将[绑定挂载选项 consistency](/reference/cli/docker/service/create/#options-for-bind-mounts) 设置为 `:consistent` 会绕过**同步文件共享（Synchronized file shares）**。

## 探索您的文件共享实例

**Synchronized file shares** 部分会显示您的所有文件共享实例，并提供有关每个实例的有用信息，包括：
- 文件共享内容的来源
- 状态更新
- 每个文件共享使用的空间大小
- 文件系统条目数量
- 符号链接数量
- 哪个（哪些）容器正在使用该文件共享实例

选择某个文件共享实例会展开下拉菜单并显示这些信息。

## 使用 `.syncignore`

您可以在每个文件共享的根目录下使用 `.syncignore` 文件，以从文件共享实例中排除本地文件。它支持与 `.dockerignore` 文件相同的语法，并会排除和/或重新包含同步路径。`.syncignore` 文件在文件共享根目录以外的任何位置都会被忽略。

您可能希望添加到 `.syncignore` 文件中的一些示例包括：
- 大型依赖目录，例如 `node_modules` 和 `composer` 目录（除非您依赖通过绑定挂载访问它们）
- `.git` 目录（同样，除非您需要它们）

通常，使用 `.syncignore` 文件排除对您工作流程不关键的项目，尤其是那些同步缓慢或占用大量存储空间的项目。

## 已知问题

- 对 `.syncignore` 所做的更改不会导致立即删除，除非重新创建文件共享。换句话说，由于 `.syncignore` 文件的修改而新被忽略的文件仍会保留在其当前位置，但在同步期间不再更新。

- 每个文件共享实例的文件数量限制约为 200 万个。为了获得最佳性能，如果您有这么大尺寸的文件共享实例，请尝试将其分解为多个共享，分别对应各个绑定挂载位置。

- 由于 Linux 区分大小写而 macOS/Windows 仅保留大小写，大小写冲突（Case conflicts）会在 GUI 中显示为 **File exists** 问题。这些可以忽略。但是，如果它们持续存在，您可以报告该问题。

- **同步文件共享（Synchronized file shares）** 会主动报告临时问题，这可能导致同步期间 GUI 中偶尔出现 **Conflict** 和 **Problem** 指示器。这些可以忽略。但是，如果它们持续存在，您可以报告该问题。

- 如果您在 Windows 上从 WSL2 切换到 Hyper-V，则需要完全重启 Docker Desktop。

- 不支持 POSIX 风格的 Windows 路径。避免在 Docker Compose 中设置 [`COMPOSE_CONVERT_WINDOWS_PATHS`](/compose/how-tos/environment-variables/envvars/#compose_convert_windows_paths) 环境变量。

- 如果您没有创建符号链接的正确权限，并且您的容器尝试在文件共享实例中创建符号链接，则会显示 **unable to create symbolic link** 错误消息。对于 Windows 用户，请参阅 Microsoft 的[创建符号链接文档](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/security-policy-settings/create-symbolic-links)，了解最佳实践以及 **Create symbolic links** 安全策略设置的位置。对于 Mac 和 Linux 用户，请检查您对该文件夹是否具有写入权限。