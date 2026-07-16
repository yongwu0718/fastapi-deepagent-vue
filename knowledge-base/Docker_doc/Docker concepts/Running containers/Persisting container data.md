# Persisting container data（持久化容器数据）

## 解释

当容器（container）启动时，它使用镜像（image）提供的文件和配置。每个容器都可以创建、修改和删除文件，并且这样做不会影响任何其他容器。当容器被删除时，这些文件更改也会被删除。

虽然容器的这种临时性（ephemeral nature）很好，但当你想持久化数据时，它会带来挑战。例如，如果你重启一个数据库容器，你可能不希望从一个空数据库开始。那么，如何持久化文件呢？

### Container volumes（容器卷）

Volumes 是一种存储机制，能够提供超越单个容器生命周期的数据持久化能力。可以把它想象成从容器内部到容器外部的一个快捷方式或符号链接。

例如，假设你创建了一个名为 `log-data` 的 volume：

```console
docker volume create log-data
```

当使用以下命令启动一个容器时，该 volume 将被挂载（mount）到容器内的 `/logs` 目录：

```console
docker run -d -p 80:80 -v log-data:/logs docker/welcome-to-docker
```

如果 volume `log-data` 不存在，Docker 会自动为你创建它。

当容器运行时，它写入 `/logs` 文件夹的所有文件都将保存在这个 volume 中，位于容器外部。如果你删除容器，然后使用同一个 volume 启动一个新容器，这些文件仍然存在。

> **使用 volumes 共享文件**
>
> 你可以将同一个 volume 挂载到多个容器上，以便在容器之间共享文件。这在日志聚合、数据管道或其他事件驱动的应用中可能会很有帮助。

### Managing volumes（管理 volumes）

Volumes 拥有超出容器范围的生命周期，并且根据你使用的数据类型和应用，可能会变得相当大。以下命令有助于管理 volumes：

- `docker volume ls` - 列出所有 volumes
- `docker volume rm <volume-name-or-id>` - 删除一个 volume（仅当该 volume 没有挂载到任何容器时有效）
- `docker volume prune` - 删除所有未使用（未挂载）的 volumes

## 动手试一试

在本指南中，你将练习创建和使用 volumes 来持久化 Postgres 容器生成的数据。当数据库运行时，它会将文件存储到 `/var/lib/postgresql` 目录中。通过将 volume 挂载到此目录，你可以在多次重启容器时保留数据。

### 使用 volumes

1. [下载并安装](/get-started/get-docker/) Docker Desktop。

2. 使用以下命令启动一个使用 [Postgres image](https://hub.docker.com/_/postgres) 的容器：

```console
docker run --name=db -e POSTGRES_PASSWORD=secret -d -v postgres_data:/var/lib/postgresql postgres:18
```

这将在后台启动数据库，用密码进行配置，并将一个 volume 挂载到 PostgreSQL 用于持久化数据库文件的目录。

3. 使用以下命令连接到数据库：

```console
docker exec -ti db psql -U postgres
```

4. 在 PostgreSQL 命令行中，运行以下命令创建一个数据库表并插入两条记录：

```text
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    description VARCHAR(100)
);
INSERT INTO tasks (description) VALUES ('Finish work'), ('Have fun');
```

5. 通过在 PostgreSQL 命令行中运行以下命令验证数据是否在数据库中：

```text
SELECT * FROM tasks;
```

你应该会得到类似下面的输出：

```text
id | description
----+-------------
    1 | Finish work
    2 | Have fun
(2 rows)
```

6. 运行以下命令退出 PostgreSQL shell：

```console
\q
```

7. 停止并删除数据库容器。请记住，即使容器已被删除，数据仍持久化在 `postgres_data` volume 中。

```console
docker stop db
docker rm db
```

8. 运行以下命令启动一个新容器，并挂载包含持久化数据的同一个 volume：

```console
docker run --name=new-db -d -v postgres_data:/var/lib/postgresql postgres:18
```

你可能注意到 `POSTGRES_PASSWORD` 环境变量被省略了。这是因为该变量仅在引导新数据库时使用。

9. 通过运行以下命令验证数据库是否仍包含记录：

```console
docker exec -ti new-db psql -U postgres -c "SELECT * FROM tasks"
```

### 查看 volume 内容

Docker Desktop Dashboard 提供了查看任何 volume 内容的功能，以及导出、导入、清空、删除和克隆 volumes 的功能。

1. 打开 Docker Desktop Dashboard 并导航到 **Volumes** 视图。在此视图中，你应该会看到 **postgres_data** volume。

2. 选择 **postgres_data** volume 的名称。

3. **Stored Data** 选项卡显示 volume 的内容，并提供浏览文件的功能。**Container in-use** 选项卡显示使用该 volume 的容器名称、镜像名称、容器使用的端口号以及目标（target）。目标（target）是容器内部的一个路径，用于访问 volume 中的文件。**Exports** 选项卡允许你导出 volume。双击文件可以查看内容并进行更改。

4. 右键单击任何文件可以保存或删除它。

### 删除 volumes

在删除 volume 之前，它不能挂载到任何容器上。如果你还没有删除之前的容器，请使用以下命令删除（`-f` 会先停止容器然后删除）：

```console
docker rm -f new-db
```

有几种方法可以删除 volumes，包括以下几种：

- 在 Docker Desktop Dashboard 中选择某个 volume 上的 **Delete Volume** 选项。
- 使用 `docker volume rm` 命令：

```console
docker volume rm postgres_data
```
- 使用 `docker volume prune` 命令删除所有未使用的 volumes：

```console
docker volume prune
```

## 更多资源

以下资源将帮助你进一步学习 volumes：

- [Manage data in Docker](/engine/storage)
- [Volumes](/engine/storage/volumes)
- [Volume mounts](/engine/containers/run/#volume-mounts)

## 下一步

现在你已经学习了持久化容器数据，接下来该学习如何与容器共享本地文件了。

[Sharing local files with containers（与容器共享本地文件）](/get-started/docker-concepts/running-containers/persisting-container-data/sharing-local-files)