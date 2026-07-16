# Docker Compose 快速入门

本教程旨在通过引导您开发一个基本的 Python Web 应用，来介绍 Docker Compose 的核心概念。

该应用使用 Flask 框架，并在 Redis 中实现了一个计数器（hit counter），以此展示 Docker Compose 如何在 Web 开发场景中应用。即使您不熟悉 Python，这里演示的概念也应该能够理解。

## 前提条件

请确保您已：

- [安装了最新版本的 Docker Compose](/compose/install/)
- 对 Docker 的基本概念及其工作原理有初步了解

## 步骤 1：设置项目

1. 为项目创建一个目录：

   ```console
   $ mkdir compose-demo
   $ cd compose-demo
   ```

2. 在项目目录中创建 `app.py` 并添加以下内容：

   ```python
   import os
   import redis
   from flask import Flask

   app = Flask(__name__)
   cache = redis.Redis(
       host=os.getenv("REDIS_HOST", "redis"),
       port=int(os.getenv("REDIS_PORT", "6379")),
   )

   @app.route("/")
   def hello():
       count = cache.incr("hits")
       return f"Hello from Docker! I have been seen {count} time(s).\n"
   ```

   该应用从环境变量中读取 Redis 连接信息，并提供了合理的默认值，因此开箱即用。

3. 在项目目录中创建 `requirements.txt` 并添加以下内容：

   ```text
   flask
   redis
   ```

4. 创建一个 `Dockerfile`：

   ```dockerfile
   # syntax=docker/dockerfile:1
   FROM python:3.12-alpine  # 使用 Python 3.12 镜像构建
   WORKDIR /code  # 将工作目录设置为 `/code`
   ENV FLASK_APP=app.py  # 设置 `flask` 命令使用的环境变量
   ENV FLASK_RUN_HOST=0.0.0.0
   RUN apk add --no-cache gcc musl-dev linux-headers  # 安装 `gcc` 和其他依赖
   COPY requirements.txt .  # 复制 `requirements.txt`
   RUN pip install -r requirements.txt  # 安装 Python 依赖
   COPY . .  # 将项目中的当前目录 `.` 复制到镜像中的工作目录 `.`
   EXPOSE 5000
   CMD ["flask", "run", "--debug"]  # 将容器的默认命令设置为 `flask run --debug`
   ```

   > [!IMPORTANT]
   >
   > 请确保文件名为 `Dockerfile`（无扩展名）。某些编辑器会自动添加 `.txt`，这会导致构建失败。

   有关如何编写 Dockerfile 的更多信息，请参阅 [Dockerfile 参考](/reference/dockerfile/)。

5. 创建一个 `.env` 文件来存放配置值：

   ```text
   APP_PORT=8000
   REDIS_HOST=redis
   REDIS_PORT=6379
   ```

   Compose 会自动读取 `.env` 并使这些值可用于 `compose.yaml` 中的插值。对于本例来说收益不大，但在实际中，将配置移出 Compose 文件可以更方便地：
   - 在不编辑 YAML 的情况下跨环境更改值
   - 避免将 secrets 提交到版本控制系统
   - 在多个服务之间复用值

6. 创建一个 `.dockerignore` 文件，以防止不必要的文件进入构建上下文（build context）：

   ```text
   .env
   *.pyc
   __pycache__
   redis-data
   ```

   Docker 在构建镜像时会发送项目目录中的所有内容到守护进程。如果没有 `.dockerignore`，就会包含您的 `.env` 文件（可能含有 secrets）以及任何缓存的 Python 字节码。排除这些文件可以保持构建速度，并避免意外地将敏感值固化到镜像层中。

## 步骤 2：定义并启动服务

Compose 可以简化对整个应用栈的控制，让您通过单个 YAML 配置文件轻松管理 services、networks 和 volumes。

