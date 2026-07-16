# Dockerfile 参考

Docker 可以通过读取 Dockerfile 中的指令自动构建镜像。Dockerfile 是一个文本文档，其中包含了用户可以在命令行上调用来组装镜像的所有命令。本页描述了可以在 Dockerfile 中使用的命令。

## 概述

Dockerfile 支持以下指令：

| 指令                                  | 描述                                                         |
| :------------------------------------ | :----------------------------------------------------------- |
| [`ADD`](#add)                         | 添加本地或远程的文件和目录。                                 |
| [`ARG`](#arg)                         | 使用构建时变量。                                             |
| [`CMD`](#cmd)                         | 指定默认命令。                                               |
| [`COPY`](#copy)                       | 复制文件和目录。                                             |
| [`ENTRYPOINT`](#entrypoint)           | 指定默认的可执行文件。                                       |
| [`ENV`](#env)                         | 设置环境变量。                                               |
| [`EXPOSE`](#expose)                   | 描述容器监听的应用端口。                                     |
| [`FROM`](#from)                       | 基于基础镜像创建一个新的构建阶段。                           |
| [`HEALTHCHECK`](#healthcheck)         | 检查容器的健康状态。                                         |
| [`LABEL`](#label)                     | 为镜像添加元数据。                                           |
| [`MAINTAINER`](#maintainer-deprecated) | 指定镜像的作者。                                             |
| [`ONBUILD`](#onbuild)                 | 当镜像被用作构建基础时执行指令。                             |
| [`RUN`](#run)                         | 执行构建命令。                                               |
| [`SHELL`](#shell)                     | 设置镜像的默认 Shell。                                       |
| [`STOPSIGNAL`](#stopsignal)           | 指定退出容器的系统调用信号。                                 |
| [`USER`](#user)                       | 设置用户和组 ID。                                            |
| [`VOLUME`](#volume)                   | 创建卷挂载点。                                               |
| [`WORKDIR`](#workdir)                 | 更改工作目录。                                               |

## 格式

Dockerfile 的格式如下：

```dockerfile
# 注释
INSTRUCTION 参数
```

指令不区分大小写。但惯例是使用大写字母，以便更容易与参数区分。

Docker 按顺序执行 Dockerfile 中的指令。Dockerfile **必须以 `FROM` 指令开头**。`FROM` 之前可以出现[解析器指令](#parser-directives)、[注释](#format)和全局作用域的 [`ARG`](#arg)。`FROM` 指令指定了构建所依据的[基础镜像](https://docs.docker.com/glossary/#base-image)。在 `FROM` 之前只能有一个或多个 `ARG` 指令，这些 `ARG` 用于声明 Dockerfile 中 `FROM` 行中使用的参数。

BuildKit 将以 `#` 开头的行视为注释，除非该行是有效的[解析器指令](#parser-directives)。如果一行中其他位置出现 `#`，则被视为参数。例如：

```dockerfile
# 注释
RUN echo 'we are running some # of cool things'
```

注释行会在 Dockerfile 指令执行前被移除。以下示例中的注释在 Shell 执行 `echo` 命令之前被移除。

```dockerfile
RUN echo hello \
# comment
world
```

下面的示例等效。

```dockerfile
RUN echo hello \
world
```

注释不支持行续接符。

> [!NOTE]
> **关于空白字符**
>
> 为了向后兼容，注释（`#`）和指令（如 `RUN`）之前的行首空白字符会被忽略，但不推荐使用。在这些情况下，行首空白字符不会被保留，因此以下示例是等效的：
>
> ```dockerfile
>         # this is a comment-line
>     RUN echo hello
> RUN echo world
> ```
>
> ```dockerfile
> # this is a comment-line
> RUN echo hello
> RUN echo world
> ```
>
> 然而，指令参数中的空白字符不会被忽略。以下示例会输出 `    hello    world`，保留了指定的行首空白字符：
>
> ```dockerfile
> RUN echo "\
>      hello\
>      world"
> ```

## 解析器指令

解析器指令是可选的，它影响 Dockerfile 中后续行的处理方式。解析器指令不会向构建添加层，也不会作为构建步骤出现。解析器指令以特殊注释的形式编写，格式为 `# directive=value`。每个指令只能使用一次。

支持以下解析器指令：

- [`syntax`](#syntax)
- [`escape`](#escape)
- [`check`](#check)（自 Dockerfile v1.8.0 起）

一旦处理了注释、空行或构建器指令，BuildKit 就不再查找解析器指令。之后任何格式类似于解析器指令的内容都将被视为注释，并且不会尝试验证它是否为解析器指令。因此，所有解析器指令必须放在 Dockerfile 的最顶部。

解析器指令的关键字（如 `syntax` 或 `check`）不区分大小写，但按照惯例使用小写。指令的值区分大小写，必须按照指令要求的大小写书写。例如，`#check=skip=jsonargsrecommended` 是无效的，因为检查名称必须使用 PascalCase，而不是小写。也建议在解析器指令后面包含一个空行。解析器指令中不支持行续接符。

由于这些规则，以下示例都是无效的：

由于行续接符而无效：

```dockerfile
# direc \
tive=value
```

由于出现两次而无效：

```dockerfile
# directive=value1
# directive=value2

FROM ImageName
```

因为出现在构建器指令之后而被视为注释：

```dockerfile
FROM ImageName
# directive=value
```

因为出现在非解析器指令的注释之后而被视为注释：

```dockerfile
# About my dockerfile
# directive=value
FROM ImageName
```

下面的 `unknowndirective` 因为不被识别而被视为注释。已知的 `syntax` 指令因为出现在非解析器指令的注释之后也被视为注释。

```dockerfile
# unknowndirective=value
# syntax=value
```

解析器指令中允许非换行空白字符。因此，以下各行的处理方式完全相同：

```dockerfile
#directive=value
# directive =value
#	directive= value
# directive = value
#	  dIrEcTiVe=value
```

### syntax

<a name="external-implementation-features"><!-- 包含用于旧节的深层链接 --></a>

使用 `syntax` 解析器指令声明构建所使用的 Dockerfile 语法版本。如果未指定，BuildKit 会使用捆绑版本的 Dockerfile 前端。声明语法版本可让您自动使用最新的 Dockerfile 版本，而无需升级 BuildKit 或 Docker Engine，甚至可以使用自定义的 Dockerfile 实现。

大多数用户希望将此解析器指令设置为 `docker/dockerfile:1`，这将使 BuildKit 在构建前拉取最新的稳定版 Dockerfile 语法。

```dockerfile
# syntax=docker/dockerfile:1
```

有关解析器指令工作原理的更多信息，请参阅[自定义 Dockerfile 语法](https://docs.docker.com/build/buildkit/dockerfile-frontend/)。

### escape

```dockerfile
# escape=\
```

或者

```dockerfile
# escape=`
```

`escape` 指令设置用于转义 Dockerfile 中字符的转义字符。如果未指定，默认转义字符为 `\`。

转义字符既用于转义行中的字符，也用于转义换行符。这允许 Dockerfile 指令跨越多行。请注意，无论 Dockerfile 中是否包含 `escape` 解析器指令，在 `RUN` 命令中，除了行尾之外，不会执行转义。

在 `Windows` 上，将转义字符设置为 `` ` `` 特别有用，因为 `\` 是目录路径分隔符。`` ` `` 与 [Windows PowerShell](https://technet.microsoft.com/en-us/library/hh847755.aspx) 保持一致。

考虑以下在 Windows 上可能以不明显方式失败的示例。第二行末尾的第二个 `\` 将被解释为对换行符的转义，而不是第一个 `\` 的转义目标。类似地，第三行末尾的 `\`，假设它确实被当作指令处理，将导致它被视为行续接符。此 Dockerfile 的结果是第二行和第三行被视为一条指令：

```dockerfile
FROM microsoft/nanoserver
COPY testfile.txt c:\\
RUN dir c:\
```

结果是：

```console
PS E:\myproject> docker build -t cmd .

Sending build context to Docker daemon 3.072 kB
Step 1/2 : FROM microsoft/nanoserver
 ---> 22738ff49c6d
Step 2/2 : COPY testfile.txt c:\RUN dir c:
GetFileAttributesEx c:RUN: The system cannot find the file specified.
PS E:\myproject>
```

上述问题的一个解决方案是使用 `/` 作为 `COPY` 指令和 `dir` 的目标。但是，这种语法在 Windows 上不自然，容易出错，因为并非所有 Windows 命令都支持 `/` 作为路径分隔符。

通过添加 `escape` 解析器指令，以下 Dockerfile 按预期成功运行，并在 Windows 上使用了自然的平台语义：

```dockerfile
# escape=`

FROM microsoft/nanoserver
COPY testfile.txt c:\
RUN dir c:\
```

结果是：

```console
PS E:\myproject> docker build -t succeeds --no-cache=true .

Sending build context to Docker daemon 3.072 kB
Step 1/3 : FROM microsoft/nanoserver
 ---> 22738ff49c6d
Step 2/3 : COPY testfile.txt c:\
 ---> 96655de338de
Removing intermediate container 4db9acbb1682
Step 3/3 : RUN dir c:\
 ---> Running in a2c157f842f5
 Volume in drive C has no label.
 Volume Serial Number is 7E6D-E0F7

 Directory of c:\

10/05/2016  05:04 PM             1,894 License.txt
10/05/2016  02:22 PM    <DIR>          Program Files
10/05/2016  02:14 PM    <DIR>          Program Files (x86)
10/28/2016  11:18 AM                62 testfile.txt
10/28/2016  11:20 AM    <DIR>          Users
10/28/2016  11:20 AM    <DIR>          Windows
           2 File(s)          1,956 bytes
           4 Dir(s)  21,259,096,064 bytes free
 ---> 01c7f3bef04f
Removing intermediate container a2c157f842f5
Successfully built 01c7f3bef04f
PS E:\myproject>
```

### check

```dockerfile
# check=skip=<checks|all>
# check=error=<boolean>
```

`check` 指令用于配置[构建检查](https://docs.docker.com/build/checks/)的评估方式。默认情况下，运行所有检查，失败被视为警告。

您可以使用 `#check=skip=<check-name>` 禁用特定的检查。要指定多个要跳过的检查，请用逗号分隔：

```dockerfile
# check=skip=JSONArgsRecommended,StageNameCasing
```

要禁用所有检查，请使用 `#check=skip=all`。

默认情况下，存在失败构建检查的构建会以零状态码退出，尽管有警告。要使构建在警告时失败，请设置 `#check=error=true`。

```dockerfile
# check=error=true
```

> [!NOTE]
> 使用 `check` 指令并设置 `error=true` 选项时，建议将 [Dockerfile 语法](#syntax)固定到特定版本。否则，当未来版本中添加新检查时，您的构建可能会开始失败。

要同时使用 `skip` 和 `error` 选项，请用分号分隔：

```dockerfile
# check=skip=JSONArgsRecommended;error=true
```

要查看所有可用的检查，请参阅[构建检查参考](https://docs.docker.com/reference/build-checks/)。请注意，可用的检查取决于 Dockerfile 语法版本。为确保您获得最新的检查，请使用 [`syntax`](#syntax) 指令将 Dockerfile 语法版本指定为最新的稳定版。

## 环境替换

环境变量（使用 [`ENV` 语句](#env)声明）也可以在某些指令中用作变量，由 Dockerfile 解释。转义也用于将类似变量的语法直接包含到语句中。

环境变量在 Dockerfile 中用 `$variable_name` 或 `${variable_name}` 表示。它们是等价的，大括号语法通常用于处理不带空格的变量名，如 `${foo}_bar`。

`${variable_name}` 语法还支持一些标准的 `bash` 修饰符，如下所示：

- `${variable:-word}` 表示如果 `variable` 已设置且非空，则结果为该值。如果 `variable` 未设置或为空，则结果为 `word`。
- `${variable-word}` 表示如果 `variable` 已设置（即使为空），则结果为该值。如果 `variable` 未设置，则结果为 `word`。
- `${variable:+word}` 表示如果 `variable` 已设置且非空，则结果为 `word`，否则结果为空字符串。
- `${variable+word}` 表示如果 `variable` 已设置（即使为空），则结果为 `word`，否则结果为空字符串。

以下变量替换在 Dockerfile 语法的预发布版本中受支持，当您在 Dockerfile 中使用 `# syntax=docker/dockerfile-upstream:master` 语法指令时：

- `${variable#pattern}` 从 `variable` 开头开始，删除与 `pattern` 的最短匹配。

  ```bash
  str=foobarbaz echo ${str#f*b}     # arbaz
  ```

- `${variable##pattern}` 从 `variable` 开头开始，删除与 `pattern` 的最长匹配。

  ```bash
  str=foobarbaz echo ${str##f*b}    # az
  ```

- `${variable%pattern}` 从 `variable` 末尾开始反向查找，删除与 `pattern` 的最短匹配。

  ```bash
  string=foobarbaz echo ${string%b*}    # foobar
  ```

- `${variable%%pattern}` 从 `variable` 末尾开始反向查找，删除与 `pattern` 的最长匹配。

  ```bash
  string=foobarbaz echo ${string%%b*}   # foo
  ```

- `${variable/pattern/replacement}` 将 `variable` 中第一个出现的 `pattern` 替换为 `replacement`

  ```bash
  string=foobarbaz echo ${string/ba/fo}  # fooforbaz
  ```

- `${variable//pattern/replacement}` 将 `variable` 中所有出现的 `pattern` 替换为 `replacement`

  ```bash
  string=foobarbaz echo ${string//ba/fo}  # fooforfoz
  ```

在所有情况下，`word` 可以是任何字符串，包括其他环境变量。

`pattern` 是一个 glob 模式，其中 `?` 匹配任意单个字符，`*` 匹配任意数量的字符（包括零个）。要匹配字面量 `?` 和 `*`，请使用反斜杠转义：`\?` 和 `\*`。

您可以通过在变量名前添加 `\` 来转义整个变量名：例如 `\$foo` 或 `\${foo}` 将分别转换为字面量 `$foo` 和 `${foo}`。

示例（解析后的表示形式显示在 `#` 之后）：

```dockerfile
FROM busybox
ENV FOO=/bar
WORKDIR ${FOO}   # WORKDIR /bar
ADD . $FOO       # ADD . /bar
COPY \$FOO /quux # COPY $FOO /quux
```

Dockerfile 中的以下指令支持环境变量：

- `ADD`
- `COPY`
- `ENV`
- `EXPOSE`
- `FROM`
- `LABEL`
- `STOPSIGNAL`
- `USER`
- `VOLUME`
- `WORKDIR`
- `ONBUILD`（与上述受支持的指令之一结合使用时）

您也可以在 `RUN`、`CMD` 和 `ENTRYPOINT` 指令中使用环境变量，但在这些情况下，变量替换由命令 shell 处理，而不是构建器。请注意，使用 exec 形式的指令不会自动调用命令 shell。请参阅[变量替换](#variable-substitution)。

环境变量替换在整个指令中对每个变量使用相同的值。更改变量的值仅在后续指令中生效。请考虑以下示例：

```dockerfile
ENV abc=hello
ENV abc=bye def=$abc
ENV ghi=$abc
```

- `def` 的值变为 `hello`
- `ghi` 的值变为 `bye`

## .dockerignore 文件

您可以使用 `.dockerignore` 文件从构建上下文中排除文件和目录。有关更多信息，请参阅[.dockerignore 文件](https://docs.docker.com/build/building/context/#dockerignore-files)。

## Shell 和 Exec 形式

`RUN`、`CMD` 和 `ENTRYPOINT` 指令都有两种形式：

- `INSTRUCTION ["executable","param1","param2"]` (exec 形式)
- `INSTRUCTION command param1 param2` (shell 形式)

exec 形式可以避免 shell 字符串篡改，并且可以使用特定的命令 shell 或任何其他可执行文件来调用命令。它使用 JSON 数组语法，其中数组中的每个元素都是一个命令、标志或参数。

shell 形式更加宽松，强调易用性、灵活性和可读性。shell 形式自动使用命令 shell，而 exec 形式则不会。

### Exec 形式

exec 形式被解析为 JSON 数组，这意味着您必须使用双引号（"）包裹单词，而不是单引号（'）。

```dockerfile
ENTRYPOINT ["/bin/bash", "-c", "echo hello"]
```

exec 形式最适合与 `CMD` 结合使用来指定 `ENTRYPOINT` 指令，为可在运行时覆盖的默认参数提供设置。有关更多信息，请参阅 [ENTRYPOINT](#entrypoint)。

#### 变量替换

使用 exec 形式不会自动调用命令 shell。这意味着正常的 shell 处理（如变量替换）不会发生。例如，`RUN [ "echo", "$HOME" ]` 不会处理 `$HOME` 的变量替换。

如果您需要 shell 处理，请使用 shell 形式，或者使用 exec 形式直接执行 shell，例如：`RUN [ "sh", "-c", "echo $HOME" ]`。当使用 exec 形式并直接执行 shell 时，进行环境变量替换的是 shell，而不是构建器。

#### 反斜杠

在 exec 形式中，您必须转义反斜杠。这在 Windows 上尤其重要，因为反斜杠是路径分隔符。否则，下面的行将因为不是有效的 JSON 而被视为 shell 形式，并以意外的方式失败：

```dockerfile
RUN ["c:\windows\system32\tasklist.exe"]
```

此示例的正确语法是：

```dockerfile
RUN ["c:\\windows\\system32\\tasklist.exe"]
```

### Shell 形式

与 exec 形式不同，使用 shell 形式的指令始终使用命令 shell。shell 形式不使用 JSON 数组格式，而是普通字符串。shell 形式字符串允许您使用[转义字符](#escape)（默认为反斜杠）转义换行符，从而将一条指令延续到下一行。这使得它更易于处理较长的命令，因为您可以将它们分成多行。例如，考虑以下两行：

```dockerfile
RUN source $HOME/.bashrc && \
echo $HOME
```

它们等效于以下行：

```dockerfile
RUN source $HOME/.bashrc && echo $HOME
```

您还可以将 heredocs 与 shell 形式一起使用来拆分受支持的命令。

```dockerfile
RUN <<EOF
  source $HOME/.bashrc
  echo $HOME
EOF
```

有关 heredocs 的更多信息，请参阅[此处文档](#here-documents)。

### 使用不同的 Shell

您可以使用 `SHELL` 命令更改默认 shell。例如：

```dockerfile
SHELL ["/bin/bash", "-c"]
RUN echo hello
```

有关更多信息，请参阅 [SHELL](#shell)。

## FROM

```dockerfile
FROM [--platform=<platform>] <image> [AS <name>]
```

或者

```dockerfile
FROM [--platform=<platform>] <image>[:<tag>] [AS <name>]
```

或者

```dockerfile
FROM [--platform=<platform>] <image>[@<digest>] [AS <name>]
```

`FROM` 指令初始化一个新的构建阶段，并为后续指令设置[基础镜像](https://docs.docker.com/glossary/#base-image)。因此，一个有效的 Dockerfile 必须以 `FROM` 指令开头。镜像可以是任何有效的镜像。

- `ARG` 是 Dockerfile 中唯一可以出现在 `FROM` 之前的指令。请参阅[理解 ARG 和 FROM 的交互](#understand-how-arg-and-from-interact)。
- `FROM` 可以在同一个 Dockerfile 中出现多次，以创建多个镜像或将一个构建阶段用作另一个构建阶段的依赖项。只需记下每个新 `FROM` 指令之前提交的最后一个镜像 ID。每个 `FROM` 指令都会清除之前指令创建的任何状态。
- 可选地，可以通过在 `FROM` 指令中添加 `AS name` 为新的构建阶段命名。该名称可以在后续的 `FROM <name>`、[`COPY --from=<name>`](#copy---from) 和 [`RUN --mount=type=bind,from=<name>`](#run---mounttypebind) 指令中用于引用此阶段构建的镜像。

  使用前一个构建阶段作为后续阶段的基础是一种常见的模式，用于共享共同的基础环境：

  ```dockerfile
  FROM ubuntu AS base
  RUN apt-get update && apt-get install -y shared-tooling

  FROM base AS dev
  RUN apt-get install -y dev-tooling

  FROM base AS prod
  COPY --from=build /app /app
  ```
- `tag` 或 `digest` 值是可选的。如果省略两者，构建器默认假定 `latest` 标签。如果找不到 `tag` 值，构建器将返回错误。

可选的 `--platform` 标志可用于在 `FROM` 引用多平台镜像时指定镜像的平台。例如 `linux/amd64`、`linux/arm64` 或 `windows/amd64`。默认情况下，使用构建请求的目标平台。全局构建参数可用作此标志的值，例如[自动平台 ARG](#automatic-platform-args-in-the-global-scope) 允许您强制某个阶段使用本地构建平台（`--platform=$BUILDPLATFORM`），并在阶段内使用它交叉编译到目标平台。

### 理解 ARG 和 FROM 的交互

`FROM` 指令支持由第一个 `FROM` 之前出现的任何 `ARG` 指令声明的变量。

```dockerfile
ARG  CODE_VERSION=latest
FROM base:${CODE_VERSION}
CMD  /code/run-app

FROM extras:${CODE_VERSION}
CMD  /code/run-extras
```

在 `FROM` 之前声明的 `ARG` 位于构建阶段之外，因此不能在 `FROM` 之后的任何指令中使用。要在构建阶段内使用第一个 `FROM` 之前声明的 `ARG` 的默认值，请使用不带值的 `ARG` 指令：

```dockerfile
ARG VERSION=latest
FROM busybox:$VERSION
ARG VERSION
RUN echo $VERSION > image_version
```

## RUN

`RUN` 指令将执行任何命令，并在当前镜像之上创建一个新层。添加的层将用于 Dockerfile 中的下一步。`RUN` 有两种形式：

```dockerfile
# Shell 形式：
RUN [OPTIONS] <command> ...
# Exec 形式：
RUN [OPTIONS] [ "<command>", ... ]
```

有关这两种形式之间差异的更多信息，请参阅[shell 或 exec 形式](#shell-and-exec-form)。

shell 形式最常用，它允许您将较长的指令分成多行，可以使用换行符[转义](#escape)，也可以使用[heredocs](#here-documents)：

```dockerfile
RUN <<EOF
apt-get update
apt-get install -y curl
EOF
```

`RUN` 指令可用的 `[OPTIONS]` 包括：

| 选项                              | 最低 Dockerfile 版本 |
| --------------------------------- | -------------------- |
| [`--device`](#run---device)       | 1.14-labs            |
| [`--mount`](#run---mount)         | 1.2                  |
| [`--network`](#run---network)     | 1.3                  |
| [`--security`](#run---security)   | 1.20                 |

### RUN 指令的缓存失效

`RUN` 指令的缓存在下次构建时不会自动失效。类似 `RUN apt-get dist-upgrade -y` 的指令的缓存在下次构建时会被重用。可以使用 `--no-cache` 标志使 `RUN` 指令的缓存失效，例如 `docker build --no-cache`。

更多信息请参阅 [Dockerfile 最佳实践指南](https://docs.docker.com/engine/userguide/eng-image/dockerfile_best-practices/)。

[`ADD`](#add) 和 [`COPY`](#copy) 指令可以使 `RUN` 指令的缓存失效。

### RUN --device

> [!NOTE]
> 在稳定语法中尚不可用，请使用 [`docker/dockerfile:1-labs`](#syntax) 版本。还需要 BuildKit 0.20.0 或更高版本。

```dockerfile
RUN --device=name,[required]
```

`RUN --device` 允许构建请求 [CDI 设备](https://github.com/moby/buildkit/blob/master/docs/cdi.md) 在构建步骤中可用。

> [!WARNING]
> 使用 `--device` 受 `device` 权限保护，需要在启动 buildkitd 守护进程时使用 `--allow-insecure-entitlement device` 标志或在 [buildkitd 配置](https://github.com/moby/buildkit/blob/master/docs/buildkitd.toml.md)中启用，并且在构建请求中使用 [`--allow device` 标志](https://docs.docker.com/engine/reference/commandline/buildx_build/#allow)。

设备 `name` 由 BuildKit 中注册的 CDI 规范提供。

在以下示例中，多个设备已注册到 `vendor1.com/device` 供应商的 CDI 规范中。

```yaml
cdiVersion: "0.6.0"
kind: "vendor1.com/device"
devices:
  - name: foo
    containerEdits:
      env:
        - FOO=injected
  - name: bar
    annotations:
      org.mobyproject.buildkit.device.class: class1
    containerEdits:
      env:
        - BAR=injected
  - name: baz
    annotations:
      org.mobyproject.buildkit.device.class: class1
    containerEdits:
      env:
        - BAZ=injected
  - name: qux
    annotations:
      org.mobyproject.buildkit.device.class: class2
    containerEdits:
      env:
        - QUX=injected
annotations:
  org.mobyproject.buildkit.device.autoallow: true
```

设备名称格式灵活，接受多种模式以支持多种设备配置：

* `vendor1.com/device`：请求为该供应商找到的第一个设备
* `vendor1.com/device=foo`：请求特定设备
* `vendor1.com/device=*`：请求该供应商的所有设备
* `class1`：按 `org.mobyproject.buildkit.device.class` 注解请求设备

> [!NOTE]
> CDI 规范从 0.6.0 版本开始支持注解。

> [!NOTE]
> 要自动允许 CDI 规范中注册的所有设备，您可以设置 `org.mobyproject.buildkit.device.autoallow` 注解。您也可以为特定设备设置此注解。

#### 示例：CUDA 驱动的 LLaMA 推理

在此示例中，我们使用 `--device` 标志通过 CDI 运行 `llama.cpp` 推理，使用 NVIDIA GPU 设备：

```dockerfile
# syntax=docker/dockerfile:1-labs

FROM scratch AS model
ADD https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf /model.gguf

FROM scratch AS prompt
COPY <<EOF prompt.txt
Q: Generate  a list of 10 unique biggest countries by population in JSON with their estimated poulation in 1900 and 2024. Answer only newline formatted JSON with keys "country", "population_1900", "population_2024" with 10 items.
A:
[
    {

EOF

FROM ghcr.io/ggml-org/llama.cpp:full-cuda-b5124
RUN --device=nvidia.com/gpu=all \
    --mount=from=model,target=/models \
    --mount=from=prompt,target=/tmp \
    ./llama-cli -m /models/model.gguf -no-cnv -ngl 99 -f /tmp/prompt.txt
```

### RUN --mount

```dockerfile
RUN --mount=[type=<TYPE>][,option=<value>[,option=<value>]...]
```

`RUN --mount` 允许您创建构建可以访问的文件系统挂载。这可用于：

- 创建到主机文件系统或其他构建阶段的绑定挂载
- 访问构建密钥或 ssh-agent 套接字
- 使用持久的包管理缓存来加速构建

支持的挂载类型有：

| 类型                                         | 描述                                                                                         |
| -------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [`bind`](#run---mounttypebind) (默认)        | 绑定挂载上下文目录（只读）。                                                                 |
| [`cache`](#run---mounttypecache)             | 挂载临时目录以缓存编译器和包管理器的目录。                                                     |
| [`tmpfs`](#run---mounttypetmpfs)             | 在构建容器中挂载 `tmpfs`。                                                                   |
| [`secret`](#run---mounttypesecret)           | 允许构建容器访问安全文件（如私钥），而无需将其烘焙到镜像或构建缓存中。                       |
| [`ssh`](#run---mounttypessh)                 | 允许构建容器通过 SSH 代理访问 SSH 密钥，支持密码短语。                                         |

### RUN --mount=type=bind

此挂载类型允许将文件或目录绑定到构建容器。绑定挂载默认为只读。

| 选项                                   | 描述                                                                                         |
| -------------------------------------- | -------------------------------------------------------------------------------------------- |
| `target`, `dst`, `destination`[^1]     | 挂载路径。                                                                                   |
| `source`                               | `from` 中的源路径。默认为 `from` 的根目录。                                                  |
| `from`                                 | 源根目录的构建阶段、上下文或镜像名称。默认为构建上下文。                                       |
| `rw`,`readwrite`                       | 允许在挂载上写入。写入的数据将在 `RUN` 指令完成后丢弃，不会提交到镜像层。                     |

### RUN --mount=type=cache

此挂载类型允许构建容器缓存编译器和包管理器的目录。

| 选项                                   | 描述                                                                                         |
| -------------------------------------- | -------------------------------------------------------------------------------------------- |
| `id`                                   | 可选 ID，用于标识单独/不同的缓存。默认为 `target` 的值。                                      |
| `target`, `dst`, `destination`[^1]     | 挂载路径。                                                                                   |
| `ro`,`readonly`                        | 如果设置，则为只读。                                                                         |
| `sharing`                              | `shared`、`private` 或 `locked` 之一。默认为 `shared`。`shared` 缓存挂载可被多个写入者并发使用。`private` 在存在多个写入者时创建新挂载。`locked` 会暂停第二个写入者，直到第一个写入者释放挂载。 |
| `from`                                 | 用作缓存挂载基础的构建阶段、上下文或镜像名称。默认为空目录。                                   |
| `source`                               | `from` 中要挂载的子路径。默认为 `from` 的根目录。                                            |
| `mode`                                 | 新缓存目录的文件模式（八进制）。默认为 `0755`。                                                |
| `uid`                                  | 新缓存目录的用户 ID。默认为 `0`。                                                             |
| `gid`                                  | 新缓存目录的组 ID。默认为 `0`。                                                               |

缓存目录的内容在构建器调用之间持续存在，不会使指令缓存失效。缓存挂载应仅用于提高性能。您的构建应该能够处理缓存目录的任何内容，因为其他构建可能会覆盖文件，或者如果存储空间不足，GC 可能会清理它。

#### 示例：缓存 Go 包

```dockerfile
# syntax=docker/dockerfile:1
FROM golang
RUN --mount=type=cache,target=/root/.cache/go-build \
  go build ...
```

#### 示例：缓存 apt 包

```dockerfile
# syntax=docker/dockerfile:1
FROM ubuntu
RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update && apt-get --no-install-recommends install -y gcc
```

Apt 需要独占访问其数据，因此缓存使用 `sharing=locked` 选项，这将确保多个使用相同缓存挂载的并行构建将相互等待，不会同时访问相同的缓存文件。如果您希望每个构建在这种情况下创建另一个缓存目录，也可以使用 `sharing=private`。

### RUN --mount=type=tmpfs

此挂载类型允许在构建容器中挂载 `tmpfs`。

| 选项                                   | 描述                                                                                         |
| -------------------------------------- | -------------------------------------------------------------------------------------------- |
| `target`, `dst`, `destination`[^1]     | 挂载路径。                                                                                   |
| `size`                                 | 指定文件系统大小的上限。                                                                     |

### RUN --mount=type=secret

此挂载类型允许构建容器访问密钥值（如令牌或私钥），而无需将其烘焙到镜像中。

默认情况下，密钥作为文件挂载。您也可以通过设置 `env` 选项将密钥挂载为环境变量。

| 选项                               | 描述                                                                                         |
| ---------------------------------- | -------------------------------------------------------------------------------------------- |
| `id`                               | 密钥的 ID。默认为目标路径的基本名称。                                                        |
| `target`, `dst`, `destination`     | 将密钥挂载到指定路径。如果未设置且 `env` 也未设置，则默认为 `/run/secrets/` + `id`。         |
| `env`                              | 将密钥挂载到环境变量而不是文件，或两者都挂载（自 Dockerfile v1.10.0 起）。                    |
| `required`                         | 如果设置为 `true`，当密钥不可用时指令出错。默认为 `false`。                                   |
| `mode`                             | 密钥文件的文件模式（八进制）。默认为 `0400`。                                                |
| `uid`                              | 密钥文件的用户 ID。默认为 `0`。                                                              |
| `gid`                              | 密钥文件的组 ID。默认为 `0`。                                                                |

#### 示例：访问 S3

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3
RUN pip install awscli
RUN --mount=type=secret,id=aws,target=/root/.aws/credentials \
  aws s3 cp s3://... ...
```

```console
$ docker buildx build --secret id=aws,src=$HOME/.aws/credentials .
```

#### 示例：挂载为环境变量

以下示例使用密钥 `API_KEY` 并将其挂载为同名的环境变量。

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
RUN --mount=type=secret,id=API_KEY,env=API_KEY \
    some-command --token-from-env $API_KEY
```

假设 `API_KEY` 环境变量已在构建环境中设置，您可以使用以下命令构建它：

```console
$ docker buildx build --secret id=API_KEY .
```

### RUN --mount=type=ssh

此挂载类型允许构建容器通过 SSH 代理访问 SSH 密钥，支持密码短语。

| 选项                               | 描述                                                                                         |
| ---------------------------------- | -------------------------------------------------------------------------------------------- |
| `id`                               | SSH 代理套接字或密钥的 ID。默认为 "default"。                                                |
| `target`, `dst`, `destination`     | SSH 代理套接字路径。默认为 `/run/buildkit/ssh_agent.${N}`。                                  |
| `required`                         | 如果设置为 `true`，当密钥不可用时指令出错。默认为 `false`。                                   |
| `mode`                             | 套接字的文件模式（八进制）。默认为 `0600`。                                                  |
| `uid`                              | 套接字的用户 ID。默认为 `0`。                                                                |
| `gid`                              | 套接字的组 ID。默认为 `0`。                                                                  |

#### 示例：访问 GitLab

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
RUN apk add --no-cache openssh-client
RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan gitlab.com >> ~/.ssh/known_hosts
RUN --mount=type=ssh \
  ssh -q -T git@gitlab.com 2>&1 | tee /hello
# "Welcome to GitLab, @GITLAB_USERNAME_ASSOCIATED_WITH_SSHKEY" should be printed here
# with the type of build progress is defined as `plain`.
```

```console
$ eval $(ssh-agent)
$ ssh-add ~/.ssh/id_rsa
(Input your passphrase here)
$ docker buildx build --ssh default=$SSH_AUTH_SOCK .
```

您也可以直接指定主机上 `*.pem` 文件的路径，而不是 `$SSH_AUTH_SOCK`。但是，不支持带有密码短语的 pem 文件。

### RUN --network

```dockerfile
RUN --network=<TYPE>
```

`RUN --network` 允许控制命令运行的网络环境。

支持的网络类型有：

| 类型                                             | 描述                             |
| ------------------------------------------------ | -------------------------------- |
| [`default`](#run---networkdefault) (默认)        | 在默认网络中运行。               |
| [`none`](#run---networknone)                     | 无网络访问的情况下运行。         |
| [`host`](#run---networkhost)                     | 在主机的网络环境中运行。         |

### RUN --network=default

等同于不提供任何标志，命令在构建的默认网络中运行。

### RUN --network=none

命令在无网络访问的情况下运行（`lo` 仍然可用，但与此进程隔离）。

#### 示例：隔离外部影响

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.6
ADD mypackage.tgz wheels/
RUN --network=none pip install --find-links wheels mypackage
```

`pip` 只能安装在 tar 文件中提供的包，这可以由较早的构建阶段控制。

### RUN --network=host

命令在主机的网络环境中运行（类似于 `docker build --network=host`，但是按指令的粒度）。

> [!WARNING]
> 使用 `--network=host` 受 `network.host` 权限保护，需要在启动 buildkitd 守护进程时使用 `--allow-insecure-entitlement network.host` 标志或在 [buildkitd 配置](https://github.com/moby/buildkit/blob/master/docs/buildkitd.toml.md)中启用，并且在构建请求中使用 [`--allow network.host` 标志](https://docs.docker.com/engine/reference/commandline/buildx_build/#allow)。

### RUN --security

```dockerfile
RUN --security=<sandbox|insecure>
```

默认安全模式是 `sandbox`。使用 `--security=insecure`，构建器在非安全模式下运行命令而不使用沙箱，这允许运行需要提升权限的流程（例如 containerd）。这等效于运行 `docker run --privileged`。

> [!WARNING]
> 要访问此功能，需要在启动 buildkitd 守护进程时使用 `--allow-insecure-entitlement security.insecure` 标志或在 [buildkitd 配置](https://github.com/moby/buildkit/blob/master/docs/buildkitd.toml.md)中启用 `security.insecure` 权限，并且在构建请求中使用 [`--allow security.insecure` 标志](https://docs.docker.com/engine/reference/commandline/buildx_build/#allow)。

默认沙箱模式可以通过 `--security=sandbox` 激活，但这无操作。

#### 示例：检查权限

```dockerfile
# syntax=docker/dockerfile:1
FROM ubuntu
RUN --security=insecure cat /proc/self/status | grep CapEff
```

```text
#84 0.093 CapEff:	0000003fffffffff
```

## CMD

`CMD` 指令设置从镜像运行容器时要执行的命令。

您可以使用 [shell 或 exec 形式](#shell-and-exec-form)指定 `CMD` 指令：

- `CMD ["executable","param1","param2"]` (exec 形式)
- `CMD ["param1","param2"]` (exec 形式，作为 `ENTRYPOINT` 的默认参数)
- `CMD command param1 param2` (shell 形式)

一个 Dockerfile 中只能有一个 `CMD` 指令。如果您列出多个 `CMD`，只有最后一个生效。

`CMD` 的目的是为执行中的容器提供默认值。这些默认值可以包含可执行文件，也可以省略可执行文件（在这种情况下，您还必须指定 `ENTRYPOINT` 指令）。

如果您希望容器每次都运行相同的可执行文件，那么您应该考虑将 `ENTRYPOINT` 与 `CMD` 结合使用。请参阅 [`ENTRYPOINT`](#entrypoint)。如果用户向 `docker run` 提供了参数，它们将覆盖 `CMD` 中指定的默认值，但仍然使用默认的 `ENTRYPOINT`。

如果 `CMD` 用于为 `ENTRYPOINT` 指令提供默认参数，则 `CMD` 和 `ENTRYPOINT` 指令都应以 [exec 形式](#exec-form)指定。

> [!NOTE]
> 不要混淆 `RUN` 和 `CMD`。`RUN` 实际运行命令并提交结果；`CMD` 在构建时不执行任何操作，而是指定镜像的预期命令。

## LABEL

```dockerfile
LABEL <key>=<value> [<key>=<value>...]
```

`LABEL` 指令为镜像添加元数据。`LABEL` 是一个键值对。要在 `LABEL` 值中包含空格，请像在命令行解析中那样使用引号和反斜杠。几个使用示例：

```dockerfile
LABEL "com.example.vendor"="ACME Incorporated"
LABEL com.example.label-with-value="foo"
LABEL version="1.0"
LABEL description="This text illustrates \
that label-values can span multiple lines."
```

一个镜像可以有多个标签。您可以在单行上指定多个标签。在 Docker 1.10 之前，这可以减少最终镜像的大小，但现在情况已不再如此。您仍然可以选择在一条指令中指定多个标签，使用以下两种方式之一：

```dockerfile
LABEL multi.label1="value1" multi.label2="value2" other="value3"
```

```dockerfile
LABEL multi.label1="value1" \
      multi.label2="value2" \
      other="value3"
```

> [!NOTE]
> 确保使用双引号而不是单引号。特别是当您使用字符串插值时（例如 `LABEL example="foo-$ENV_VAR"`），单引号将按原样使用字符串，而不会解包变量的值。

基础镜像（`FROM` 行中的镜像）中包含的标签会被您的镜像继承。如果某个标签已存在但值不同，则最近应用的值会覆盖之前设置的值。

在多阶段构建中，只有最终阶段直接或间接（通过 `FROM`）基于中间阶段时，中间阶段的标签才会出现在最终镜像中。仅通过 `COPY --from` 或 `RUN --mount=from=` 引用的阶段的标签不会包含在输出镜像中。最终 `FROM` 指令中指定的基础镜像的标签总是被继承。

要查看镜像的标签，请使用 `docker image inspect` 命令。您可以使用 `--format` 选项仅显示标签：

```console
$ docker image inspect --format='{{json .Config.Labels}}' myimage
```

```json
{
  "com.example.vendor": "ACME Incorporated",
  "com.example.label-with-value": "foo",
  "version": "1.0",
  "description": "This text illustrates that label-values can span multiple lines.",
  "multi.label1": "value1",
  "multi.label2": "value2",
  "other": "value3"
}
```

## MAINTAINER (已弃用)

```dockerfile
MAINTAINER <name>
```

`MAINTAINER` 指令设置生成镜像的 _Author_ 字段。`LABEL` 指令是此指令的更灵活版本，您应该使用它，因为它可以设置您需要的任何元数据，并且可以轻松查看，例如使用 `docker inspect`。要设置对应于 `MAINTAINER` 字段的标签，您可以使用：

```dockerfile
LABEL org.opencontainers.image.authors="SvenDowideit@home.org.au"
```

然后这将与其他标签一起在 `docker inspect` 中可见。

## EXPOSE

```dockerfile
EXPOSE <port> [<port>/<protocol>...]
```

`EXPOSE` 指令通知 Docker 容器在运行时监听指定的网络端口。您可以指定端口监听 TCP 还是 UDP，如果未指定协议，默认为 TCP。

`EXPOSE` 指令实际上并不发布端口。它作为一种文档，在构建镜像的人和运行容器的人之间传达哪些端口旨在被发布。要在运行容器时发布端口，请在 `docker run` 上使用 `-p` 标志来发布和映射一个或多个端口，或使用 `-P` 标志来发布所有暴露的端口并将其映射到高阶端口。

默认情况下，`EXPOSE` 假定为 TCP。您也可以指定 UDP：

```dockerfile
EXPOSE 80/udp
```

要同时暴露 TCP 和 UDP，请包含两行：

```dockerfile
EXPOSE 80/tcp
EXPOSE 80/udp
```

在这种情况下，如果您在 `docker run` 中使用 `-P`，端口将分别暴露一次 TCP 和一次 UDP。请记住，`-P` 在主机上使用临时的高阶主机端口，因此 TCP 和 UDP 不会使用相同的端口。

无论 `EXPOSE` 设置如何，您都可以在运行时使用 `-p` 标志覆盖它们。例如

```console
$ docker run -p 80:80/tcp -p 80:80/udp ...
```

要在主机系统上设置端口重定向，请参阅[使用 -P 标志](https://docs.docker.com/reference/cli/docker/container/run/#publish)。`docker network` 命令支持创建用于容器间通信的网络，无需暴露或发布特定端口，因为连接到网络的容器可以通过任何端口相互通信。有关详细信息，请参阅[此功能的概述](https://docs.docker.com/engine/userguide/networking/)。

## ENV

```dockerfile
ENV <key>=<value> [<key>=<value>...]
```

`ENV` 指令将环境变量 `<key>` 设置为值 `<value>`。该值将存在于构建阶段中所有后续指令的环境中，并且可以在许多指令中进行[内联替换](#environment-replacement)。该值将被解释为其他环境变量，因此如果未转义，引号字符将被删除。与命令行解析一样，可以使用引号和反斜杠在值中包含空格。

示例：

```dockerfile
ENV MY_NAME="John Doe"
ENV MY_DOG=Rex\ The\ Dog
ENV MY_CAT=fluffy
```

`ENV` 指令允许一次设置多个 `<key>=<value>` 变量，下面的示例将在最终镜像中产生相同的净结果：

```dockerfile
ENV MY_NAME="John Doe" MY_DOG=Rex\ The\ Dog \
    MY_CAT=fluffy
```

使用 `ENV` 设置的环境变量将在从生成的镜像运行容器时持续存在。您可以使用 `docker inspect` 查看这些值，并使用 `docker run --env <key>=<value>` 更改它们。

一个阶段会继承其父阶段或任何祖先阶段使用 `ENV` 设置的任何环境变量。有关更多信息，请参阅手册中的[多阶段构建部分](https://docs.docker.com/build/building/multi-stage/)。

环境变量的持久性可能导致意外的副作用。例如，设置 `ENV DEBIAN_FRONTEND=noninteractive` 会改变 `apt-get` 的行为，并可能使镜像的用户感到困惑。

如果环境变量仅在构建期间需要，而在最终镜像中不需要，请考虑为单个命令设置值：

```dockerfile
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y ...
```

或者使用 [`ARG`](#arg)，它不会保留在最终镜像中：

```dockerfile
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y ...
```

> [!NOTE]
> **替代语法**
>
> `ENV` 指令还允许一种替代语法 `ENV <key> <value>`，省略 `=`。例如：
>
> ```dockerfile
> ENV MY_VAR my-value
> ```
>
> 此语法不允许在单个 `ENV` 指令中设置多个环境变量，并且可能令人困惑。例如，以下指令设置单个环境变量 (`ONE`)，其值为 `"TWO= THREE=world"`：
>
> ```dockerfile
> ENV ONE TWO= THREE=world
> ```
>
> 支持替代语法是为了向后兼容，但由于上述原因不推荐使用，并且可能在将来的版本中删除。

## ADD

ADD 有两种形式。
对于包含空格的路径，需要使用后一种形式。

```dockerfile
ADD [OPTIONS] <src> ... <dest>
ADD [OPTIONS] ["<src>", ... "<dest>"]
```

可用的 `[OPTIONS]` 包括：

| 选项                                        | 最低 Dockerfile 版本 |
| ------------------------------------------- | -------------------- |
| [`--keep-git-dir`](#add---keep-git-dir)     | 1.1                  |
| [`--checksum`](#add---checksum)             | 1.6                  |
| [`--chmod`](#add---chmod)                   | 1.2                  |
| [`--chown`](#add---chown)                   |                      |
| [`--link`](#add---link)                     | 1.4                  |
| [`--unpack`](#add---unpack)                 | 1.17                 |
| [`--exclude`](#add---exclude)               | 1.19                 |

`ADD` 指令从 `<src>` 复制新文件或目录，并将它们添加到镜像的文件系统中的 `<dest>` 路径。文件和目录可以从构建上下文、远程 URL 或 Git 仓库复制。

`ADD` 和 `COPY` 指令在功能上相似，但用途略有不同。了解更多关于 [`ADD` 和 `COPY` 之间的差异](https://docs.docker.com/build/building/best-practices/#add-or-copy)。

### 源

您可以使用 `ADD` 指定多个源文件或目录。最后一个参数必须始终是目标路径。例如，要将构建上下文中的两个文件 `file1.txt` 和 `file2.txt` 添加到构建容器的 `/usr/src/things/` 中：

```dockerfile
ADD file1.txt file2.txt /usr/src/things/
```

如果您直接或使用通配符指定多个源文件，则目标必须是一个目录（必须以斜杠 `/` 结尾）。

要从远程位置添加文件，您可以将 URL 或 Git 仓库地址指定为源。例如：

```dockerfile
ADD https://example.com/archive.zip /usr/src/things/
ADD git@github.com:user/repo.git /usr/src/things/
```

BuildKit 检测 `<src>` 的类型并相应处理。

- 如果 `<src>` 是本地文件或目录，则将目录的内容复制到指定的目标。请参阅[从构建上下文添加文件](#adding-files-from-the-build-context)。
- 如果 `<src>` 是本地 tar 归档文件，则将其解压缩并提取到指定的目标。请参阅[添加本地 tar 归档文件](#adding-local-tar-archives)。
- 如果 `<src>` 是 URL，则下载 URL 的内容并将其放置到指定的目标。请参阅[从 URL 添加文件](#adding-files-from-a-url)。
- 如果 `<src>` 是 Git 仓库，则将仓库克隆到指定的目标。请参阅[从 Git 仓库添加文件](#adding-files-from-a-git-repository)。

#### 从构建上下文添加文件

任何不以 `http://`、`https://` 或 `git@` 协议前缀开头的相对或本地路径都被视为本地文件路径。本地文件路径相对于构建上下文。例如，如果构建上下文是当前目录，则 `ADD file.txt /` 将 `./file.txt` 文件添加到构建容器的文件系统根目录。

指定带有前导斜杠或导航到构建上下文之外的源路径，例如 `ADD ../something /something`，会自动删除任何父目录导航（`../`）。源路径中的尾部斜杠也会被忽略，因此 `ADD something/ /something` 等效于 `ADD something /something`。

如果源是目录，则复制目录的内容，包括文件系统元数据。目录本身不会被复制，只会复制其内容。如果它包含子目录，则这些子目录也会被复制，并与目标处的任何现有目录合并。任何冲突都以逐文件方式解决，优先处理要添加的内容，除非您尝试将目录复制到现有文件上，在这种情况下会引发错误。

如果源是文件，则将文件和其元数据复制到目标。文件权限将被保留。如果源是文件，并且目标处存在同名的目录，则会引发错误。

如果您通过 stdin 将 Dockerfile 传递给构建（`docker build - < Dockerfile`），则没有构建上下文。在这种情况下，您只能使用 `ADD` 指令复制远程文件。您也可以通过 stdin 传递 tar 归档文件（`docker build - < archive.tar`），归档文件根目录下的 Dockerfile 和归档文件的其余部分将用作构建的上下文。

##### 模式匹配

对于本地文件，每个 `<src>` 可以包含通配符，匹配将使用 Go 的 [filepath.Match](https://golang.org/pkg/path/filepath#Match) 规则进行。

例如，要添加构建上下文根目录中以 `.png` 结尾的所有文件和目录：

```dockerfile
ADD *.png /dest/
```

在以下示例中，`?` 是单字符通配符，匹配例如 `index.js` 和 `index.ts`。

```dockerfile
ADD index.?s /dest/
```

当添加包含特殊字符（如 `[` 和 `]`）的文件或目录时，您需要按照 Golang 规则转义这些路径，以防止它们被视为匹配模式。例如，要添加名为 `arr[0].txt` 的文件，请使用以下命令：

```dockerfile
ADD arr[[]0].txt /dest/
```

#### 添加本地 tar 归档文件

当使用本地 tar 归档文件作为 `ADD` 的源时，如果归档文件是公认的压缩格式（`gzip`、`bzip2` 或 `xz`，或未压缩），则归档文件将被解压缩并提取到指定的目标。本地 tar 归档文件默认被提取，请参阅 [`ADD --unpack` 标志](#add---unpack)。

当提取目录时，其行为与 `tar -x` 相同。结果是以下内容的并集：

1. 目标路径中已存在的内容，以及
2. 源树的内容，以逐文件方式解决冲突，优先处理要添加的内容。

> [!NOTE]
> 文件是否被识别为公认的压缩格式仅基于文件的内容，而不是文件名。例如，如果一个空文件恰好以 `.tar.gz` 结尾，它不会被识别为压缩文件，也不会产生任何解压缩错误消息，而是将文件直接复制到目标。

#### 从 URL 添加文件

当源是远程文件 URL 时，目标的权限为 600。如果 HTTP 响应包含 `Last-Modified` 头，则该头中的时间戳将用于设置目标文件的 `mtime`。然而，与 `ADD` 期间处理的任何其他文件一样，`mtime` 不包含在确定文件是否已更改以及缓存是否应更新的判断中。

如果远程文件是 tar 归档文件，默认情况下不会提取归档文件。要下载并提取归档文件，请使用 [`ADD --unpack` 标志](#add---unpack)。

如果目标以尾部斜杠结尾，则文件名从 URL 路径推断。例如，`ADD http://example.com/foobar /` 将创建文件 `/foobar`。URL 必须具有非平凡的路径，以便可以发现适当的文件名（`http://example.com` 无效）。

如果目标不以尾部斜杠结尾，则目标路径成为从 URL 下载的文件的文件名。例如，`ADD http://example.com/foo /bar` 创建文件 `/bar`。

如果您的 URL 文件受身份验证保护，您需要使用 `RUN wget`、`RUN curl` 或使用容器内的其他工具，因为 `ADD` 指令不支持身份验证。

#### 从 Git 仓库添加文件

要将 Git 仓库用作 `ADD` 的源，您可以将仓库的 HTTP 或 SSH 地址作为源引用。仓库将被克隆到镜像中的指定目标。

```dockerfile
ADD https://github.com/user/repo.git /mydir/
```

您可以使用 URL 片段来指定特定的分支、标签、提交或子目录。例如，要添加 `buildkit` 仓库的 `v0.14.1` 标签的 `docs` 目录：

```dockerfile
ADD git@github.com:moby/buildkit.git#v0.14.1:docs /buildkit-docs
```

有关 Git URL 片段的更多信息，请参阅 [URL 片段](https://docs.docker.com/build/building/context/#url-fragments)。

当从 Git 仓库添加时，文件的权限位为 644。如果仓库中的文件设置了可执行位，则其权限将设置为 755。目录的权限设置为 755。

当使用 Git 仓库作为源时，仓库必须可以从构建上下文访问。要通过 SSH 添加仓库，无论是公共的还是私有的，您都必须传递 SSH 密钥进行身份验证。例如，给定以下 Dockerfile：

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
ADD git@git.example.com:foo/bar.git /bar
```

要构建此 Dockerfile，请将 `--ssh` 标志传递给 `docker build` 以将 SSH 代理套接字挂载到构建中。例如：

```console
$ docker build --ssh default .
```

有关使用密钥进行构建的更多信息，请参阅[构建密钥](https://docs.docker.com/build/building/secrets/)。

### 目标

如果目标路径以正斜杠开头，则将其解释为绝对路径，并将源文件复制到相对于当前构建阶段根目录的指定目标。

```dockerfile
# 创建 /abs/test.txt
ADD test.txt /abs/
```

尾部斜杠很重要。例如，`ADD test.txt /abs` 在 `/abs` 处创建一个文件，而 `ADD test.txt /abs/` 则创建 `/abs/test.txt`。

如果目标路径不以正斜杠开头，则将其解释为相对于构建容器的工作目录。

```dockerfile
WORKDIR /usr/src/app
# 创建 /usr/src/app/rel/test.txt
ADD test.txt rel/
```

如果目标不存在，则会创建它以及其路径中所有缺失的目录。

如果源是文件，并且目标不以尾部斜杠结尾，则源文件将作为文件写入目标路径。

### ADD --keep-git-dir

```dockerfile
ADD [--keep-git-dir=<boolean>] <src> ... <dir>
```

当 `<src>` 是远程 Git 仓库的 HTTP 或 SSH 地址时，BuildKit 默认将 Git 仓库的内容添加到镜像中，排除 `.git` 目录。

`--keep-git-dir=true` 标志允许您保留 `.git` 目录。

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
ADD --keep-git-dir=true https://github.com/moby/buildkit.git#v0.10.1 /buildkit
```

### ADD --checksum

```dockerfile
ADD [--checksum=<hash>] <src> ... <dir>
```

`--checksum` 标志允许您验证远程 Git 或 HTTP 资源的校验和：

- 对于 Git 源，校验和是提交 SHA。它可以是完整的提交 SHA 或匹配前缀（1 个或多个字符）。
- 对于 HTTP 源，校验和是 SHA-256 内容摘要，格式为 `sha256:<hash>`。SHA-256 是唯一支持的哈希算法。

```dockerfile
ADD --checksum=be1f38e https://github.com/moby/buildkit.git#v0.26.2 /
ADD --checksum=sha256:24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d https://mirrors.edge.kernel.org/pub/linux/kernel/Historic/linux-0.01.tar.gz /
```

### ADD --chmod

请参阅 [`COPY --chmod`](#copy---chmod)。

### ADD --chown

请参阅 [`COPY --chown`](#copy---chown)。

### ADD --link

请参阅 [`COPY --link`](#copy---link)。

### ADD --unpack

```dockerfile
ADD [--unpack=<bool>] <src> ... <dir>
```

`--unpack` 标志控制是否在将 tar 归档文件（包括压缩格式如 `gzip` 或 `bzip2`）添加到镜像时自动解包。本地 tar 归档文件默认解包，而远程 tar 归档文件（其中 `src` 是 URL）则下载而不解包。

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
# 下载并解压 archive.tar.gz 到 /download:
ADD --unpack=true https://example.com/archive.tar.gz /download
# 添加本地 tar 而不解包：
ADD --unpack=false my-archive.tar.gz .
```

### ADD --exclude

请参阅 [`COPY --exclude`](#copy---exclude)。

## COPY

COPY 有两种形式。
对于包含空格的路径，需要使用后一种形式。

```dockerfile
COPY [OPTIONS] <src> ... <dest>
COPY [OPTIONS] ["<src>", ... "<dest>"]
```

可用的 `[OPTIONS]` 包括：

| 选项                                 | 最低 Dockerfile 版本 |
| ------------------------------------ | -------------------- |
| [`--from`](#copy---from)             |                      |
| [`--chmod`](#copy---chmod)           | 1.2                  |
| [`--chown`](#copy---chown)           |                      |
| [`--link`](#copy---link)             | 1.4                  |
| [`--parents`](#copy---parents)       | 1.20                 |
| [`--exclude`](#copy---exclude)       | 1.19                 |

`COPY` 指令从 `<src>` 复制新文件或目录，并将它们添加到镜像的文件系统中的 `<dest>` 路径。文件和目录可以从构建上下文、构建阶段、命名上下文或镜像复制。

`ADD` 和 `COPY` 指令在功能上相似，但用途略有不同。了解更多关于 [`ADD` 和 `COPY` 之间的差异](https://docs.docker.com/build/building/best-practices/#add-or-copy)。

### 源

您可以使用 `COPY` 指定多个源文件或目录。最后一个参数必须始终是目标路径。例如，要将构建上下文中的两个文件 `file1.txt` 和 `file2.txt` 复制到构建容器的 `/usr/src/things/` 中：

```dockerfile
COPY file1.txt file2.txt /usr/src/things/
```

如果您直接或使用通配符指定多个源文件，则目标必须是一个目录（必须以斜杠 `/` 结尾）。

`COPY` 接受一个标志 `--from=<name>`，允许您将源位置指定为构建阶段、上下文或镜像。以下示例从名为 `build` 的阶段复制文件：

```dockerfile
FROM golang AS build
WORKDIR /app
RUN --mount=type=bind,target=. go build -o /myapp ./cmd

COPY --from=build /myapp /usr/bin/
```

有关从命名源复制的更多信息，请参阅 [`--from` 标志](#copy---from)。

#### 从构建上下文复制

当从构建上下文复制源文件时，路径被解释为相对于上下文根目录。

指定带有前导斜杠或导航到构建上下文之外的源路径，例如 `COPY ../something /something`，会自动删除任何父目录导航（`../`）。源路径中的尾部斜杠也会被忽略，因此 `COPY something/ /something` 等效于 `COPY something /something`。

如果源是目录，则复制目录的内容，包括文件系统元数据。目录本身不会被复制，只会复制其内容。如果它包含子目录，则这些子目录也会被复制，并与目标处的任何现有目录合并。任何冲突都以逐文件方式解决，优先处理要添加的内容，除非您尝试将目录复制到现有文件上，在这种情况下会引发错误。

如果源是文件，则将文件和其元数据复制到目标。文件权限将被保留。如果源是文件，并且目标处存在同名的目录，则会引发错误。

如果您通过 stdin 将 Dockerfile 传递给构建（`docker build - < Dockerfile`），则没有构建上下文。在这种情况下，您只能使用 `COPY` 指令从其他阶段、命名上下文或镜像复制文件，使用 [`--from` 标志](#copy---from)。您也可以通过 stdin 传递 tar 归档文件（`docker build - < archive.tar`），归档文件根目录下的 Dockerfile 和归档文件的其余部分将用作构建的上下文。

当使用 Git 仓库作为构建上下文时，复制文件的权限位为 644。如果仓库中的文件设置了可执行位，则其权限将设置为 755。目录的权限设置为 755。

##### 模式匹配

对于本地文件，每个 `<src>` 可以包含通配符，匹配将使用 Go 的 [filepath.Match](https://golang.org/pkg/path/filepath#Match) 规则进行。

例如，要添加构建上下文根目录中以 `.png` 结尾的所有文件和目录：

```dockerfile
COPY *.png /dest/
```

在以下示例中，`?` 是单字符通配符，匹配例如 `index.js` 和 `index.ts`。

```dockerfile
COPY index.?s /dest/
```

当添加包含特殊字符（如 `[` 和 `]`）的文件或目录时，您需要按照 Golang 规则转义这些路径，以防止它们被视为匹配模式。例如，要添加名为 `arr[0].txt` 的文件，请使用以下命令：

```dockerfile
COPY arr[[]0].txt /dest/
```

### 目标

如果目标路径以正斜杠开头，则将其解释为绝对路径，并将源文件复制到相对于当前构建阶段根目录的指定目标。

```dockerfile
# 创建 /abs/test.txt
COPY test.txt /abs/
```

尾部斜杠很重要。例如，`COPY test.txt /abs` 在 `/abs` 处创建一个文件，而 `COPY test.txt /abs/` 则创建 `/abs/test.txt`。

如果目标路径不以正斜杠开头，则将其解释为相对于构建容器的工作目录。

```dockerfile
WORKDIR /usr/src/app
# 创建 /usr/src/app/rel/test.txt
COPY test.txt rel/
```

如果目标不存在，则会创建它以及其路径中所有缺失的目录。

如果源是文件，并且目标不以尾部斜杠结尾，则源文件将作为文件写入目标路径。

### COPY --from

默认情况下，`COPY` 指令从构建上下文复制文件。`COPY --from` 标志允许您改为从镜像、构建阶段或命名上下文复制文件。

```dockerfile
COPY [--from=<image|stage|context>] <src> ... <dest>
```

要从[多阶段构建](https://docs.docker.com/build/building/multi-stage/)中的构建阶段复制，请指定要从中复制的阶段的名称。您可以使用 `FROM` 指令中的 `AS` 关键字指定阶段名称。

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine AS build
COPY . .
RUN apk add clang
RUN clang -o /hello hello.c

FROM scratch
COPY --from=build /hello /
```

您也可以直接从命名上下文（使用 `--build-context <name>=<source>` 指定）或镜像复制文件。以下示例从官方 Nginx 镜像复制 `nginx.conf` 文件。

```dockerfile
COPY --from=nginx:latest /etc/nginx/nginx.conf /nginx.conf
```

`COPY --from` 的源路径始终从您指定的镜像或阶段的文件系统根目录解析。

### COPY --chmod

```dockerfile
COPY [--chmod=<perms>] <src> ... <dest>
```

`--chmod` 标志支持八进制表示法（例如 `755`、`644`）和符号表示法（例如 `+x`、`g=u`）。符号表示法（在 Dockerfile 1.14 版本中添加）在八进制不够灵活时很有用。例如，`u=rwX,go=rX` 将目录设置为 755，文件设置为 644，同时保留已具有可执行位的文件的可执行位。（大写 `X` 表示“仅当它是目录或已可执行时才可执行”。）

有关符号表示法语法的更多信息，请参阅 [chmod(1) 手册](https://man.freebsd.org/cgi/man.cgi?chmod)。

使用八进制表示法的示例：

```dockerfile
COPY --chmod=755 app.sh /app/
COPY --chmod=644 file.txt /data/
ARG MODE=440
COPY --chmod=$MODE . .
```

使用符号表示法的示例：

```dockerfile
COPY --chmod=+x script.sh /app/
COPY --chmod=u=rwX,go=rX . /app/
COPY --chmod=g=u config/ /config/
```

构建 Windows 容器时不支持 `--chmod` 标志。

### COPY --chown

```dockerfile
COPY [--chown=<user>:<group>] <src> ... <dest>
```

设置复制文件的所有权。没有此标志时，文件以 UID 和 GID 为 0 创建。

该标志接受用户名、组名、UID 或 GID 的任意组合。如果仅指定用户，则 GID 设置为与 UID 相同的数值。

```dockerfile
COPY --chown=55:mygroup files* /somedir/
COPY --chown=bin files* /somedir/
COPY --chown=1 files* /somedir/
COPY --chown=10:11 files* /somedir/
COPY --chown=myuser:mygroup --chmod=644 files* /somedir/
```

当使用名称而不是数字 ID 时，BuildKit 使用容器根文件系统中的 `/etc/passwd` 和 `/etc/group` 解析它们。如果这些文件缺失或不包含指定的名称，则构建失败。数字 ID 不需要此查找。

构建 Windows 容器时不支持 `--chown` 标志。

### COPY --link

```dockerfile
COPY [--link[=<boolean>]] <src> ... <dest>
```

在 `COPY` 或 `ADD` 命令中启用此标志，允许您使用增强的语义复制文件，其中您的文件保持独立于自己的层，并且不会在更改先前层上的命令时失效。

当使用 `--link` 时，您的源文件被复制到一个空的目标目录。该目录变成一个层，链接在您先前状态之上。

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
COPY --link /foo /bar
```

等效于进行两次构建：

```dockerfile
FROM alpine
```

和

```dockerfile
FROM scratch
COPY /foo /bar
```

并将两个镜像的所有层合并在一起。

#### 使用 `--link` 的好处

使用 `--link` 可以在后续构建中重用已构建的层，即使先前的层已更改，也可以使用 `--cache-from`。这对于多阶段构建尤其重要，其中 `COPY --from` 语句如果同一阶段中的任何先前命令发生更改，将会失效，导致需要重新构建中间阶段。使用 `--link`，先前构建生成的层会被重用并合并到新层之上。这也意味着当基础镜像收到更新时，您可以轻松地重新设置镜像的基础，而无需再次执行整个构建。在支持的后端中，BuildKit 可以执行此重新设置基础的操作，而无需在客户端和注册表之间推送或拉取任何层。BuildKit 将检测这种情况，并仅创建包含新层和旧层按正确顺序排列的新镜像清单。

当使用 `--link` 并且没有其他需要访问基础镜像中文件的命令时，也可能发生 BuildKit 避免拉取基础镜像的相同行为。在这种情况下，BuildKit 将仅为 `COPY` 命令构建层，并将它们直接推送到注册表，位于基础镜像的层之上。

#### 与 `--link=false` 的不兼容性

当使用 `--link` 时，`COPY/ADD` 命令不允许读取先前状态中的任何文件。这意味着，如果在先前状态中目标目录是包含符号链接的路径，则 `COPY/ADD` 无法跟踪它。在最终镜像中，使用 `--link` 创建的目标路径将始终是仅包含目录的路径。

如果您不依赖于跟踪目标路径中符号链接的行为，则始终建议使用 `--link`。`--link` 的性能等同于或优于默认行为，并且它为缓存重用创造了更好的条件。

### COPY --parents

```dockerfile
COPY [--parents[=<boolean>]] <src> ... <dest>
```

`--parents` 标志为 `src` 条目保留父目录。此标志默认为 `false`。

```dockerfile
# syntax=docker/dockerfile:1
FROM scratch

COPY ./x/a.txt ./y/a.txt /no_parents/
COPY --parents ./x/a.txt ./y/a.txt /parents/

# /no_parents/a.txt
# /parents/x/a.txt
# /parents/y/a.txt
```

此行为类似于 [Linux `cp` 实用程序](https://www.man7.org/linux/man-pages/man1/cp.1.html) 的 `--parents` 或 [`rsync`](https://man7.org/linux/man-pages/man1/rsync.1.html) 的 `--relative` 标志。

与 Rsync 一样，可以通过在源路径中插入一个点和一个斜杠（`./`）来限制保留哪些父目录。如果存在这样的点，则仅保留该点之后的父目录。这在 `--from` 阶段的复制中尤其有用，其中源路径需要是绝对路径。

```dockerfile
# syntax=docker/dockerfile:1
FROM scratch

COPY --parents ./x/./y/*.txt /parents/

# Build context:
# ./x/y/a.txt
# ./x/y/b.txt
#
# Output:
# /parents/y/a.txt
# /parents/y/b.txt
```

`**` 通配符匹配任意数量的路径组件（包括零个），可用于递归匹配目录级别的文件：

```dockerfile
# syntax=docker/dockerfile:1
FROM scratch

COPY --parents ./src/**/*.txt /parents/

# Build context:
# ./src/a.txt
# ./src/x/b.txt
# ./src/x/y/c.txt
#
# Output:
# /parents/src/a.txt
# /parents/src/x/b.txt
# /parents/src/x/y/c.txt
```

请注意，如果没有指定 `--parents` 标志，任何文件名冲突都会导致 Linux `cp` 操作失败并显示明确的错误消息（`cp: will not overwrite just-created './x/a.txt' with './y/a.txt'`），而 Buildkit 将静默覆盖目标处的目标文件。

虽然可以保留仅包含一个 `src` 条目的 `COPY` 指令的目录结构，但通常保持最终镜像中的层数尽可能低更有益。因此，使用 `--parents` 标志时，Buildkit 能够将多个 `COPY` 指令打包在一起，同时保持目录结构完整。

### COPY --exclude

```dockerfile
COPY [--exclude=<path> ...] <src> ... <dest>
```

`--exclude` 标志允许您指定要排除的文件的路径表达式。

路径表达式遵循与 `<src>` 相同的格式，支持通配符并使用 Go 的 [filepath.Match](https://golang.org/pkg/path/filepath#Match) 规则进行匹配。例如，要添加所有以 "hom" 开头的文件，排除具有 `.txt` 扩展名的文件：

```dockerfile
# syntax=docker/dockerfile:1
FROM scratch

COPY --exclude=*.txt hom* /mydir/
```

您可以为一条 `COPY` 指令多次指定 `--exclude` 选项。多个 `--exclude` 是匹配其模式的文件不会被复制，即使文件路径与 `<src>` 中指定的模式匹配。要添加所有以 "hom" 开头的文件，排除具有 `.txt` 或 `.md` 扩展名的文件：

```dockerfile
# syntax=docker/dockerfile:1
FROM scratch

COPY --exclude=*.txt --exclude=*.md hom* /mydir/
```

## ENTRYPOINT

`ENTRYPOINT` 允许您配置将作为可执行文件运行的容器。

`ENTRYPOINT` 有两种可能的形式：

- exec 形式，这是首选形式：

  ```dockerfile
  ENTRYPOINT ["executable", "param1", "param2"]
  ```

- shell 形式：

  ```dockerfile
  ENTRYPOINT command param1 param2
  ```

有关不同形式的更多信息，请参阅 [Shell 和 Exec 形式](#shell-and-exec-form)。

以下命令从 `nginx` 启动一个容器，使用其默认内容，监听端口 80：

```console
$ docker run -i -t --rm -p 80:80 nginx
```

`docker run <image>` 的命令行参数将附加到 exec 形式 `ENTRYPOINT` 的所有元素之后，并覆盖使用 `CMD` 指定的所有元素。

这允许将参数传递给入口点，即 `docker run <image> -d` 将传递 `-d` 参数给入口点。您可以使用 `docker run --entrypoint` 标志覆盖 `ENTRYPOINT` 指令。

shell 形式的 `ENTRYPOINT` 会忽略任何 `CMD` 或 `docker run` 命令行参数。它还会将您的 `ENTRYPOINT` 作为 `/bin/sh -c` 的子命令启动，这不传递信号。这意味着可执行文件不会是容器的 `PID 1`，并且不会接收 Unix 信号。在这种情况下，您的可执行文件不会从 `docker stop <container>` 接收到 `SIGTERM`。

Dockerfile 中只有最后一个 `ENTRYPOINT` 指令生效。

### Exec 形式 ENTRYPOINT 示例

您可以使用 exec 形式的 `ENTRYPOINT` 设置相当稳定的默认命令和参数，然后使用 `CMD` 设置更可能更改的其他默认值。

当将 exec 形式的 `ENTRYPOINT` 与 `CMD` 结合使用时，也请使用 exec 形式的 `CMD`。使用 shell 形式的 `CMD` 会导致它被包装在 `/bin/sh -c` 中，这意味着 `ENTRYPOINT` 接收的是 shell 调用作为其参数，而不是裸命令和参数。请参阅[理解 CMD 和 ENTRYPOINT 的交互](#understand-how-cmd-and-entrypoint-interact)。

```dockerfile
FROM ubuntu
ENTRYPOINT ["top", "-b"]
CMD ["-c"]
```

当您运行容器时，您可以看到 `top` 是唯一的进程：

```console
$ docker run -it --rm --name test  top -H

top - 08:25:00 up  7:27,  0 users,  load average: 0.00, 0.01, 0.05
Threads:   1 total,   1 running,   0 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.1 us,  0.1 sy,  0.0 ni, 99.7 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
KiB Mem:   2056668 total,  1616832 used,   439836 free,    99352 buffers
KiB Swap:  1441840 total,        0 used,  1441840 free.  1324440 cached Mem

  PID USER      PR  NI    VIRT    RES    SHR S %CPU %MEM     TIME+ COMMAND
    1 root      20   0   19744   2336   2080 R  0.0  0.1   0:00.04 top
```

要进一步检查结果，您可以使用 `docker exec`：

```console
$ docker exec -it test ps aux

USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  2.6  0.1  19752  2352 ?        Ss+  08:24   0:00 top -b -H
root         7  0.0  0.1  15572  2164 ?        R+   08:25   0:00 ps aux
```

您可以使用 `docker stop test` 优雅地请求 `top` 关闭。

以下 Dockerfile 展示了使用 `ENTRYPOINT` 在前台运行 Apache（即作为 `PID 1`）：

```dockerfile
FROM debian:stable
RUN apt-get update && apt-get install -y --force-yes apache2
EXPOSE 80 443
VOLUME ["/var/www", "/var/log/apache2", "/etc/apache2"]
ENTRYPOINT ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]
```

如果您需要为单个可执行文件编写启动脚本，可以通过使用 `exec` 和 `gosu` 命令确保最终可执行文件接收 Unix 信号：

```bash
#!/usr/bin/env bash
set -e

if [ "$1" = 'postgres' ]; then
    chown -R postgres "$PGDATA"

    if [ -z "$(ls -A "$PGDATA")" ]; then
        gosu postgres initdb
    fi

    exec gosu postgres "$@"
fi

exec "$@"
```

最后，如果您需要在关闭时进行一些额外的清理（或与其他容器通信），或者协调多个可执行文件，您可能需要确保 `ENTRYPOINT` 脚本接收 Unix 信号，将它们传递，然后执行更多工作：

```bash
#!/bin/sh
# 注意：我用 sh 编写，以便它也可以在 busybox 容器中工作

# 如果需要在服务停止后也进行手动清理，或者需要在一个容器中启动多个服务，请使用 trap
trap "echo TRAPed signal" HUP INT QUIT TERM

# 在此处后台启动服务
/usr/sbin/apachectl start

echo "[hit enter key to exit] or run 'docker stop <container>'"
read

# 在此处停止服务并进行清理
echo "stopping apache"
/usr/sbin/apachectl stop

echo "exited $0"
```

如果您使用 `docker run -it --rm -p 80:80 --name test apache` 运行此镜像，则可以使用 `docker exec` 或 `docker top` 检查容器的进程，然后要求脚本停止 Apache：

```console
$ docker exec -it test ps aux

USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.1  0.0   4448   692 ?        Ss+  00:42   0:00 /bin/sh /run.sh 123 cmd cmd2
root        19  0.0  0.2  71304  4440 ?        Ss   00:42   0:00 /usr/sbin/apache2 -k start
www-data    20  0.2  0.2 360468  6004 ?        Sl   00:42   0:00 /usr/sbin/apache2 -k start
www-data    21  0.2  0.2 360468  6000 ?        Sl   00:42   0:00 /usr/sbin/apache2 -k start
root        81  0.0  0.1  15572  2140 ?        R+   00:44   0:00 ps aux

$ docker top test

PID                 USER                COMMAND
10035               root                {run.sh} /bin/sh /run.sh 123 cmd cmd2
10054               root                /usr/sbin/apache2 -k start
10055               33                  /usr/sbin/apache2 -k start
10056               33                  /usr/sbin/apache2 -k start

$ /usr/bin/time docker stop test

test
real	0m 0.27s
user	0m 0.03s
sys	0m 0.03s
```

> [!NOTE]
> 您可以使用 `--entrypoint` 覆盖 `ENTRYPOINT` 设置，但这只能设置要执行的二进制文件（不会使用 `sh -c`）。

### Shell 形式 ENTRYPOINT 示例

您可以为 `ENTRYPOINT` 指定一个纯字符串，它将在 `/bin/sh -c` 中执行。此形式将使用 shell 处理来替换 shell 环境变量，并将忽略任何 `CMD` 或 `docker run` 命令行参数。为了确保 `docker stop` 能够正确地向任何长时间运行的 `ENTRYPOINT` 可执行文件发送信号，您需要记住使用 `exec` 启动它：

```dockerfile
FROM ubuntu
ENTRYPOINT exec top -b
```

当您运行此镜像时，您将看到单个 `PID 1` 进程：

```console
$ docker run -it --rm --name test top

Mem: 1704520K used, 352148K free, 0K shrd, 0K buff, 140368121167873K cached
CPU:   5% usr   0% sys   0% nic  94% idle   0% io   0% irq   0% sirq
Load average: 0.08 0.03 0.05 2/98 6
  PID  PPID USER     STAT   VSZ %VSZ %CPU COMMAND
    1     0 root     R     3164   0%   0% top -b
```

在 `docker stop` 时干净地退出：

```console
$ /usr/bin/time docker stop test

test
real	0m 0.20s
user	0m 0.02s
sys	0m 0.04s
```

如果您忘记在 `ENTRYPOINT` 开头添加 `exec`：

```dockerfile
FROM ubuntu
ENTRYPOINT top -b
CMD -- --ignored-param1
```

然后您可以运行它（为下一步命名）：

```console
$ docker run -it --name test top --ignored-param2

top - 13:58:24 up 17 min,  0 users,  load average: 0.00, 0.00, 0.00
Tasks:   2 total,   1 running,   1 sleeping,   0 stopped,   0 zombie
%Cpu(s): 16.7 us, 33.3 sy,  0.0 ni, 50.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :   1990.8 total,   1354.6 free,    231.4 used,    404.7 buff/cache
MiB Swap:   1024.0 total,   1024.0 free,      0.0 used.   1639.8 avail Mem

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
    1 root      20   0    2612    604    536 S   0.0   0.0   0:00.02 sh
    6 root      20   0    5956   3188   2768 R   0.0   0.2   0:00.00 top
```

您可以从 `top` 的输出中看到指定的 `ENTRYPOINT` 不是 `PID 1`。

如果您随后运行 `docker stop test`，容器将不会干净地退出 - `stop` 命令将在超时后被迫发送 `SIGKILL`：

```console
$ docker exec -it test ps waux

USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.4  0.0   2612   604 pts/0    Ss+  13:58   0:00 /bin/sh -c top -b --ignored-param2
root         6  0.0  0.1   5956  3188 pts/0    S+   13:58   0:00 top -b
root         7  0.0  0.1   5884  2816 pts/1    Rs+  13:58   0:00 ps waux

$ /usr/bin/time docker stop test

test
real	0m 10.19s
user	0m 0.04s
sys	0m 0.03s
```

### 理解 CMD 和 ENTRYPOINT 的交互

`CMD` 和 `ENTRYPOINT` 指令都定义了运行容器时执行什么命令。有几条规则描述了它们的协作。

1. Dockerfile 应至少指定 `CMD` 或 `ENTRYPOINT` 命令之一。

2. 当将容器用作可执行文件时，应定义 `ENTRYPOINT`。

3. `CMD` 应该用作定义 `ENTRYPOINT` 命令的默认参数或在容器中执行临时命令的方式。

4. 当使用替代参数运行容器时，`CMD` 将被覆盖。

下表显示了对于不同的 `ENTRYPOINT` / `CMD` 组合，执行什么命令：

|                                | 无 ENTRYPOINT              | ENTRYPOINT exec_entry p1_entry | ENTRYPOINT ["exec_entry", "p1_entry"]          |
| :----------------------------- | :------------------------- | :----------------------------- | :--------------------------------------------- |
| **无 CMD**                     | 错误，不允许               | /bin/sh -c exec_entry p1_entry | exec_entry p1_entry                            |
| **CMD ["exec_cmd", "p1_cmd"]** | exec_cmd p1_cmd            | /bin/sh -c exec_entry p1_entry | exec_entry p1_entry exec_cmd p1_cmd            |
| **CMD exec_cmd p1_cmd**        | /bin/sh -c exec_cmd p1_cmd | /bin/sh -c exec_entry p1_entry | exec_entry p1_entry /bin/sh -c exec_cmd p1_cmd |

> [!NOTE]
> 如果 `CMD` 是从基础镜像定义的，则设置 `ENTRYPOINT` 会将 `CMD` 重置为空值。在这种情况下，必须在此当前镜像中定义 `CMD` 才能具有值。

## VOLUME

```dockerfile
VOLUME ["/data"]
```

`VOLUME` 指令创建一个具有指定名称的挂载点，并将其标记为保存来自本地主机或其他容器的外部挂载卷。该值可以是 JSON 数组，如 `VOLUME ["/var/log/"]`，也可以是带有多个参数的纯字符串，如 `VOLUME /var/log` 或 `VOLUME /var/log /var/db`。有关更多信息/示例以及通过 Docker 客户端进行挂载的说明，请参阅[_通过卷共享目录_](https://docs.docker.com/storage/volumes/)文档。

`docker run` 命令使用基础镜像中指定位置存在的任何数据初始化新创建的卷。例如，考虑以下 Dockerfile 片段：

```dockerfile
FROM ubuntu
RUN mkdir /myvol
RUN echo "hello world" > /myvol/greeting
VOLUME /myvol
```

此 Dockerfile 生成一个镜像，使 `docker run` 在 `/myvol` 处创建一个新的挂载点，并将 `greeting` 文件复制到新创建的卷中。

### 关于指定卷的注意事项

请记住 Dockerfile 中关于卷的以下几点。

- **基于 Windows 的容器上的卷**：当使用基于 Windows 的容器时，容器内卷的目标必须是以下之一：
  - 不存在或空目录
  - `C:` 以外的驱动器

- **从 Dockerfile 内部更改卷**：如果在声明卷之后的任何构建步骤更改了卷内的数据，当使用旧版构建器时，这些更改将被丢弃。当使用 Buildkit 时，更改将被保留。

- **JSON 格式**：该列表被解析为 JSON 数组。您必须使用双引号（`"`）而不是单引号（`'`）括起单词。

- **主机目录在容器运行时声明**：主机目录（挂载点）本质上是依赖于主机的。这是为了保持镜像的可移植性，因为不能保证给定的主机目录在所有主机上都可用。因此，您不能从 Dockerfile 内部挂载主机目录。`VOLUME` 指令不支持指定 `host-dir` 参数。您必须在创建或运行容器时指定挂载点。

## USER

```dockerfile
USER <user>[:<group>]
```

或

```dockerfile
USER <UID>[:<GID>]
```

`USER` 指令设置用户名（或 UID）以及可选的用户组（或 GID），用作当前阶段其余部分的默认用户和组。指定的用户用于 `RUN` 指令，并在运行时运行相关的 `ENTRYPOINT` 和 `CMD` 命令。

> 请注意，当为用户指定组时，该用户将 _仅_ 拥有指定的组成员身份。任何其他配置的组成员身份将被忽略。

> [!WARNING]
> 当用户没有主组时，镜像（或后续指令）将以 `root` 组运行。
>
> 在 Windows 上，如果用户不是内置帐户，则必须首先创建该用户。这可以通过在 Dockerfile 中调用 `net user` 命令来完成。

```dockerfile
FROM microsoft/windowsservercore
# 在容器中创建 Windows 用户
RUN net user /add patrick
# 为后续命令设置它
USER patrick
```

## WORKDIR

```dockerfile
WORKDIR /path/to/workdir
```

`WORKDIR` 指令为 Dockerfile 中跟在它后面的任何 `RUN`、`CMD`、`ENTRYPOINT`、`COPY` 和 `ADD` 指令设置工作目录。如果 `WORKDIR` 不存在，即使它在后续的 Dockerfile 指令中未被使用，也会被创建。

`WORKDIR` 指令可以在 Dockerfile 中使用多次。如果提供了相对路径，它将相对于前一个 `WORKDIR` 指令的路径。例如：

```dockerfile
WORKDIR /a
WORKDIR b
WORKDIR c
RUN pwd
```

此 Dockerfile 中最终 `pwd` 命令的输出将是 `/a/b/c`。

`WORKDIR` 指令可以解析先前使用 `ENV` 设置的环境变量。您只能使用在 Dockerfile 中显式设置的环境变量。例如：

```dockerfile
ENV DIRPATH=/path
WORKDIR $DIRPATH/$DIRNAME
RUN pwd
```

此 Dockerfile 中最终 `pwd` 命令的输出将是 `/path/$DIRNAME`。

如果未指定，默认工作目录是 `/`。实际上，如果您不是从 `scratch` 构建 Dockerfile（`FROM scratch`），则 `WORKDIR` 很可能由您使用的基础镜像设置。

因此，为了避免在未知目录中进行意外操作，最佳实践是显式设置您的 `WORKDIR`。

## ARG

```dockerfile
ARG <name>[=<default value>] [<name>[=<default value>]...]
```

`ARG` 指令定义了一个变量，用户可以在构建时使用 `docker build` 命令通过 `--build-arg <varname>=<value>` 标志传递给构建器。该变量可以在后续指令中使用，例如 `FROM`、`ENV`、`WORKDIR` 等，使用 `${VAR}` 或 `$VAR` 模板语法。它也会作为构建时环境变量传递给所有后续的 `RUN` 指令。

与 `ENV` 不同，`ARG` 变量不会嵌入镜像中，并且在最终容器中不可用。

> [!WARNING]
> 不建议使用构建参数传递秘密信息，如用户凭据、API 令牌等。构建参数在 `docker history` 命令和 `max` 模式来源证明中可见，如果您使用 Buildx GitHub Actions 并且您的 GitHub 仓库是公共的，默认情况下会附加到镜像上。
>
> 请参阅 [`RUN --mount=type=secret`](#run---mounttypesecret) 部分，了解在构建镜像时安全使用秘密的方法。

Dockerfile 可能包含一个或多个 `ARG` 指令。例如，以下是一个有效的 Dockerfile：

```dockerfile
FROM busybox
ARG user1
ARG buildno
# ...
```

### 默认值

`ARG` 指令可以选择包含默认值：

```dockerfile
FROM busybox
ARG user1=someuser
ARG buildno=1
# ...
```

如果 `ARG` 指令具有默认值，并且在构建时没有传递值，则构建器使用默认值。

### 作用域

`ARG` 变量从其声明所在行开始在 Dockerfile 中生效。例如，考虑以下 Dockerfile：

```dockerfile
FROM busybox
USER ${username:-some_user}
ARG username
USER $username
# ...
```

用户通过调用以下命令构建此文件：

```console
$ docker build --build-arg username=what_user .
```

- 第 2 行的 `USER` 指令评估为 `some_user` 后备值，因为 `username` 变量尚未声明。
- `username` 变量在第 3 行声明，并从此处开始可供 Dockerfile 指令引用。
- 第 4 行的 `USER` 指令评估为 `what_user`，因为此时 `username` 参数具有通过命令行传递的值 `what_user`。在其被 `ARG` 指令定义之前，任何对变量的使用都会导致空字符串。

在构建阶段内声明的 `ARG` 变量会自动被基于该阶段的其他阶段继承。不相关的构建阶段无法访问该变量。要在多个不同的阶段中使用参数，每个阶段必须包含 `ARG` 指令，或者它们都必须基于同一 Dockerfile 中声明了该变量的共享基础阶段。

有关更多信息，请参阅[变量作用域](https://docs.docker.com/build/building/variables/#scoping)。

### 使用 ARG 变量

您可以使用 `ARG` 或 `ENV` 指令来指定对 `RUN` 指令可用的变量。使用 `ENV` 指令定义的环境变量总是覆盖同名的 `ARG` 指令。考虑这个包含 `ENV` 和 `ARG` 指令的 Dockerfile。

```dockerfile
FROM ubuntu
ARG CONT_IMG_VER
ENV CONT_IMG_VER=v1.0.0
RUN echo $CONT_IMG_VER
```

然后，假设此镜像是使用以下命令构建的：

```console
$ docker build --build-arg CONT_IMG_VER=v2.0.1 .
```

在这种情况下，`RUN` 指令使用 `v1.0.0` 而不是用户传递的 `ARG` 设置：`v2.0.1`。此行为类似于 shell 脚本，其中局部作用域的变量从其定义点开始覆盖作为参数传递或从环境继承的变量。

使用上面的示例但不同的 `ENV` 规范，您可以在 `ARG` 和 `ENV` 指令之间创建更有用的交互：

```dockerfile
FROM ubuntu
ARG CONT_IMG_VER
ENV CONT_IMG_VER=${CONT_IMG_VER:-v1.0.0}
RUN echo $CONT_IMG_VER
```

与 `ARG` 指令不同，`ENV` 值始终保留在构建的镜像中。考虑不带 `--build-arg` 标志的 docker 构建：

```console
$ docker build .
```

使用此 Dockerfile 示例，`CONT_IMG_VER` 仍然保留在镜像中，但其值将为 `v1.0.0`，因为这是第 3 行 `ENV` 指令设置的默认值。

此示例中的变量扩展技术允许您从命令行传递参数，并通过利用 `ENV` 指令将它们保留在最终镜像中。变量扩展仅受[一组有限的 Dockerfile 指令](#environment-replacement)支持。

### 预定义 ARG

Docker 有一组预定义的 `ARG` 变量，您可以在没有相应 `ARG` 指令的情况下在 Dockerfile 中使用它们。

- `HTTP_PROXY`
- `http_proxy`
- `HTTPS_PROXY`
- `https_proxy`
- `FTP_PROXY`
- `ftp_proxy`
- `NO_PROXY`
- `no_proxy`
- `ALL_PROXY`
- `all_proxy`

要使用它们，请使用 `--build-arg` 标志在命令行上传递它们，例如：

```console
$ docker build --build-arg HTTPS_PROXY=https://my-proxy.example.com .
```

默认情况下，这些预定义的变量从 `docker history` 的输出中排除。排除它们降低了在 `HTTP_PROXY` 变量中意外泄漏敏感身份验证信息的风险。

例如，考虑使用 `--build-arg HTTP_PROXY=http://user:pass@proxy.lon.example.com` 构建以下 Dockerfile

```dockerfile
FROM ubuntu
RUN echo "Hello World"
```

在这种情况下，`HTTP_PROXY` 变量的值在 `docker history` 中不可用，并且不会被缓存。如果您更改位置，并且您的代理服务器更改为 `http://user:pass@proxy.sfo.example.com`，后续构建不会导致缓存未命中。

如果您需要覆盖此行为，可以通过在 Dockerfile 中添加 `ARG` 语句来实现，如下所示：

```dockerfile
FROM ubuntu
ARG HTTP_PROXY
RUN echo "Hello World"
```

当构建此 Dockerfile 时，`HTTP_PROXY` 会保留在 `docker history` 中，更改其值会使构建缓存失效。

### 全局作用域中的自动平台 ARG

此功能仅在使用 [BuildKit](https://docs.docker.com/build/buildkit/) 后端时可用。

BuildKit 支持一组预定义的 `ARG` 变量，其中包含执行构建的节点平台（构建平台）和结果镜像平台（目标平台）的信息。目标平台可以使用 `docker build` 上的 `--platform` 标志指定。

以下 `ARG` 变量会自动设置：

- `TARGETPLATFORM` - 构建结果的平台。例如 `linux/amd64`、`linux/arm/v7`、`windows/amd64`。
- `TARGETOS` - TARGETPLATFORM 的 OS 组件
- `TARGETARCH` - TARGETPLATFORM 的架构组件
- `TARGETVARIANT` - TARGETPLATFORM 的变体组件
- `BUILDPLATFORM` - 执行构建的节点的平台。
- `BUILDOS` - BUILDPLATFORM 的 OS 组件
- `BUILDARCH` - BUILDPLATFORM 的架构组件
- `BUILDVARIANT` - BUILDPLATFORM 的变体组件

这些参数在全局作用域中定义，因此不会自动在构建阶段内部或您的 `RUN` 命令中可用。要在构建阶段内部公开这些参数之一，请不带值地重新定义它。

例如：

```dockerfile
FROM alpine
ARG TARGETPLATFORM
RUN echo "I'm building for $TARGETPLATFORM"
```

### BuildKit 内置构建参数

| 参数                            | 类型    | 描述                                                                                                                               |
| ------------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `BUILDKIT_BUILD_NAME`           | String  | 覆盖 [`buildx history` 命令](https://docs.docker.com/reference/cli/docker/buildx/history/) 和 [Docker Desktop Builds 视图](https://docs.docker.com/desktop/use-desktop/builds/) 中显示的构建名称。 |
| `BUILDKIT_CACHE_MOUNT_NS`       | String  | 设置可选的缓存 ID 命名空间。                                                                                                        |
| `BUILDKIT_CONTEXT_KEEP_GIT_DIR` | Bool    | 触发 Git 上下文保留 `.git` 目录。                                                                                                 |
| `BUILDKIT_INLINE_CACHE`[^2]     | Bool    | 是否将缓存元数据内联到镜像配置中。                                                                                                 |
| `BUILDKIT_MULTI_PLATFORM`       | Bool    | 选择是否忽略多平台输出的确定性输出。                                                                                               |
| `BUILDKIT_SANDBOX_HOSTNAME`     | String  | 设置主机名（默认 `buildkitsandbox`）。                                                                                             |
| `BUILDKIT_SYNTAX`               | String  | 设置前端镜像。设置为 `dockerfile.v0` 以忽略 Dockerfile `# syntax=` 指令并使用内置前端。                                             |
| `SOURCE_DATE_EPOCH`             | Int     | 为创建的镜像和层设置 Unix 时间戳。更多信息请参阅[可重现构建](https://reproducible-builds.org/docs/source-date-epoch/)。自 Dockerfile 1.5，BuildKit 0.11 起支持。 |

#### 示例：保留 `.git` 目录

当使用 Git 上下文时，`.git` 目录在检出时不会被保留。如果您想在构建期间检索 git 信息，保留它可能很有用：

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
WORKDIR /src
RUN --mount=target=. \
  make REVISION=$(git rev-parse HEAD) build
```

```console
$ docker build --build-arg BUILDKIT_CONTEXT_KEEP_GIT_DIR=1 https://github.com/user/repo.git#main
```

### 对构建缓存的影响

`ARG` 变量不像 `ENV` 变量那样持久化到构建的镜像中。然而，`ARG` 变量确实以类似的方式影响构建缓存。如果 Dockerfile 定义了一个 `ARG` 变量，其值与之前构建不同，则在其首次使用时会发生“缓存未命中”，而不是在其定义时。特别是，`ARG` 指令之后的所有 `RUN` 指令都会隐式使用 `ARG` 变量（作为环境变量），因此可能导致缓存未命中。所有预定义的 `ARG` 变量都免除缓存，除非 Dockerfile 中有匹配的 `ARG` 语句。

例如，考虑以下两个 Dockerfile：

```dockerfile
FROM ubuntu
ARG CONT_IMG_VER
RUN echo $CONT_IMG_VER
```

```dockerfile
FROM ubuntu
ARG CONT_IMG_VER
RUN echo hello
```

如果您在命令行上指定 `--build-arg CONT_IMG_VER=<value>`，在这两种情况下，第 2 行的规范不会导致缓存未命中；第 3 行会导致缓存未命中。`ARG CONT_IMG_VER` 导致 `RUN` 行被识别为与运行 `CONT_IMG_VER=<value> echo hello` 相同，因此如果 `<value>` 更改，您会得到缓存未命中。

在相同的命令行下考虑另一个示例：

```dockerfile
FROM ubuntu
ARG CONT_IMG_VER
ENV CONT_IMG_VER=$CONT_IMG_VER
RUN echo $CONT_IMG_VER
```

在此示例中，缓存未命中发生在第 3 行。发生未命中是因为 `ENV` 中的变量值引用了 `ARG` 变量，并且该变量通过命令行更改了。在此示例中，`ENV` 命令导致镜像包含该值。

如果 `ENV` 指令覆盖了同名的 `ARG` 指令，如下 Dockerfile：

```dockerfile
FROM ubuntu
ARG CONT_IMG_VER
ENV CONT_IMG_VER=hello
RUN echo $CONT_IMG_VER
```

第 3 行不会导致缓存未命中，因为 `CONT_IMG_VER` 的值是常量（`hello`）。因此，在 `RUN`（第 4 行）上使用的环境变量和值在构建之间不会改变。

## ONBUILD

```dockerfile
ONBUILD <INSTRUCTION>
```

`ONBUILD` 指令向镜像添加一个触发指令，以便在稍后该镜像被用作另一个构建的基础时执行。该触发器将在下游构建的上下文中执行，就好像它被直接插入在下游 Dockerfile 中的 `FROM` 指令之后一样。

如果您正在构建一个将用作基础来构建其他镜像的镜像，例如应用程序构建环境或可以使用用户特定配置进行自定义的守护程序，这将非常有用。

例如，如果您的镜像是一个可重用的 Python 应用程序构建器，它需要将应用程序源代码添加到一个特定目录中，并且可能需要在此之后调用一个构建脚本。您现在不能直接调用 `ADD` 和 `RUN`，因为您还没有访问应用程序源代码的权限，并且每个应用程序构建的源代码都会不同。您可以简单地提供应用程序开发人员一个样板 Dockerfile 来复制粘贴到他们的应用程序中，但这效率低下，容易出错，并且难以更新，因为它与特定于应用程序的代码混合在一起。

解决方案是使用 `ONBUILD` 注册预先指令，以便在下一个构建阶段稍后运行。

它的工作原理如下：

1. 当构建器遇到 `ONBUILD` 指令时，它会向正在构建的镜像的元数据添加一个触发器。该指令不会以其他方式影响当前构建。
2. 在构建结束时，所有触发器的列表都存储在镜像清单中，键为 `OnBuild`。可以使用 `docker inspect` 命令检查它们。
3. 稍后，该镜像可能被用作新构建的基础，使用 `FROM` 指令。作为处理 `FROM` 指令的一部分，下游构建器查找 `ONBUILD` 触发器，并按照它们注册的顺序执行它们。如果任何触发器失败，则 `FROM` 指令将中止，从而导致构建失败。如果所有触发器成功，则 `FROM` 指令完成，构建继续照常进行。
4. 触发器在执行后从最终镜像中清除。换句话说，它们不会被“孙子”构建继承。

例如，您可以添加如下内容：

```dockerfile
ONBUILD ADD . /app/src
ONBUILD RUN /usr/local/bin/python-build --dir /app/src
```

### 从阶段、镜像或上下文复制或挂载

从 Dockerfile 语法 1.11 开始，您可以将 `ONBUILD` 与从其他阶段、镜像或构建上下文复制或挂载文件的指令一起使用。例如：

```dockerfile
# syntax=docker/dockerfile:1.11
FROM alpine AS baseimage
ONBUILD COPY --from=build /usr/bin/app /app
ONBUILD RUN --mount=from=config,target=/opt/appconfig ...
```

如果 `from` 的源是构建阶段，则该阶段必须在触发 `ONBUILD` 的 Dockerfile 中定义。如果它是命名上下文，则该上下文必须传递给下游构建。

### ONBUILD 限制

- 不允许使用 `ONBUILD ONBUILD` 链接 `ONBUILD` 指令。
- `ONBUILD` 指令不能触发 `FROM` 或 `MAINTAINER` 指令。

## STOPSIGNAL

```dockerfile
STOPSIGNAL signal
```

`STOPSIGNAL` 指令设置将发送到容器以退出的系统调用信号。该信号可以是 `SIG<NAME>` 格式的信号名称，例如 `SIGKILL`，或者是一个与内核系统调用表中的位置匹配的无符号数字，例如 `9`。如果未定义，默认为 `SIGTERM`。

`STOPSIGNAL` 适用于 `docker stop`（以及 Docker 守护进程停止容器时）发送的信号。它不影响键盘快捷键（如 Ctrl+C）发送的信号，后者无论 `STOPSIGNAL` 设置如何，都会直接将 `SIGINT` 发送到进程。

可以使用 `docker run` 和 `docker create` 上的 `--stop-signal` 标志，按容器覆盖镜像的默认停止信号。

## HEALTHCHECK

`HEALTHCHECK` 指令有两种形式：

- `HEALTHCHECK [OPTIONS] CMD command`（通过在容器内运行命令来检查容器健康状况）
- `HEALTHCHECK NONE`（禁用从基础镜像继承的任何健康检查）

`HEALTHCHECK` 指令告诉 Docker 如何测试容器以检查它是否仍在工作。这可以检测诸如 Web 服务器陷入无限循环而无法处理新连接的情况，即使服务器进程仍在运行。

当容器指定了健康检查时，它除了正常状态外，还有一个健康状态。此状态初始为 `starting`。每当健康检查通过时，它变为 `healthy`（无论之前处于什么状态）。在连续失败一定次数后，它变为 `unhealthy`。

可以在 `CMD` 之前出现的选项有：

- `--interval=DURATION` (默认: `30s`)
- `--timeout=DURATION` (默认: `30s`)
- `--start-period=DURATION` (默认: `0s`)
- `--start-interval=DURATION` (默认: `5s`)
- `--retries=N` (默认: `3`)

健康检查将在容器启动 **interval** 秒后首次运行，然后在每次先前检查完成后再过 **interval** 秒再次运行。在 **start period** 期间，健康检查改为以 **start interval** 频率运行。

如果单次检查运行时间超过 **timeout** 秒，则检查被视为失败。执行检查的进程会使用 `SIGKILL` 突然终止。

容器需要 **retries** 次连续健康检查失败才能被视为 `unhealthy`。

**start period** 为需要时间启动的容器提供初始化时间。在此期间内的探测失败将不计入最大重试次数。然而，如果在启动期间健康检查成功，则容器被视为已启动，所有后续失败将计入最大重试次数。

**start interval** 是启动期间健康检查之间的时间。此选项需要 Docker Engine 25.0 或更高版本。

一个 Dockerfile 中只能有一个 `HEALTHCHECK` 指令。如果您列出多个，则只有最后一个 `HEALTHCHECK` 生效。

`CMD` 关键字后面的命令可以是 shell 命令（例如 `HEALTHCHECK CMD /bin/check-running`），也可以是 exec 数组（如其他 Dockerfile 命令；有关详细信息，请参阅 `ENTRYPOINT`）。

命令的退出状态指示容器的健康状态。可能的值有：

- 0: 成功 - 容器健康且准备就绪
- 1: 不健康 - 容器工作不正常
- 2: 保留 - 不要使用此退出代码

例如，大约每五分钟检查一次 Web 服务器是否能够在三秒内提供网站主页：

```dockerfile
HEALTHCHECK --interval=5m --timeout=3s \
  CMD curl -f http://localhost/ || exit 1
```

为了帮助调试失败的探测，命令写入 stdout 或 stderr 的任何输出文本（UTF-8 编码）将存储在健康状态中，并可以使用 `docker inspect` 查询。此类输出应保持简短（当前仅存储前 4096 字节）。

当容器的健康状态更改时，将生成一个 `health_status` 事件，其中包含新状态。

## SHELL

```dockerfile
SHELL ["executable", "parameters"]
```

`SHELL` 指令允许覆盖命令的 shell 形式使用的默认 shell。Linux 上的默认 shell 是 `["/bin/sh", "-c"]`，Windows 上是 `["cmd", "/S", "/C"]`。`SHELL` 指令必须在 Dockerfile 中以 JSON 形式编写。

`SHELL` 指令在 Windows 上特别有用，因为 Windows 上有两个常用且相当不同的原生 shell：`cmd` 和 `powershell`，以及其他可用的 shell，包括 `sh`。

`SHELL` 指令可以出现多次。每个 `SHELL` 指令覆盖所有先前的 `SHELL` 指令，并影响所有后续指令。例如：

```dockerfile
FROM microsoft/windowsservercore

# 以 cmd /S /C echo default 执行
RUN echo default

# 以 cmd /S /C powershell -command Write-Host default 执行
RUN powershell -command Write-Host default

# 以 powershell -command Write-Host hello 执行
SHELL ["powershell", "-command"]
RUN Write-Host hello

# 以 cmd /S /C echo hello 执行
SHELL ["cmd", "/S", "/C"]
RUN echo hello
```

当在 Dockerfile 中使用它们的 shell 形式时，以下指令可能会受到 `SHELL` 指令的影响：`RUN`、`CMD` 和 `ENTRYPOINT`。

以下示例是在 Windows 上发现的常见模式，可以通过使用 `SHELL` 指令来简化：

```dockerfile
RUN powershell -command Execute-MyCmdlet -param1 "c:\foo.txt"
```

构建器调用的命令将是：

```powershell
cmd /S /C powershell -command Execute-MyCmdlet -param1 "c:\foo.txt"
```

这效率低下有两个原因。首先，有一个不必要的 `cmd.exe` 命令处理器（即 shell）被调用。其次，每个 shell 形式的 `RUN` 指令都需要在命令前添加额外的 `powershell -command` 前缀。

为了使其更高效，可以采用两种机制之一。一种是使用 `RUN` 命令的 JSON 形式，例如：

```dockerfile
RUN ["powershell", "-command", "Execute-MyCmdlet", "-param1 \"c:\\foo.txt\""]
```

虽然 JSON 形式明确且不使用不必要的 `cmd.exe`，但它需要通过双引号和转义来获得更多的冗长性。另一种机制是使用 `SHELL` 指令和 shell 形式，为 Windows 用户提供更自然的语法，特别是与 `escape` 解析器指令结合使用时：

```dockerfile
# escape=`

FROM microsoft/nanoserver
SHELL ["powershell","-command"]
RUN New-Item -ItemType Directory C:\Example
ADD Execute-MyCmdlet.ps1 c:\example\
RUN c:\example\Execute-MyCmdlet -sample 'hello world'
```

结果是：

```console
PS E:\myproject> docker build -t shell .

Sending build context to Docker daemon 4.096 kB
Step 1/5 : FROM microsoft/nanoserver
 ---> 22738ff49c6d
Step 2/5 : SHELL powershell -command
 ---> Running in 6fcdb6855ae2
 ---> 6331462d4300
Removing intermediate container 6fcdb6855ae2
Step 3/5 : RUN New-Item -ItemType Directory C:\Example
 ---> Running in d0eef8386e97


    Directory: C:\


Mode         LastWriteTime              Length Name
----         -------------              ------ ----
d-----       10/28/2016  11:26 AM              Example


 ---> 3f2fbf1395d9
Removing intermediate container d0eef8386e97
Step 4/5 : ADD Execute-MyCmdlet.ps1 c:\example\
 ---> a955b2621c31
Removing intermediate container b825593d39fc
Step 5/5 : RUN c:\example\Execute-MyCmdlet 'hello world'
 ---> Running in be6d8e63fe75
hello world
 ---> 8e559e9bf424
Removing intermediate container be6d8e63fe75
Successfully built 8e559e9bf424
PS E:\myproject>
```

`SHELL` 指令也可用于修改 shell 操作的方式。例如，在 Windows 上使用 `SHELL cmd /S /C /V:ON|OFF`，可以修改延迟环境变量扩展语义。

如果需要替代 shell（例如 `zsh`、`csh`、`tcsh` 等），也可以在 Linux 上使用 `SHELL` 指令。

## Here-Documents

Here-document 允许将后续的 Dockerfile 行重定向到 `RUN` 或 `COPY` 命令的输入。如果这样的命令包含 [here-document](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_07_04)，Dockerfile 会将接下来的行（直到仅包含 here-doc 分隔符的行为止）视为同一命令的一部分。

### 示例：运行多行脚本

```dockerfile
# syntax=docker/dockerfile:1
FROM debian
RUN <<EOT bash
  set -ex
  apt-get update
  apt-get install -y vim
EOT
```

如果命令仅包含一个 here-document，其内容将使用默认 shell 进行评估。

```dockerfile
# syntax=docker/dockerfile:1
FROM debian
RUN <<EOT
  mkdir -p foo/bar
EOT
```

或者，可以使用 shebang 标头来定义解释器。

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.6
RUN <<EOT
#!/usr/bin/env python
print("hello world")
EOT
```

更复杂的示例可能使用多个 here-document。

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
RUN <<FILE1 cat > file1 && <<FILE2 cat > file2
I am
first
FILE1
I am
second
FILE2
```

### 示例：创建内联文件

对于 `COPY` 指令，您可以用 here-doc 指示符替换源参数，以将 here-document 的内容直接写入文件。以下示例使用 `COPY` 指令创建一个包含 `hello world` 的 `greeting.txt` 文件。

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
COPY <<EOF greeting.txt
hello world
EOF
```

常规的 here-doc [变量扩展和制表符剥离规则](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_07_04)适用。以下示例显示了一个小型 Dockerfile，它使用带有 here-document 的 `COPY` 指令创建一个 `hello.sh` 脚本文件。

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
ARG FOO=bar
COPY <<-EOT /script.sh
  echo "hello ${FOO}"
EOT
ENTRYPOINT ash /script.sh
```

在这种情况下，文件脚本打印 "hello bar"，因为变量在 `COPY` 指令执行时被展开。

```console
$ docker build -t heredoc .
$ docker run heredoc
hello bar
```

相反，如果您引用 here-document 单词 `EOT` 的任何部分，则变量在构建时不会展开。

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine
ARG FOO=bar
COPY <<-"EOT" /script.sh
  echo "hello ${FOO}"
EOT
ENTRYPOINT ash /script.sh
```

请注意，这里的 `ARG FOO=bar` 是多余的，可以删除。该变量在运行时（脚本被调用时）被解释：

```console
$ docker build -t heredoc .
$ docker run -e FOO=world heredoc
hello world
```

## Dockerfile 示例

有关 Dockerfile 的示例，请参阅：

- [构建最佳实践页面](https://docs.docker.com/build/building/best-practices/)
- [“入门”教程](https://docs.docker.com/get-started/)
- [特定语言的入门指南](https://docs.docker.com/guides/language/)

[^1]: /reference/ 必需的值
[^2]: /reference/ 对于与 Docker 集成的 [BuildKit](https:/docs.docker.com/build/buildkit#getting-started) 和 `docker buildx build`
