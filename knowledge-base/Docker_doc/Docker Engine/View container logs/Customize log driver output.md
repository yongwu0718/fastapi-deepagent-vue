# Customize log driver output（自定义日志驱动输出）

`tag` 日志选项指定了如何格式化一个用于标识容器日志消息的 tag。默认情况下，系统使用容器 ID 的前 12 个字符。要覆盖此行为，请指定一个 `tag` 选项：

```console
$ docker run --log-driver=fluentd --log-opt fluentd-address=myhost.local:24224 --log-opt tag="mailer"
```

Docker 支持一些特殊的模板标记，您可以在指定 tag 的值时使用：

| Markup（标记）         | Description（描述）                            |
| ------------------ | ------------------------------------------- |
| `{{.ID}}`          | 容器 ID 的前 12 个字符。                       |
| `{{.FullID}}`      | 完整的容器 ID。                               |
| `{{.Name}}`        | 容器名称。                                   |
| `{{.ImageID}}`     | 容器镜像 ID 的前 12 个字符。                   |
| `{{.ImageFullID}}` | 容器的完整镜像 ID。                           |
| `{{.ImageName}}`   | 容器所使用的镜像名称。                         |
| `{{.DaemonName}}`  | Docker 程序的名称（`docker`）。               |

例如，指定 `--log-opt tag="{{.ImageName}}/{{.Name}}/{{.ID}}"` 值会生成类似如下的 `syslog` 日志行：

```text
Aug  7 18:33:19 HOSTNAME hello-world/foobar/5790672ab6a0[9103]: Hello from Docker.
```

在启动时，系统会设置 `container_name` 字段以及 tags 中的 `{{.Name}}`。如果您使用 `docker rename` 重命名一个 container，新的名称不会反映在日志消息中。相反，这些消息将继续使用原始的 container 名称。
