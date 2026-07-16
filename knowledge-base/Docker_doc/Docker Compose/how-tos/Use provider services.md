# 使用 provider services

Docker Compose 支持 provider services，允许集成那些生命周期由第三方组件管理而非 Compose 本身管理的服务（services）。  
此功能使您能够定义和使用特定于平台的服务（platform-specific services），而无需手动设置或直接管理其生命周期。

## 什么是 provider services？

Provider services 是 Compose 中一种特殊的 service 类型，代表的是平台能力而非容器（containers）。  
它们允许您声明应用所需的特定平台功能的依赖关系。

当您在 Compose 文件中定义一个 provider service 时，Compose 会与平台协作，以配置（provision）和设置所请求的能力，并将其提供给您的应用 services。

## 使用 provider services

要在 Compose 文件中使用 provider service，您需要：

1. 使用 `provider` 属性定义一个 service
2. 指定要使用的 provider 的 `type`
3. 配置任何特定于 provider 的 options
4. 从您的应用 services 声明对 provider service 的依赖（dependencies）

以下是一个基本示例：

```yaml
services:
  database:
    provider:
      type: awesomecloud
      options:
        type: mysql
        foo: bar  
  app:
    image: myapp 
    depends_on:
       - database
```

请注意 `database` service 中专门的 `provider` 属性。  
该属性指定该 service 由 provider 管理，并允许您定义特定于该 provider type 的 options。

`app` service 中的 `depends_on` 属性指定它依赖于 `database` service。  
这意味着 `database` service 将在 `app` service 之前启动，从而允许将 provider 信息注入到 `app` service 中。

## 工作原理

在执行 `docker compose up` 命令期间，Compose 会识别依赖 provider 的 services，并与它们协作以配置所请求的能力。然后，provider 会使用有关如何访问已配置资源的信息来填充 Compose model。

这些信息会传递给那些声明对 provider service 有依赖的 services，通常通过 environment variables 传递。这些变量的命名约定为：

```env
<<PROVIDER_SERVICE_NAME>>_<<VARIABLE_NAME>>
```

例如，如果您的 provider service 名为 `database`，您的应用 service 可能会收到如下的 environment variables：

- `DATABASE_URL`，包含访问已配置资源的 URL
- `DATABASE_TOKEN`，包含一个认证 token
- 其他特定于 provider 的变量

然后，您的应用可以使用这些 environment variables 与已配置的资源进行交互。

## Provider types

Provider service 中的 `type` 字段引用以下之一的名称：

1. 一个 Docker CLI plugin（例如 `docker-model`）
2. 用户 PATH 中的一个可执行二进制文件
3. 指向该二进制文件或脚本的路径

当 Compose 遇到 provider service 时，它会查找具有指定名称的 plugin 或二进制文件，以处理所请求能力的配置。

例如，如果您指定 `type: model`，Compose 将在 PATH 中查找名为 `docker-model` 的 Docker CLI plugin 或名为 `model` 的二进制文件。

```yaml
services:
  ai-runner:
    provider:
      type: model  # 查找 docker-model plugin 或 model 二进制文件
      options:
        model: ai/example-model
```

该 plugin 或二进制文件负责：

1. 解释 provider service 中提供的 options
2. 配置所请求的能力
3. 返回有关如何访问已配置资源的信息

然后，这些信息会作为 environment variables 传递给依赖的 services。

> [!TIP]
>
> 如果您在 Compose 中处理 AI 模型，请改用 [`models` 顶层元素](/ai/compose/models-and-compose/)。

## 使用 provider services 的好处

在 Compose 应用中使用 provider services 有以下几个好处：

1. 简化的配置：您无需手动配置和管理平台能力
2. 声明式方法：您可以在一个地方声明应用的所有依赖
3. 一致的工作流：您使用相同的 Compose 命令来管理整个应用，包括平台能力

## 创建您自己的 provider

如果您想创建自己的 provider 以扩展 Compose 的自定义能力，您可以实现一个注册 provider types 的 Compose plugin。

有关如何创建和实现您自己的 provider 的详细信息，请参阅 [Compose Extensions 文档](https://github.com/docker/compose/blob/main/docs/extension.md)。  
该指南解释了允许您向 Compose 添加新 provider types 的扩展机制。

## 参考

- [Docker Model Runner 文档](/ai/model-runner/)
- [Compose Extensions 文档](https://github.com/docker/compose/blob/main/docs/extension.md)