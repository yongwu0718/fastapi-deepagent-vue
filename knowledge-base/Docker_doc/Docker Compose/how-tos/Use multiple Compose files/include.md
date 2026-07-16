# Include

通过 `include`，您可以将一个独立的 `compose.yaml` 文件直接合并到当前的 `compose.yaml` 文件中。这使得将复杂应用模块化为子 Compose 文件变得容易，从而让应用配置更简单、更明确。

[`include` 顶层元素](/reference/compose-file/include/)有助于在配置文件组织结构中直接反映出负责代码的工程团队。它同时还解决了 [`extends`](/compose/how-tos/multiple-compose-files/include/extends/) 和 [merge](/compose/how-tos/multiple-compose-files/include/merge/) 所存在的相对路径问题。

`include` 部分中列出的每个路径都会作为一个独立的 Compose 应用模型加载，并带有自己的项目目录（project directory），以便解析相对路径。

一旦被 include 的 Compose 应用加载完成，其所有资源都会被复制到当前的 Compose 应用模型中。

> [!NOTE]
>
> `include` 是递归生效的，因此如果一个被 include 的 Compose 文件自身又声明了 `include` 部分，那么这些文件也会被 include。

## 示例

```yaml
include:
  - my-compose-include.yaml  # 其中声明了 serviceB
services:
  serviceA:
    build: .
    depends_on:
      - serviceB # 直接使用 serviceB，就像它是在这个 Compose 文件中声明的一样
```

`my-compose-include.yaml` 管理着 `serviceB`，其中详细定义了若干副本（replicas）、用于检查数据的 web UI、隔离的网络（networks）、用于数据持久化的卷（volumes）等。依赖于 `serviceB` 的应用不需要了解这些基础设施的细节，只需将这份 Compose 文件作为一个可靠的基础构件来使用即可。

这意味着管理 `serviceB` 的团队可以对其自身的数据库组件进行重构（例如引入额外的 services），而不会影响到任何依赖方团队。这也意味着依赖方团队在运行每个 Compose 命令时，无需额外添加各种标志（flags）。

```yaml
include:
  - oci://docker.io/username/my-compose-app:latest # 使用存储为 OCI 构件的 Compose 文件
services:
  serviceA:
    build: .
    depends_on:
      - serviceB 
```

`include` 允许您从远程源（例如 OCI artifacts 或 Git repositories）引用 Compose 文件。  
此处 `serviceB` 是在一个存储在 Docker Hub 上的 Compose 文件中定义的。

## 对被 include 的 Compose 文件使用 override

如果当前模型中的任何资源与被 include 的 Compose 文件中的资源发生冲突，Compose 会报告错误。此规则旨在防止与被 include 的 Compose 文件作者所定义的资源发生意外冲突。然而，在某些情况下，您可能希望自定义被 include 的模型。可以通过向 include 指令添加一个 override 文件来实现：

```yaml
include:
  - path : 
      - third-party/compose.yaml
      - override.yaml  # 针对第三方模型的本地 override
```

这种方法的主要限制是，您需要为每个 include 维护一个专用的 override 文件。对于具有多个 include 的复杂项目，这会导致产生大量的 Compose 文件。

另一种选择是使用 `compose.override.yaml` 文件。虽然使用 `include` 的文件在声明相同资源时会拒绝冲突，但一个全局的 Compose override 文件可以覆盖最终合并后的模型，如下例所示：

主 `compose.yaml` 文件：
```yaml
include:
  - team-1/compose.yaml # 声明 service-1
  - team-2/compose.yaml # 声明 service-2
```

Override `compose.override.yaml` 文件：
```yaml
services:
  service-1:
    # 覆盖被 include 的 service-1，以启用调试端口
    ports:
      - 2345:2345

  service-2:
    # 覆盖被 include 的 service-2，以使用包含测试数据的本地数据文件夹
    volumes:
      - ./data:/data
```

将两者结合，您可以受益于第三方可复用组件，同时根据需要调整 Compose 模型。

## 参考信息

[`include` 顶层元素](/reference/compose-file/include/)