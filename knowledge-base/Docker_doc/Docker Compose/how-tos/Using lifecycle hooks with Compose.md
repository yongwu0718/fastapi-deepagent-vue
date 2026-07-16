# 使用 Compose 的生命周期钩子（lifecycle hooks）

## 服务的生命周期钩子（Services lifecycle hooks）

当 Docker Compose 运行一个 container 时，它会使用两个元素 —— [ENTRYPOINT 和 COMMAND](/engine/containers/run/#default-command-and-options) —— 来管理 container 启动和停止时发生的事情。

然而，有时使用生命周期钩子（lifecycle hooks）来分别处理这些任务会更简单 —— 这些钩子是在 container 启动后或即将停止前立即运行的命令。

生命周期钩子特别有用，因为它们可以拥有特殊权限（例如以 root 用户身份运行），即使 container 本身出于安全考虑以较低权限运行。这意味着某些需要更高权限的任务可以在不损害 container 整体安全性的前提下完成。

### Post-start hooks（启动后钩子）

Post-start hooks 是在 container 启动后运行的命令，但它们的执行时间没有固定的保证。钩子的执行时机在 container 的 `entrypoint` 执行期间是无法保证的。

由于钩子和 container 的 entrypoint 之间没有顺序保证，**post-start hooks 最适合用于那些不需要在应用开始运行之前完成的任务**，例如向外部系统注册 container。

在以下示例中，container 启动后，一个 root 级别的钩子将该服务（service）注册到内部服务注册表中。应用不依赖于注册在其开始处理请求之前完成。

```yaml
services:
  app:
    image: backend
    user: 1001
    post_start:
      - command: /opt/scripts/register-service.sh
        user: root
```

### Pre-stop hooks（停止前钩子）

Pre-stop hooks 是在 container 被特定命令（如 `docker compose down` 或手动按 `Ctrl+C` 停止）停止之前运行的命令。如果 container 自行停止或被突然杀死，这些钩子不会运行。

由于 pre-stop hook 在停止信号发送到 container 之前运行，**pre-stop hooks 最适合用于那些必须在应用仍在完全运行时完成的操作**。

在以下示例中，钩子在 container 收到停止信号之前备份一个数据文件。

```yaml
services:
  app:
    image: backend
    volumes:
      - data:/data
    pre_stop:
      - command: cp /data/app.db /data/app.db.bak

volumes:
  data: {} # a Docker volume is created with root ownership
```

## 参考信息

- [`post_start`](/reference/compose-file/services/#post_start)
- [`pre_stop`](/reference/compose-file/services/#pre_stop)