# Docker CLI 命令参考

本文档整理了常用的 Docker CLI 命令，按照使用流程分类。每条命令均保留英文原样，并附中文说明。

---

## 镜像管理

### 搜索镜像

```console
docker search <image-name>
```

> 注意：部分镜像仓库可能需要科学上网。

### 拉取镜像

```console
docker pull <image-name>
```

### 查看本地镜像列表

```console
docker image ls
```

或简写：

```console
docker images
```

### 查看镜像的层历史

```console
docker image history <image-name>
```

---

## 容器生命周期管理

### 运行容器

```console
docker run -d -p 8080:80 docker/welcome-to-docker
```

- `-d`：后台运行容器（detach）
- `-p`：端口映射 `主机端口:容器端口`

### 查看运行中的容器

```console
docker ps
```

- 添加 `-a` 标志可以列出所有容器（包括已停止的）：
  ```console
  docker ps -a
  ```

### 停止容器

```console
docker stop <container-id-or-name>
```

### 删除容器

```console
docker rm <container-id-or-name>
```

- 强制删除（即使正在运行）：
  ```console
  docker rm -f <container-id-or-name>
  ```

---

## 构建与推送镜像

### 准备：克隆示例项目

```console
git clone https://github.com/dockersamples/helloworld-demo-node
cd helloworld-demo-node
```

### 构建镜像

```console
docker build -t <YOUR_DOCKER_USERNAME>/docker-quickstart .
```

- `-t`：为镜像指定名称和标签
- 末尾的 `.` 表示构建上下文为当前目录

### 测试运行构建的镜像

```console
docker run -d -p 8080:8080 <YOUR_DOCKER_USERNAME>/docker-quickstart
```

- 通过浏览器访问 `http://localhost:8080` 验证服务是否正常。

### 给镜像打标签（新增版本）

```console
docker tag <YOUR_DOCKER_USERNAME>/docker-quickstart <YOUR_DOCKER_USERNAME>/docker-quickstart:1.0
```

### 推送镜像到 Docker Hub

```console
docker push <YOUR_DOCKER_USERNAME>/docker-quickstart:1.0
```

- 推送前需先执行 `docker login` 登录。

---

## Docker Compose 编排

### 启动服务栈

```console
docker compose up -d --build
```

- `-d`：后台运行
- `--build`：启动前重新构建镜像

### 停止并移除服务栈（保留数据卷）

```console
docker compose down
```

### 停止并移除服务栈（同时删除数据卷）

```console
docker compose down --volumes
```

### 查看服务日志

```console
docker compose logs -f
```

- `-f`：实时跟踪日志输出

### 列出 Compose 项目中的容器状态

```console
docker compose ps
```

### 在运行中的服务内执行命令

```console
docker compose exec <service-name> <command>
```

---

## 网络与卷管理（补充）

### 创建网络

```console
docker network create <network-name>
```

### 列出网络

```console
docker network ls
```

### 创建数据卷

```console
docker volume create <volume-name>
```

### 列出数据卷

```console
docker volume ls
```

### 删除未使用的卷

```console
docker volume prune
```

---

> **提示**：更多命令细节可参考 [Docker CLI 官方文档](https://docs.docker.com/reference/cli/docker/)。