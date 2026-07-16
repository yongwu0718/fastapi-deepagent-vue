# Compose 中的网络

默认情况下，Compose 会为您处理网络，但也允许您在需要时进行精细控制。本页解释了默认网络的工作原理以及容器如何通过名称发现彼此。它还涵盖了何时以及如何定义自定义网络、跨独立的 Compose 项目连接服务、映射自定义主机名以及调试连接问题。

## 默认网络与服务发现

默认情况下，Compose 会为您的应用设置一个[网络](/reference/cli/docker/network/create/)。每个服务的容器都会加入默认网络，并且可以被该网络上的其他容器访问，也可以通过其服务名称（service name）被发现。该网络使用 `bridge` 驱动。要了解何时使用不同的驱动，请参阅[网络驱动：bridge vs host](#change-the-network-mode)。

对于大多数开发环境而言，默认网络就足够了。当您运行 `docker compose up` 时，Compose 会创建一个名为 `<project-name>_default` 的网络，并将所有服务（services）连接到该网络。每个服务都会将其名称注册到内部 DNS 服务器，因此容器可以直接使用服务名称相互访问。不需要 IP 地址或手动配置。

例如，假设您的应用位于名为 `myapp` 的目录中，并且您的 `compose.yaml` 如下所示：

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
  db:
    image: postgres:latest
    ports:
      - "8001:5432"
```

Compose 会自动将所有服务连接到默认网络，因此您无需在 Compose 文件中显式定义 `networks`。

当您运行 `docker compose up` 时，会发生以下情况：

1. 创建一个名为 `myapp_default` 的网络。
2. 使用 `web` 的配置创建一个容器。它以名称 `web` 加入 `myapp_default`。
3. 使用 `db` 的配置创建一个容器。它以名称 `db` 加入 `myapp_default`。

现在，每个容器都可以查找服务名称 `web` 或 `db`，并返回相应容器的 IP 地址。`web` 服务可以连接到 `postgres://db:5432` 的数据库。从主机上，如果您的容器在本地运行，则可以通过 `postgres://localhost:8001` 访问同一个数据库。

> [!TIP]
>
> Docker 在每次容器启动时动态地从网络的子网分配容器 IP 地址，因此它们不会在重启或重建后保持不变。这意味着您应该始终通过服务名称而不是 IP 地址来引用服务。当容器被重新创建时（例如，在配置更改后），它们会获得一个新的 IP 地址。服务名称保持不变。

您的应用网络基于“项目名称”（project name）命名，该名称取自它所在目录的名称。您可以使用 [`--project-name` 标志](/reference/cli/docker/compose/)或 [`COMPOSE_PROJECT_NAME` 环境变量](/compose/how-tos/networking/environment-variables/envvars/#compose_project_name)覆盖项目名称。

`HOST_PORT` 和 `CONTAINER_PORT` 用途不同。在上面的示例中，对于 `db`，`HOST_PORT` 是 `8001`，容器端口是 `5432`（Postgres 默认值）。网络化的服务间通信使用 `CONTAINER_PORT`。主机端口仅用于从网络外部访问服务。

### 更新网络上的容器

如果您对服务进行配置更改并运行 `docker compose up` 来更新它，旧的容器将被移除，新的容器将以不同的 IP 地址但相同的名称加入网络。正在运行的容器可以查找该名称并连接到新地址，但旧地址将停止工作。

如果任何容器有连接到旧容器的打开连接，这些连接将被关闭。每个容器负责检测这种情况、再次查找名称并重新连接。

## 更改网络模式

默认情况下，每个服务都加入项目的 bridge 网络。这是最安全的网络模式。如果您不指定 [`network_mode`](/reference/compose-file/services/#network_mode)，这就是您正在创建的网络类型。

您可以基于每个服务覆盖网络模式。`network_mode` 选项接受以下值：

- `host`：容器共享主机的网络栈。不需要也不支持端口映射，服务名称 DNS 解析无法工作。适用于需要直接访问主机接口的系统级工具，如网络监视器。使用 `network_mode: host` 的容器可以访问所有主机端口并观察主机上的所有网络流量。仅在确实需要时使用。
- `none`：关闭所有容器网络。
- `service:{name}`：通过引用指定服务的名称，使容器能够访问该指定容器。
- `container:{name}`：通过引用指定容器的 ID，使容器能够访问该指定容器。

您可以在单个项目中混合使用多种模式：

```yaml
services:
  app:
    image: myapp
    networks:
      - isolated
    ports:
      - "3000:3000"

  monitoring:
    image: netdata/netdata
    network_mode: host   # 可以监控主机系统和所有主机端口

networks:
  isolated:
    driver: bridge
```

## 指定自定义网络

除了使用默认的应用网络，您还可以使用顶层 `networks` 键指定自己的网络。这允许您创建更复杂的拓扑结构，并指定[自定义网络驱动](/engine/extend/plugins_network/)和选项。您还可以使用它将服务连接到不由 Compose 管理的外部创建的网络。

每个服务可以使用服务级别的 `networks` 键指定要连接的网络，该键是一个名称列表，引用顶层 `networks` 键下的条目。

以下示例显示了一个定义了两个自定义网络的 Compose 文件。`proxy` 服务与 `db` 服务隔离，因为它们没有共享共同的网络。只有 `app` 可以同时与两者通信。

```yaml
services:
  proxy:
    build: ./proxy
    networks:
      - frontend
  app:
    build: ./app
    networks:
      - frontend
      - backend
  db:
    image: postgres:latest
    networks:
      - backend

networks:
  frontend:
    driver: bridge   # 指定驱动选项
    driver_opts:
      com.docker.network.bridge.host_binding_ipv4: "127.0.0.1"
  backend:
    driver: custom-driver  # 使用自定义驱动
```

通过为每个附加网络设置 [ipv4_address 和/或 ipv6_address](/reference/compose-file/services/#ipv4_address-ipv6_address)，可以使用静态 IP 地址配置网络。

网络也可以被赋予一个[自定义名称](/reference/compose-file/networks/#name)：

```yaml
services:
  # ...
networks:
  frontend:
    name: custom_frontend
    driver: custom-driver-1
```

### 内部网络（Internal networks）

在网络上设置 `internal: true` 会创建一个与主机网络接口没有连接的网络。它没有用于外部连接性的默认网关。这对于诸如数据库之类的服务非常有用，这些服务应该完全不能从容器网络外部访问：

```yaml
services:
  cache:
    image: redis
    networks:
      - isolated

  worker:
    image: myworker
    networks:
      - isolated
      - public

networks:
  isolated:
    internal: true   # 无外部连接性
  public:   # 标准 bridge 网络，由 Compose 在 docker compose up 时创建
```

请注意，同时连接到内部网络和非内部网络的服务（如上面的 `worker`）仍然可以通过非内部网络 `public` 访问互联网。

### 配置默认网络

除了指定自己的网络之外，您还可以通过在 `networks` 下定义一个名为 `default` 的条目来更改应用范围默认网络的设置：

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
  db:
    image: postgres:latest

networks:
  default:
    driver: custom-driver-1   # 使用自定义驱动
```

## 使用现有的外部网络

如果您已经使用 `docker network create` 手动创建了一个 bridge 网络，您可以通过将该网络标记为 [`external`](/reference/compose-file/networks/#external) 来将您的 Compose 服务连接到它：

```yaml
services:
  # ...
networks:
  network1:
    name: my-pre-existing-network
    external: true
```

Compose 不会创建 `<project-name>_default`，而是查找名为 `my-pre-existing-network` 的网络，并将您的容器连接到它。

### 连接多个 Compose 项目

当独立的 Compose 项目中的服务需要通信时，外部网络特别有用。创建一个共享网络一次，然后在每个项目中将其引用为 external：

```bash
docker network create inter-project
```

backend-compose.yaml：

```yaml
services:
  api:
    image: myapi:latest
    networks:
      - shared
      - default   # 同时保留项目的内部网络

networks:
  shared:
    external: true
    name: inter-project
```

frontend-compose.yaml：

```yaml
services:
  web:
    image: myfrontend:latest
    environment:
      API_URL: http://api:8080   # 通过服务名称引用
    networks:
      - shared

networks:
  shared:
    external: true
    name: inter-project
```

同一外部网络上的服务可以像在单个项目内部一样，通过服务名称相互访问。

> [!IMPORTANT]
>
> 外部网络必须在运行 `docker compose up` 之前存在。如果不存在，Compose 会失败并报 `Network not found` 错误。始终先用 `docker network create` 创建它。

## 混合网络（Hybrid networking）

一个服务可以同时属于一个外部共享网络和它自己的项目内部网络。这使您只暴露那些需要从其他项目访问的服务，同时保持其他所有内容（如数据库）完全隔离：

```yaml
services:
  api:
    image: myapp-api
    networks:
      - shared     # 可从其他项目访问
      - internal   # 也可以访问数据库

  database:
    image: postgres:latest
    networks:
      - internal   # 未暴露在共享网络上

networks:
  shared:
    name: inter-project
    external: true
  internal: {}     # 项目特定的、隔离的网络
```

## 使用 `extra_hosts` 进行自定义 DNS

您可以使用 [`extra_hosts`](/reference/compose-file/services/#extra_hosts) 将自定义的主机名到 IP 的映射添加到容器的 `/etc/hosts` 文件中。当某个服务需要解析未在 Docker 内部 DNS 中注册的主机名时，这非常有用。例如，一个固定 IP 的依赖项或一个预发布端点：

```yaml
services:
  app:
    image: myapp
    extra_hosts:
      - "api.staging:192.168.1.100"
      - "cache.internal:192.168.1.101"
```

要动态地将主机名映射到主机的 IP，请使用特殊值 `host-gateway`：

```yaml
services:
  app:
    image: myapp
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

在 Linux 上，`host-gateway` 解析为默认 bridge 网络上主机的 IP。在 Mac 和 Windows 上，Docker 会自动提供此功能，`host-gateway` 解析为与 `host.docker.internal` 相同的内部 IP 地址。

您还可以使用环境变量来驱动 `extra_hosts`，这使得在不同环境下将服务指向不同的目标变得容易：

```yaml
services:
  app:
    image: myapp
    extra_hosts:
      - "api.service:${API_HOST:-127.0.0.1}"
      - "auth.service:${AUTH_HOST:-127.0.0.1}"
```

其中 `.env.development` 可能设置 `API_HOST=localhost`，而生产环境文件可能设置 `API_HOST=10.0.1.50`。

要验证已注入的内容，请检查容器内的 hosts 文件：

```bash
$ docker compose exec app cat /etc/hosts
```

## 多主机网络

当在启用了 [Swarm 模式](/engine/swarm/)的 Docker Engine 上部署 Compose 应用时，您可以使用内置的 `overlay` 驱动来启用多主机通信。Overlay 网络总是作为 `attachable` 创建的。您可以选择将 [`attachable`](/reference/compose-file/networks/#attachable) 属性设置为 `false`。

要了解更多信息，请参阅 [overlay 网络驱动文档](/engine/network/drivers/overlay/)。

## 链接容器

Links 允许您定义额外的别名，通过该别名可以从另一个服务访问一个服务。它们对于基本的服务间通信不是必需的。默认情况下，任何服务都可以通过该服务的名称访问任何其他服务。在以下示例中，`web` 可以通过主机名 `db` 和 `database` 访问 `db`：

```yaml
services:
  web:
    build: .
    links:
      - "db:database"
  db:
    image: postgres:latest
```

有关更多信息，请参阅 [links 参考](/reference/compose-file/services/#links)。

## 调试

当一个服务无法访问另一个服务时，请按顺序执行以下步骤：首先确认网络配置看起来正确，然后确认容器确实已连接，最后测试实时连接性。

### 检查端口映射

要找出哪个主机端口映射到容器端口，请使用 `docker compose port`：

```bash
# 哪个主机端口映射到 db 上的容器端口 5432？
$ docker compose port db 5432
# 输出：0.0.0.0:8001
```

当使用动态端口映射时，这尤其有用，因为主机端口在每次 `docker compose up` 时都会改变：

```yaml
services:
  web:
    image: nginx
    ports:
      - "80"   # Docker 动态分配主机端口
```

```bash
$ docker compose port web 80
# 输出：0.0.0.0:55432
```

当您扩展一个服务时，每个副本都会获得自己的动态端口。使用 `--index` 来查询特定的副本：

```bash
$ docker compose up -d --scale web=3

$ docker compose port --index=1 web 80   # 输出：0.0.0.0:55001
$ docker compose port --index=2 web 80   # 输出：0.0.0.0:55002
$ docker compose port --index=3 web 80   # 输出：0.0.0.0:55003
```

默认情况下，`docker compose port` 查找 TCP 映射。如果某个服务在同一端口上同时暴露 TCP 和 UDP，请使用 `--protocol`：

```bash
$ docker compose port --protocol=udp myservice 53
```

### 验证网络成员资格

要检查哪些容器连接到网络（在排除跨外部或自定义网络的连接性问题时很有用）：

```bash
$ docker network inspect <network-name>
```

### 检查连接性

如果网络成员资格看起来正确，但服务仍然无法相互访问，请使用 `docker compose exec` 从正在运行的容器内部测试连接性。

## 更多参考信息

有关可用网络配置选项的完整详细信息，请参阅以下参考：

- [顶层 `networks` 元素](/reference/compose-file/networks/)
- [服务级别 `networks` 属性](/reference/compose-file/services/#networks)