1. 在项目目录中创建 `compose.yaml` 并粘贴以下内容：

   ```yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}

     redis:
       image: redis:alpine
   ```

   这个 Compose 文件定义了两个 services：

   - `web` service 使用从当前目录下的 `Dockerfile` 构建的 image。它将主机的 `8000` 端口映射到 container 内 Flask 默认监听的 `5000` 端口。

   - `redis` service 使用从 Docker Hub registry 拉取的公共 [Redis](https://registry.hub.docker.com/_/redis/) image。

   有关 `compose.yaml` 文件的更多信息，请参阅 [Compose 的工作原理](/compose/gettingstarted/compose-application-model/)。

2. 启动应用：

```console
docker compose up
```

   只需一条命令，您就可以从配置文件中创建并启动所有 services。Compose 会构建您的 web image，拉取 Redis image，并启动两个 containers。

3. 打开 `http://localhost:8000`。您应该看到：

   ```text
   Hello from Docker! I have been seen 1 time(s).
   ```

   刷新页面——计数器会在每次访问时递增。

   这个最小的设置可以工作，但存在两个问题，您将在后续步骤中修复：

   - **启动竞态**：`web` 和 `redis` 同时启动。如果 Redis 尚未就绪，Flask app 将连接失败并崩溃。
   - **无持久化**：如果运行 `docker compose down` 然后再次 `docker compose up`，计数器会重置为零。`docker compose down` 会删除 containers，同时也删除了写入 container 可写层的所有数据。`docker compose stop` 会保留 containers，因此数据不会丢失，但在生产环境中（containers 会被定期替换）不能依赖于此。

4. 继续之前请停止当前栈：

   ```console
    docker compose down
   ```

## 步骤 3：使用 health checks 修复启动竞态

要修复启动竞态，Compose 需要在确认 `redis` 健康（healthy）之后才启动 `web`。

1. 更新 `compose.yaml`：

   ```yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}
       depends_on:
         redis:
           condition: service_healthy

     redis:
       image: redis:alpine
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 5
         start_period: 10s
   ```

   `healthcheck` 块告诉 Compose 如何测试 Redis 是否就绪：

   - `test` 是 Compose 在 container 内部运行的命令，用于检查健康状况。`redis-cli ping` 连接到 Redis 并期望返回 `PONG` 响应——如果收到，则 container 为 healthy。
   - `start_period` 给予 Redis 10 秒的初始化时间，然后再开始 health checks。在此期间发生的任何失败都不会计入重试限制。
   - `interval` 指定在启动期过后每 5 秒运行一次检查。
   - `timeout` 指定每次检查在超时前有 3 秒的响应时间，超时则视为失败。
   - `retries` 设置在 Compose 将 container 标记为 unhealthy 之前允许的连续失败次数。使用 `interval: 5s` 和 `retries: 5`，Compose 在放弃前最多等待 25 秒。

2. 启动栈以确认顺序已被修复：

   ```console
   docker compose up
   ```

   您应该看到类似如下输出：

   ```text
   [+] Running 2/2
   ✔ Container compose-demo-redis-1  Healthy                       0.0s
   ```

3. 打开 `http://localhost:8000` 确认 app 仍然工作，然后停止栈以便继续：

   ```console
   docker compose down
   ```

## 步骤 4：启用 Compose Watch 实现实时更新

如果没有 Compose Watch，每次代码更改都需要停止栈、重建 image 并重启 containers。Compose Watch 通过在您保存文件时自动将更改同步到运行中的 container，消除了这个循环。

1. 更新 `compose.yaml`，为 `web` service 添加 `develop.watch` 块：

   ```yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}
       depends_on:
         redis:
           condition: service_healthy
       develop:
         watch:
           - action: sync+restart
             path: .
             target: /code
           - action: rebuild
             path: requirements.txt

     redis:
       image: redis:alpine
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 5
         start_period: 10s
   ```

   `watch` 块定义了两条规则：
   - `sync+restart` 操作监视主机上的项目目录（`.`）。当文件发生更改时，Compose 将任何更改的文件复制到运行中 container 的 `/code` 内，然后重启 container。由于 container 在重启时已经包含了更新后的文件，Flask 启动时会直接读取新代码——无需手动重建或重启。
   - 对 `requirements.txt` 的 `rebuild` 操作会在您添加新依赖时触发完整的 image rebuild，因为安装 packages 需要重建 image，而不仅仅是同步文件。

2. 启用 Watch 模式启动栈：

   ```console
   $ docker compose up --watch
   ```

3. 进行实时更改。打开 `app.py` 并修改问候语：

   ```python
   return f"Hello from Compose Watch! I have been seen {count} time(s).\n"
   ```

4. 保存文件。Compose Watch 会检测到更改并立即同步：

   ```text
   Syncing service "web" after changes were detected
   ```

5. 刷新 `http://localhost:8000`。更新后的问候语会显示出来，无需任何重启，并且计数器应该仍在递增。

6. 继续之前停止栈：

   ```console
    docker compose down
   ```

   有关 Compose Watch 工作原理的更多信息，请参阅 [使用 Compose Watch](/compose/how-tos/file-watch/)。

## 步骤 5：使用 named volumes 持久化数据

每次停止并重启栈时，访问计数器都会重置为零。Redis 数据存在于 container 内部，因此当 container 被删除时数据也会消失。named volume 通过将数据存储在主机上（独立于 container 生命周期）来解决这个问题。

1. 更新 `compose.yaml`：

   ```yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}
       depends_on:
         redis:
           condition: service_healthy
       develop:
         watch:
           - action: sync+restart
             path: .
             target: /code
           - action: rebuild
             path: requirements.txt

     redis:
       image: redis:alpine
       volumes:
         - redis-data:/data
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 5
         start_period: 10s

   volumes:
     redis-data:
   ```

   `redis.volumes` 下的 `redis-data:/data` 条目将 named volume 挂载到 `/data`，这是 Redis 写入其数据文件的路径。顶层的 `volumes` 键向 Docker 注册该 volume，使其在 `compose down` 和 `compose up` 周期之间得以持久化。

2. 使用 `docker compose up --watch` 启动栈，并多次刷新 `http://localhost:8000` 以累积计数。

3. 使用 `docker compose down` 拆除栈，然后再次使用 `docker compose up --watch` 重新启动。

4. 打开 `http://localhost:8000`——计数器会从上一次的值继续增加。

5. 现在使用 `docker compose down -v` 重置计数器。

   `-v` 标志会连同 containers 一起删除 named volumes。请有意识地使用此操作——它会永久删除存储的数据。

## 步骤 6：使用多个 Compose 文件组织项目

随着应用的增长，单个 `compose.yaml` 会变得难以维护。顶层元素 `include` 允许您将 services 拆分到多个文件中，同时仍将它们作为同一个应用的一部分。

当不同的团队拥有栈的不同部分，或者您希望在多个项目之间复用基础设施定义时，这一点尤其有用。

1. 在项目目录中创建一个名为 `infra.yaml` 的新文件，并将 Redis service 和 volume 移入其中：

   ```yaml
    services:
     redis:
       image: redis:alpine
       volumes:
         - redis-data:/data
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 5
         start_period: 10s

   volumes:
     redis-data:
   ```

2. 更新 `compose.yaml` 以包含 `infra.yaml`：

   ```yaml
   include:
      - path: ./infra.yaml
   services:
     web:
       build: .
       ports:
         - "${APP_PORT}:5000"
       environment:
         - REDIS_HOST=${REDIS_HOST}
         - REDIS_PORT=${REDIS_PORT}
       depends_on:
         redis:
           condition: service_healthy
       develop:
         watch:
           - action: sync+restart
             path: .
             target: /code
           - action: rebuild
             path: requirements.txt
   ```

3. 运行应用以确认一切仍然正常：

   ```console
   $ docker compose up --watch
   ```

   Compose 在启动时会合并两个文件。`web` service 仍然可以通过名称引用 `redis`，因为所有被包含的 services 共享同一个默认 network。

   这是一个简化的示例，但它演示了 `include` 的基本原理，以及如何使模块化复杂应用成为可能。有关 `include` 和使用多个 Compose 文件的更多信息，请参阅 [使用多个 Compose 文件](/compose/how-tos/multiple-compose-files/)。

4. 继续之前停止栈：

   ```console
   $ docker compose down
   ```

## 步骤 7：检查并调试运行中的栈

有了一个完整配置的栈，您可以在不停止任何服务的情况下观察 container 内部发生的事情。本步骤涵盖了检查解析后的配置、流式传输日志以及在运行中 container 内部执行命令的核心命令。

在启动栈之前，验证 Compose 已经正确解析了您的 `.env` 变量并合并了所有文件：

```console
$ docker compose config
```

`docker compose config` 不需要栈处于运行状态——它完全基于您的文件工作。输出中值得注意的几点：

- `${APP_PORT}`、`${REDIS_HOST}` 和 `${REDIS_PORT}` 都已替换为来自 `.env` 文件的值。
- 短格式端口表示法（`"8000:5000"`）被扩展为其规范字段（`target`、`published`、`protocol`）。
- 默认的 network 和 volume 名称被显式化，并加上项目名称 `compose-demo` 作为前缀。
- 输出是完全解析后的配置，通过 `include` 引入的任何文件都被合并为一个视图。

任何时候您想确认 Compose 实际将应用什么配置，尤其是调试变量替换或处理多个 Compose 文件时，都可以使用 `docker compose config`。

现在以 detached 模式启动栈，以便终端保持空闲以供后续命令使用：

```console
$ docker compose up -d
```

### 从所有 services 流式传输日志

```console
$ docker compose logs -f
```

`-f` 标志实时跟踪日志流，将两个 containers 的输出交错显示，并带有颜色编码的 service 名称前缀。多次刷新 `http://localhost:8000`，观察 Flask 请求日志的出现。要跟踪单个 service 的日志，请传递其名称：

```console
$ docker compose logs -f web
```

按 `Ctrl+C` 停止跟踪日志。containers 会继续运行。

### 在运行中的 container 内执行命令

`docker compose exec` 在已经运行的 container 中执行命令，而无需启动新 container。这是实时调试的主要工具。

#### 验证环境变量是否正确设置

```console
$ docker compose exec web env | grep REDIS
```

```text
REDIS_HOST=redis
REDIS_PORT=6379
```

#### 测试 `web` container 能否使用 service 名称作为主机名访问 Redis

```console
$ docker compose exec web python -c "import redis; r = redis.Redis(host='redis'); print(r.ping())"
```

```text
True
```

这使用了与应用相同的 `redis` library，因此返回 `True` 确认 service discovery、networking 以及 Redis 连接都是端到端正常的。

#### 检查 Redis 中计数器的实时值

```console
$ docker compose exec redis redis-cli GET hits
```

## 下一步

- [探索 Compose 命令的完整列表](/reference/cli/docker/compose/)
- [探索 Compose 文件参考](/reference/compose-file/)
- [在 LinkedIn Learning 上观看《Learning Docker Compose》视频](https://www.linkedin.com/learning/learning-docker-compose/)
- [了解如何在 Compose 中设置环境变量](/compose/how-tos/environment-variables/set-environment-variables/)
- [了解如何打包和分发您的 Compose 应用](/compose/how-tos/oci-artifact/)