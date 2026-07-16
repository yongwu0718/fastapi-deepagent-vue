# 在 Docker Compose 中配置预定义的环境变量

Docker Compose 包含多个预定义的环境变量。它同时也继承了常见的 Docker CLI 环境变量，如 `DOCKER_HOST` 和 `DOCKER_CONTEXT`。详细信息请参阅 [Docker CLI 环境变量参考](/reference/cli/docker/#environment-variables)。

本页说明如何设置或更改以下预定义的环境变量：

- `COMPOSE_PROJECT_NAME`
- `COMPOSE_FILE`
- `COMPOSE_PROFILES`
- `COMPOSE_CONVERT_WINDOWS_PATHS`
- `COMPOSE_PATH_SEPARATOR`
- `COMPOSE_IGNORE_ORPHANS`
- `COMPOSE_REMOVE_ORPHANS`
- `COMPOSE_PARALLEL_LIMIT`
- `COMPOSE_ANSI`
- `COMPOSE_STATUS_STDOUT`
- `COMPOSE_ENV_FILES`
- `COMPOSE_DISABLE_ENV_FILE`
- `COMPOSE_MENU`
- `COMPOSE_EXPERIMENTAL`
- `COMPOSE_PROGRESS`

## 覆盖方法

| 方法          | 描述                                              |
| ------------- | ------------------------------------------------- |
| [`.env` 文件](/compose/how-tos/environment-variables/variable-interpolation/) | 位于工作目录中。                                  |
| [Shell](/compose/how-tos/environment-variables/envvars/variable-interpolation/#substitute-from-the-shell) | 在主机操作系统的 shell 中定义。                   |
| CLI           | 在运行时通过 `--env` 或 `-e` 标志传递。           |

在更改或设置任何环境变量时，请注意[环境变量优先级](/compose/how-tos/environment-variables/envvars/envvars-precedence/)。

## 配置详情

### 项目和文件配置

#### COMPOSE\_PROJECT\_NAME

设置项目名称（project name）。该值在启动时会与 service 名称一起作为 container 名称的前缀。

例如，如果项目名称为 `myapp`，且包含两个 services `db` 和 `web`，则 Compose 会分别启动名为 `myapp-db-1` 和 `myapp-web-1` 的 containers。

Compose 可以通过不同方式设置项目名称。每种方法的优先级（从高到低）如下：

1. `-p` 命令行标志
2. `COMPOSE_PROJECT_NAME`
3. 配置文件中的顶层 `name:` 变量（或使用 `-f` 指定的一系列配置文件中的最后一个 `name:`）
4. 包含配置文件的项目目录的基名（或包含使用 `-f` 指定的第一个配置文件的目录的基名）
5. 如果未指定配置文件，则使用当前目录的基名

项目名称只能包含小写字母、数字、短横线和下划线，并且必须以小写字母或数字开头。如果项目目录或当前目录的基名违反此约束，您必须使用其他机制之一。

另请参阅 [使用 `-p` 指定项目名称](/reference/cli/docker/compose/#use--p-to-specify-a-project-name)。

#### COMPOSE\_FILE

指定一个或多个 Compose 文件的路径。支持指定多个 Compose 文件。

- 默认行为：如果未提供，Compose 会在当前目录中查找名为 `compose.yaml` 的文件；如果未找到，则会递归搜索每个父目录，直到找到该名称的文件。
- 当指定多个 Compose 文件时，路径分隔符默认为：
   - Mac 和 Linux：`:` (冒号)
   - Windows：`;` (分号)
   例如：
   ```console
   COMPOSE_FILE=compose.yaml:compose.prod.yaml
   ```
   路径分隔符也可以使用 [`COMPOSE_PATH_SEPARATOR`](#compose_path_separator) 进行自定义。

另请参阅 [使用 `-f` 指定一个或多个 Compose 文件的名称和路径](/reference/cli/docker/compose/#use--f-to-specify-the-name-and-path-of-one-or-more-compose-files)。

#### COMPOSE\_PROFILES

指定在运行 `docker compose up` 时要启用的一个或多个 profiles。

具有匹配 profile 的 services 以及未定义任何 profile 的 services 都会被启动。

例如，使用 `COMPOSE_PROFILES=frontend` 调用 `docker compose up` 会选中具有 `frontend` profile 的 services，以及任何未指定 profile 的 services。

如果指定多个 profiles，请使用逗号作为分隔符。

以下示例启用与 `frontend` 和 `debug` profiles 匹配的所有 services，以及没有 profile 的 services。

```console
COMPOSE_PROFILES=frontend,debug
```

另请参阅 [在 Compose 中使用 profiles](/compose/how-tos/profiles/) 以及 [`--profile` 命令行选项](/reference/cli/docker/compose/#use-profiles-to-enable-optional-services)。

#### COMPOSE\_PATH\_SEPARATOR

为 `COMPOSE_FILE` 中列出的项指定不同的路径分隔符。

- 默认为：
    - 在 macOS 和 Linux 上为 `:`
    - 在 Windows 上为 `;`

#### COMPOSE\_ENV\_FILES

指定当未使用 `--env-file` 时 Compose 应使用哪些环境文件。

当使用多个环境文件时，请使用逗号作为分隔符。例如：

```console
COMPOSE_ENV_FILES=.env.envfile1,.env.envfile2
```

如果未设置 `COMPOSE_ENV_FILES`，并且您在 CLI 中没有提供 `--env-file`，Docker Compose 将使用默认行为，即在项目目录中查找 `.env` 文件。

#### COMPOSE\_DISABLE\_ENV\_FILE

允许您禁用默认的 `.env` 文件的使用。

- 支持的值：
    - `true` 或 `1`，Compose 忽略 `.env` 文件
    - `false` 或 `0`，Compose 在项目目录中查找 `.env` 文件
- 默认值：`0`

### 环境处理与容器生命周期

#### COMPOSE\_CONVERT\_WINDOWS\_PATHS

启用后，Compose 会在 volume 定义中执行从 Windows 风格到 Unix 风格的路径转换。

- 支持的值：
    - `true` 或 `1`，启用
    - `false` 或 `0`，禁用
- 默认值：`0`

#### COMPOSE\_IGNORE\_ORPHANS

启用后，Compose 不会尝试检测项目的孤儿（orphaned）容器。

- 支持的值：
   - `true` 或 `1`，启用
   - `false` 或 `0`，禁用
- 默认值：`0`

#### COMPOSE\_REMOVE\_ORPHANS

启用后，Compose 在更新 service 或 stack 时会自动移除孤儿（orphaned）容器。孤儿容器是指由先前配置创建但不再在当前 `compose.yaml` 文件中定义的 containers。

- 支持的值：
   - `true` 或 `1`，启用孤儿容器的自动移除
   - `false` 或 `0`，禁用自动移除。Compose 会显示关于孤儿容器的警告。
- 默认值：`0`

#### COMPOSE\_PARALLEL\_LIMIT

指定并发引擎调用的最大并行度。

### 输出

#### COMPOSE\_ANSI

指定何时打印 ANSI 控制字符。

- 支持的值：
   - `auto`，Compose 检测是否可以使用 TTY 模式。否则，使用纯文本模式
   - `never`，使用纯文本模式
   - `always` 或 `0`，使用 TTY 模式
- 默认值：`auto`

#### COMPOSE\_STATUS\_STDOUT

启用后，Compose 会将其内部状态和进度消息写入 `stdout` 而不是 `stderr`。
默认值为 false，以便清晰区分 Compose 消息和容器日志的输出流。

- 支持的值：
   - `true` 或 `1`，启用
   - `false` 或 `0`，禁用
- 默认值：`0`

#### COMPOSE\_PROGRESS

定义进度输出的类型（如果未使用 `--progress`）。

支持的值有 `auto`、`tty`、`plain`、`json` 和 `quiet`。
默认值为 `auto`。

### 用户体验

#### COMPOSE\_MENU

启用后，Compose 会显示一个导航菜单，您可以在其中选择在 Docker Desktop 中打开 Compose stack、切换到 [`watch` 模式](/compose/how-tos/file-watch/)或使用 [Docker Debug](/reference/cli/docker/debug/)。

- 支持的值：
   - `true` 或 `1`，启用
   - `false` 或 `0`，禁用
- 默认值：如果您通过 Docker Desktop 获得 Docker Compose，则为 `1`，否则默认值为 `0`

#### COMPOSE\_EXPERIMENTAL

这是一个选择退出的变量。关闭时会停用实验性功能。

- 支持的值：
   - `true` 或 `1`，启用
   - `false` 或 `0`，禁用
- 默认值：`1`

## Compose V2 中不支持的环境变量

以下环境变量在 Compose V2 中无效。

- `COMPOSE_API_VERSION`
    默认情况下，API 版本与服务器协商。请使用 `DOCKER_API_VERSION`。
    请参阅 [Docker CLI 环境变量参考](/reference/cli/docker/#environment-variables)页面。
- `COMPOSE_HTTP_TIMEOUT`
- `COMPOSE_TLS_VERSION`
- `COMPOSE_FORCE_WINDOWS_HOST`
- `COMPOSE_INTERACTIVE_NO_CLI`
- `COMPOSE_DOCKER_CLI_BUILD`
    使用 `DOCKER_BUILDKIT` 在 BuildKit 和经典构建器之间进行选择。如果 `DOCKER_BUILDKIT=0`，则 `docker compose build` 使用经典构建器来构建 images。