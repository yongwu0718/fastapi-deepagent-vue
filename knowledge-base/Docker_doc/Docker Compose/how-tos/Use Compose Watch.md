# 使用 Compose Watch

`watch` 属性会在您编辑和保存代码时，自动更新并预览正在运行的 Compose 服务（services）。对于许多项目而言，一旦 Compose 运行起来，这就能实现无需干预的开发工作流，因为当您保存工作时，服务（services）会自动更新。

`watch` 遵循以下文件路径规则：
* 除 ignore 文件模式外，所有路径都相对于项目目录
* 目录会被递归式地监视
* 不支持 glob 模式
* 遵循 `.dockerignore` 中的规则
  * 使用 `ignore` 选项可以定义额外的忽略路径（语法相同）
  * 常见 IDE（Vim、Emacs、JetBrains 等）的临时/备份文件会被自动忽略
  * `.git` 目录会被自动忽略

您不需要为 Compose 项目中的所有服务（services）都开启 `watch`。在某些情况下，可能只有项目的一部分（例如 JavaScript 前端）适合自动更新。

Compose Watch 专为使用 `build` 属性从本地源代码构建的服务（services）而设计。它不会跟踪依赖于通过 `image` 属性指定的预构建镜像（image）的服务（services）的更改。

## Compose Watch 与 bind mounts 的对比

Compose 支持在服务容器（container）内共享主机目录。Watch 模式并不会替代这一功能，而是作为一个补充，特别适合在容器（container）中进行开发。

更重要的是，`watch` 提供了比 bind mount 更精细的控制粒度。Watch 规则允许您在被监视的树中忽略特定文件或整个目录。

例如，在 JavaScript 项目中，忽略 `node_modules/` 目录有两个好处：
* 性能：包含许多小文件的目录树在某些配置下可能导致较高的 I/O 负载。
* 多平台：如果主机 OS 或架构与容器（container）不同，则编译后的产物无法共享。

例如，在 Node.js 项目中，不建议同步 `node_modules/` 目录。尽管 JavaScript 是解释型语言，但 `npm` 包可能包含不可跨平台移植的原生代码。

## 配置

`watch` 属性定义了一个规则列表，用于根据本地文件更改控制自动服务（service）更新。

每条规则都需要一个 `path` 模式，以及在检测到修改时要执行的 `action`。`watch` 有两种可能的 `action`，并且根据 `action` 的不同，可能还会接受或要求额外的字段。

Watch 模式可以与许多不同的语言和框架一起使用。具体的路径和规则会因项目而异，但概念是相同的。

### 前提条件

为了正常工作，`watch` 依赖于常见的可执行文件。请确保您的服务镜像（service image）包含以下二进制文件：
* stat
* mkdir
* rmdir

`watch` 还要求容器（container）的 `USER` 能够写入目标路径，以便更新文件。一种常见的模式是使用 Dockerfile 中的 `COPY` 指令将初始内容复制到容器（container）中。为了确保这些文件由配置的用户拥有，请使用 `COPY --chown` 标志：

```dockerfile
# 以非特权用户身份运行
FROM node:18
RUN useradd -ms /bin/sh -u 1001 app
USER app

# 安装依赖
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install

# 将源文件复制到应用程序目录
COPY --chown=app:app . /app
```

### `action`

#### Sync

如果 `action` 设置为 `sync`，Compose 会确保对主机上文件所做的任何更改都会自动匹配到服务容器（service container）内的对应文件。

`sync` 非常适合支持“热重载（Hot Reload）”或类似功能的框架。

更一般地说，在许多开发用例中，`sync` 规则可以替代 bind mounts。

#### Rebuild

如果 `action` 设置为 `rebuild`，Compose 会使用 BuildKit 自动构建一个新的镜像（image），并替换正在运行的服务容器（service container）。

其行为与运行 `docker compose up --build <svc>` 相同。

Rebuild 非常适合编译型语言，或者作为对需要完整镜像（image）重建的特定文件（例如 `package.json`）修改的备用方案。

#### Sync + Restart

如果 `action` 设置为 `sync+restart`，Compose 会将您的更改同步到服务容器（service container）中，并重启它们。

当配置文件发生更改，并且您不需要重建镜像（image），而只需重启服务容器（service container）的主进程时，`sync+restart` 是理想的选择。例如，当您更新数据库配置或 `nginx.conf` 文件时，它会很好地工作。

