# Studio 故障排除

## Safari 连接问题

Safari 阻止 localhost 上的纯 HTTP 流量。当使用 `langgraph dev` 运行 Studio 时，您可能会看到“Failed to load assistants”错误。

### 解决方案 1：使用 Cloudflare Tunnel

```shell
    pip install -U langgraph-cli>=0.2.6
    langgraph dev --tunnel
    ```

```shell
    # 需要 @langchain/langgraph-cli>=0.0.26
    npx @langchain/langgraph-cli dev --tunnel
    ```

该命令输出一个隧道 URL。要连接 Studio：

1. 复制隧道 URL（例如 `https://hamilton-praise-heart-costumes.trycloudflare.com`）
2. 打开 Studio：`https://smith.langchain.com/studio/`
3. 点击 **Connect to a local server**
4. 粘贴隧道 URL 并将其添加到 **Allowed Origins**
5. 点击 **Connect**

出于安全考虑，此手动步骤是必需的——Studio 在连接到外部 URL 之前需要明确的用户确认。

Cloudflare 隧道可能不稳定，可能会间歇性断开。

### 解决方案 2：使用 Chromium 浏览器

Chrome 和其他 Chromium 浏览器允许 localhost 上的 HTTP。使用 `langgraph dev` 无需额外配置。

## Chrome 连接问题

从 Chrome 142 版本开始，当尝试通过 `langgraph dev` 将 LangSmith Studio 连接到本地开发服务器时，您可能会遇到“Failed to initialize Studio”错误，并显示“TypeError: Failed to fetch”。即使 API 服务器在 `http://127.0.0.1:2024/docs` 成功加载，也会发生这种情况。

**根本原因：** Chrome 142 完全强制执行私有网络访问规范，没有回退机制，默认阻止 HTTPS 站点（如 `https://smith.langchain.com`）访问 HTTP localhost 服务器。

### 症状

* 运行 `langgraph dev` 成功启动服务器。
* 导航到 `http://127.0.0.1:2024/docs` 正确显示 API 文档。
* LangSmith Studio 在 `https://smith.langchain.com` 显示：“Failed to initialize Studio - Please verify if the API server is running or accessible from the browser. TypeError: Failed to fetch”。
* 浏览器控制台显示类似错误：`Permission was denied for this request to access the 'unknown' address space`。

### 解决方案：在 Chrome 中允许本地网络访问

1. 在 Chrome 中打开 LangSmith Studio `https://smith.langchain.com`。
2. 点击地址栏左侧的**锁图标**（或站点信息图标）。
3. 在下拉菜单中查找 **“Local network access”** 选项。
4. 将该设置从 **“Ask (default)”** 或 **“Block”** 更改为 **“Allow”**。
5. 重新加载页面。

Studio 现在应该可以成功连接到您的本地开发服务器。

### 其他故障排除

**检查浏览器扩展冲突**

浏览器扩展（尤其是 Ollama Chrome 扩展或 AI 模型扩展）可能会干扰 localhost 连接：

1. 暂时禁用所有浏览器扩展。
2. 重启 Chrome。
3. 再次尝试连接到 Studio。
4. 如果成功，逐一重新启用扩展以找出问题所在。

**验证依赖项是否最新**

```shell
pip install -U "langgraph-cli[inmem]"
```

**清除浏览器缓存和站点数据**

1. 在 Chrome 中，转到 **Settings** > **Privacy and Security** > **Site Settings**。
2. 在列表中找到 `https://smith.langchain.com`。
3. 点击 **Clear data**。
4. 重启 Chrome 并重试。

## Brave 连接问题

当启用 Brave Shields 时，Brave 会阻止 localhost 上的纯 HTTP 流量。当使用 `langgraph dev` 运行 Studio 时，您可能会看到“Failed to load assistants”错误。

### 解决方案 1：禁用 Brave Shields

使用 URL 栏中的 Brave 图标为 LangSmith 禁用 Brave Shields。

### 解决方案 2：使用 Cloudflare Tunnel

```shell
    pip install -U langgraph-cli>=0.2.6
    langgraph dev --tunnel
    ```

```shell
    # 需要 @langchain/langgraph-cli>=0.0.26
    npx @langchain/langgraph-cli dev --tunnel
    ```

该命令输出一个隧道 URL。要连接 Studio：

1. 复制隧道 URL（例如 `https://hamilton-praise-heart-costumes.trycloudflare.com`）
2. 打开 Studio：`https://smith.langchain.com/studio/`
3. 点击 **Connect to a local server**
4. 粘贴隧道 URL 并将其添加到 **Allowed Origins**
5. 点击 **Connect**

出于安全考虑，此手动步骤是必需的——Studio 在连接到外部 URL 之前需要明确的用户确认。

## Graph 边的问题

未定义的条件边可能会在您的 graph 中显示意外的连接。这是因为在没有正确定义的情况下，Studio 假定条件边可以访问所有其他节点。要解决此问题，请使用以下方法之一明确定义路由路径：

### 解决方案 1：路径映射

定义路由器输出与目标节点之间的映射：

```python
    graph.add_conditional_edges("node_a", routing_function, {True: "node_b", False: "node_c"})
    ```

```ts
    graph.addConditionalEdges("node_a", routingFunction, { true: "node_b", false: "node_c" });
    ```

### 解决方案 2：路由器类型定义

使用 Python 的 `Literal` 类型指定可能的路由目的地：

```python
def routing_function(state: GraphState) -> Literal["node_b","node_c"]:
    if state['some_condition'] == True:
        return "node_b"
    else:
        return "node_c"
```

## Studio 中的实验故障排除

### **Run experiment** 按钮被禁用

请检查以下项：

* **已部署的应用**：如果您的应用部署在 LangSmith 上，您可能需要创建一个新的修订版才能启用此功能。
* **本地开发服务器**：如果您在本地运行应用，请确保已升级到最新版本的 `langgraph-cli`（`pip install -U langgraph-cli`）。此外，通过在项目的 `.env` 文件中设置 `LANGSMITH_API_KEY` 来确保启用了追踪。

### 评估器结果缺失

当您运行实验时，任何附加的评估器都会被安排到队列中执行。如果您没有立即看到结果，很可能它们仍在等待中。