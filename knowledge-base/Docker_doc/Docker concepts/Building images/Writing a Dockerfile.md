# Writing a Dockerfile（编写 Dockerfile）

## 解释

**Dockerfile** 是一个基于文本的文档，用于创建 Container Image。它为 Image 构建器提供指令，包括要运行的命令、要复制的文件、启动命令等。

例如，以下 Dockerfile 将生成一个可直接运行的 Python 应用：

```dockerfile
# 使用 Python 3.13 官方镜像作为基础
FROM python:3.13

# 设置容器内的工作目录为 /usr/local/app
WORKDIR /usr/local/app

# 安装应用依赖项
# 先将 requirements.txt 复制到工作目录（利用 Docker 缓存，仅当 requirements.txt 变化时才重新安装依赖）
COPY requirements.txt ./
# 安装依赖，--no-cache-dir 避免缓存占用额外空间
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝源代码（将本地的 src 目录复制到容器的 /usr/local/app/src）
COPY src ./src

# 声明容器运行时监听的端口（仅文档用途，实际监听由 CMD 中的 uvicorn 决定）
EXPOSE 8080

# 创建一个普通用户 app（提升安全性，避免容器以 root 身份运行）
RUN useradd app
# 切换到 app 用户（后续指令及容器启动都使用该用户）
USER app

# 容器启动时运行的命令：使用 uvicorn 运行 app.main 中的 app 对象，监听所有地址的 8080 端口
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 常见指令（Common instructions）

`Dockerfile` 中最常见的一些指令包括：

- **`FROM image`**：指定构建所基于的 Base Image（基础镜像）。
- **`WORKDIR <路径>`**：指定“工作目录”，即镜像中用于拷贝文件和执行命令的路径。
- **`COPY <主机路径> <镜像路径>`**：告诉构建器从主机拷贝文件并将其放入 Container Image 中。
- **`RUN <命令>`**：告诉构建器运行指定的命令。
- **`ENV <名称> <值>`**：设置一个环境变量，运行中的 Container 会使用该变量。
- **`EXPOSE <端口号>`**：在镜像上设置配置，指明镜像希望暴露的端口。
- **`USER <用户名或 UID>`**：为所有后续指令设置默认用户。
- **`CMD ["<命令>", "<参数1>"]`**：设置使用该镜像的 Container 的默认命令。

要阅读所有指令或查看更多详细信息，请查看 [Dockerfile reference](https://docs.docker.com/engine/reference/builder/)。

## 动手试一试

正如你在前面的示例中看到的，Dockerfile 通常遵循以下步骤：

1. 确定你的 Base Image
2. 安装应用依赖项
3. 拷贝所有相关的源代码和/或二进制文件
4. 配置最终的 Image

在这个快速动手指南中，你将编写一个 Dockerfile 来构建一个简单的 Node.js 应用。如果你不熟悉基于 JavaScript 的应用也没关系，这并不妨碍你跟随本指南进行操作。

### 准备

[下载此 ZIP 文件](https://github.com/docker/getting-started-todo-app/archive/refs/heads/build-image-from-scratch.zip) 并将其解压到你机器上的一个目录中。

如果你不想下载 ZIP 文件，也可以克隆 https://github.com/docker/getting-started-todo-app 项目，并切换到 `build-image-from-scratch` 分支。

### 创建 Dockerfile

现在你已经有了项目，可以开始创建 `Dockerfile` 了。

1. [下载并安装](https://www.docker.com/products/docker-desktop/) Docker Desktop。

2. 检查项目结构。

   浏览 `getting-started-todo-app/app/` 的内容。你会注意到已经存在一个 `Dockerfile`。它是一个简单的文本文件，可以用任何文本或代码编辑器打开。

3. 删除现有的 `Dockerfile`。

   在本练习中，我们假设从头开始，创建一个新的 `Dockerfile`。

4. 在 `getting-started-todo-app/app/` 文件夹中创建一个名为 `Dockerfile` 的文件。

   > **Dockerfile 文件扩展名**
   >
   > 需要注意的是，`Dockerfile` **没有** 文件扩展名。某些编辑器会自动为文件添加扩展名（或者会报错说没有扩展名）。

5. 在 `Dockerfile` 中，通过添加以下行来定义你的 Base Image：

   ```dockerfile
   FROM node:22-alpine
   ```

6. 现在，使用 `WORKDIR` 指令定义工作目录。这将指定后续命令的运行位置以及文件在 Container Image 内部被拷贝到的目录。

   ```dockerfile
   
   ```

7. 使用 `COPY` 指令将你机器上项目中的所有文件拷贝到 Container Image 中：

   ```dockerfile
   COPY . .
   ```

8. 使用 `yarn` CLI 和包管理器安装应用的依赖项。为此，使用 `RUN` 指令来运行命令：

   ```dockerfile
   RUN yarn install --production
   ```

9. 最后，使用 `CMD` 指令指定要运行的默认命令：

   ```dockerfile
   CMD ["node", "./src/index.js"]
   ```

   至此，你应该得到以下 Dockerfile：

   ```dockerfile
   FROM node:22-alpine
   WORKDIR /app
   COPY . .
   RUN yarn install --production
   CMD ["node", "./src/index.js"]
   ```

> **这个 Dockerfile 尚未达到生产就绪状态**
>
> 需要注意的是，这个 Dockerfile **并未** 遵循所有最佳实践（这是有意为之）。它可以构建应用，但构建速度不够快，镜像也不够安全。
>
> 请继续阅读，了解更多关于如何最大化利用构建缓存、以非 root 用户身份运行以及使用多阶段构建（multi-stage builds）来优化镜像的内容。

## 更多资源

要了解更多关于编写 Dockerfile 的内容，请访问以下资源：

- [Dockerfile reference](/reference/dockerfile/)
- [Dockerfile best practices](/develop/develop-images/dockerfile_best-practices/)
- [Base images](/build/building/base-images/)
- [Gordon](/ai/gordon/) — Docker 的 AI 助手可以为你的项目生成 Dockerfile。让 Gordon 分析你的代码，并针对你的语言和框架推荐一个优化的 Dockerfile。

## 下一步

现在你已经创建了一个 Dockerfile 并学习了基础知识，接下来该学习如何构建、打标签（tagging）和推送（pushing）镜像了。

[Build, tag and publish the Image（构建、打标签并发布镜像）](/get-started/docker-concepts/building-images/writing-a-dockerfile/build-tag-and-publish-an-image)