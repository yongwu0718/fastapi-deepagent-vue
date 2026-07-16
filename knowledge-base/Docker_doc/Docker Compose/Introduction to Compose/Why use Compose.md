# 为什么要使用 Compose？

## Docker Compose 的主要优势

使用 Docker Compose 有多个优势，能够简化容器化应用的开发、部署和管理：

- **简化的控制**：在单个 YAML 文件中定义和管理多容器应用，从而简化编排和复制。

- **高效的协作**：可共享的 YAML 文件支持开发人员与运维人员之间的顺畅协作，改善工作流程和问题解决，进而提升整体效率。

- **快速的应用开发**：Compose 会缓存用于创建容器的配置。当您重启一个未发生变更的服务（service）时，Compose 会复用现有容器。复用容器意味着您可以快速对环境进行更改。

- **跨环境的可移植性**：Compose 支持在 Compose 文件中使用变量（variables）。您可以使用这些变量针对不同环境或不同用户定制您的组合（composition）。

## Docker Compose 的常见使用场景

Compose 可以有多种不同的使用方式。下面列举了一些常见场景。

### 开发环境

在软件开发过程中，能够在隔离环境中运行应用并与之交互是至关重要的。Compose 命令行工具可用于创建环境并与之交互。

[Compose file](/reference/compose-file/) 提供了一种方式来记录和配置应用的所有服务依赖项（databases、queues、caches、web service APIs 等）。使用 Compose 命令行工具，您只需一条命令（`docker compose up`）即可为每个依赖项创建并启动一个或多个容器。

这些特性共同为您提供了一种启动项目的便捷方式。Compose 可以将多页的“开发者入门指南”缩减为一个机器可读的 Compose 文件和几条命令。

### 自动化测试环境

任何持续部署（Continuous Deployment）或持续集成（Continuous Integration）流程的重要部分都是自动化测试套件。自动化端到端测试需要一个运行测试的环境。Compose 提供了一种便捷的方式来为您的测试套件创建和销毁隔离的测试环境。通过在 [Compose file](/reference/compose-file/) 中定义完整环境，您只需几条命令即可创建和销毁这些环境：

```console
$ docker compose up -d
$ ./run_tests
$ docker compose down
```

### 单主机部署

Compose 支持在单台主机上进行生产部署。您可以使用 Compose 将应用部署到远程 Docker 主机，并管理特定于生产的配置。

有关使用面向生产的功能的详细信息，请参阅 [生产环境中的 Compose](/compose/how-tos/production/)。

## 下一步？

- [了解 Compose 的历史](/compose/intro/features-uses/history/)
- [理解 Compose 的工作原理](/compose/intro/features-uses/compose-application-model/)
- [尝试快速入门指南](/compose/gettingstarted/)