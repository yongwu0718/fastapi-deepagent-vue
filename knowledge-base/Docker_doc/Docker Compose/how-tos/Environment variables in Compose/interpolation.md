# 使用插值（interpolation）在 Compose 文件中设置、使用和管理变量

Compose 文件可以使用变量来提供更大的灵活性。如果您想快速切换 image 标签以测试多个版本，或者想根据本地环境调整 volume 源，您不需要每次都编辑 Compose 文件，只需设置变量，在运行时将值插入到 Compose 文件中即可。

插值（interpolation）也可用于在运行时将值插入到 Compose 文件中，进而将变量传递到容器的环境中。

下面是一个简单的示例：

```console
$ cat .env
TAG=v1.5
$ cat compose.yaml
services:
  web:
    image: "webapp:${TAG}"
```

当您运行 `docker compose up` 时，Compose 文件中定义的 `web` service 会将 image `webapp:v1.5` [插值](/compose/how-tos/environment-variables/variable-interpolation/variable-interpolation/)进来，该值是在 `.env` 文件中设置的。您可以使用 [config 命令](/reference/cli/docker/compose/config/)来验证，该命令会将解析后的应用配置打印到终端：

```console
$ docker compose config
services:
  web:
    image: 'webapp:v1.5'
```

## 插值语法（interpolation syntax）

插值适用于未加引号和双引号的值。
支持大括号形式（`${VAR}`）和无大括号形式（`$VAR`）。

对于大括号表达式，支持以下格式：
- 直接替换
  - `${VAR}` -> `VAR` 的值
- 默认值
  - `${VAR:-default}` -> 如果 `VAR` 已设置且非空，则为 `VAR` 的值，否则为 `default`
  - `${VAR-default}` -> 如果 `VAR` 已设置，则为 `VAR` 的值，否则为 `default`
- 必需值
  - `${VAR:?error}` -> 如果 `VAR` 已设置且非空，则为 `VAR` 的值，否则退出并报错
  - `${VAR?error}` -> 如果 `VAR` 已设置，则为 `VAR` 的值，否则退出并报错
- 替代值
  - `${VAR:+replacement}` -> 如果 `VAR` 已设置且非空，则为 `replacement`，否则为空
  - `${VAR+replacement}` -> 如果 `VAR` 已设置，则为 `replacement`，否则为空

更多信息请参见 Compose Specification 中的 [插值（Interpolation）](/reference/compose-file/interpolation/)。

## 使用插值设置变量的方法

Docker Compose 可以从多个源将变量插值到您的 Compose 文件中。

请注意，当同一个变量被多个源声明时，优先级规则如下：

1. 来自 shell 环境的变量
2. 如果未设置 `--env-file`，则由本地工作目录（`PWD`）中的 `.env` 文件设置的变量
3. 由 `--env-file` 设置的文件或项目目录中的 `.env` 文件设置的变量

您可以通过运行 `docker compose config --environment` 来检查 Compose 用于插值 Compose model 的变量和值。

### `.env` 文件

Docker Compose 中的 `.env` 文件是一个文本文件，用于定义在运行 `docker compose up` 时应可用于插值的变量。该文件通常包含变量的键值对，让您能够集中在一个地方管理和配置。当您需要存储多个变量时，`.env` 文件非常有用。

