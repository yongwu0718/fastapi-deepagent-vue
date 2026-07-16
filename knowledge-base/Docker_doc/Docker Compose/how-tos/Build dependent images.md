# 构建依赖的镜像（dependent images）

为了减少推送/拉取时间和镜像大小，Compose 应用的一个常见实践是让服务尽可能多地共享基础层。您通常会为所有服务选择相同的操作系统基础镜像。但当您的镜像共享相同的系统软件包时，还可以更进一步地共享镜像层。需要解决的问题是：避免在所有服务中重复完全相同的 Dockerfile 指令。

为便于说明，本页假设您希望所有服务都基于 `alpine` 基础镜像构建，并安装系统包 `openssl`。

## 多阶段 Dockerfile

推荐的方法是将共享声明分组到单个 Dockerfile 中，并使用多阶段（multi-stage）特性，以便服务镜像基于此共享声明进行构建。

Dockerfile：

```dockerfile
FROM alpine as base
RUN /bin/sh -c apk add --update --no-cache openssl

FROM base as service_a
# 构建 service a
...

FROM base as service_b
# 构建 service b
...
```

Compose 文件：

```yaml
services:
  a:
     build:
       target: service_a
  b:
     build:
       target: service_b
```

## 使用另一个服务的镜像作为基础镜像

一种常见的模式是在一个服务中复用另一个服务的镜像作为基础镜像。由于 Compose 不会解析 Dockerfile，它无法自动检测服务之间的这种依赖关系来正确排序构建执行。

a.Dockerfile：

```dockerfile
FROM alpine
RUN /bin/sh -c apk add --update --no-cache openssl
```

b.Dockerfile：

```dockerfile
FROM service_a
# 构建 service b
```

Compose 文件：

```yaml
services:
  a:
     image: service_a 
     build:
       dockerfile: a.Dockerfile
  b:
     image: service_b
     build:
       dockerfile: b.Dockerfile
```

传统的 Docker Compose v1 按顺序构建镜像，这使得这种模式可以直接使用。Compose v2 使用 BuildKit 来优化构建并并行构建镜像，因此需要显式声明。

推荐的方法是将依赖的基础镜像声明为额外的构建上下文（additional build context）：

Compose 文件：

```yaml
services:
  a:
     image: service_a
     build: 
       dockerfile: a.Dockerfile
  b:
     image: service_b
     build:
       dockerfile: b.Dockerfile
       additional_contexts:
         # `FROM service_a` 将被解析为对服务 "a" 的依赖，a 必须先被构建
         service_a: "service:a"
```

使用 `additional_contexts` 属性，您可以引用由另一个服务构建的镜像，而无需显式命名它：

b.Dockerfile：

```dockerfile
FROM base_image  
# `base_image` 不会解析为实际镜像。它用于指向一个命名的额外上下文

# 构建 service b
```

Compose 文件：

```yaml
services:
  a:
     build: 
       dockerfile: a.Dockerfile
       # 构建的镜像将被标记为 <project_name>_a
  b:
     build:
       dockerfile: b.Dockerfile
       additional_contexts:
         # `FROM base_image` 将被解析为对服务 "a" 的依赖，a 必须先被构建
         base_image: "service:a"
```

## 使用 Bake 构建

使用 [Bake](/build/bake/) 可以传递所有服务的完整构建定义，并以最有效的方式编排构建执行。

要启用此功能，请在环境中设置 `COMPOSE_BAKE=true` 变量来运行 Compose。

```console
$ COMPOSE_BAKE=true docker compose build
[+] Building 0.0s (0/1)                                                         
 => [internal] load local bake definitions                                 0.0s
...
[+] Building 2/2 manifest list sha256:4bd2e88a262a02ddef525c381a5bdb08c83  0.0s
 ✔ service_b  Built                                                        0.7s 
 ✔ service_a  Built    
```

也可以通过编辑 `$HOME/.docker/config.json` 配置文件将 Bake 选为默认构建器：
```json
{
  ...
  "plugins": {
    "compose": {
      "build": "bake"
    }
  }
  ...
}
```

## 其他资源

- [Docker Compose build 参考](/reference/cli/docker/compose/build/)
- [了解多阶段 Dockerfile](/build/building/multi-stage/)