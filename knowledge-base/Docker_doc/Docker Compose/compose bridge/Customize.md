# 自定义 Compose Bridge

您可以自定义 Compose Bridge 将 Docker Compose 文件转换为特定平台格式的方式。

本页说明了 Compose Bridge 如何使用模板（templating）生成 Kubernetes manifests，以及如何根据您的特定需求自定义这些模板，或者如何构建您自己的转换（transformation）。

## 工作原理

Compose Bridge 使用转换（transformations）让您将 Compose model 转换为另一种形式。

一个转换被打包为一个 Docker image，它接收完全解析后的 Compose model 作为 `/in/compose.yaml`，并可以在 `/out` 下生成任何目标格式的文件。

Compose Bridge 包含一个使用 Go 模板的默认 Kubernetes 转换，您可以通过替换或扩展模板来自定义它。

### 模板语法

Compose Bridge 利用模板将 Compose 配置文件转换为 Kubernetes manifests。模板是使用 [Go 模板语法](https://pkg.go.dev/text/template)的纯文本文件。这使得可以插入逻辑和数据，使模板根据 Compose model 动态且可适配。

当执行模板时，它必须生成一个 YAML 文件，这是 Kubernetes manifests 的标准格式。可以生成多个文件，只要它们用 `---` 分隔即可。

每个 YAML 输出文件以自定义头部标记开头，例如：

```yaml
#! manifest.yaml
```

在以下示例中，一个模板遍历 `compose.yaml` 文件中定义的 services。对于每个 service，会生成一个专用的 Kubernetes manifest 文件，以 service 命名并包含指定的配置。

```yaml
{{ range $name, $service := .services }}
---
#! {{ $name }}-manifest.yaml
# Generated code, do not edit
key: value
## ...
{{ end }}
```

### 输入模型

您可以通过运行 `docker compose config` 来生成输入模型。

这个规范的 YAML 输出作为 Compose Bridge 转换的输入。在模板中，可以使用点符号访问来自 `compose.yaml` 的数据，从而允许您遍历嵌套的数据结构。例如，要访问一个 service 的部署模式，您可以使用 `service.deploy.mode`：

```yaml
# iterate over a yaml sequence
{{ range $name, $service := .services }}
  # access a nested attribute using dot notation
  {{ if eq $service.deploy.mode "global" }}
kind: DaemonSet
  {{ end }}
{{ end }}
```

您可以查阅 [Compose Specification JSON schema](https://github.com/compose-spec/compose-go/blob/main/schema/compose-spec.json) 以全面了解 Compose model。该 schema 概述了 Compose model 中所有可能的配置及其数据类型。

### 辅助函数

作为 Go 模板语法的一部分，Compose Bridge 提供了一组 YAML 辅助函数，旨在高效地操作模板中的数据：

| 函数        | 描述                                                                          |
| ----------- | ----------------------------------------------------------------------------- |
| `seconds`   | 将 [duration](/reference/compose-file/extension/#specifying-durations) 转换为整数（秒）。 |
| `uppercase` | 将字符串转换为大写。                                                          |
| `title`     | 将每个单词的首字母大写。                                                      |
| `safe`      | 将字符串转换为安全标识符（将非小写字符替换为 `-`）。                        |
| `truncate`  | 从列表中删除前 N 个元素。                                                     |
| `join`      | 使用分隔符将列表元素连接成单个字符串。                                        |
| `base64`    | 将字符串编码为 base64（用于 Kubernetes secrets）。                           |
| `map`       | 使用 `“value -> newValue”` 语法映射值。                                      |
| `indent`    | 将字符串内容缩进 N 个空格。                                                   |
| `helmValue` | 输出 Helm 风格的模板值。                                                      |

在以下示例中，模板检查是否为 service 指定了 healthcheck interval，应用 `seconds` 函数将此 interval 转换为秒，并将值赋给 `periodSeconds` 属性。

```yaml
{{ if $service.healthcheck.interval }}
            periodSeconds: {{ $service.healthcheck.interval | seconds }}{{ end }}
{{ end }}
```

## 自定义默认模板

由于 Kubernetes 是一个通用平台，有许多方法可以将 Compose 概念映射到 Kubernetes 资源定义中。Compose Bridge 允许您自定义转换，以匹配您自己的基础设施决策和偏好，并提供不同的灵活性和工作量级别。

### 修改默认模板

您可以提取默认转换 `docker/compose-bridge-kubernetes` 使用的模板：

```console
$ docker compose bridge transformations create --from docker/compose-bridge-kubernetes my-template
```

模板被提取到一个以您的模板名称命名的目录中，此处为 `my-template`。它包含：

- 一个 Dockerfile，允许您创建自己的 image 以分发您的模板
- 一个包含模板文件的目录

根据需要编辑、[添加](#add-your-own-templates)或删除模板。

然后，您可以使用生成的 Dockerfile 将您的更改打包到一个新的转换 image 中，然后可以与 Compose Bridge 一起使用：

```console
$ docker build --tag mycompany/transform --push .
```

使用您的转换作为替换：

```console
$ docker compose bridge convert --transformations mycompany/transform 
```

#### Model Runner 模板

默认转换还包含用于使用 LLM 的应用的模板：

- `model-runner-deployment.tmpl`：为 Docker Model Runner 生成 Kubernetes deployment。自定义它可以更改副本数、image tags、资源请求和限制、GPU 调度设置、容忍度或额外的 environment variables。
- `model-runner-service.tmpl`：构建暴露 Docker Model Runner 的 service。更新它可以在 `ClusterIP`、`NodePort` 或 `LoadBalancer` 类型之间切换，调整 ports，或为 ingress 和 service meshes 添加 annotations。
- `model-runner-pvc.tmpl`：定义用于存储下载模型的 persistent volume claim。编辑它可以设置存储大小、storage class、访问模式或存储提供商所需的 volume annotations。
- `/overlays/model-runner/kustomization.yaml`：当您将 Model Runner 部署到独立的 Kubernetes 集群时应用的 Kustomize overlay。扩展它可以为 labels 和 annotations 添加 patches，附加 `NetworkPolicies`，或包含额外的 manifests。
- `/overlays/desktop/deployment.tmpl`：特定于桌面的 deployment 模板，它将集群内的 Model Runner 规模缩减，并将工作负载指向主机 endpoint。如果您更改了 Desktop endpoint 或希望将 Model Runner 部署在 Desktop 上而不是依赖主机服务，请调整它。

常见的自定义场景：

- 通过在 `model-runner-deployment.tmpl` 中添加供应商特定的资源请求、限制和 node selectors 来启用 GPU 支持。
- 通过编辑 `model-runner-pvc.tmpl` 来增加或调整模型工件的存储，设置所需的大小、storage class 或访问模式。
- 通过更改 `model-runner-service.tmpl` 中的 service type 或在 model-runner overlay 中添加 ingress annotations，将 Model Runner 暴露在集群外部。
- 通过 `/overlays/model-runner/kustomization.yaml` 添加 labels、annotations 或 NetworkPolicies 来对齐集群策略。

更多详细信息，请参阅 [使用 Model Runner](/compose/bridge/customize/use-model-runner/)。

### 添加您自己的模板

对于 Compose Bridge 默认转换不管理的资源，您可以构建自己的模板。

`compose.yaml` model 可能不提供填充目标 manifest 所需的所有配置属性。如果出现这种情况，您可以依赖 Compose 自定义扩展来更好地描述应用，并提供一种与平台无关的转换。

例如，如果您在 `compose.yaml` 文件中为 service 定义添加了 `x-virtual-host` 元数据，则可以使用以下自定义属性来生成 Ingress 规则：

```yaml
{{ $project := .name }}
#! {{ $name }}-ingress.yaml
# Generated code, do not edit
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: virtual-host-ingress
  namespace: {{ $project }}
spec:
  rules:  
{{ range $name, $service := .services }}
{{ range index $service "x-virtual-host" }}
  - host: ${{ . }}
    http:
      paths:
      - path: "/"
        backend:
          service:
            name: ${{ name }}
            port:
              number: 80  
{{ end }}
{{ end }}
```

一旦打包到 Docker image 中，您可以在将 Compose models 转换为 Kubernetes 时，将此自定义模板与其他转换一起使用：

```console
$ docker compose bridge convert \
    --transformation docker/compose-bridge-kubernetes \
    --transformation mycompany/transform 
```

### 构建您自己的转换

虽然 Compose Bridge 模板使您可以轻松地进行最小程度的自定义，但您可能希望进行重大更改，或者依赖现有的转换工具。

Compose Bridge 转换是一个 Docker image，旨在从 `/in/compose.yaml` 获取 Compose model，并在 `/out` 下生成平台 manifests。这个简单的契约使得使用 [Kompose](https://kompose.io/) 打包替代转换变得容易：

```Dockerfile
FROM alpine

# Get kompose from github release page
RUN apk add --no-cache curl
ARG VERSION=1.32.0
RUN ARCH=$(uname -m | sed 's/armv7l/arm/g' | sed 's/aarch64/arm64/g' | sed 's/x86_64/amd64/g') && \
    curl -fsL \
    "https://github.com/kubernetes/kompose/releases/download/v${VERSION}/kompose-linux-${ARCH}" \
    -o /usr/bin/kompose
RUN chmod +x /usr/bin/kompose

CMD ["/usr/bin/kompose", "convert", "-f", "/in/compose.yaml", "--out", "/out"]
```

此 Dockerfile 打包了 Kompose，并根据 Compose Bridge 转换合约定义了运行此工具的命令。