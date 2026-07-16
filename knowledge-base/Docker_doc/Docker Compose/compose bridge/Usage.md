# 使用默认的 Compose Bridge 转换

Compose Bridge 包含一个内置转换功能，可将您的 Compose 配置自动转换为一组 Kubernetes manifests。

基于您的 `compose.yaml` 文件，它会生成：

- 一个 [Namespace](https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/)，以便所有资源隔离，避免与其他部署的资源冲突。
- 一个 [ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/)，为 Compose 应用中的每个 [config](/reference/compose-file/configs/) 资源提供对应条目。
- 针对应用 services 的 [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)。这确保了 Kubernetes 集群中维护了指定数量的应用实例。
- 用于 service 间通信的 [Services](https://kubernetes.io/docs/concepts/services-networking/service/)，对应 services 暴露的 ports。
- 用于 services 发布的 ports 的 [Services](https://kubernetes.io/docs/concepts/services-networking/service/)，类型为 `LoadBalancer`，以便 Docker Desktop 也能在主机上暴露相同的 port。
- 用于复制 `compose.yaml` 文件中定义的网络拓扑的 [Network policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)。
- 用于 volumes 的 [PersistentVolumeClaims](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)，使用 `hostpath` storage class，以便 Docker Desktop 管理 volume 创建。
- 包含编码后 secret 的 [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)。这专为测试环境的本地使用而设计。

此外，它还提供了一个专用于 Docker Desktop 的 Kustomize overlay，包含：
- 为需要向主机暴露端口的 services 提供 `Loadbalancer`。
- 一个 `PersistentVolumeClaim`，使用 Docker Desktop 的存储 provisioner `desktop-storage-provisioner` 更有效地处理 volume provisioning。
- 一个 `Kustomization.yaml` 文件，用于将所有资源链接在一起。

如果您的 Compose 文件为某个 service 定义了 `models` 部分，Compose Bridge 会自动配置您的部署，以便您的 service 能够通过 Docker Model Runner 定位并使用其 models。

对于每个声明的 model，转换会注入两个 environment variables：

- `<MODELNAME>_URL`：Docker Model Runner 提供该 model 的 endpoint
- `<MODELNAME>_MODEL`：model 的名称或标识符

您可以选择使用 `endpoint_var` 和 `model_var` 自定义这些变量名。

默认转换生成两个不同的 overlays —— 一个用于使用本地 Docker Model Runner 实例的 Docker Desktop，另一个是包含所有相关 Kubernetes 资源以在 pod 中部署 Docker Model Runner 的 `model-runner` overlay。

| 环境            | Endpoint                                        |
| -------------- | ----------------------------------------------- |
| Docker Desktop | `http://host.docker.internal:12434/engines/v1/` |
| Kubernetes     | `http://model-runner/engines/v1/`               |

更多详细信息，请参阅 [使用 Model Runner](/compose/bridge/usage/use-model-runner/)。

## 使用默认的 Compose Bridge 转换

要使用默认转换转换您的 Compose 文件：

```console
$ docker compose bridge convert
```

Compose 会在当前目录中查找 `compose.yaml` 文件，并生成 Kubernetes manifests。

输出示例：

```console
$ docker compose -f compose.yaml bridge convert
Kubernetes resource backend-deployment.yaml created
Kubernetes resource frontend-deployment.yaml created
Kubernetes resource backend-expose.yaml created
Kubernetes resource frontend-expose.yaml created
Kubernetes resource 0-my-project-namespace.yaml created
Kubernetes resource default-network-policy.yaml created
Kubernetes resource backend-service.yaml created
Kubernetes resource frontend-service.yaml created
Kubernetes resource kustomization.yaml created
Kubernetes resource backend-deployment.yaml created
Kubernetes resource frontend-deployment.yaml created
Kubernetes resource backend-service.yaml created
Kubernetes resource frontend-service.yaml created
Kubernetes resource kustomization.yaml created
Kubernetes resource model-runner-configmap.yaml created
Kubernetes resource model-runner-deployment.yaml created
Kubernetes resource model-runner-service.yaml created
Kubernetes resource model-runner-volume-claim.yaml created
Kubernetes resource kustomization.yaml created
```

所有生成的文件都存储在项目中的 `/out` 目录下。

## 部署生成的 manifests

> [!IMPORTANT]
>
> 在部署 Compose Bridge 转换结果之前，请确保已在 Docker Desktop 中[启用 Kubernetes](/desktop/settings-and-maintenance/settings/#kubernetes)。

一旦 manifests 生成完毕，将其部署到您的本地 Kubernetes 集群：

```console
$ kubectl apply -k out/overlays/desktop/
```

> [!TIP]
>
> 您可以从 Compose 文件查看器中转换并部署 Compose 项目到 Kubernetes 集群。
> 
> 确保您已登录 Docker 账户，导航到 **Containers** 视图中的容器，然后在右上角选择 **View configurations**，接着选择 **Convert and Deploy to Kubernetes**。

## 其他命令

转换位于另一个目录中的 `compose.yaml` 文件：

```console
$ docker compose -f <path-to-file>/compose.yaml bridge convert
```

要查看所有可用的 flags，请运行：

```console
$ docker compose bridge convert --help
```

## 下一步

- [探索如何自定义 Compose Bridge](/compose/bridge/usage/customize/)
- [使用 Model Runner](/compose/bridge/usage/use-model-runner/)