`.env` 文件是设置变量的默认方法。`.env` 文件应放置在项目目录的根目录下，与 `compose.yaml` 文件相邻。有关环境文件格式的更多信息，请参阅[环境文件语法](#env-file-syntax)。

基本示例：

```console
$ cat .env
## 根据 DEV_MODE 定义 COMPOSE_DEBUG，默认为 false
COMPOSE_DEBUG=${DEV_MODE:-false}

$ cat compose.yaml 
  services:
    webapp:
      image: my-webapp-image
      environment:
        - DEBUG=${COMPOSE_DEBUG}

$ DEV_MODE=true docker compose config
services:
  webapp:
    environment:
      DEBUG: "true"
```

#### 补充信息

- 如果您在 `.env` 文件中定义了一个变量，您可以在 `compose.yaml` 中通过 [`environment` 属性](/reference/compose-file/services/#environment)直接引用它。例如，如果您的 `.env` 文件包含环境变量 `DEBUG=1`，并且您的 `compose.yaml` 文件如下所示：
   ```yaml
    services:
      webapp:
        image: my-webapp-image
        environment:
          - DEBUG=${DEBUG}
   ```
   Docker Compose 会将 `${DEBUG}` 替换为 `.env` 文件中的值。

   > [!IMPORTANT]
   >
   > 当在 `.env` 文件中使用变量作为容器环境中的环境变量时，请注意[环境变量优先级](/compose/how-tos/environment-variables/variable-interpolation/envvars-precedence/)。

- 您可以将 `.env` 文件放在项目根目录以外的位置，然后在 CLI 中使用 [`--env-file` 选项](#substitute-with---env-file)，以便 Compose 能够找到它。

- 您的 `.env` 文件可以被另一个 `.env` 文件覆盖，如果该文件是通过 `--env-file` [替换](#substitute-with---env-file)的。

> [!IMPORTANT]
>
> 从 `.env` 文件进行替换是 Docker Compose CLI 的一项功能。
>
> 在 Swarm 中运行 `docker stack deploy` 时不支持此功能。

#### `.env` 文件语法

以下语法规则适用于环境文件：

- 以 `#` 开头的行被视为注释并被忽略。
- 空白行被忽略。
- 未加引号和双引号（`"`）的值会应用插值。
- 每行代表一个键值对。值可以选择性地加引号。
- 分隔键和值的分隔符可以是 `=` 或 `:`。
- 值前后的空格被忽略。
  - `VAR=VAL` -> `VAL`
  - `VAR="VAL"` -> `VAL`
  - `VAR='VAL'` -> `VAL`
  - `VAR: VAL` -> `VAL`
  - `VAR = VAL  ` -> `VAL`
- 对于未加引号的值，行内注释必须以空格开头。
  - `VAR=VAL # comment` -> `VAL`
  - `VAR=VAL# not a comment` -> `VAL# not a comment`
- 对于加引号的值，行内注释必须跟在结束引号之后。
  - `VAR="VAL # not a comment"` -> `VAL # not a comment`
  - `VAR="VAL" # comment` -> `VAL`
- 单引号（`'`）的值按字面意思使用。
  - `VAR='$OTHER'` -> `$OTHER`
  - `VAR='${OTHER}'` -> `${OTHER}`
- 引号可以用 `\` 转义。
  - `VAR='Let\'s go!'` -> `Let's go!`
  - `VAR="{\"hello\": \"json\"}"` -> `{"hello": "json"}`
- 常见的 shell 转义序列，包括 `\n`、`\r`、`\t` 和 `\\`，在双引号值中受支持。
  - `VAR="some\tvalue"` -> `some  value`
  - `VAR='some\tvalue'` -> `some\tvalue`
  - `VAR=some\tvalue` -> `some\tvalue`
- 单引号值可以跨越多行。示例：

   ```yaml
   KEY='SOME
   VALUE'
   ```

   如果您随后运行 `docker compose config`，您将看到：

   ```yaml
   environment:
     KEY: |-
       SOME
       VALUE
   ```

### 使用 `--env-file` 进行替换

您可以在一个 `.env` 文件中为多个环境变量设置默认值，然后在 CLI 中将该文件作为参数传递。

这种方法的优点是可以将文件存储在任何位置并适当地命名。该文件路径是相对于执行 Docker Compose 命令的当前工作目录的。使用 `--env-file` 选项传递文件路径：

```console
$ docker compose --env-file ./config/.env.dev up
```

#### 补充信息

- 如果您想临时覆盖已在 `compose.yaml` 文件中引用的 `.env` 文件，此方法非常有用。例如，您可能为生产环境（`.env.prod`）和测试环境（`.env.test`）准备了不同的 `.env` 文件。
  在以下示例中，有两个环境文件：`.env` 和 `.env.dev`。它们为 `TAG` 设置了不同的值。
  ```console
  $ cat .env
  TAG=v1.5
  $ cat ./config/.env.dev
  TAG=v1.6
  $ cat compose.yaml
  services:
    web:
      image: "webapp:${TAG}"
  ```
  如果命令行中未使用 `--env-file`，则默认加载 `.env` 文件：
  ```console
  $ docker compose config
  services:
    web:
      image: 'webapp:v1.5'
  ```
  传递 `--env-file` 参数会覆盖默认文件路径：
  ```console
  $ docker compose --env-file ./config/.env.dev config
  services:
    web:
      image: 'webapp:v1.6'
  ```
  当传递无效的文件路径作为 `--env-file` 参数时，Compose 会返回错误：
  ```console
  $ docker compose --env-file ./doesnotexist/.env.dev  config
  ERROR: Couldn't find env file: /home/user/./doesnotexist/.env.dev
  ```
- 您可以使用多个 `--env-file` 选项来指定多个环境文件，Docker Compose 会按顺序读取它们。后面的文件可以覆盖前面文件中的变量。
  ```console
  $ docker compose --env-file .env --env-file .env.override up
  ```
- 您可以在启动容器时从命令行覆盖特定的环境变量。
  ```console
  $ docker compose --env-file .env.dev up -e DATABASE_URL=mysql://new_user:new_password@new_db:3306/new_database
  ```

### 本地 `.env` 文件与项目目录 `.env` 文件

`.env` 文件也可用于声明[预定义的环境变量](/compose/how-tos/environment-variables/variable-interpolation/envvars/)，以控制 Compose 行为和要加载的文件。

当没有显式的 `--env-file` 标志执行时，Compose 会在您的工作目录（[PWD](https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html#index-PWD)）中搜索 `.env` 文件，并加载其中的值，既用于自身配置也用于插值。如果该文件中的值定义了预定义变量 `COMPOSE_FILE`，导致项目目录被设置为另一个文件夹，Compose 将加载第二个 `.env` 文件（如果存在）。这第二个 `.env` 文件的优先级较低。

这种机制使得可以使用一组自定义变量作为覆盖来调用现有的 Compose 项目，而无需通过命令行传递环境变量。

```console
$ cat .env
COMPOSE_FILE=../compose.yaml
POSTGRES_VERSION=9.3

$ cat ../compose.yaml 
services:
  db:
    image: "postgres:${POSTGRES_VERSION}"
$ cat ../.env
POSTGRES_VERSION=9.2

$ docker compose config
services:
  db:
    image: "postgres:9.3"
```

### 从 shell 替换

您可以使用来自主机或执行 `docker compose` 命令的 shell 环境中现有的环境变量。这使您可以在运行时动态地将值注入到 Docker Compose 配置中。
例如，假设 shell 中包含 `POSTGRES_VERSION=9.3`，并且您提供以下配置：

```yaml
db:
  image: "postgres:${POSTGRES_VERSION}"
```

当您使用此配置运行 `docker compose up` 时，Compose 会在 shell 中查找 `POSTGRES_VERSION` 环境变量并替换其值。在此示例中，Compose 在运行配置之前将 image 解析为 `postgres:9.3`。

如果某个环境变量未设置，Compose 会用空字符串替换。在前面的示例中，如果未设置 `POSTGRES_VERSION`，则 image 选项的值为 `postgres:`。

> [!NOTE]
>
> `postgres:` 不是一个有效的 image 引用。Docker 期望要么是不带标签的引用（如 `postgres`，它默认为 latest image），要么是带有标签的引用（如 `postgres:15`）。