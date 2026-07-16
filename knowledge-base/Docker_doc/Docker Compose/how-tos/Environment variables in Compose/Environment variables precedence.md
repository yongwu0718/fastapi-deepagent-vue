# Docker Compose 中的环境变量优先级（precedence）

当同一个环境变量在多个源中被设置时，Docker Compose 会遵循优先级规则来确定该变量在容器环境中的最终值。

本页解释了当环境变量在多个位置定义时，Docker Compose 如何确定其最终值。

优先级顺序（从高到低）如下：
1. 通过 CLI 中的 [`docker compose run -e` 设置](/compose/how-tos/environment-variables/envvars-precedence/set-environment-variables/#set-environment-variables-with-docker-compose-run---env)。
2. 通过 `environment` 或 `env_file` 属性设置，但其值从 [shell](/compose/how-tos/environment-variables/envvars-precedence/variable-interpolation/#substitute-from-the-shell) 或环境文件（默认的 [`.env` 文件](/compose/how-tos/environment-variables/envvars-precedence/variable-interpolation/#env-file)，或 CLI 中的 [`--env-file` 参数](/compose/how-tos/environment-variables/envvars-precedence/variable-interpolation/#substitute-with---env-file)）进行插值（interpolated）。
3. 仅使用 Compose 文件中的 [`environment` 属性](/compose/how-tos/environment-variables/envvars-precedence/set-environment-variables/#use-the-environment-attribute)设置。
4. 使用 Compose 文件中的 [`env_file` 属性](/compose/how-tos/environment-variables/envvars-precedence/set-environment-variables/#use-the-env_file-attribute)设置。
5. 在容器镜像的 [ENV 指令](/reference/dockerfile/#env)中设置。
   仅当 Docker Compose 中没有 `environment`、`env_file` 或 `run --env` 条目时，Dockerfile 中的 `ARG` 或 `ENV` 设置才会生效。

## 简单示例

在以下示例中，同一个环境变量在 `.env` 文件和 Compose 文件的 `environment` 属性中有不同的值：

```console
$ cat ./webapp.env
NODE_ENV=test

$ cat compose.yaml
services:
  webapp:
    image: 'webapp'
    env_file:
     - ./webapp.env
    environment:
     - NODE_ENV=production
```

使用 `environment` 属性定义的环境变量优先级更高。

```console
$ docker compose run webapp env | grep NODE_ENV
NODE_ENV=production
```

## 高级示例

下表以 `VALUE` 这个环境变量为例，它定义了一个镜像的版本。

### 表格说明

每一列代表一个可以设置值或替换值的上下文。

`Host OS environment` 和 `.env` 文件列仅用于说明。实际上，它们本身不会在容器中产生变量，而是与 `environment` 或 `env_file` 属性结合使用。

每一行代表 `VALUE` 被设置、替换或两者兼有的上下文组合。**Result** 列表示每种场景下 `VALUE` 的最终值。

|  # |  `docker compose run`  |  `environment` 属性  |  `env_file` 属性  |  镜像 `ENV` |  `Host OS` 环境  |  `.env` 文件      |   结果       |
|:--:|:----------------:|:-------------------------------:|:----------------------:|:------------:|:-----------------------:|:-----------------:|:----------:|
|  1 |   -              |   -                             |   -                    |   -          |  `VALUE=1.4`            |  `VALUE=1.3`      | -               |
|  2 |   -              |   -                             |  `VALUE=1.6`           |  `VALUE=1.5` |  `VALUE=1.4`            |   -               |**`VALUE=1.6`**  |
|  3 |   -              |  `VALUE=1.7`                    |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |   -               |**`VALUE=1.7`**  |
|  4 |   -              |   -                             |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.5`**  |
|  5 |`--env VALUE=1.8` |   -                             |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.8`**  |
|  6 |`--env VALUE`     |   -                             |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.4`**  |
|  7 |`--env VALUE`     |   -                             |   -                    |  `VALUE=1.5` |   -                     |  `VALUE=1.3`      |**`VALUE=1.3`**  |
|  8 |   -              |   -                             |   `VALUE`              |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.4`**  |
|  9 |   -              |   -                             |   `VALUE`              |  `VALUE=1.5` |   -                     |  `VALUE=1.3`      |**`VALUE=1.3`**  |
| 10 |   -              |  `VALUE`                        |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.4`**  |
| 11 |   -              |  `VALUE`                        |   -                    |  `VALUE=1.5` |  -                      |  `VALUE=1.3`      |**`VALUE=1.3`**  |
| 12 |`--env VALUE`     |  `VALUE=1.7`                    |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.4`**  |
| 13 |`--env VALUE=1.8` |  `VALUE=1.7`                    |   -                    |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.8`**  |
| 14 |`--env VALUE=1.8` |   -                             |  `VALUE=1.6`           |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.8`**  |
| 15 |`--env VALUE=1.8` |  `VALUE=1.7`                    |  `VALUE=1.6`           |  `VALUE=1.5` |  `VALUE=1.4`            |  `VALUE=1.3`      |**`VALUE=1.8`**  |

### 理解优先级结果

结果 1：本地环境优先级更高，但 Compose 文件未设置为在容器内复制该值，因此未设置该变量。

结果 2：Compose 文件中的 `env_file` 属性为 `VALUE` 定义了一个显式值，因此容器环境被相应设置。

结果 3：Compose 文件中的 `environment` 属性为 `VALUE` 定义了一个显式值，因此容器环境被相应设置。

结果 4：镜像的 `ENV` 指令声明了变量 `VALUE`，由于 Compose 文件未设置为覆盖该值，因此该变量由镜像定义。

结果 5：`docker compose run` 命令设置了 `--env` 标志并带有显式值，覆盖了镜像设置的值。

结果 6：`docker compose run` 命令设置了 `--env` 标志以从环境复制值。Host OS 值优先级更高，并被复制到容器的环境中。

结果 7：`docker compose run` 命令设置了 `--env` 标志以从环境复制值。来自 `.env` 文件的值被选中用于定义容器的环境。

结果 8：Compose 文件中的 `env_file` 属性设置为从本地环境复制 `VALUE`。Host OS 值优先级更高，并被复制到容器的环境中。

结果 9：Compose 文件中的 `env_file` 属性设置为从本地环境复制 `VALUE`。来自 `.env` 文件的值被选中用于定义容器的环境。

结果 10：Compose 文件中的 `environment` 属性设置为从本地环境复制 `VALUE`。Host OS 值优先级更高，并被复制到容器的环境中。

结果 11：Compose 文件中的 `environment` 属性设置为从本地环境复制 `VALUE`。来自 `.env` 文件的值被选中用于定义容器的环境。

结果 12：`--env` 标志的优先级高于 `environment` 和 `env_file` 属性，并设置为从本地环境复制 `VALUE`。Host OS 值优先级更高，并被复制到容器的环境中。

结果 13 至 15：`--env` 标志的优先级高于 `environment` 和 `env_file` 属性，因此设置该值。

## 下一步

- [在 Compose 中设置环境变量](/compose/how-tos/environment-variables/envvars-precedence/set-environment-variables/)
- [在 Compose 文件中使用变量插值（interpolation）](/compose/how-tos/environment-variables/envvars-precedence/variable-interpolation/)