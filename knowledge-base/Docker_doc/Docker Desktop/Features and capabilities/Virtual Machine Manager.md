# Mac 版 Docker Desktop 的虚拟机管理器 (Virtual Machine Manager)

Docker Desktop 支持多种**虚拟机管理器 (Virtual Machine Manager, VMM)** 来驱动运行容器的 Linux 虚拟机。您可以根据系统架构（Intel 或 Apple Silicon）、性能需求和功能要求选择最合适的选项。本页概述了可用的选项。

要更改 VMM，请前往 **Settings** > **General** > **Virtual Machine Manager**。

## Docker VMM

**Docker VMM** 是一个针对容器优化的 hypervisor。通过优化 Linux 内核和 hypervisor 层，**Docker VMM** 在常见开发者任务中提供了显著的性能提升。

**Docker VMM** 提供的一些关键性能改进包括：

- **更快的 I/O 操作**：在冷缓存情况下，使用 `find` 遍历大型共享文件系统时，速度比使用 Apple Virtualization framework 快 2 倍。
- **改进的缓存**：在热缓存情况下，性能可提升高达 25 倍，甚至超过原生 Mac 操作。

这些改进直接影响那些在容器化开发中依赖频繁文件访问和整体系统响应能力的开发者。**Docker VMM** 标志着速度的重大飞跃，可实现更顺畅的工作流和更快的迭代周期。

> [!NOTE]
>
> **Docker VMM** 需要至少为 Docker Linux 虚拟机分配 4GB 内存。需要在启用 **Docker VMM** 之前增加内存，这可以在 **Settings** 的 **Resources** 选项卡中完成。

### 已知问题

由于 **Docker VMM** 仍处于 Beta 阶段，存在一些已知限制：

- **Docker VMM** 目前不支持 Rosetta，因此 amd64 架构的模拟速度较慢。Docker 正在探索潜在的解决方案。
- 某些数据库（如 MongoDB 和 Cassandra）在将 virtiofs 与 **Docker VMM** 一起使用时可能会失败。此问题预计将在未来版本中解决。

## Apple Virtualization framework

**Apple Virtualization framework** 是一个稳定且成熟的选择，用于在 Mac 上管理虚拟机。多年来，它一直是许多 Mac 用户可靠的选择。该框架最适合那些喜欢经过验证的解决方案、具有稳定性能和广泛兼容性的开发者。

## Apple Silicon 的 QEMU（旧版）

> [!NOTE]
>
> QEMU 已在 4.44 及更高版本中被弃用。更多信息，请参阅[博客公告](https://www.docker.com/blog/docker-desktop-for-mac-qemu-virtualization-option-to-be-deprecated-in-90-days/)。

QEMU 是 Apple Silicon Mac 的旧版虚拟化选项，主要为了支持旧用例。

Docker 建议过渡到更新的替代方案，例如 **Docker VMM** 或 **Apple Virtualization framework**，因为它们提供卓越的性能和持续的支持。特别是 **Docker VMM** 提供了显著的速度提升和更高效的开发环境，使其成为使用 Apple Silicon 的开发者的一个引人注目的选择。

请注意，这与在[多平台构建](/build/building/multi-platform/#qemu)中使用 QEMU 模拟非原生架构无关。

## 基于 Intel 的 Mac 的 HyperKit（旧版）

> [!NOTE]
>
> HyperKit 已被弃用。Docker 建议切换到 **Apple Virtualization framework**。

HyperKit 是基于 Intel 的 Mac 的旧版虚拟化选项。Docker 建议切换到现代替代方案以获得更好的性能，并让您的环境面向未来。