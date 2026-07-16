# 构建 Image 的完整流程：从 Dockerfile 到最终镜像

---

## 概述

Docker 镜像构建是一个从 **Dockerfile** 文本文件出发，通过 **分层存储 + 构建缓存 + 多阶段构建** 三大核心机制，最终产出精简、安全、可复用的容器镜像的完整流水线。

```
Dockerfile  ──▶  docker build  ──▶  Image Layers  ──▶  Container Image
                  ▲                        ▲
                  │                        │
             Build Cache             Union Filesystem
            (加速重复构建)            (层堆叠与复用)
```

---

## 第一章：一切从 Dockerfile 开始

### 1.1 什么是 Dockerfile

**Dockerfile** 是一个纯文本文件，包含了构建镜像所需的所有指令。它告诉 Docker 构建器（builder）每一步该做什么——从选择基础镜像、安装依赖、复制代码，到最终配置启动命令。

### 1.2 核心指令一览

| 指令 | 作用 |
|------|------|
| `FROM <image>` | 指定基础镜像 |
| `WORKDIR <path>` | 设定工作目录（后续指令的运行位置） |
| `COPY <host> <image>` | 从宿主机复制文件到镜像 |
| `RUN <command>` | 在镜像内执行命令（安装依赖等） |
| `ENV <key> <value>` | 设置环境变量 |
| `EXPOSE <port>` | 声明容器监听的端口（文档性质） |
| `USER <user/uid>` | 切换运行用户（提升安全性） |
| `CMD ["cmd", "arg1"]` | 容器启动时的默认命令 |

### 1.3 Dockerfile 标准步骤

```
Step 1 ── 确定基础镜像        FROM python:3.13
Step 2 ── 设定工作目录        WORKDIR /usr/local/app
Step 3 ── 安装应用依赖        COPY requirements.txt ./ → RUN pip install ...
Step 4 ── 复制源代码          COPY src ./src
Step 5 ── 配置运行环境        EXPOSE / USER / CMD
```

### 1.4 一个完整的 Dockerfile 示例

```dockerfile
FROM python:3.13
WORKDIR /usr/local/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
EXPOSE 8080
RUN useradd app
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

> **关键设计思路**：先复制依赖文件（`requirements.txt`）再安装依赖，最后才复制源代码。这样做是为了充分利用 **构建缓存**（见第三章）。

---

## 第二章：镜像的分层结构

### 2.1 层（Layer）的概念

每一条 Dockerfile 指令（`RUN`、`COPY`、`ADD`）都会创建一个新的 **层**。层是一组文件系统的变更记录——新增、删除或修改。层一旦创建就**不可变（immutable）**。

```
Layer 1 ── 基础命令 + 包管理器（如 apt）
Layer 2 ── 安装 Python 运行时 + pip
Layer 3 ── 复制 requirements.txt
Layer 4 ── 安装应用依赖
Layer 5 ── 复制源代码
```
![alt text](container_image_layers.webp)

### 2.2 层的复用机制

层是**可共享**的。多个镜像可以共用相同的基础层（例如都基于 `python:3.13`），这带来三个好处：

- **构建更快**：公共层只需构建一次
- **存储更省**：相同层在磁盘上只存一份
- **分发更高效**：拉取镜像时公共层无需重复下载
![alt text](container_image_layer_reuse.webp)

### 2.3 联合文件系统（Union Filesystem）

当容器运行时，Docker 通过联合文件系统将所有层**堆叠**成一个统一的视图：

```
┌──────────────────────────────┐
│   Container 读写层 (可写)     │  ← 仅当前容器可见
├──────────────────────────────┤
│   Layer 5: 源代码            │
├──────────────────────────────┤
│   Layer 4: 应用依赖          │
├──────────────────────────────┤
│   Layer 3: requirements.txt  │
├──────────────────────────────┤
│   Layer 2: Python 运行时     │
├──────────────────────────────┤
│   Layer 1: 基础系统          │
└──────────────────────────────┘
```

- 下方所有 Image 层是**只读**的
- 最上方的 Container 层是**可写**的（Copy-on-Write）
- 同一个 Image 可以启动多个 Container，各自拥有独立的可写层

---

## 第三章：构建缓存（Build Cache）机制

### 3.1 缓存的工作原理

当你执行 `docker build` 时，Docker 会逐条执行 Dockerfile 指令。对于每一条指令，Docker 会检查**之前是否执行过相同的指令**（相同的命令 + 相同的上下文）。如果命中缓存，该层直接复用，不再重新构建。

```
第一次构建（无缓存）：
  FROM  →  WORKDIR  →  COPY . .  →  RUN yarn install  →  ← 耗时 20s

