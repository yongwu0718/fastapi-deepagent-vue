# Compose 文件的信任模型（Trust model）

Docker Compose 将每个 Compose 文件视为受信任的输入。当一个 Compose 文件请求提升权限、主机文件系统访问或任何其他配置时，Compose 会按原样应用它。这与直接将标志（flags）传递给 `docker run` 的行为相同。

这意味着，您运行的任何 Compose 文件，无论它位于本地文件系统、Git 仓库还是 OCI registry 中，都完全控制容器（containers）如何与您的主机交互。安全边界不在于文件来源，而在于您是否信任作者。

评估信任意味着要问：谁编写了这个文件？自您上次审查以来它是否发生了变化？您是否理解它请求的每一项特权？

## 依赖链（The dependency chain）

一个 Compose 应用可以由多个来源组装而成。[`include`](/reference/compose-file/include/) 指令导入完整的 Compose 文件，而 [`extends`](/reference/compose-file/services/#extends) 则从另一个文件中的特定服务（service）继承配置。两者都支持远程引用，并且可以链式连接：

```text
Your command
  └─ compose.yaml                                    (local or remote)
       ├─ services, volumes, networks                (direct config)
       ├─ include:
       │    └─ oci://registry.example.com/base:v2   (remote dependency)
       │         └─ services, volumes, networks      (indirect config)
       └─ services:
            └─ app:
                 └─ extends:
                      └─ file: oci://registry.example.com/templates:v1
                           └─ service: webapp        (inherited config)
```

每一层都具有相同的能力。您检查的顶层文件可能看起来很安全，而嵌套的 `include` 或 `extends` 却引入了具有提升权限、主机绑定挂载（bind mounts）或不受信任镜像（images）的服务（services）。这些依赖项也可能独立变化。危险的设置可能由嵌套依赖引入，除非您检查完全解析后的输出，否则永远看不到。

> [!IMPORTANT]
>
> 当配置引用远程源时，Compose 会发出警告。在未理解链中每个引用之前，请不要接受。

## 最佳实践（Best practices）

### 检查完整配置

要准确查看 Compose 应用的内容（包括所有解析后的 `includes`、`extends`、合并的 overrides 和插值变量），请使用：

```console
$ docker compose config
```

对于远程引用：

```console
$ docker compose -f oci://registry.example.com/myapp:latest config
```

在运行 `up` 或 `create` 之前，请检查此输出，尤其是当配置来自您未审计的源时。

#### 需要注意的字段（Fields to look out for）

Compose 配置对容器（containers）如何与主机交互具有广泛的控制权。以下是非穷举的字段列表，当由不受信任的作者设置时，这些字段会带来安全隐患：

| 字段 | 影响 |
|------|------|
| `privileged` | 授予容器对主机的完全访问权限 |
| `cap_add` | 添加 Linux 能力（capabilities），例如 `SYS_ADMIN` 或 `NET_RAW` |
| `security_opt` | 配置安全配置文件，包括 seccomp 和 AppArmor |
| `volumes` / bind mounts | 将主机目录挂载到容器中 |
| `network_mode: host` | 共享主机网络栈 |
| `pid: host` | 共享主机 PID 命名空间 |
| `devices` | 将主机设备暴露给容器 |
| `image` | 拉取并运行任意容器镜像 |

如有疑问，请在运行配置之前查阅任何不熟悉字段的影响。

### CI/CD 环境

自动化流水线尤其敏感，因为它们通常运行时可访问凭证、云提供商令牌或 Docker 套接字（sockets）。

- 避免在自动化流水线中引用公共或未经验证的 Compose 配置。
- 将更新置于正常的代码审查流程之后。
- 尽可能使用只读的 Docker 套接字挂载以限制风险。

### 将远程引用固定到 digest（Pin remote references to digests）

标签（tags）是可变的，这意味着任何对 registry 有推送权限的人都可以静默覆盖一个标签，因此您上周审查的引用可能指向今天的不同内容。

Digests 是不可变的。不要通过标签引用，而是固定到 digest。

```yaml
include:
  - oci://registry.example.com/base@sha256:a1b2c3d4...
```

将对固定 digest 的任何更新视为代码更改。在更新引用之前，请务必审查新内容。

### 其他

- 使用私有 registry（private registry）：将 OCI 构件托管在您组织控制的 registry 上。限制谁可以推送。
- 审计传递依赖（transitive dependencies）：检查链中的每个远程 `include` 和 `extends` 引用，而不仅仅是顶层文件。
- 检查所有 Compose 确认提示：当加载远程 Compose 文件时，Compose 会显示插值变量、环境值和远程 includes 的确认提示。在接受之前请仔细审查。

## 延伸阅读

- [OCI 构件应用（OCI artifact applications）](/compose/how-tos/oci-artifact/)
- [在生产环境中使用 Compose（Use Compose in production）](/compose/how-tos/production/)
- [`include` 参考](/reference/compose-file/include/)
- [`extends` 参考](/reference/compose-file/services/#extends)
- [在 Compose 中管理 secrets（Manage secrets in Compose）](/compose/how-tos/use-secrets/)