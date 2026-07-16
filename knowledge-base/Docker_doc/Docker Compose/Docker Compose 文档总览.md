# Docker Compose 速查手册

> 这是一份**可直接实战**的 Compose 参考。每个小节都是独立可用的代码片段，复制即用。

---

## 常用命令

```powershell
# 启动（前台，看日志）
docker compose up

# 后台启动
docker compose up -d

# 后台启动 + 启用文件监视
docker compose up --watch

# 重新构建并启动
docker compose up --build

# 停止并清理
docker compose down

# 停止并清理（含 volumes）
docker compose down -v

# 查看日志
docker compose logs -f          # 所有服务
docker compose logs -f web      # 只看 web

# 查看状态
docker compose ps

# 在服务中执行命令
docker compose exec web bash
docker compose run --rm web python manage.py migrate

# 查看解析后的完整配置
docker compose config

# 构建镜像
docker compose build
docker compose build web        # 只构建 web
```

---

## 完整 compose.yaml 模板

```yaml
name: myapp                    # 项目名称（可选）

services:
  # ---- Web 应用 ----
  web:
    build: .                   # 从当前目录 Dockerfile 构建
    # image: nginx:alpine      # 或直接用镜像
    ports:
      - "8000:80"              # 主机:容器
    environment:
      - DEBUG=false
      - DB_HOST=db
    env_file: .env             # 从文件加载环境变量
    depends_on:
      db:
        condition: service_healthy
        restart: true          # db 重启时 web 也重启
    volumes:
      - ./src:/app/src         # 代码热更新（开发用）
      - app_data:/app/data     # 命名卷持久化
    restart: always            # 生产环境必备
    develop:                   # Compose Watch（开发用）
      watch:
        - action: sync
          path: ./src
          target: /app/src
          ignore:
            - node_modules/
        - action: rebuild
          path: package.json

  # ---- 数据库 ----
  db:
    image: postgres:18-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password  # 从文件读密码
    secrets:
      - db_password
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d myapp"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # ---- 缓存 ----
  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data

# ---- 卷 ----
volumes:
  db_data:
  redis_data:
  app_data:

# ---- 密钥 ----
secrets:
  db_password:
    file: ./secrets/db_password.txt

# ---- 网络 ----
networks:
  default:
    driver: bridge
```

---

## 网络：服务间如何通信

### 默认行为（零配置）

Compose 自动创建 `<目录名>_default` 网络，**服务名就是 hostname**：

```yaml
# 不需要定义 networks，自动生效
services:
  web:
    image: nginx
    # 代码里连数据库：postgres://db:5432
  db:
    image: postgres:18
```

### 隔离网络

```yaml
services:
  proxy:
    networks:
      - frontend                     # 只连前端
  app:
    networks:
      - frontend
      - backend                      # 连前后端
  db:
    networks:
      - backend                      # 只连后端，外部无法访问

networks:
  frontend:
  backend:
    internal: true                   # 禁止访问外网
```

### 跨项目通信

```powershell
# 先创建共享网络
docker network create shared

# 在多个 compose.yaml 中引用
```

```yaml
networks:
  shared:
    external: true                   # 不创建，使用已存在的
```

---

## 启动顺序：depends_on + healthcheck

```yaml
services:
  web:
    depends_on:
      db:
        condition: service_healthy   # 等 db 健康后才启动
        restart: true
      redis:
        condition: service_started   # 只等 redis 启动（不关心就绪）

  db:
    image: postgres:18
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s              # 给 30s 初始化时间
```

---

## 环境变量速查

### 三种设置方式

```yaml
services:
  app:
    # 方式一：直接写
    environment:
      - DEBUG=true
      - NODE_ENV=production

    # 方式二：从文件加载
    env_file: .env

    # 方式三：插值（从 .env 或 shell 取值）
    environment:
      - TAG=${TAG:-latest}            # 默认值 latest
      - DB_PASS=${DB_PASS:?必须设置}  # 未设置则报错
```

### 优先级（从高到低）

```
docker compose run -e VAR=val  >  environment/env_file（插值）  >  environment（硬编码）  >  env_file  >  Dockerfile ENV
```

### 常用预定义变量

| 变量 | 作用 |
|------|------|
| `COMPOSE_PROJECT_NAME` | 项目名（容器前缀） |
| `COMPOSE_FILE` | 指定 compose 文件 |
| `COMPOSE_PROFILES` | 启用的 profile |

---

## Profiles：按场景激活服务

```yaml
services:
  app:                              # 无 profile，始终启动
    image: myapp

  debug-tools:
    image: phpmyadmin
    profiles: [debug]               # 仅 --profile debug 时启动

  frontend:
    image: nginx
    profiles: [frontend]
```

```powershell
docker compose --profile debug up
docker compose --profile frontend --profile debug up
COMPOSE_PROFILES=debug docker compose up
```

---

## Secrets：安全传递密码/密钥

```yaml
services:
  db:
    image: postgres:18
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password  # 官方镜像约定

secrets:
  db_password:
    file: ./secrets/db_password.txt  # 文件内容即为密码
```