第二次构建（全缓存）：
  CACHED → CACHED → CACHED → CACHED  ← 耗时 1s
```

### 3.2 缓存失效（Cache Invalidation）的触发条件

以下任何一种情况都会导致缓存失效：

| 触发条件 | 说明 |
|----------|------|
| `RUN` 命令内容变化 | 只要命令字符串有任何改动，该层缓存即失效 |
| `COPY` / `ADD` 的文件内容变化 | Docker 会校验文件内容的 checksum |
| 前一层失效 | **一旦某一层失效，其后的所有层全部失效**（级联失效） |

### 3.3 缓存优化的黄金法则：依赖前置

**不好的写法**（每次代码改动都重新安装依赖）：

```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY . .                          # ← 源代码变动导致此层失效
RUN yarn install --production     # ← 被迫重新安装所有依赖！
CMD ["node", "./src/index.js"]
```

**优化后的写法**（依赖安装被缓存）：

```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY package.json yarn.lock ./    # ← 仅依赖文件变化时才失效
RUN yarn install --production     # ← 依赖未变则走缓存！
COPY . .                          # ← 只有源代码变化时此层才重建
EXPOSE 3000
CMD ["node", "src/index.js"]
```

```
依赖文件未变、只改了源代码时的构建：
  FROM → WORKDIR → CACHED → CACHED → COPY . .  ← 只有最后一层重建！
```

### 3.4 `.dockerignore` 文件

创建 `.dockerignore` 排除不需要发送到构建上下文的文件（如 `node_modules`），可以减少构建上下文大小，提高 `COPY` 指令的速度：

```plaintext
node_modules
.git
*.md
```

---

## 第四章：多阶段构建（Multi-stage Builds）

### 4.1 为什么需要多阶段构建

传统的单阶段构建会将**所有构建工具、中间产物、源码**都留在最终镜像中，导致：

- 镜像体积庞大（可能达到 **880 MB** 甚至更大）
- 包含编译器、SDK 等不必要的攻击面
- 生产环境中携带开发/调试工具

多阶段构建的核心思想：**将"构建环境"与"运行环境"彻底分离**。

### 4.2 多阶段构建的结构

```dockerfile
# ===== Stage 1: 构建阶段 =====
FROM <builder-image> AS builder
WORKDIR /app
COPY 源代码和依赖文件 .
RUN 编译/打包命令

# ===== Stage 2: 运行时阶段 =====
FROM <runtime-image> AS final
WORKDIR /app
COPY --from=builder /构建产物的路径 /最终位置
CMD ["启动命令"]
```

关键语法：
- **`FROM ... AS <stage-name>`**：为阶段命名
- **`COPY --from=<stage-name>`**：从指定阶段复制产物（而非从宿主机）

### 4.3 实战对比：Spring Boot Java 应用

**优化前（单阶段构建）—— 880 MB：**

```dockerfile
FROM eclipse-temurin:21.0.8_9-jdk-jammy
WORKDIR /app
COPY .mvn/ .mvn
COPY mvnw pom.xml ./
RUN ./mvnw dependency:go-offline
COPY src ./src
CMD ["./mvnw", "spring-boot:run"]
```

镜像中包含：完整 JDK + Maven + 源码 + 中间产物。

**优化后（多阶段构建）—— 428 MB（缩小约 51%）：**

```dockerfile
# Stage 1: 构建（完整 JDK + Maven）
FROM eclipse-temurin:21.0.8_9-jdk-jammy AS builder
WORKDIR /opt/app
COPY .mvn/ .mvn
COPY mvnw pom.xml ./
RUN ./mvnw dependency:go-offline
COPY ./src ./src
RUN ./mvnw clean install          # ← 编译打包成 JAR

