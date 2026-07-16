# Using the build cache（使用构建缓存）

## 解释

回顾一下你之前为 getting-started 应用创建的 Dockerfile：

```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY . .
RUN yarn install --production
CMD ["node", "./src/index.js"]
```

当你运行 `docker build` 命令创建新镜像时，Docker 会按照指定的顺序执行 Dockerfile 中的每条指令，为每条命令创建一个层。对于每条指令，Docker 都会检查是否可以复用之前构建中的指令。如果发现之前已经执行过类似的指令，Docker 就无需重做，而是直接使用缓存的结果。这样，你的构建过程就会变得更快、更高效，为你节省宝贵的时间和资源。

有效利用 **build cache** 可以通过复用先前构建的结果并跳过不必要的工作来实现更快的构建。为了最大化缓存利用率并避免资源密集和耗时的重建，理解缓存失效（cache invalidation）的工作原理非常重要。以下是几种可能导致缓存失效的情况：

- 对 `RUN` 指令的命令进行任何修改都会导致该层失效。如果 Dockerfile 中的 `RUN` 命令发生任何变化，Docker 会检测到该变化并使构建缓存失效。
- 通过 `COPY` 或 `ADD` 指令复制到镜像中的文件发生任何更改。Docker 会密切关注项目目录内文件的任何改动，无论是内容变化还是权限等属性变化，Docker 都会将这些修改视为触发缓存失效的因素。
- 一旦某一层失效，其后的所有层也会失效。如果任何先前的层（包括基础镜像或中间层）因更改而失效，Docker 会确保依赖它的后续层也失效。这保持了构建过程的同步并防止不一致。

在编写或编辑 Dockerfile 时，请注意避免不必要的缓存未命中，以确保构建尽可能快速高效地运行。

## 动手试一试

在本动手指南中，你将学习如何为 Node.js 应用有效使用 Docker build cache。

### 构建应用

