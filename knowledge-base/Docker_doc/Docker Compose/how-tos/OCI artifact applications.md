# 将 Docker Compose 应用打包并部署为 OCI 构件

Docker Compose 支持与 [OCI 构件](/docker-hub/repos/manage/hub-images/oci-artifacts/) 一起使用，允许您通过容器 registry 打包和分发 Compose 应用。这意味着您可以将 Compose 文件与容器镜像（container images）一起存储，从而更轻松地对多容器应用进行版本控制、共享和部署。

## 将您的 Compose 应用发布为 OCI 构件

要将 Compose 应用作为 OCI 构件分发，您可以使用 `docker compose publish` 命令，将其发布到兼容 OCI 的 registry。这样，其他人就可以直接从 registry 部署您的应用。

发布功能支持 Compose 的大部分组合能力，例如 overrides、extends 或 include，但存在[一些限制](#limitations)。

### 一般步骤

1. 进入您的 Compose 应用目录。  
   确保您位于包含 `compose.yml` 文件的目录中，或者使用 `-f` 标志指定您的 Compose 文件。

2. 在终端中登录您的 Docker 账户，以便通过 Docker Hub 进行身份验证。

   ```console
   $ docker login
   ```

3. 使用 `docker compose publish` 命令将您的应用作为 OCI 构件推送：

   ```console
   $ docker compose publish username/my-compose-app:latest
   ```
   如果您有多个 Compose 文件，请运行：

   ```console
   $ docker compose -f compose-base.yml -f compose-production.yml publish username/my-compose-app:latest
   ```

### 高级发布选项

发布时，您可以传递额外的选项：
- `--oci-version`：指定 OCI 版本（默认自动确定）。
- `--resolve-image-digests`：将镜像标签（image tags）固定为 digest。
- `--with-env`：在发布的 OCI 构件中包含环境变量（environment variables）。

Compose 会检查您的配置中是否包含敏感数据，并显示您的环境变量，以确认您希望发布它们。

```text
...
you are about to publish sensitive data within your OCI artifact.
please double check that you are not leaking sensitive data
AWS Client ID
"services.serviceA.environment.AWS_ACCESS_KEY_ID": xxxxxxxxxx
AWS Secret Key
"services.serviceA.environment.AWS_SECRET_ACCESS_KEY": aws"xxxx/xxxx+xxxx+"
Github authentication
"GITHUB_TOKEN": ghp_xxxxxxxxxx
JSON Web Token
"": xxxxxxx.xxxxxxxx.xxxxxxxx
Private Key
"": -----BEGIN DSA PRIVATE KEY-----
xxxxx
-----END DSA PRIVATE KEY-----
Are you ok to publish these sensitive data? [y/N]:y

you are about to publish environment variables within your OCI artifact.
please double check that you are not leaking sensitive data
Service/Config  serviceA
FOO=bar
Service/Config  serviceB
FOO=bar
QUIX=
BAR=baz
Are you ok to publish these environment variables? [y/N]: 
```

如果您拒绝，发布过程将停止，不会向 registry 发送任何内容。

## 限制

将 Compose 应用发布为 OCI 构件存在一些限制。您不能发布具有以下情况的 Compose 配置：
- 某个 service 包含 bind mounts
- 某个 service 仅包含 `build` 部分
- 使用 `include` 属性包含本地文件。要成功发布，请确保任何被包含的本地文件也一同被发布。然后，您可以使用 `include` 来引用这些文件，因为支持远程 `include`。

## 启动一个 OCI 构件应用

要启动一个使用了 OCI 构件的 Docker Compose 应用，您可以使用 `-f`（或 `--file`）标志，后跟 OCI 构件引用。这允许您指定一个作为 OCI 构件存储在 registry 中的 Compose 文件。

`oci://` 前缀表示 Compose 文件应从兼容 OCI 的 registry 拉取，而不是从本地文件系统加载。

```console
$ docker compose -f oci://docker.io/username/my-compose-app:latest up
```

然后，使用 `docker compose up` 命令并带上指向 OCI 构件的 `-f` 标志来运行 Compose 应用：

```console
$ docker compose -f oci://docker.io/username/my-compose-app:latest up
```

### 故障排除

当您从 OCI 构件运行应用时，Compose 可能会显示警告消息，要求您确认以下内容，以降低运行恶意应用的风险：

- 所用插值变量（interpolation variables）及其值的列表
- 应用使用的所有环境变量的列表
- 您的 OCI 构件应用是否正在使用其他远程资源（例如通过 [`include`](/reference/compose-file/include/)）

```text 
$ REGISTRY=myregistry.com docker compose -f oci://docker.io/username/my-compose-app:latest up

Found the following variables in configuration:
VARIABLE     VALUE                SOURCE        REQUIRED    DEFAULT
REGISTRY     myregistry.com      command-line   yes         
TAG          v1.0                environment    no          latest
DOCKERFILE   Dockerfile          default        no          Dockerfile
API_KEY      <unset>             none           no          

Do you want to proceed with these variables? [Y/n]:y

Warning: This Compose project includes files from remote sources:
- oci://registry.example.com/stack:latest
Remote includes could potentially be malicious. Make sure you trust the source.
Do you want to continue? [y/N]: 
```

如果您同意启动应用，Compose 会显示 OCI 构件中所有资源被下载到的目录：

```text
...
Do you want to continue? [y/N]: y

Your compose stack "oci://registry.example.com/stack:latest" is stored in "~/Library/Caches/docker-compose/964e715660d6f6c3b384e05e7338613795f7dcd3613890cfa57e3540353b9d6d"
```

`docker compose publish` 命令支持非交互式执行，通过包含 `-y`（或 `--yes`）标志可以跳过确认提示：

```console
$ docker compose publish -y username/my-compose-app:latest
```

## 下一步

- [熟悉 Compose 的信任模型](/compose/trust-model/)
- [了解 Docker Hub 中的 OCI 构件](/docker-hub/repos/manage/hub-images/oci-artifacts/)
- [Compose publish 命令](/reference/cli/docker/compose/publish/)
- [理解 `include`](/reference/compose-file/include/)