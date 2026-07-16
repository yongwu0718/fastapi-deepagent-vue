# Docker contexts

## 引言

本指南介绍如何使用 context 来通过单个客户端管理多个 Docker daemon。

每个 context 包含了管理 daemon 上所有资源所需的信息。
`docker context` 命令可以轻松配置这些 context 并在它们之间切换。

例如，一个 Docker 客户端可以配置两个 context：

- 一个本地运行的默认 context
- 一个远程的共享 context

配置好这些 context 后，
您可以使用 `docker context use <context-name>` 命令
在它们之间切换。

## 前提条件

要跟随本指南中的示例，您需要：

- 一个支持顶层 `context` 命令的 Docker 客户端

运行 `docker context` 来验证您的 Docker 客户端是否支持 context。

## context 的结构

一个 context 是若干属性的组合。这些属性包括：

- Name（名称）和 description（描述）
- Endpoint（端点）配置
- TLS 信息

要列出可用的 context，请使用 `docker context ls` 命令。

```console
$ docker context ls
NAME        DESCRIPTION                               DOCKER ENDPOINT               ERROR
default *                                             unix:///var/run/docker.sock
```

这里显示了一个名为 "default" 的 context。
它被配置为通过本地的 `/var/run/docker.sock` Unix socket 与一个 daemon 通信。

`NAME` 列中的星号表示这是当前激活的 context。
这意味着所有 `docker` 命令都将针对该 context 执行，
除非被诸如 `DOCKER_HOST` 和 `DOCKER_CONTEXT` 等环境变量覆盖，
或者在命令行中使用了 `--context` 和 `--host` 标志。

使用 `docker context inspect` 可以查看更详细的信息。
下面的示例展示了如何检查名为 `default` 的 context。

```console
$ docker context inspect default
[
    {
        "Name": "default",
        "Metadata": {},
        "Endpoints": {
            "docker": {
                "Host": "unix:///var/run/docker.sock",
                "SkipTLSVerify": false
            }
        },
        "TLSMaterial": {},
        "Storage": {
            "MetadataPath": "\u003cIN MEMORY\u003e",
            "TLSPath": "\u003cIN MEMORY\u003e"
        }
    }
]
```

### 创建一个新的 context

您可以使用 `docker context create` 命令创建新的 context。

下面的示例创建了一个名为 `docker-test` 的新 context，
并将其 host endpoint（主机端点）指定为 TCP socket `tcp://docker:2375`。

```console
$ docker context create docker-test --docker host=tcp://docker:2375
docker-test
Successfully created context "docker-test"
```

新 context 存储在 `~/.docker/contexts/` 目录下的 `meta.json` 文件中。
您创建的每个新 context 都会在 `~/.docker/contexts/` 的专用子目录中获得各自的 `meta.json`。

您可以使用 `docker context ls` 和 `docker context inspect <context-name>` 查看新 context。

```console
$ docker context ls
NAME          DESCRIPTION                             DOCKER ENDPOINT               ERROR
default *                                             unix:///var/run/docker.sock
docker-test                                           tcp://docker:2375
```

当前 context 通过星号（"*"）标出。

## 使用不同的 context

您可以使用 `docker context use` 在不同的 context 之间切换。

以下命令将切换 `docker` CLI 以使用 `docker-test` context。

```console
$ docker context use docker-test
docker-test
Current context is now "docker-test"
```

通过列出所有 context 并确保星号（"*"）位于 `docker-test` context 旁边，来验证操作结果。

```console
$ docker context ls
NAME            DESCRIPTION                           DOCKER ENDPOINT               ERROR
default                                               unix:///var/run/docker.sock
docker-test *                                         tcp://docker:2375
```

现在 `docker` 命令将指向 `docker-test` context 中定义的 endpoints。

您还可以使用 `DOCKER_CONTEXT` 环境变量来设置当前 context。
环境变量会覆盖通过 `docker context use` 设置的 context。

使用下面的适当命令，通过环境变量将 context 设置为 `docker-test`。

**PowerShell**

```ps
> $env:DOCKER_CONTEXT='docker-test'
```

**Bash**

```console
$ export DOCKER_CONTEXT=docker-test
```

运行 `docker context ls` 来验证 `docker-test` context 现在是当前激活的 context。

您也可以使用全局的 `--context` 标志来覆盖当前 context。
下面的命令使用了一个名为 `production` 的 context。

```console
$ docker --context production container ls
```

## 导出和导入 Docker contexts

您可以使用 `docker context export` 和 `docker context import` 命令
在不同主机上导出和导入 context。

`docker context export` 命令将现有的 context 导出到一个文件。
该文件可以导入到任何安装了 `docker` 客户端的主机上。

### 导出和导入一个 context

下面的示例导出现有的名为 `docker-test` 的 context。
它将被写入一个名为 `docker-test.dockercontext` 的文件。

```console
$ docker context export docker-test
Written file "docker-test.dockercontext"
```

检查导出文件的内容。

```console
$ cat docker-test.dockercontext
```

在另一台主机上使用 `docker context import` 导入该文件，
以创建具有相同配置的 context。

```console
$ docker context import docker-test docker-test.dockercontext
docker-test
Successfully imported context "docker-test"
```

您可以通过 `docker context ls` 验证 context 是否已成功导入。

导入命令的格式是 `docker context import <context-name> <context-file>`。

## 更新一个 context

您可以使用 `docker context update` 来更新现有 context 中的字段。

下面的示例更新了现有 `docker-test` context 中的 description 字段。

```console
$ docker context update docker-test --description "Test context"
docker-test
Successfully updated context "docker-test"
```