# Stage 2: 运行（仅 JRE）
FROM eclipse-temurin:21.0.8_9-jre-jammy AS final
WORKDIR /opt/app
EXPOSE 8080
COPY --from=builder /opt/app/target/*.jar /opt/app/*.jar
ENTRYPOINT ["java", "-jar", "/opt/app/*.jar"]
```

### 4.4 多阶段构建对各语言的好处

| 语言类型 | 构建阶段 | 运行阶段 | 收益 |
|----------|----------|----------|------|
| **编译型**（Go, Rust, C） | 编译源码 | 仅复制二进制 | 镜像不含编译器，体积极小 |
| **解释型**（Python, JS, Ruby） | 构建/压缩代码 | 复制生产就绪文件 | 不含 devDependencies、构建工具 |
| **JVM 语言**（Java, Kotlin） | JDK + Maven/Gradle | 仅 JRE + JAR | 从 880MB 降至 428MB |

### 4.5 仅构建指定阶段

使用 `--target` 参数可以只构建到某个中间阶段（调试时有用）：

```console
$ docker build -t debug-image --target builder .
```

---

## 第五章：完整流程总结

```
                            ┌──────────────────────────────────────────────┐
                            │              docker build 全过程               │
                            └──────────────────────────────────────────────┘

   1. Dockerfile          2. 分层构建                   3. 缓存判断
   ┌──────────┐         ┌──────────────────┐        ┌──────────────┐
   │ FROM ... │────────▶│ Layer 1: 基础镜像 │───────▶│ 之前有缓存？   │
   │ WORKDIR  │         │ Layer 2: 依赖安装 │        │ YES → CACHED  │
   │ COPY ... │         │ Layer 3: 源码复制 │        │ NO  → 重建    │
   │ RUN ...  │         │ Layer 4: 编译打包 │        └──────┬───────┘
   │ CMD ...  │         │ ...              │               │
   └──────────┘         └──────────────────┘               ▼
                                                 ┌──────────────────┐
   4. 多阶段构建                                  │ 级联规则：        │
   ┌──────────────────────┐                      │ 一层失效 → 后续   │
   │ Stage 1: builder     │                      │ 全部失效         │
   │  ├─ 编译/打包        │                      └──────────────────┘
   │  └─ 产出 JAR/二进制   │                              │
   │                      │                              ▼
   │ Stage 2: runtime     │◀── COPY --from=builder
   │  ├─ 仅包含运行时依赖  │
   │  └─ 更小、更安全     │
   └──────────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ 最终 Container   │
                     │ Image           │
                     │                 │
                     │ ✓ 体积小         │
                     │ ✓ 安全           │
                     │ ✓ 构建快         │
                     │ ✓ 可复用         │
                     └─────────────────┘
```

### 关键原则

1. **依赖前置**：先复制依赖定义文件，安装依赖，最后才复制源代码——最大化缓存命中率
2. **分层设计**：每个 `RUN`/`COPY`/`ADD` 产生一个新层；层不可变、可复用
3. **缓存意识**：理解缓存失效的触发条件，合理安排指令顺序
4. **多阶段分离**：构建环境 ≠ 运行环境，用 `COPY --from` 仅传递最终产物
5. **最小权限**：使用 `USER` 切换非 root 用户，减少安全风险
6. **使用 `.dockerignore`**：减少构建上下文，避免不必要的缓存失效