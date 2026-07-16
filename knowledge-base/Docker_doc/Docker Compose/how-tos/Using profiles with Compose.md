以下是删除重复内容后的完整文档：

# 使用 Compose 的 profiles

Profiles 帮助您根据不同的环境或使用场景调整 Compose 应用，通过选择性地激活 services。Services 可以被分配到一个或多个 profiles；未分配 profile 的 services 默认会启动/停止，而分配了 profile 的 services 仅在其 profile 激活时才启动/停止。这种设置允许将特定 services（例如用于调试或开发的 services）包含在单个 `compose.yml` 文件中，并仅在需要时激活。

## 为 services 分配 profiles

Services 通过 [`profiles` 属性](/reference/compose-file/services/#profiles)与 profiles 关联，该属性接受一个 profile 名称的数组：

```yaml
services:
  frontend:
    image: frontend
    profiles: [frontend]

  phpmyadmin:
    image: phpmyadmin
    depends_on: [db]
    profiles: [debug]

  backend:
    image: backend

  db:
    image: mysql
```

在此，services `frontend` 和 `phpmyadmin` 分别分配给了 profile `frontend` 和 `debug`，因此它们仅当各自的 profile 启用时才会启动。

没有 `profiles` 属性的 services 始终被启用。在这种情况下，运行 `docker compose up` 只会启动 `backend` 和 `db`。

有效的 profile 名称遵循正则表达式格式 `[a-zA-Z0-9][a-zA-Z0-9_.-]+`。

> [!TIP]
>
> 应用的核心 services 不应分配 `profiles`，以便它们始终被启用并自动启动。

## 启动特定的 profiles

要启动特定的 profile，请使用 `--profile` [命令行选项](/reference/cli/docker/compose/)或 [`COMPOSE_PROFILES` 环境变量](/compose/how-tos/profiles/environment-variables/envvars/#compose_profiles)：

```console
docker compose --profile debug up
```
```console
COMPOSE_PROFILES=debug docker compose up
```

这两个命令都会启动启用了 `debug` profile 的 services。在前面的 `compose.yaml` 文件中，这将启动 services `db`、`backend` 和 `phpmyadmin`。

### 启动多个 profiles

您也可以启用多个 profiles，例如使用 `docker compose --profile frontend --profile debug up` 将启用 profiles `frontend` 和 `debug`。

可以通过传递多个 `--profile` 标志或为 `COMPOSE_PROFILES` 环境变量传递逗号分隔的列表来指定多个 profiles：

```console
docker compose --profile frontend --profile debug up
```

```console
COMPOSE_PROFILES=frontend,debug docker compose up
```

如果您想同时启用所有 profiles，可以运行 `docker compose --profile "*"`。

## 自动启动 profiles 与依赖解析

当您在命令行上明确指定一个分配了一个或多个 profiles 的 service 时，您不需要手动启用该 profile，因为 Compose 会运行该 service，无论其 profile 是否激活。这对于运行一次性 services 或调试工具非常有用。

只有被明确指定的 service（以及通过 `depends_on` 声明的依赖项）会被启动。共享同一个 profile 的其他 services 不会被启动，除非：
- 它们也被明确指定，或者
- 使用 `--profile` 或 `COMPOSE_PROFILES` 显式启用了该 profile。

当命令行上明确指定了一个分配了 `profiles` 的 service 时，其 profiles 会自动启动，因此您不需要手动启动它们。这可用于一次性 services 和调试工具。例如，考虑以下配置：

```yaml
services:
  backend:
    image: backend

  db:
    image: mysql

  db-migrations:
    image: backend
    command: myapp migrate
    depends_on:
      - db
    profiles:
      - tools
```

```sh
# 仅启动 backend 和 db（不涉及 profiles）
docker compose up -d

# 运行 db-migrations service，无需手动启用 'tools' profile
docker compose run db-migrations
```

在此示例中，`db-migrations` 运行，尽管它被分配给了 tools profile，因为它被明确指定了。`db` service 也会自动启动，因为它被列在 `depends_on` 中。

如果指定的 service 所具有的依赖也被 profile 所限制，您必须确保这些依赖要么：
- 在同一个 profile 中
- 单独启动
- 未分配给任何 profile，从而始终被启用

## 使用特定 profiles 停止应用和 services

与启动特定 profiles 类似，您可以使用 `--profile` [命令行选项](/reference/cli/docker/compose/#use--p-to-specify-a-project-name)或 [`COMPOSE_PROFILES` 环境变量](/compose/how-tos/profiles/environment-variables/envvars/#compose_profiles)：

```console
docker compose --profile debug down
```
```console
COMPOSE_PROFILES=debug docker compose down
```

这两个命令都会停止并移除具有 `debug` profile 的 services 以及没有 profile 的 services。在下面的 `compose.yaml` 文件中，这将停止 services `db`、`backend` 和 `phpmyadmin`。

```yaml
services:
  frontend:
    image: frontend
    profiles: [frontend]

  phpmyadmin:
    image: phpmyadmin
    depends_on: [db]
    profiles: [debug]

  backend:
    image: backend

  db:
    image: mysql
```

如果您只想停止 `phpmyadmin` service，可以运行：

```console 
docker compose down phpmyadmin
``` 
或 
```console 
docker compose stop phpmyadmin
```

> [!NOTE]
>
> 运行 `docker compose down` 只会停止 `backend` 和 `db`。

## 参考信息

[`profiles`](/reference/compose-file/services/#profiles)