1. [下载并安装](https://www.docker.com/products/docker-desktop/) Docker Desktop。

2. 打开终端，[克隆这个示例应用](https://github.com/dockersamples/todo-list-app)：

```console
$ git clone https://github.com/dockersamples/todo-list-app
```

3. 进入 `todo-list-app` 目录：

```console
$ cd todo-list-app
```

   在这个目录中，你会找到一个名为 `Dockerfile` 的文件，内容如下：

```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY . .
RUN yarn install --production
EXPOSE 3000
CMD ["node", "./src/index.js"]
```

4. 执行以下命令来构建 Docker 镜像：

```console
$ docker build .
```

以下是构建过程的结果：

```console
[+] Building 20.0s (10/10) FINISHED
```

第一行显示整个构建过程耗时 *20.0 秒*。第一次构建可能需要一些时间，因为它会安装依赖项。

5. 在不做任何更改的情况下重新构建。

现在，在不更改源代码或 Dockerfile 的情况下重新运行 `docker build` 命令：

```console
$ docker build .
```

由于缓存机制，只要命令和上下文保持不变，初始构建之后的后续构建会更快。Docker 会缓存构建过程中生成的中间层。当你重新构建镜像而不对 Dockerfile 或源代码做任何更改时，Docker 可以复用缓存的层，从而显著加快构建过程。

```console
[+] Building 1.0s (9/9) FINISHED                                                                            docker:desktop-linux
   => [internal] load build definition from Dockerfile                                                                        0.0s
   => => transferring dockerfile: 187B                                                                                        0.0s
   ...
   => [internal] load build context                                                                                           0.0s
   => => transferring context: 8.16kB                                                                                         0.0s
   => CACHED [2/4] WORKDIR /app                                                                                               0.0s
   => CACHED [3/4] COPY . .                                                                                                   0.0s
   => CACHED [4/4] RUN yarn install --production                                                                              0.0s
   => exporting to image                                                                                                      0.0s
   => => exporting layers                                                                                                     0.0s
   => => exporting manifest
```

后续构建通过利用缓存层仅用了 1.0 秒就完成了。无需重复安装依赖等耗时的步骤。

回到 `docker image history` 的输出，你会看到 Dockerfile 中的每条命令都成为镜像中的一新层。你可能还记得，当你对镜像进行更改时，`yarn` 依赖项必须重新安装。有没有办法解决这个问题？每次构建都重新安装相同的依赖项并没有太大意义，对吧？

为了解决这个问题，重新构建你的 Dockerfile，使依赖缓存保持有效，除非确实需要使其失效对于基于 Node 的应用，依赖项定义在 `package.json` 文件中。你希望在该文件发生变化时重新安装依赖项，但如果文件没有变化，则使用缓存的依赖项。因此，首先只复制该文件，然后安装依赖项，最后再复制其他所有内容。这样，只有当 `package.json` 文件发生变化时，才需要重新创建 yarn 依赖项。

6. 更新 Dockerfile，首先复制 `package.json` 文件，安装依赖项，然后再复制其他所有内容：

```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --production 
COPY . . 
EXPOSE 3000
CMD ["node", "src/index.js"]
```

7. 在与 Dockerfile 相同的文件夹中创建一个名为 `.dockerignore` 的文件，内容如下：

```plaintext
node_modules
```

8. 构建新镜像：

```console
docker build .
```

然后你会看到类似下面的输出：

```console
[+] Building 16.1s (10/10) FINISHED
=> [internal] load build definition from Dockerfile                                               0.0s
=> => transferring dockerfile: 175B                                                               0.0s
=> [internal] load .dockerignore                                                                  0.0s
=> => transferring context: 2B                                                                    0.0s
=> [internal] load metadata for docker.io/library/node:22-alpine                                  0.0s
=> [internal] load build context                                                                  0.8s
=> => transferring context: 53.37MB                                                               0.8s
=> [1/5] FROM docker.io/library/node:22-alpine                                                    0.0s
=> CACHED [2/5] WORKDIR /app                                                                      0.0s
=> [3/5] COPY package.json yarn.lock ./                                                           0.2s
=> [4/5] RUN yarn install --production                                                           14.0s
=> [5/5] COPY . .                                                                                 0.5s
=> exporting to image                                                                             0.6s
=> => exporting layers                                                                            0.6s
=> => writing image     
sha256:d6f819013566c54c50124ed94d5e66c452325327217f4f04399b45f94e37d25        0.0s
=> => naming to docker.io/library/node-app:2.0                                                 0.0s
```

你会看到所有层都重建了。这完全可以接受，因为你大幅修改了 Dockerfile。

9. 现在，修改 `src/static/index.html` 文件（例如，将标题改为 "The Awesome Todo App"）。

10. 构建 Docker 镜像。这一次，你的输出应该会有所不同。

```console
docker build -t node-app:3.0 .
```

然后你会看到类似下面的输出：

```console
[+] Building 1.2s (10/10) FINISHED 
=> [internal] load build definition from Dockerfile                                               0.0s
=> => transferring dockerfile: 37B                                                                0.0s
=> [internal] load .dockerignore                                                                  0.0s
=> => transferring context: 2B                                                                    0.0s
=> [internal] load metadata for docker.io/library/node:22-alpine                                  0.0s 
=> [internal] load build context                                                                  0.2s
=> => transferring context: 450.43kB                                                              0.2s
=> [1/5] FROM docker.io/library/node:22-alpine                                                    0.0s
=> CACHED [2/5] WORKDIR /app                                                                      0.0s
=> CACHED [3/5] COPY package.json yarn.lock ./                                                    0.0s
=> CACHED [4/5] RUN yarn install --production                                                     0.0s
=> [5/5] COPY . .                                                                                 0.5s 
=> exporting to image                                                                             0.3s
=> => exporting layers                                                                            0.3s
=> => writing image     
sha256:91790c87bcb096a83c2bd4eb512bc8b134c757cda0bdee4038187f98148e2eda       0.0s
=> => naming to docker.io/library/node-app:3.0                                                 0.0s
```

首先，你会注意到构建速度快了很多。你会看到有几个步骤使用了先前缓存的层。这是个好消息；你正在使用 build cache。推送和拉取此镜像及其更新也会快得多。

通过遵循这些优化技术，你可以使 Docker 构建更快、更高效，从而缩短迭代周期并提高开发生产力。

## 更多资源

- [Optimizing builds with cache management](/build/cache/)
- [Cache Storage Backend](/build/cache/backends/)
- [Build cache invalidation](/build/cache/invalidation/)

## 下一步

现在你已经理解了如何有效使用 Docker build cache，接下来可以学习多阶段构建（Multi-stage builds）了。

[Multi-stage builds（多阶段构建）](/get-started/docker-concepts/building-images/using-the-build-cache/multi-stage-builds)