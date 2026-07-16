# 扩展（Extend）您的 Compose 文件

Docker Compose 的 [`extends` 属性](/reference/compose-file/services/#extends) 允许您在不同的文件甚至完全不同的项目之间共享通用配置。

当您有多个服务（services）复用一组公共配置选项时，扩展服务（extending services）非常有用。通过 `extends`，您可以在一个地方定义一组通用的服务选项，并从任何地方引用它。您可以引用另一个 Compose 文件，选择一个您也想在自己的应用中使用的服务（service），并能够根据自身需求覆盖某些属性。

> [!IMPORTANT]
>
> 当您使用多个 Compose 文件时，必须确保所有文件中的路径都是相对于基础 Compose 文件（即您主项目文件夹中的 Compose 文件）的。这是因为扩展文件（extend files）不一定是有效的 Compose 文件。扩展文件可以包含小的配置片段。跟踪服务的哪个片段相对于哪个路径是困难且令人困惑的，因此为了更容易理解路径，所有路径都必须相对于基础文件定义。

> [!NOTE]
>
> 当使用 `docker stack deploy` 部署时，不支持 `extends`。在使用了 `extends` 的 Compose 文件上运行 `docker stack config` 会返回错误：`Configuration contains forbidden properties`。

## `extends` 属性的工作原理

### 从另一个文件扩展服务（Extending services）

以以下示例为例：

```yaml
services:
  web:
    extends:
      file: common-services.yml
      service: webapp
```

这指示 Compose 仅复用 `common-services.yml` 文件中定义的 `webapp` 服务的属性。`webapp` 服务本身不是最终项目的一部分。

如果 `common-services.yml` 如下所示：

```yaml
services:
  webapp:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - "/data"
```

您将得到与直接在 `web` 下编写具有相同 `build`、`ports` 和 `volumes` 配置值的 `compose.yaml` 完全相同的结果。

为了在从另一个文件扩展服务时，将服务 `webapp` 包含在最终项目中，您需要显式地将这两个服务都包含在当前 Compose 文件中。例如（仅用于说明）：

```yaml
services:
  web:
    build: ./alpine
    command: echo
    extends:
      file: common-services.yml
      service: webapp
  webapp:
    extends:
      file: common-services.yml
      service: webapp
```

或者，您可以使用 [include](/compose/how-tos/multiple-compose-files/extends/include/)。

### 在同一文件中扩展服务（Extending services within the same file）

如果您在同一 Compose 文件中定义服务，并且从一个服务扩展另一个服务，则原始服务和扩展服务都将成为最终配置的一部分。例如：

```yaml 
services:
  web:
    build: ./alpine
    extends: webapp
  webapp:
    environment:
      - DEBUG=1
```

### 在同一文件中以及从另一个文件扩展服务

您可以更进一步，在 `compose.yaml` 中本地定义或重新定义配置：

```yaml
services:
  web:
    extends:
      file: common-services.yml
      service: webapp
    environment:
      - DEBUG=1
    cpu_shares: 5

  important_web:
    extends: web
    cpu_shares: 10
```

## 附加示例

当您有多个具有通用配置的服务时，扩展单个服务非常有用。下面的示例是一个具有两个服务的 Compose 应用：一个 Web 应用程序和一个队列 worker。这两个服务都使用相同的代码库并共享许多配置选项。

`common.yaml` 文件定义了通用配置：

```yaml
services:
  app:
    build: .
    environment:
      CONFIG_FILE_PATH: /code/config
      API_KEY: xxxyyy
    cpu_shares: 5
```

`compose.yaml` 定义了使用通用配置的具体服务：

```yaml
services:
  webapp:
    extends:
      file: common.yaml
      service: app
    command: /code/run_web_app
    ports:
      - 8080:8080
    depends_on:
      - queue
      - db

  queue_worker:
    extends:
      file: common.yaml
      service: app
    command: /code/run_worker
    depends_on:
      - queue
```

## 相对路径（Relative paths）

当 `extends` 使用指向另一个文件夹的 `file` 属性时，被扩展的服务声明的相对路径会被转换，以便在被扩展服务使用时仍然指向相同的文件。这在以下示例中得到了说明：

基础 Compose 文件：
```yaml
services:
  webapp:
    image: example
    extends:
      file: ../commons/compose.yaml
      service: base
```

`commons/compose.yaml` 文件：
```yaml
services:
  base:
    env_file: ./container.env
```

生成的服务引用 `commons` 目录内的原始 `container.env` 文件。这可以通过 `docker compose config` 来确认，它会检查实际的模型：
```yaml
services:
  webapp:
    image: example
    env_file: 
      - ../commons/container.env
```

## 参考信息

- [`extends`](/reference/compose-file/services/#extends)