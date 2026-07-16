# Docker object labels

Labels（标签）是一种为 Docker 对象添加元数据的机制，可应用于以下对象：

- Images（镜像）
- Containers（容器）
- Local daemons（本地守护进程）
- Volumes（数据卷）
- Networks（网络）
- Swarm nodes（Swarm 节点）
- Swarm services（Swarm 服务）

您可以使用 label 来组织镜像、记录许可信息、标注容器、数据卷和网络之间的关系，或以任何适合您业务或应用的方式使用。

## Label keys and values（标签的键和值）

一个 label 是一个键值对（key-value pair），以字符串形式存储。您可以为同一个对象指定多个 label，但每个 key 在该对象内必须唯一。如果同一个 key 被赋予多个值，最后写入的值会覆盖之前的所有值。

### Key 格式建议

Label key 是键值对中的左侧部分。Key 是由字母数字组成的字符串，可包含点号（`.`）、下划线（`_`）、斜杠（`/`）和连字符（`-`）。大多数 Docker 用户会使用其他组织创建的镜像，以下指南有助于防止不同对象之间意外重复 label，特别是当您计划将 label 用作自动化机制时。

- 第三方工具的作者应使用其拥有的域名的反向 DNS 表示法作为每个 label key 的前缀，例如 `com.example.some-label`。
- 未经域名所有者许可，请勿在 label key 中使用该域名。
- `com.docker.*`、`io.docker.*` 和 `org.dockerproject.*` 命名空间由 Docker 保留供内部使用。
- Label key 应以小写字母开头和结尾，且只能包含小写字母数字字符、点号（`.`）和连字符（`-`）。不允许连续使用点号或连字符。
- 点号（`.`）用于分隔命名空间中的“字段”。没有命名空间的 label key 预留给 CLI 使用，以便 CLI 用户能够使用更短、更易输入的字符串交互式地为 Docker 对象添加 label。

这些指南目前并未强制执行，特定使用场景可能还适用其他指南。

### Value 指南

Label value（标签值）可以包含任何能够表示为字符串的数据类型，包括但不限于 JSON、XML、CSV 或 YAML。唯一的要求是，该值必须首先使用与该结构类型对应的机制序列化为字符串。例如，要将 JSON 序列化为字符串，可以使用 JavaScript 的 `JSON.stringify()` 方法。

由于 Docker 不会反序列化这些值，因此除非您在第三方工具中构建相关功能，否则在通过 label value 进行查询或过滤时，无法将 JSON 或 XML 文档视为嵌套结构。

## 在对象上管理 labels

每种支持 label 的对象类型都有相应的机制来添加、管理它们，并根据该对象类型的特点来使用它们。

对于镜像、容器、本地守护进程、数据卷和网络上的 labels，在对象的整个生命周期内是静态的。要更改这些 label，您必须重新创建该对象。Swarm 节点和服务上的 labels 可以动态更新。

### Images（镜像）

通过 Dockerfile 中的 [`LABEL` 指令](/reference/dockerfile/#label) 为镜像添加 label：

```dockerfile
LABEL com.example.version="1.0"
LABEL com.example.description="Web application"
```

您也可以在构建时使用 `--label` 标志设置 label，而无需在 Dockerfile 中编写 `LABEL` 指令：

```console
$ docker build --label "com.example.version=1.0" -t myapp .
```

使用 `docker inspect` 查看镜像上的 labels：

```console
$ docker inspect --format='{{json .Config.Labels}}' myapp
```

通过 [`docker image ls --filter`](/reference/cli/docker/image/ls/#filter) 按 label 过滤镜像：

```console
$ docker image ls --filter "label=com.example.version"
```

### Containers（容器）

在使用 [`docker run --label`](/reference/cli/docker/container/run/#label) 启动容器时覆盖或添加 label：

```console
$ docker run --label "com.example.env=prod" myapp
```

查看容器上的 labels：

```console
$ docker inspect --format='{{json .Config.Labels}}' mycontainer
```

通过 [`docker container ls --filter`](/reference/cli/docker/container/ls/#filter) 按 label 过滤容器：

```console
$ docker container ls --filter "label=com.example.env=prod"
```

### Local Docker daemons（本地 Docker 守护进程）

通过在启动 `dockerd` 时传递 `--label` 标志，或在[守护进程配置文件](/reference/cli/dockerd/#daemon-configuration-file)中设置 `"labels"` 来为 Docker 守护进程添加 label：

```json
{
  "labels": ["com.example.environment=production"]
}
```

使用 `docker system info` 查看守护进程的 labels。

### Volumes（数据卷）

在[创建数据卷](/reference/cli/docker/volume/create/)时添加 label：

```console
$ docker volume create --label "com.example.purpose=database" myvolume
```

查看数据卷的 labels：

```console
$ docker volume inspect myvolume --format='{{json .Labels}}'
```

通过 [`docker volume ls --filter`](/reference/cli/docker/volume/ls/#filter) 按 label 过滤数据卷：

```console
$ docker volume ls --filter "label=com.example.purpose"
```

### Networks（网络）

在[创建网络](/reference/cli/docker/network/create/)时添加 label：

```console
$ docker network create --label "com.example.purpose=frontend" mynetwork
```

查看网络的 labels：

```console
$ docker network inspect mynetwork --format='{{json .Labels}}'
```

通过 [`docker network ls --filter`](/reference/cli/docker/network/ls/#filter) 按 label 过滤网络：

```console
$ docker network ls --filter "label=com.example.purpose"
```

### Swarm nodes（Swarm 节点）

- [添加或更新 Swarm 节点的 label](/reference/cli/docker/node/update/#label-add)
- [按 label 过滤 Swarm 节点](/reference/cli/docker/node/ls/#filter)

### Swarm services（Swarm 服务）

- [创建 Swarm 服务时添加 label](/reference/cli/docker/service/create/#label)
- [更新 Swarm 服务的 label](/reference/cli/docker/service/update/)
- [按 label 过滤 Swarm 服务](/reference/cli/docker/service/ls/#filter)