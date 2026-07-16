# Multi-stage builds（多阶段构建）

## 解释

在传统构建中，所有构建指令都按顺序在单个构建容器中执行：下载依赖项、编译代码、打包应用。所有这些层最终都会进入你的最终镜像。这种方法虽然可行，但会导致镜像体积庞大、携带不必要的负担并增加安全风险。这时就需要 **Multi-stage builds** 登场了。

Multi-stage builds 在 Dockerfile 中引入多个阶段（stages），每个阶段都有特定的目的。可以把它理解为**能够同时在多个不同的环境中运行构建的不同部分**。通过将构建环境与最终运行时环境分离，你可以显著减小镜像大小和攻击面。这对于具有大量构建依赖项的应用尤其有益。

Multi-stage builds 被推荐用于所有类型的应用。

- 对于解释型语言（如 JavaScript、Ruby 或 Python），你可以在一个阶段中构建和压缩代码，然后将生产就绪的文件复制到一个更小的运行时镜像中。这优化了你的部署镜像。
- 对于编译型语言（如 C、Go 或 Rust），multi-stage builds 让你可以在一个阶段中进行编译，然后将编译好的二进制文件复制到最终的运行时镜像中。无需在最终镜像中打包整个编译器。

下面是一个使用伪代码编写的 multi-stage build 结构示例。注意有多个 `FROM` 语句和一个新的 `AS <stage-name>`。此外，第二个阶段中的 `COPY` 语句正在从上一个阶段 `--from` 复制内容。

```dockerfile
# Stage 1: Build Environment（构建环境）
FROM builder-image AS build-stage 
# 安装构建工具（例如 Maven、Gradle）
# 复制源代码
# 构建命令（例如编译、打包）

# Stage 2: Runtime environment（运行时环境）
FROM runtime-image AS final-stage  
# 从构建阶段复制应用产物（例如 JAR 文件）
COPY --from=build-stage /path/in/build/stage /path/to/place/in/final/stage
# 定义运行时配置（例如 CMD、ENTRYPOINT）
```

这个 Dockerfile 使用了两个阶段：

- **构建阶段（build stage）** 使用一个包含编译应用所需构建工具的基础镜像。它包括安装构建工具、复制源代码和执行构建命令的指令。
- **最终阶段（final stage）** 使用一个更适合运行应用的更小的基础镜像。它从构建阶段复制编译好的产物（例如 JAR 文件）。最后，它定义了启动应用的运行时配置（使用 `CMD` 或 `ENTRYPOINT`）。

## 动手试一试

在本动手指南中，你将解锁 multi-stage builds 的强大功能，为一个示例 Java 应用创建精简高效的 Docker 镜像。你将使用一个基于 Spring Boot 的简单 "Hello World" 应用，使用 Maven 构建作为示例。

