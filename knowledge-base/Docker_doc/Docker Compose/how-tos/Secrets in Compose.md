# 在 Docker Compose 中安全地管理 secrets

secret 是任何不应通过网络传输或在 Dockerfile 或应用程序源代码中未加密存储的数据片段，例如密码、证书或 API key。

Docker Compose 提供了一种使用 secrets 的方法，而无需使用 environment variables 来存储信息。如果您将密码和 API key 作为 environment variables 注入，则会面临无意中暴露信息的风险。services 只有在顶层的 `services` 元素中的 `secrets` 属性显式授予权限时才能访问 secrets。

Environment variables 通常对所有进程可用，并且难以跟踪访问。它们还可能在您不知情的情况下，在调试错误时被打印到日志中。使用 secrets 可以减轻这些风险。

## 使用 secrets

Secrets 作为文件挂载在容器内的 `/run/secrets/<secret_name>` 中。

将 secret 放入容器是一个两步过程。首先，使用 [Compose 文件中的顶层 secrets 元素](/reference/compose-file/secrets/)定义 secret。其次，更新您的 service 定义，通过 [secrets 属性](/reference/compose-file/services/#secrets)引用它们所需的 secrets。Compose 基于每个 service 授予对 secrets 的访问权限。

与其他方法不同，这允许通过标准文件系统权限在 service 容器内进行细粒度的访问控制。

## 示例

### 单 service secret 注入

在以下示例中，`frontend` service 被授予访问 `my_secret` secret 的权限。在容器中，`/run/secrets/my_secret` 被设置为文件 `./my_secret.txt` 的内容。

```yaml
services:
  myapp:
    image: myapp:latest
    secrets:
      - my_secret
secrets:
  my_secret:
    file: ./my_secret.txt
```

### 多 service secret 共享与密码管理

```yaml
services:
   db:
     image: mysql:latest
     volumes:
       - db_data:/var/lib/mysql
     environment:
       MYSQL_ROOT_PASSWORD_FILE: /run/secrets/db_root_password
       MYSQL_DATABASE: wordpress
       MYSQL_USER: wordpress
       MYSQL_PASSWORD_FILE: /run/secrets/db_password
     secrets:
       - db_root_password
       - db_password

   wordpress:
     depends_on:
       - db
     image: wordpress:latest
     ports:
       - "8000:80"
     environment:
       WORDPRESS_DB_HOST: db:3306
       WORDPRESS_DB_USER: wordpress
       WORDPRESS_DB_PASSWORD_FILE: /run/secrets/db_password
     secrets:
       - db_password

secrets:
   db_password:
     file: db_password.txt
   db_root_password:
     file: db_root_password.txt

volumes:
    db_data:
```

在上述高级示例中：

- 每个 service 下的 `secrets` 属性定义了您要注入到特定容器中的 secrets。
- 顶层的 `secrets` 部分定义了变量 `db_password` 和 `db_root_password`，并提供了填充其值的 `file`。
- 每个容器的部署意味着 Docker 会在 `/run/secrets/<secret_name>` 下创建一个 bind mount，并赋予其特定的值。

> [!NOTE]
>
> 此处演示的 `_FILE` environment variables 是一些镜像使用的约定，包括 Docker Official Images 如 [mysql](https://hub.docker.com/_/mysql) 和 [postgres](https://hub.docker.com/_/postgres)。

### Build secrets

在以下示例中，`npm_token` secret 在构建时可用。其值取自 `NPM_TOKEN` environment variable。

```yaml
services:
  myapp:
    build:
      secrets:
        - npm_token
      context: .

secrets:
  npm_token:
    environment: NPM_TOKEN
```

## 资源

- [熟悉 Compose 的信任模型](/compose/trust-model/)
- [Secrets 顶层元素](/reference/compose-file/secrets/)
- [services 顶层元素的 secrets 属性](/reference/compose-file/services/#secrets)
- [Build secrets](https://docs.docker.com/build/building/secrets/)