# 开始使用 Studio

LangSmith Deployment UI 中的 Studio 支持连接到两种类型的 graphs：

* 部署在云或自托管环境中的 graphs。
* 使用 Agent Server 本地运行的 graphs。

## 已部署的 graphs

在 LangSmith UI 中，通过 **Deployments** 导航进入 Studio。

对于已部署的应用，您可以作为该部署的一部分访问 Studio。为此，请在 UI 中导航到该部署，然后选择 **Studio**。

这将加载连接到您实时部署的 Studio，允许您在该部署中创建、读取和更新 threads、assistants 和 memory。

## 本地开发服务器

### 前提条件

要使用 Studio 在本地测试您的应用：

* 请先按照本地应用快速入门操作。
* 如果您不希望数据被追踪到 LangSmith，请在应用的 `.env` 文件中设置 `LANGSMITH_TRACING=false`。禁用追踪后，不会有数据离开您的本地服务器。

### 设置

1. 安装 LangGraph CLI：

```bash
uv add "langgraph-cli[inmem]"
langgraph dev
```

**浏览器兼容性**
  Safari 会阻止连接到 Studio 的 `localhost`。要解决此问题，请使用 `--tunnel` 运行命令，通过安全隧道访问 Studio。您需要点击 Studio UI 中的 **Connect to a local server**，手动将隧道 URL 添加到允许的源中。具体步骤请参阅故障排除指南。

这将启动本地运行的 Agent Server，在内存中运行。服务器将以监视模式运行，监听代码更改并自动重启。请阅读此参考以了解启动 API 服务器的所有选项。

您将看到以下日志：

```
> Ready!
>
> - API: http://localhost:2024
>
> - Docs: http://localhost:2024/docs
>
> - LangSmith Studio Web UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```
运行后，您将自动被引导到 Studio。

2. 对于正在运行的服务器，通过以下方式之一访问调试器：

a. 直接导航到以下 URL：`https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`。
b. 在 UI 中导航到 **Deployments**，点击某个部署上的 **Studio** 按钮，输入 `http://127.0.0.1:2024` 并点击 **Connect**。

如果您的服务器运行在不同的主机或端口上，请更新 `baseUrl` 以匹配。

### （可选）附加调试器

要进行带断点和变量检查的单步调试，请运行以下命令：

```bash
# 安装 debugpy 包
uv add debugpy
# 启用调试启动服务器
langgraph dev --debug-port 5678
```

然后附加您偏好的调试器：

将此配置添加到 `launch.json`：

```json
{
  "name": "Attach to LangGraph",
  "type": "debugpy",
  "request": "attach",
  "connect": {
    "host": "0.0.0.0",
    "port": 5678
  }
}
```
如果入门时遇到问题，请参阅故障排除指南。

## 后续步骤

有关如何运行 Studio 的更多信息，请参阅以下指南：

* 运行应用
* 管理 assistants
* 管理 threads
* 迭代 prompts
* 调试 LangSmith traces
* 将节点添加到 dataset