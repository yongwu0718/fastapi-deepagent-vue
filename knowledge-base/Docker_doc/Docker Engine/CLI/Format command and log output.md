# 格式化命令和日志输出（Format command and log output）

Docker 支持 **Go 模板**，你可以用它来操控特定命令和日志驱动的输出格式。

Docker 提供了一组基础函数来操作模板元素。下面的所有示例都使用 `docker inspect` 命令，但许多其他 CLI 命令也有 `--format` 标志，并且很多 CLI 命令参考中包含自定义输出格式的示例。

> [!NOTE]
>
> 使用 `--format` 标志时，需要注意你的 shell 环境。
> 在 POSIX shell 中，可以用单引号运行如下命令：
>
> ```console
> $ docker inspect --format '{{join .Args " , "}}'
> ```
>
> 而在 Windows shell（例如 PowerShell）中，也需要使用单引号，但需要对参数中的双引号进行转义，如下所示：
>
> ```console
> $ docker inspect --format '{{join .Args \" , \"}}'
> ```
>

## join（连接）

`join` 将一个字符串列表连接成一个单独的字符串。它在列表中的每个元素之间插入一个分隔符。

```console
$ docker inspect --format '{{join .Args " , "}}' container
```

## table（表格）

`table` 用于指定你希望在输出中看到哪些字段。

```console
$ docker image list --format "table {{.ID}}\t{{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

## json（JSON）

`json` 将一个元素编码为 JSON 字符串。

```console
$ docker inspect --format '{{json .Mounts}}' container
```

## lower（转小写）

`lower` 将一个字符串转换为小写形式。

```console
$ docker inspect --format "{{lower .Name}}" container
```

## split（分割）

`split` 使用分隔符将一个字符串切分成字符串列表。

```console
$ docker inspect --format '{{split .Image ":"}}' container
```

## title（首字母大写）

`title` 将字符串的第一个字符转为大写。

```console
$ docker inspect --format "{{title .Name}}" container
```

## upper（转大写）

`upper` 将一个字符串转换为大写形式。

```console
$ docker inspect --format "{{upper .Name}}" container
```

## pad（填充空格）

`pad` 给一个字符串添加空白填充。你可以指定在字符串前后添加的空格数量。

```console
$ docker image list --format '{{pad .Repository 5 10}}'
```

这个例子在镜像仓库名称前添加 5 个空格，在其后添加 10 个空格。

## truncate（截断）

`truncate` 将字符串缩短到指定长度。如果字符串本身比指定长度短，则保持不变。

```console
$ docker image list --format '{{truncate .Repository 15}}'
```

这个例子显示镜像仓库名称，如果它超过 15 个字符则只截取前 15 个字符。

## `println`（换行打印）

`println` 将每个值打印在新的一行。

```console
$ docker inspect --format='{{range .NetworkSettings.Networks}}{{println .IPAddress}}{{end}}' container
```

## 提示（Hint）

要了解可以打印哪些数据，可以将所有内容以 JSON 格式显示出来：

```console
$ docker container ls --format='{{json .}}'
```
