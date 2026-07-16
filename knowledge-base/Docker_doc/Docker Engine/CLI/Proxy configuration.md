# 将 Docker CLI 与代理服务器（proxy server）一起使用

本页介绍如何通过容器中的环境变量（environment variables）配置 Docker CLI 以使用代理（proxies）。

本页不介绍如何为 Docker Desktop 配置代理。有关说明，请参阅[配置 Docker Desktop 使用 HTTP/HTTPS 代理（proxies）](/desktop/settings-and-maintenance/settings/#proxies)。

如果你在没有 Docker Desktop 的情况下运行 Docker Engine，请参考[配置 Docker 守护进程（daemon）使用代理](/engine/daemon/proxy/)以了解如何为 Docker 守护进程（`dockerd`）本身配置代理服务器。

如果你的容器需要使用 HTTP、HTTPS 或 FTP 代理服务器，可以通过不同方式进行配置：

- [配置 Docker 客户端（client）](#configure-the-docker-client)
- [使用 CLI 设置代理](#set-proxy-using-the-cli)

> [!NOTE]
>
> 不幸的是，目前没有标准定义 Web 客户端应如何处理代理环境变量，也没有定义它们的格式。
>
> 如果你对这些变量的历史感兴趣，请查看 GitLab 团队关于此主题的博客文章：
> [我们需要谈谈：我们能标准化 NO_PROXY 吗？](https://about.gitlab.com/blog/2021/01/27/we-need-to-talk-no-proxy/)

## 配置 Docker 客户端（client）

你可以使用位于 `~/.docker/config.json` 的 JSON 配置文件为 Docker 客户端添加代理配置。
构建（Builds）和容器（containers）将使用此文件中指定的配置。

```json
{
 "proxies": {
   "default": {
     "httpProxy": "http://proxy.example.com:3128",
     "httpsProxy": "https://proxy.example.com:3129",
     "noProxy": "*.test.example.com,.example.org,127.0.0.0/8"
   }
 }
}
```

> [!WARNING]
>
> 代理设置可能包含敏感信息。例如，某些代理服务器要求在其 URL 中包含身份验证信息，或者其地址可能暴露你公司环境的 IP 地址或主机名。
>
> 环境变量以纯文本形式存储在容器的配置中，因此可以通过远程 API 检查，或在使用 `docker commit` 时提交到镜像中。

保存文件后配置即生效，无需重启 Docker。但是，该配置仅适用于新的容器和构建，不会影响现有容器。

下表描述了可用的配置参数。

| 属性          | 描述                                                                         |
| :------------ | :--------------------------------------------------------------------------- |
| `httpProxy`   | 设置 `HTTP_PROXY` 和 `http_proxy` 环境变量以及构建参数。                     |
| `httpsProxy`  | 设置 `HTTPS_PROXY` 和 `https_proxy` 环境变量以及构建参数。                    |
| `ftpProxy`    | 设置 `FTP_PROXY` 和 `ftp_proxy` 环境变量以及构建参数。                        |
| `noProxy`     | 设置 `NO_PROXY` 和 `no_proxy` 环境变量以及构建参数。                          |
| `allProxy`    | 设置 `ALL_PROXY` 和 `all_proxy` 环境变量以及构建参数。                        |

这些设置仅用于配置容器的代理环境变量，不用作 Docker CLI 或 Docker Engine 本身的代理设置。
有关为 CLI 和守护进程配置代理设置，请参阅[环境变量](/reference/cli/docker/#environment-variables)和[配置 Docker 守护进程使用代理服务器](/engine/daemon/proxy/)部分。

### 使用代理配置运行容器（containers）

当你启动容器时，其代理相关的环境变量会被设置为反映 `~/.docker/config.json` 中的代理配置。

例如，假设有[前面部分](#configure-the-docker-client)所示的代理配置，你运行的容器的环境变量将设置如下：

```console
$ docker run --rm alpine sh -c 'env | grep -i  _PROXY'
https_proxy=http://proxy.example.com:3129
HTTPS_PROXY=http://proxy.example.com:3129
http_proxy=http://proxy.example.com:3128
HTTP_PROXY=http://proxy.example.com:3128
no_proxy=*.test.example.com,.example.org,127.0.0.0/8
NO_PROXY=*.test.example.com,.example.org,127.0.0.0/8
```

### 使用代理配置进行构建（Build）

当你调用构建时，基于 Docker 客户端配置文件中的代理设置，代理相关的构建参数会自动预填充。

假设有[前面部分](#configure-the-docker-client)所示的代理配置，构建期间环境变量设置如下：

```console
$ docker build \
  --no-cache \
  --progress=plain \
  - <<EOF
FROM alpine
RUN env | grep -i _PROXY
EOF
```

```console
#5 [2/2] RUN env | grep -i _PROXY
#5 0.100 HTTPS_PROXY=https://proxy.example.com:3129
#5 0.100 no_proxy=*.test.example.com,.example.org,127.0.0.0/8
#5 0.100 NO_PROXY=*.test.example.com,.example.org,127.0.0.0/8
#5 0.100 https_proxy=https://proxy.example.com:3129
#5 0.100 http_proxy=http://proxy.example.com:3128
#5 0.100 HTTP_PROXY=http://proxy.example.com:3128
#5 DONE 0.1s
```

### 按守护进程（daemon）配置代理设置

`~/.docker/config.json` 中 `proxies` 下的 `default` 键为客户端连接的所有守护进程配置代理设置。
要为单个守护进程配置代理，请使用守护进程的地址代替 `default` 键。

以下示例配置了默认代理配置，并为地址 `tcp://docker-daemon1.example.com` 上的 Docker 守护进程配置了无代理覆盖：

```json
{
 "proxies": {
   "default": {
     "httpProxy": "http://proxy.example.com:3128",
     "httpsProxy": "https://proxy.example.com:3129",
     "noProxy": "*.test.example.com,.example.org,127.0.0.0/8"
   },
   "tcp://docker-daemon1.example.com": {
     "noProxy": "*.internal.example.net"
   }
 }
}
```

## 使用 CLI 设置代理

除了[配置 Docker 客户端](#configure-the-docker-client)之外，你还可以在调用 `docker build` 和 `docker run` 命令时在命令行上指定代理配置。

命令行上的代理配置使用 `--build-arg` 标志进行构建，使用 `--env` 标志在需要带代理运行容器时使用。

```console
$ docker build --build-arg HTTP_PROXY="http://proxy.example.com:3128" .
$ docker run --env HTTP_PROXY="http://proxy.example.com:3128" redis
```

有关可与 `docker build` 命令一起使用的所有代理相关构建参数的列表，请参阅[预定义 ARG（Predefined ARGs）](/reference/dockerfile/#predefined-args)。这些代理值仅在构建容器中可用，不会包含在构建输出中。

## 作为构建环境变量的代理（Proxy）

不要使用 `ENV` Dockerfile 指令为构建指定代理设置。请改用构建参数。

使用环境变量作为代理会将配置嵌入到镜像中。如果代理是内部代理，则从该镜像创建的容器可能无法访问它。

将代理设置嵌入镜像也会带来安全风险，因为这些值可能包含敏感信息。