# 使用 Docker Compose 中环境变量的最佳实践

#### 安全处理敏感信息

谨慎对待在环境变量中包含敏感数据。考虑使用 [Secrets](/compose/how-tos/use-secrets/) 来管理敏感信息。

#### 理解环境变量优先级（precedence）

了解 Docker Compose 如何处理来自不同源（`.env` 文件、shell 变量、Dockerfile）的[环境变量优先级](/compose/how-tos/environment-variables/best-practices/envvars-precedence/)。

#### 使用特定的环境文件

考虑您的应用如何适应不同环境（例如开发、测试、生产），并根据需要使用不同的 `.env` 文件。

#### 了解插值（interpolation）

理解[插值](/compose/how-tos/environment-variables/best-practices/variable-interpolation/)在 Compose 文件中的工作原理，以实现动态配置。

#### 命令行覆盖

请注意，您可以在启动容器时从命令行[覆盖环境变量](/compose/how-tos/environment-variables/best-practices/set-environment-variables/#cli)。这对于测试或临时更改非常有用。