# 合并 Compose 文件

Docker Compose 允许您将一组 Compose 文件合并和覆盖在一起，以创建一个复合的 Compose 文件。

默认情况下，Compose 读取两个文件：一个 `compose.yaml` 和一个可选的 `compose.override.yaml` 文件。按照惯例，`compose.yaml` 包含您的基础配置。override 文件可以包含对现有 services 的配置覆盖或全新的 services。

如果某个 service 在两个文件中都被定义了，Compose 将使用下面描述的规则以及 [Compose Specification](/reference/compose-file/merge/) 中的规则来合并配置。

## 如何合并多个 Compose 文件

要使用多个 override 文件或使用不同名称的 override 文件，您可以使用预定义的 [COMPOSE_FILE](/compose/how-tos/environment-variables/envvars/#compose_file) 环境变量，或者使用 `-f` 选项来指定文件列表。Compose 按照它们在命令行中指定的顺序合并文件。后面的文件可能会合并、覆盖或添加到前面的文件。

例如：

```console
$ docker compose -f compose.yaml -f compose.admin.yaml run backup_db
```

`compose.yaml` 文件可能指定了一个 `webapp` service：

```yaml
webapp:
  image: examples/web
  ports:
    - "8000:8000"
  volumes:
    - "/data"
```

`compose.admin.yaml` 也可能指定同一个 service：

```yaml
webapp:
  environment:
    - DEBUG=1
```

任何匹配的字段都会覆盖前一个文件中的值。新值会被添加到 `webapp` service 的配置中：

```yaml
webapp:
  image: examples/web
  ports:
    - "8000:8000"
  volumes:
    - "/data"
  environment:
    - DEBUG=1
```

## 合并规则

- 路径是相对于基础文件进行解析的。当您使用多个 Compose 文件时，必须确保所有文件中的路径都相对于基础 Compose 文件（即第一个通过 `-f` 指定的 Compose 文件）。这是因为 override 文件不一定是有效的 Compose 文件。Override 文件可能包含小的配置片段。跟踪 service 的哪个片段相对于哪个路径是困难且令人困惑的，因此为了更容易理解路径，所有路径都必须相对于基础文件定义。

  >[!TIP]
  >
  > 您可以使用 `docker compose config` 来查看合并后的配置并避免与路径相关的问题。

- Compose 将配置从原始 service 复制到本地 service。如果某个配置选项同时定义在原始 service 和本地 service 中，则本地的值会替换或扩展原始值。

  - 对于单值选项，如 `image`、`command` 或 `mem_limit`，新值会替换旧值。

    原始 service：

    ```yaml
    services:
      myservice:
        # ...
        command: python app.py
    ```

    本地 service：

    ```yaml
    services:
      myservice:
        # ...
        command: python otherapp.py
    ```

    结果：

    ```yaml
    services:
      myservice:
        # ...
        command: python otherapp.py
    ```

  - 对于多值选项 `ports`、`expose`、`external_links`、`dns`、`dns_search` 和 `tmpfs`，Compose 会将两组值连接起来：

    原始 service：

    ```yaml
    services:
      myservice:
        # ...
        expose:
          - "3000"
    ```

    本地 service：

    ```yaml
    services:
      myservice:
        # ...
        expose:
          - "4000"
          - "5000"
    ```

    结果：

    ```yaml
    services:
      myservice:
        # ...
        expose:
          - "3000"
          - "4000"
          - "5000"
    ```

  - 对于 `environment`、`labels`、`volumes` 和 `devices`，Compose 会“合并”条目，本地定义的值优先。对于 `environment` 和 `labels`，环境变量名或标签名决定了使用哪个值：

    原始 service：

    ```yaml
    services:
      myservice:
        # ...
        environment:
          - FOO=original
          - BAR=original
    ```

    本地 service：

    ```yaml
    services:
      myservice:
        # ...
        environment:
          - BAR=local
          - BAZ=local
    ```

    结果：

    ```yaml
    services:
      myservice:
        # ...
        environment:
          - FOO=original
          - BAR=local
          - BAZ=local
    ```

  - `volumes` 和 `devices` 的条目使用容器内的挂载路径进行合并：

    原始 service：

    ```yaml
    services:
      myservice:
        # ...
        volumes:
          - ./original:/foo
          - ./original:/bar
    ```

    本地 service：

    ```yaml
    services:
      myservice:
        # ...
        volumes:
          - ./local:/bar
          - ./local:/baz
    ```

    结果：

    ```yaml
    services:
      myservice:
        # ...
        volumes:
          - ./original:/foo
          - ./local:/bar
          - ./local:/baz
    ```

有关更多合并规则，请参阅 Compose Specification 中的 [合并与覆盖](/reference/compose-file/merge/)。

### 补充信息

- 使用 `-f` 是可选的。如果未提供，Compose 会在工作目录及其父目录中搜索 `compose.yaml` 和 `compose.override.yaml` 文件。您必须至少提供 `compose.yaml` 文件。如果两个文件位于同一目录级别，Compose 会将它们合并为一个配置。

- 您可以使用 `-f` 并将 `-`（短横线）作为文件名，从 `stdin` 读取配置。例如：
   ```console
   $ docker compose -f - <<EOF
     webapp:
       image: examples/web
       ports:
        - "8000:8000"
       volumes:
        - "/data"
       environment:
        - DEBUG=1
     EOF
   ```
   使用 `stdin` 时，配置中的所有路径都相对于当前工作目录。

- 您可以使用 `-f` 标志来指定不在当前目录中的 Compose 文件的路径，可以通过命令行或在 shell 或环境文件中设置 [COMPOSE_FILE 环境变量](/compose/how-tos/environment-variables/envvars/#compose_file)来实现。

  例如，如果您正在运行 [Compose Rails 示例](https://github.com/docker/awesome-compose/tree/master/official-documentation-samples/rails/README.md)，并且在一个名为 `sandbox/rails` 的目录中有一个 `compose.yaml` 文件。您可以使用像 [docker compose pull](/reference/cli/docker/compose/pull/) 这样的命令，通过如下使用 `-f` 标志从任何地方为 `db` service 获取 postgres image：`docker compose -f ~/sandbox/rails/compose.yaml pull db`

  以下是完整的示例：

  ```console
  $ docker compose -f ~/sandbox/rails/compose.yaml pull db
  Pulling db (postgres:18)...
  18: Pulling from library/postgres
  ef0380f84d05: Pull complete
  50cf91dc1db8: Pull complete
  d3add4cd115c: Pull complete
  467830d8a616: Pull complete
  089b9db7dc57: Pull complete
  6fba0a36935c: Pull complete
  81ef0e73c953: Pull complete
  338a6c4894dc: Pull complete
  15853f32f67c: Pull complete
  044c83d92898: Pull complete
  17301519f133: Pull complete
  dcca70822752: Pull complete
  cecf11b8ccf3: Pull complete
  Digest: sha256:1364924c753d5ff7e2260cd34dc4ba05ebd40ee8193391220be0f9901d4e1651
  Status: Downloaded newer image for postgres:18
  ```

## 示例

多文件的一个常见用例是更改开发 Compose 应用，使其适应类似生产的环境（可能是 production、staging 或 CI）。为了支持这些差异，您可以将 Compose 配置拆分为几个不同的文件：

从一个定义 services 规范配置的基础文件开始。

`compose.yaml`

```yaml
services:
  web:
    image: example/my_web_app:latest
    depends_on:
      - db
      - cache

  db:
    image: postgres:18

  cache:
    image: redis:latest
```

在此示例中，开发配置将一些端口暴露给主机，将我们的代码挂载为 volume，并构建 web image。

`compose.override.yaml`

```yaml
services:
  web:
    build: .
    volumes:
      - '.:/code'
    ports:
      - 8883:80
    environment:
      DEBUG: 'true'

  db:
    command: '-d'
    ports:
     - 5432:5432

  cache:
    ports:
      - 6379:6379
```

当您运行 `docker compose up` 时，它会自动读取 override 文件。

要在生产环境中使用此 Compose 应用，会创建另一个 override 文件，该文件可能存储在不同的 git 仓库中或由不同的团队管理。

`compose.prod.yaml`

```yaml
services:
  web:
    ports:
      - 80:80
    environment:
      PRODUCTION: 'true'

  cache:
    environment:
      TTL: '500'
```

要使用此生产 Compose 文件进行部署，您可以运行：

```console
$ docker compose -f compose.yaml -f compose.prod.yaml up -d
```

这将使用 `compose.yaml` 和 `compose.prod.yaml` 中的配置部署所有三个 services，而不使用 `compose.override.yaml` 中的开发配置。

有关更多信息，请参阅[在生产环境中使用 Compose](/compose/how-tos/production/)。

## 限制

Docker Compose 支持对要包含在应用模型中的许多资源使用相对路径：service images 的构建上下文、定义环境变量的文件位置、bind-mounted volume 中使用的本地目录路径。由于这样的限制，monorepo 中的代码组织可能会变得困难，因为自然的选择是为每个团队或组件设置专用文件夹，但那样 Compose 文件的相对路径就变得不相关了。

## 参考信息

- [合并规则](/reference/compose-file/merge/)