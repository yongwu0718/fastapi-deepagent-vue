# 使用 Docker Model Runner 与 Compose Bridge

Compose Bridge 支持模型感知的部署（model-aware deployments）。它可以部署和配置 Docker Model Runner，这是一个托管和提供机器 LLM 的轻量级服务。

这减少了为启用 LLM 的服务进行手动设置的工作量，并确保在 Docker Desktop 和 Kubernetes 环境中的部署保持一致。

如果您的 `compose.yaml` 文件中包含顶层 `models` 元素，Compose Bridge 将：

- 为每个 model 的 endpoint 和名称自动注入 environment variables。
- 针对 Docker Desktop 和 Kubernetes 环境以不同方式配置 model endpoints。
- 当在 Helm values 中启用时，可选择在 Kubernetes 中部署 Docker Model Runner。

## 配置 Model Runner 设置

当使用生成的 Helm Charts 进行部署时，您可以通过 Helm values 控制 Model Runner 配置。

```yaml
# Model Runner settings
modelRunner:
    # 对于 Docker Desktop 设置为 false（使用主机实例）
    # 对于独立的 Kubernetes 集群设置为 true
    enabled: false
    # 当 enabled=false（Docker Desktop）时使用的 endpoint
    hostEndpoint: "http://host.docker.internal:12434/engines/v1/"
    # 当 enabled=true 时的部署设置
    image: "docker/model-runner:latest"
    imagePullPolicy: "IfNotPresent"
    # GPU 支持
    gpu:
        enabled: false
        vendor: "nvidia" # nvidia 或 amd
        count: 1
    # 节点调度（根据需要取消注释并自定义）
    # nodeSelector:
    #   accelerator: nvidia-tesla-t4
    # tolerations: []
    # affinity: {}

    # Security context
    securityContext:
        allowPrivilegeEscalation: false
    # Environment variables（根据需要取消注释并添加）
    # env:
    #   DMR_ORIGINS: "http://localhost:31246"
    resources:
        limits:
            cpu: "1000m"
            memory: "2Gi"
        requests:
            cpu: "100m"
            memory: "256Mi"
    # 用于模型的存储
    storage:
        size: "100Gi"
        storageClass: "" # 空字符串表示使用默认 storage class
    # 预拉取的 models
    models:
        - ai/qwen2.5:latest
        - ai/mxbai-embed-large
```

## 部署 Model Runner

### Docker Desktop

当 `modelRunner.enabled` 为 `false` 时，Compose Bridge 会配置您的工作负载，使其连接到在主机上运行的 Docker Model Runner：

```text
http://host.docker.internal:12434/engines/v1/
```

该 endpoint 会自动注入到您的服务容器（service containers）中。

### Kubernetes

当 `modelRunner.enabled` 为 `true` 时，Compose Bridge 使用生成的 manifests 在您的集群中部署 Docker Model Runner，包括：

- Deployment：运行 `docker-model-runner` 容器
- Service：暴露端口 `80`（映射到容器端口 `12434`）
- `PersistentVolumeClaim`：存储模型文件

`modelRunner.enabled` 设置还决定了 `model-runner-deployment` 的副本数：

- 当为 `true` 时，deployment 副本数设置为 1，Docker Model Runner 被部署在 Kubernetes 集群中。
- 当为 `false` 时，副本数为 0，不会部署任何 Docker Model Runner 资源。