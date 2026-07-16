# 指定项目名称（project name）

默认情况下，Compose 会根据包含 Compose 文件的目录名称来分配项目名称（project name）。您可以通过几种方法覆盖此默认值。

本页面提供了自定义项目名称可能有用的场景示例，概述了设置项目名称的各种方法，并给出了每种方法的优先级顺序。

> [!NOTE]
>
> 默认的项目目录（project directory）是 Compose 文件所在的基目录。也可以使用 [`--project-directory` 命令行选项](/reference/cli/docker/compose/#options)为其设置自定义值。

## 示例用例

Compose 使用项目名称（project name）将各个环境相互隔离。在多种上下文中，项目名称都很有用：

- 在开发主机上：为同一个环境创建多个副本，用于为项目的每个功能分支运行稳定的副本。
- 在 CI 服务器上：通过将项目名称设置为唯一的构建编号，防止构建之间相互干扰。
- 在共享主机或开发主机上：避免可能使用相同服务名称（service names）的不同项目之间相互干扰。

## 设置项目名称（project name）

**项目名称只能包含小写字母、数字、短横线和下划线，并且必须以小写字母或数字开头**。如果项目目录或当前目录的基名违反了此约束，可以使用其他替代机制。

每种方法的优先级顺序（从高到低）如下：

1. `-p` 命令行标志。
2. [COMPOSE_PROJECT_NAME 环境变量](/compose/how-tos/project-name/environment-variables/envvars/)。
3. Compose 文件中的顶层 [`name:` 属性](/reference/compose-file/version-and-name/)。或者，如果您在命令行中使用 `-f` 标志[指定了多个 Compose 文件](/compose/how-tos/project-name/multiple-compose-files/merge/)，则使用最后一个 `name:`。
4. 包含 Compose 文件的项目目录的基名。或者，如果您在命令行中使用 `-f` 标志[指定了多个 Compose 文件](/compose/how-tos/project-name/multiple-compose-files/merge/)，则使用第一个 Compose 文件的基名。
5. 如果未指定 Compose 文件，则使用当前目录的基名。

## 下一步

- 阅读有关[使用多个 Compose 文件](/compose/how-tos/project-name/multiple-compose-files/)的内容。
- 探索一些[示例应用](https://github.com/docker/awesome-compose)。