>[!TIP]
>
> 通过[镜像层缓存（image layer caching）](/build/cache)和[多阶段构建（multi-stage builds）](/build/building/multi-stage/)来优化您的 `Dockerfile`，以实现快速的增量重建。

### `path` 和 `target`

`target` 字段控制路径如何映射到容器（container）中。

对于 `path: ./app/html` 以及对 `./app/html/index.html` 的更改：

* `target: /app/html` -> `/app/html/index.html`
* `target: /app/static` -> `/app/static/index.html`
* `target: /assets` -> `/assets/index.html`

### `ignore`

`ignore` 模式是相对于当前 `watch` 操作中定义的 `path` 的，而不是相对于项目目录。在下面的示例 1 中，ignore 路径将是相对于 `path` 属性中指定的 `./web` 目录的。

### `initial_sync`

当使用 `sync+x` 操作时，`initial_sync` 属性告诉 Compose 在启动新的 watch 会话之前，确保属于定义 `path` 的文件是最新的。

## 示例 1

这个最小示例针对一个具有以下结构的 Node.js 应用：

```text
myproject/
├── web/
│   ├── App.jsx
│   ├── index.js
│   └── node_modules/
├── Dockerfile
├── compose.yaml
└── package.json
```

```yaml
services:
  web:
    build: .
    command: npm start
    develop:
      watch:
        - action: sync
          path: ./web
          target: /src/web
          initial_sync: true
          ignore:
            - node_modules/
        - action: rebuild
          path: package.json
```

在此示例中，当运行 `docker compose up --watch` 时，将使用从项目根目录下的 `Dockerfile` 构建的镜像（image）启动一个 `web` 服务容器（container）。`web` 服务（service）运行 `npm start` 作为其命令，然后启动一个启用了模块热重载（在 Webpack、Vite、Turbopack 等打包器中）的应用开发版本。

服务（service）启动后，watch 模式开始监视目标目录和文件。然后，每当 `web/` 目录中的源文件发生更改时，Compose 会将文件同步到容器（container）内 `/src/web` 下的对应位置。例如，`./web/App.jsx` 会被复制到 `/src/web/App.jsx`。

复制完成后，打包器会在不重启的情况下更新正在运行的应用。

在这种情况下，`ignore` 规则将应用于 `myproject/web/node_modules/`，而不是 `myproject/node_modules/`。

与源代码文件不同，添加新依赖无法即时完成，因此每当 `package.json` 发生更改时，Compose 会重建镜像（image）并重新创建 `web` 服务容器（service container）。

这种模式可以用于许多语言和框架，例如 Python 与 Flask：Python 源文件可以同步，而对 `requirements.txt` 的更改则应触发重建。

## 示例 2

调整前面的示例以演示 `sync+restart`：

```yaml
services:
  web:
    build: .
    command: npm start
    develop:
      watch:
        - action: sync
          path: ./web
          target: /app/web
          ignore:
            - node_modules/
        - action: sync+restart
          path: ./proxy/nginx.conf
          target: /etc/nginx/conf.d/default.conf

  backend:
    build:
      context: backend
      target: builder
```

此设置演示了如何在 Docker Compose 中使用 `sync+restart` 操作来高效地开发和测试一个带有前端 Web 服务器和后端服务的 Node.js 应用。该配置确保应用程序代码和配置文件的更改能够快速同步和应用，并根据需要重启 `web` 服务（service）以反映更改。

## 使用 `watch`

1. 在 `compose.yaml` 中为一个或多个服务（services）添加 `watch` 部分。
2. 运行 `docker compose up --watch` 来构建和启动 Compose 项目，并启动文件监视模式。
3. 使用您喜欢的 IDE 或编辑器编辑服务（service）源文件。

> [!NOTE]
>
> 如果您不希望应用程序日志与（重）构建日志和文件系统同步事件混在一起，也可以使用专用的 `docker compose watch` 命令来使用 Watch。

> [!TIP]
>
> 查看 [`dockersamples/avatars`](https://github.com/dockersamples/avatars) 或 [Docker 文档的本地设置](https://github.com/docker/docs/blob/main/CONTRIBUTING.md)，以了解 Compose `watch` 的演示。

## 参考

- [Compose Develop 规范](/reference/compose-file/develop/)