# containerd image store（镜像存储）

Docker Desktop 默认使用 **containerd** 作为其镜像存储（image store）。镜像存储是负责在文件系统上推送（push）、拉取（pull）和存储镜像的组件。**containerd image store** 支持多平台镜像（multi-platform images）、镜像证明（image attestations）以及替代的快照器（snapshotters）等特性。

## 什么是 `containerd`？

`containerd` 是一个容器运行时，为容器生命周期和镜像管理提供轻量级、一致的接口。Docker Engine 在底层使用它来创建、启动和停止容器。

## 什么是 `containerd` image store？

镜像存储（image store）是负责在文件系统上推送、拉取和存储镜像的组件。

**containerd image store** 扩展了 Docker Engine 能够原生交互的镜像类型范围。虽然这是一个底层架构变更，但它是解锁一系列新用例的先决条件，包括：

- [构建多平台镜像](#build-multi-platform-images)以及带有证明（attestations）的镜像
- 支持使用具有独特特性的 containerd 快照器（snapshotters），例如用于容器启动时延迟拉取镜像的 [stargz][1]，或用于点对点镜像分发的 [nydus][2] 和 [dragonfly][3]。
- 运行 [Wasm](/desktop/features/containerd/wasm/) 容器的能力

[1]: https://github.com/containerd/stargz-snapshotter
[2]: https://github.com/containerd/nydus-snapshotter
[3]: https://github.com/dragonflyoss/image-service

## 经典镜像存储（Classic image store）

经典镜像存储是 Docker 的旧版存储后端，已被 **containerd image store** 取代。它不支持镜像索引（image indices）或清单列表（manifest lists），因此您无法在本地加载多平台镜像或构建带有证明的镜像。

大多数用户没有理由使用经典镜像存储。它仅适用于需要匹配旧行为或有兼容性要求的情况。

## 切换镜像存储

在 Docker Desktop 4.34 及更高版本中，**containerd image store** 默认启用。要在镜像存储之间切换：

1. 导航到 Docker Desktop 中的 **Settings**。
2. 在 **General** 选项卡中，勾选或取消勾选 **Use containerd for pulling and storing images** 选项。
3. 选择 **Apply**。

> [!NOTE]
>
> Docker Desktop 为经典镜像存储和 **containerd image store** 维护着独立的镜像存储。在它们之间切换时，来自非活动存储的镜像和容器仍保留在磁盘上，但在您切换回来之前会被隐藏。

## 构建多平台镜像

**containerd image store** 允许您构建多平台镜像并将其加载到本地镜像存储中：

使用经典镜像存储构建多平台镜像不受支持：

```console
$ docker build --platform=linux/amd64,linux/arm64 .
[+] Building 0.0s (0/0)
ERROR: Multi-platform build is not supported for the docker driver.
Switch to a different driver, or turn on the containerd image store, and try again.
Learn more at https://docs.docker.com/go/build-multi-platform/
```