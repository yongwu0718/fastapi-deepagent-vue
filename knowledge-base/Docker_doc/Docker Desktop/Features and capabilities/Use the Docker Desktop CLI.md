# 使用 Docker Desktop CLI

**Docker Desktop CLI** 允许您直接从命令行执行关键操作，例如启动（starting）、停止（stopping）、重启（restarting）和更新（updating）Docker Desktop。

**Docker Desktop CLI** 提供：

- **简化本地开发的自动化**：在脚本和测试中更高效地执行 Docker Desktop 操作。
- **改进的开发者体验**：从命令行重启、退出或重置 Docker Desktop，减少对 Docker Desktop Dashboard 的依赖，提高灵活性和效率。

## 用法 (Usage)

```console
docker desktop COMMAND [OPTIONS]
```

## 命令 (Commands)

| Command              | Description                              |
|:---------------------|:-----------------------------------------|
| `start`              | 启动 Docker Desktop                    |
| `stop`               | 停止 Docker Desktop                     |
| `restart`            | 重启 Docker Desktop                  |
| `status`             | 显示 Docker Desktop 是正在运行还是已停止。       |
| `engine ls`          | 列出可用的引擎（仅限 Windows）   |
| `engine use`         | 在 Linux 和 Windows 容器之间切换（仅限 Windows） |
| `update`             | 管理 Docker Desktop 更新。 |
| `logs`               | 打印日志条目                        |
| `disable`            | 禁用某个功能                        |
| `enable`             | 启用某个功能                         | 
| `version`            | 显示 Docker Desktop CLI 插件的版本信息 |
| `kubernetes`         | 列出 Docker Desktop 使用的 Kubernetes 镜像或重启集群。适用于 Docker Desktop 4.44 及更高版本。          |
| `diagnose`           | 诊断 Docker Desktop 并上传诊断信息。适用于 Docker Desktop 4.60 及更高版本。 |

有关每个命令的更多详细信息，请参阅 [Docker Desktop CLI 参考](/reference/cli/docker/desktop/)。