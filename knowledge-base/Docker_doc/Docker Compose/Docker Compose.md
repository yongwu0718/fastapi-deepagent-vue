# Docker Compose

Docker Compose 是一个用于定义和运行多容器应用的工具。它是实现流畅、高效的开发与部署体验的关键。

Compose 可以简化对整个应用栈的控制，让您能通过单个 YAML 配置文件轻松管理服务（services）、网络（networks）和存储卷（volumes）。然后，仅需一条命令，即可从配置文件中创建并启动所有服务。

Compose 适用于所有环境——生产、预发布、开发、测试以及 CI 工作流。它还提供了管理应用完整生命周期的命令：

- 启动（Start）、停止（stop）和重建（rebuild）服务
- 查看运行中服务的状态
- 流式输出运行中服务的日志
- 在服务上执行一次性命令（one-off command）