> 密钥挂载到 `/run/secrets/<name>`，是文件而非环境变量，更安全。

---

## Compose Watch：代码变更自动同步

```yaml
services:
  web:
    build: .
    develop:
      watch:
        - action: sync               # 同步文件，不重启（前端热重载）
          path: ./src
          target: /app/src
          ignore:
            - node_modules/

        - action: sync+restart       # 同步后重启（配置文件变更）
          path: ./nginx.conf
          target: /etc/nginx/conf.d/default.conf

        - action: rebuild            # 重建镜像（依赖变更）
          path: package.json
```

```powershell
docker compose up --watch
```

---

## 生产环境部署

```yaml
# compose.yaml（基础）
services:
  web:
    build: .
    ports:
      - "8000:80"
    volumes:
      - ./src:/app/src               # 开发用

# compose.prod.yaml（生产覆盖）
services:
  web:
    build: .                         # 或 image: xxx
    ports:
      - "80:80"
    restart: always                  # 挂了自动重启
    volumes: []                      # 清除开发挂载
    # 生产不要 volumes 挂载源码
```

```powershell
# 合并两个文件启动
docker compose -f compose.yaml -f compose.prod.yaml up -d

# 更新单个服务
docker compose build web
docker compose up --no-deps -d web   # 不重建依赖
```

---

## 多 Compose 文件合并

```powershell
docker compose -f compose.yaml -f compose.admin.yaml up
```

合并规则：
- 单值字段（`image`、`command`）：**后面覆盖前面**
- 列表字段（`ports`、`expose`）：**追加合并**
- 映射字段（`environment`、`volumes`）：**同名覆盖，新键追加**

---

## extends：复用公共配置

```yaml
# common.yml
services:
  base:
    build: .
    environment:
      - API_KEY=xxx
    cpu_shares: 5

# compose.yaml
services:
  web:
    extends:
      file: common.yml
      service: base
    command: /code/run_web
    ports:
      - "8080:8080"

  worker:
    extends:
      file: common.yml
      service: base
    command: /code/run_worker
```

---

## GPU 支持

```yaml
services:
  trainer:
    image: nvidia/cuda:12.9.0-base-ubuntu22.04
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1                # 或 device_ids: ['0', '3']
              capabilities: [gpu]
```

---

## 生命周期钩子

```yaml
services:
  app:
    image: backend
    post_start:                       # 启动后执行
      - command: /opt/register.sh
        user: root                    # 可以 root 执行（即使容器非 root）
    pre_stop:                         # 停止前执行
      - command: cp /data/app.db /data/app.db.bak
```

---

## 构建依赖镜像

```yaml
# 多阶段 Dockerfile 方式
# Dockerfile:
#   FROM alpine AS base
#   RUN apk add --no-cache openssl
#   FROM base AS service_a
#   ...

services:
  a:
    build:
      target: service_a
  b:
    build:
      target: service_b
```

```yaml
# 服务间依赖方式
services:
  a:
    build:
      dockerfile: a.Dockerfile
  b:
    build:
      dockerfile: b.Dockerfile
      additional_contexts:
        service_a: "service:a"        # 声明 b 依赖 a 的镜像
```

---

## Compose Bridge：转 Kubernetes

```powershell
# 生成 K8s manifests
docker compose bridge convert

# 部署到 Docker Desktop 的 K8s
kubectl apply -k out/overlays/desktop/

# 自定义转换
docker compose bridge transformations create --from docker/compose-bridge-kubernetes my-template
docker build --tag mycompany/transform --push .
docker compose bridge convert --transformations mycompany/transform
```

---

## OCI 构件：发布到 Registry

```powershell
docker compose publish username/my-app:latest
docker compose -f oci://docker.io/username/my-app:latest up
```

---

## 安全检查清单

- `docker compose config` 查看完整解析结果
- 审查远程 `include` / `extends` 的 digest（不要用 tag）
- 生产环境不要 `volumes` 挂载源码
- 密码用 `secrets`，不要用 `environment`
- 避免 `privileged: true` 和 `network_mode: host`

---

## 文档索引

| 需要深入了解 | 文件 |
|-------------|------|
| 完整快速入门教程 | [Quickstart.md](Quickstart.md) |
| 信任模型细节 | [Trust model for Compose files.md](Trust%20model%20for%20Compose%20files.md) |
| 环境变量优先级详解 | [how-tos/Environment variables in Compose/Environment variables precedence.md](Environment%20variables%20precedence.md) |
| 插值完整语法 | [how-tos/Environment variables in Compose/interpolation.md](interpolation.md) |
| 预定义环境变量列表 | [how-tos/Environment variables in Compose/Pre-defined environment variables.md](Pre-defined%20environment%20variables.md) |
| Compose Bridge 自定义 | [compose bridge/Customize.md](Customize.md) |
| Provider Services | [how-tos/Use provider services.md](Use%20provider%20services.md) |
| 合并规则详解 | [how-tos/Use multiple Compose files/Merge Compose files.md](Merge%20Compose%20files.md) |