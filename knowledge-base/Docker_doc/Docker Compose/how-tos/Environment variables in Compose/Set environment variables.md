# 在容器的环境中设置环境变量

容器的环境（environment）只有在服务（service）配置中显式声明时才会被设置。使用 Compose，有两种方式可以在 Compose 文件中为容器设置环境变量。

>[!TIP]
>
> 不要使用环境变量传递敏感信息（例如密码）到容器中。请改用 [secrets](/compose/how-tos/use-secrets/)。

## 使用 `environment` 属性

您可以在 `compose.yaml` 中通过 [`environment` 属性](/reference/compose-file/services/#environment)直接在容器的环境中设置环境变量。

它支持列表和映射两种语法：

```yaml
services:
  webapp:
    environment:
      DEBUG: "true"
```
等效于
```yaml
services:
  webapp:
    environment:
      - DEBUG=true
```

有关如何使用它的更多示例，请参阅 [`environment` 属性](/reference/compose-file/services/#environment)。

### 补充信息

- 您可以选择不设置值，而将 shell 中的环境变量直接传递到容器中。其工作方式与 `docker run -e VARIABLE …` 相同：
  ```yaml
  web:
    environment:
      - DEBUG
  ```
容器中 `DEBUG` 变量的值取自运行 Compose 的 shell 中同名变量的值。请注意，如果 shell 环境中的 `DEBUG` 变量未设置，此情况下不会发出警告。

- 您还可以利用 [插值（interpolation）](/compose/how-tos/environment-variables/set-environment-variables/variable-interpolation/#interpolation-syntax)。在以下示例中，结果与上述类似，但如果 `DEBUG` 变量在 shell 环境或项目目录的 `.env` 文件中未设置，Compose 会给出警告。

  ```yaml
  web:
    environment:
      - DEBUG=${DEBUG}
  ```

## 使用 `env_file` 属性

容器的环境也可以通过 [`.env` 文件](/compose/how-tos/environment-variables/set-environment-variables/variable-interpolation/#env-file)结合 [`env_file` 属性](/reference/compose-file/services/#env_file)来设置。

```yaml
services:
  webapp:
    env_file: "webapp.env"
```

使用 `.env` 文件可以让您将同一个文件用于普通的 `docker run --env-file …` 命令，或者在多个服务之间共享同一个 `.env` 文件，而无需重复编写冗长的 `environment` YAML 块。

它还可以帮助您将环境变量与主配置文件分离，提供一种更有条理且更安全的方式来管理敏感信息，因为您不需要将 `.env` 文件放在项目根目录下。

[`env_file` 属性](/reference/compose-file/services/#env_file)还允许您在 Compose 应用中使用多个 `.env` 文件。

**在 `env_file` 属性中指定的 `.env` 文件路径是相对于 `compose.yaml` 文件位置的。**

> [!IMPORTANT]
>
> 在 `.env` 文件中进行插值（interpolation）是 Docker Compose CLI 的一项功能。
>
> 运行 `docker run --env-file …` 时不支持此功能。

### 补充信息

- 如果指定了多个文件，它们将按顺序计算，并且可以覆盖之前文件中设置的值。
- 从 Docker Compose 版本 2.24.0 开始，您可以通过 `required` 字段将 `env_file` 属性定义的 `.env` 文件设置为可选的。当 `required` 设置为 `false` 且 `.env` 文件缺失时，Compose 会静默忽略该条目。
  ```yaml
  env_file:
    - path: ./default.env
      required: true # 默认值
    - path: ./override.env
      required: false
  ``` 
- 从 Docker Compose 版本 2.30.0 开始，您可以通过 `format` 属性为 `env_file` 使用替代文件格式。更多信息请参阅 [`format`](/reference/compose-file/services/#format)。
- 可以通过 [`docker compose run -e`](#使用-docker-compose-run---env-设置环境变量) 从命令行覆盖 `.env` 文件中的值。

## 使用 `docker compose run --env` 设置环境变量

与 `docker run --env` 类似，您可以使用 `docker compose run --env` 或其短格式 `docker compose run -e` 临时设置环境变量：

```console
$ docker compose run -e DEBUG=1 web python console.py
```

### 补充信息

- 您还可以通过不给变量赋值的方式，从 shell 或环境文件中传递变量：

  ```console
  $ docker compose run -e DEBUG web python console.py
  ```

容器中 `DEBUG` 变量的值取自运行 Compose 的 shell 中同名变量的值，或者取自环境文件。

## 更多资源

- [理解环境变量的优先级（precedence）](/compose/how-tos/environment-variables/set-environment-variables/envvars-precedence/)
- [设置或更改预定义的环境变量](/compose/how-tos/environment-variables/set-environment-variables/envvars/)
- [探索最佳实践](/compose/how-tos/environment-variables/set-environment-variables/best-practices/)
- [理解插值（interpolation）](/compose/how-tos/environment-variables/set-environment-variables/variable-interpolation/)