```yaml
# Docker Compose 配置文件版本（隐式使用最新版本，此处省略版本声明）
services:
  # 定义 Node.js 应用服务
  app:
    image: node:22-alpine           # 使用 Node.js 22 的 Alpine 轻量级镜像
    command: sh -c "yarn install && yarn run dev"  # 容器启动后安装依赖并运行开发服务器
    ports:
      - 127.0.0.1:3000:3000         # 将宿主机的 3000 端口映射到容器的 3000 端口，仅监听本地回环地址
    working_dir: /app               # 设置容器内的工作目录为 /app
    volumes:
      - ./:/app                     # 将当前项目目录挂载到容器内的 /app，实现代码热更新
    environment:                    # 传递给应用的环境变量
      MYSQL_HOST: mysql             # MySQL 服务的主机名（对应下方 mysql 服务名称）
      MYSQL_USER: root              # 数据库用户名
      MYSQL_PASSWORD: secret        # 数据库密码
      MYSQL_DB: todos               # 使用的数据库名称

  # 定义 MySQL 数据库服务
  mysql:
    image: mysql:8.0                # 使用 MySQL 8.0 官方镜像
    volumes:
      - todo-mysql-data:/var/lib/mysql  # 将数据持久化到命名卷，防止容器删除后数据丢失
    environment:                    # MySQL 环境变量（用于初始化）
      MYSQL_ROOT_PASSWORD: secret   # 设置 root 用户的密码
      MYSQL_DATABASE: todos         # 自动创建的数据库名称

# 定义命名卷，用于持久化 MySQL 数据
volumes:
  todo-mysql-data:
```