1. [下载并安装](https://www.docker.com/products/docker-desktop/) Docker Desktop。

2. 打开这个[预初始化的项目](https://start.spring.io/#!type=maven-project&language=java&platformVersion=4.0.1&packaging=jar&configurationFileFormat=properties&jvmVersion=21&groupId=com.example&artifactId=spring-boot-docker&name=spring-boot-docker&description=Demo%20project%20for%20Spring%20Boot&packageName=com.example.spring-boot-docker&dependencies=web) 生成一个 ZIP 文件。如下图所示：

![alt text](multi-stage-builds-spring-initializer.webp)

[Spring Initializr](https://start.spring.io/) 是一个 Spring 项目的快速启动生成器。它提供了一个可扩展的 API 来生成基于 JVM 的项目，并支持几种常见概念的实现——例如针对 Java、Kotlin、Groovy 和 Maven 的基本语言生成。

选择 **Generate** 创建并下载此项目的 zip 文件。

在本演示中，你将 Maven 构建自动化与 Java、Spring Web 依赖项以及 Java 21 元数据配对。

3. 浏览项目目录。解压文件后，你会看到以下项目目录结构：

```plaintext
spring-boot-docker
├── HELP.md
├── mvnw
├── mvnw.cmd
├── pom.xml
└── src
    ├── main
    │   ├── java
    │   │   └── com
    │   │       └── example
    │   │           └── spring_boot_docker
    │   │               └── SpringBootDockerApplication.java
    │   └── resources
    │       ├── application.properties
    │       ├── static
    │       └── templates
    └── test
        └── java
            └── com
                └── example
                    └── spring_boot_docker
                        └── SpringBootDockerApplicationTests.java

15 directories, 7 files
```

`src/main/java` 目录包含项目的源代码，`src/test/java` 目录包含测试源代码，`pom.xml` 文件是你的项目的 Project Object Model（POM）。

`pom.xml` 文件是 Maven 项目配置的核心。它是一个包含构建自定义项目所需大部分信息的单一配置文件。POM 很庞大，可能看起来很吓人。幸运的是，你现在不需要理解每个细节就能有效使用它。

4. 创建一个显示 "Hello World!" 的 RESTful web 服务。

在 `src/main/java/com/example/spring_boot_docker/` 目录下，你可以将 `SpringBootDockerApplication.java` 文件修改为以下内容：

```java
package com.example.spring_boot_docker;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@SpringBootApplication
public class SpringBootDockerApplication {

    @RequestMapping("/")
        public String home() {
        return "Hello World";
    }

public static void main(String[] args) {
    SpringApplication.run(SpringBootDockerApplication.class, args);
}

}
```

`SpringbootDockerApplication.java` 文件首先声明了你的 `com.example.spring_boot_docker` 包并导入了必要的 Spring 框架。这个 Java 文件创建了一个简单的 Spring Boot Web 应用，当用户访问其主页时，它会响应 "Hello World"。

### 创建 Dockerfile

现在你已经有了项目，可以开始创建 `Dockerfile` 了。

1. 在与所有其他文件夹和文件（如 src、pom.xml 等）相同的文件夹中创建一个名为 `Dockerfile` 的文件。

2. 在 `Dockerfile` 中，通过添加以下行来定义你的基础镜像：

```dockerfile
FROM eclipse-temurin:21.0.8_9-jdk-jammy
```

3. 现在，使用 `WORKDIR` 指令定义工作目录。这将指定后续命令的运行位置以及文件在 Container Image 内部被拷贝到的目录。

```dockerfile
WORKDIR /app
```

4. 将 Maven 包装器脚本和你的项目的 `pom.xml` 文件复制到 Docker 容器内的当前工作目录 `/app` 中。

```dockerfile
COPY .mvn/ .mvn
COPY mvnw pom.xml ./
```

5. 在容器内执行一个命令。它运行 `./mvnw dependency:go-offline` 命令，该命令使用 Maven 包装器（`./mvnw`）下载项目的所有依赖项，而无需构建最终的 JAR 文件（有助于加快构建速度）。

```dockerfile
RUN ./mvnw dependency:go-offline
```

6. 将主机上项目中的 `src` 目录复制到容器内的 `/app` 目录。

```dockerfile
COPY src ./src
```

7. 设置容器启动时执行的默认命令。该命令指示容器运行 Maven 包装器（`./mvnw`）并带上 `spring-boot:run` 目标，这将构建并执行你的 Spring Boot 应用。

```dockerfile
CMD ["./mvnw", "spring-boot:run"]
```

至此，你应该得到以下 Dockerfile：

```dockerfile
FROM eclipse-temurin:21.0.8_9-jdk-jammy
WORKDIR /app
COPY .mvn/ .mvn
COPY mvnw pom.xml ./
RUN ./mvnw dependency:go-offline
COPY src ./src
CMD ["./mvnw", "spring-boot:run"]
```

### 构建容器镜像

1. 执行以下命令来构建 Docker 镜像：

```console
docker build -t spring-helloworld .
```

2. 使用 `docker images` 命令检查 Docker 镜像的大小：

```console
docker images
```

这样做会产生类似下面的输出：

```console
REPOSITORY          TAG       IMAGE ID       CREATED          SIZE
spring-helloworld   latest    ff708d5ee194   3 minutes ago    880MB
```

此输出显示你的镜像大小为 880MB。它包含完整的 JDK、Maven 工具链等。在生产环境中，你不需要在最终镜像中包含这些。

### 运行 Spring Boot 应用

1. 现在你已经构建了镜像，是时候运行容器了。

```console
docker run -p 8080:8080 spring-helloworld
```

然后你会在容器日志中看到类似下面的输出：

```plaintext
[INFO] --- spring-boot:3.3.4:run (default-cli) @ spring-boot-docker ---
[INFO] Attaching agents: []

    .   ____          _            __ _ _
    /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
    ( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
    \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
    '  |____| .__|_| |_|_| |_\__, | / / / /
    =========|_|==============|___/=/_/_/_/

    :: Spring Boot ::                (v3.3.4)

2024-09-29T23:54:07.157Z  INFO 159 --- [spring-boot-docker] [           main]
c.e.s.SpringBootDockerApplication        : Starting SpringBootDockerApplication using Java
21.0.2 with PID 159 (/app/target/classes started by root in /app)
….
```

2. 通过 Web 浏览器访问 [http://localhost:8080](http://localhost:8080) 来访问你的 "Hello World" 页面，或者使用以下 curl 命令：

```console
curl localhost:8080
Hello World
```

### 使用 Multi-stage builds

1. 思考以下 Dockerfile：

```dockerfile
FROM eclipse-temurin:21.0.8_9-jdk-jammy AS builder
WORKDIR /opt/app
COPY .mvn/ .mvn
COPY mvnw pom.xml ./
RUN ./mvnw dependency:go-offline
COPY ./src ./src
RUN ./mvnw clean install

FROM eclipse-temurin:21.0.8_9-jre-jammy AS final
WORKDIR /opt/app
EXPOSE 8080
COPY --from=builder /opt/app/target/*.jar /opt/app/*.jar
ENTRYPOINT ["java", "-jar", "/opt/app/*.jar"]
```

注意这个 Dockerfile 被拆分成了两个阶段。

- 第一个阶段与前一个 Dockerfile 相同，提供了一个用于构建应用的 Java Development Kit（JDK）环境。这个阶段被命名为 `builder`。
- 第二个阶段是一个名为 `final` 的新阶段。它使用一个更精简的 `eclipse-temurin:21.0.2_13-jre-jammy` 镜像，只包含运行应用所需的 Java Runtime Environment（JRE）。该镜像提供了一个 Java Runtime Environment（JRE），足以运行编译后的应用（JAR 文件）。

> 对于生产使用，强烈建议你使用 jlink 生成一个自定义的类似 JRE 的运行时。JRE 镜像适用于所有版本的 Eclipse Temurin，但 `jlink` 允许你创建一个仅包含应用所需 Java 模块的最小运行时。这可以显著减小最终镜像的大小并提高安全性。[参考此页面](https://hub.docker.com/_/eclipse-temurin) 了解更多信息。

使用 multi-stage builds，Docker 构建使用一个基础镜像进行编译、打包和单元测试，然后使用另一个镜像作为应用运行时。因此，最终镜像更小，因为它不包含任何开发或调试工具。通过将构建环境与最终运行时环境分离，你可以显著减小镜像大小并提高最终镜像的安全性。

2. 现在，重新构建你的镜像并运行你的生产就绪版本。

```console
docker build -t spring-helloworld-builder .
```

该命令使用当前目录中 Dockerfile 的最终阶段构建一个名为 `spring-helloworld-builder` 的 Docker 镜像。

> [!NOTE]
>
> 在你的 multi-stage Dockerfile 中，最终阶段（`final`）是构建的默认目标。这意味着如果你没有在 `docker build` 命令中使用 `--target` 标志显式指定目标阶段，Docker 将默认构建最后一个阶段。你可以使用 `docker build -t spring-helloworld-builder --target builder .` 来仅构建带有 JDK 环境的构建阶段。

3. 使用 `docker images` 命令查看镜像大小的差异：

```console
docker images
```

你会得到类似下面的输出：

```console
REPOSITORY          TAG       IMAGE ID       CREATED          SIZE
spring-helloworld-builder latest    c5c76cb815c0   24 minutes ago      428MB
spring-helloworld         latest    ff708d5ee194   About an hour ago   880MB
```

你的最终镜像只有 428 MB，而原始构建大小为 880 MB。

通过优化每个阶段并只包含必要的内容，你能够显著减少整体镜像大小，同时实现相同的功能。这不仅提高了性能，还使你的 Docker 镜像更轻量、更安全、更易于管理。

## 更多资源

- [Multi-stage builds](/build/building/multi-stage/)
- [Dockerfile best practices](/develop/develop-images/dockerfile_best-practices/)
- [Base images](/build/building/base-images/)
- [Spring Boot Docker](https://spring.io/guides/topicals/spring-boot-docker)