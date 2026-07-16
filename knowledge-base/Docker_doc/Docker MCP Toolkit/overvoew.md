# Docker MCP Toolkit 快速入门

Docker MCP Toolkit 让您能够轻松地在 profile 中设置、管理和运行容器化的 Model Context Protocol (MCP) 服务器，并将它们连接到 AI 代理。它提供安全的默认设置，并支持不断增长的基于 LLM 的客户端生态系统。本页将向您展示如何快速上手 Docker MCP Toolkit。

## 准备工作

在开始之前，请确保满足以下使用 Docker MCP Toolkit 的前提条件。

1. 下载并安装最新版本的 Docker Desktop。
2. 打开 Docker Desktop 设置，选择 **Beta features**。
3. 选择 **Enable Docker MCP Toolkit**。
4. 点击 **Apply**。

Docker Desktop 中的 **Learning center** 提供了演练和资源，帮助您开始使用 Docker 产品和功能。在 **MCP Toolkit** 页面上，**Get started** 演练将指导您完成安装 MCP server、连接 client 以及测试配置的整个过程。

或者，您也可以按照本页中的分步说明操作：

- [创建 profile](#创建-profile) - 用于组织服务器的工作区
- [向 profile 中添加 MCP 服务器](#添加-mcp-服务器) - 从目录中选择工具
- [连接客户端](#连接客户端)  - 将 AI 应用程序链接到您的 profile
- [验证连接](#验证连接) - 测试一切是否正常工作

配置完成后，您的 AI 应用程序可以使用 profile 中的所有服务器。

> [!TIP]
> 更喜欢在终端中操作？请参阅 [Use MCP Toolkit from the CLI](/ai/mcp-catalog-and-toolkit/get-started/cli/)，了解如何使用 `docker mcp` 命令。

## 创建 profile

Profiles 将您的 MCP 服务器组织成集合。为您的工作创建一个 profile：

> [!NOTE]
> 如果您是从旧版本的 MCP Toolkit 升级，您现有的服务器配置已经位于一个 `default` profile 中。您可以继续使用 default profile，也可以为不同的项目创建新的 profiles。

1. 在 Docker Desktop 中，选择 **MCP Toolkit**，然后选择 **Profiles** 选项卡。
2. 点击 **Create profile**。
3. 输入 profile 的名称（例如，“Frontend development”）。
4. 可选：现在或稍后添加 servers 和 clients。
5. 点击 **Create**。

您的新 profile 将出现在 profiles 列表中。

## 添加 MCP 服务器

1. 在 Docker Desktop 中，选择 **MCP Toolkit**，然后选择 **Catalog** 选项卡。
2. 浏览目录，选择您想要添加的服务器。
3. 点击 **Add to** 按钮，选择是将服务器添加到现有 profile，还是创建新的 profile。

如果某个服务器需要配置，其名称旁边会出现 **Configuration Required** 标记。您必须先完成必要的配置，然后才能使用该服务器。

现在您已成功将 MCP servers 添加到您的 profile 中。接下来，连接 MCP client 以使用 profile 中的服务器。

## 连接客户端

要将 client 连接到 MCP Toolkit：

1. 在 Docker Desktop 中，选择 **MCP Toolkit**，然后选择 **Clients** 选项卡。
2. 在列表中找到您的应用程序。
3. 点击 **Connect** 以配置 client。

如果您的 client 不在列表中，您可以通过 `stdio` 手动连接 MCP Toolkit，方法是配置您的 client 以运行带有您 profile 的 gateway：

```plaintext
docker mcp gateway run --profile my_profile
```

例如，如果您的 client 使用 JSON 文件来配置 MCP servers，您可以添加如下条目：

```json {title="示例配置"}
{
  "servers": {
    "MCP_DOCKER": {
      "command": "docker",
      "args": ["mcp", "gateway", "run", "--profile", "my_profile"],
      "type": "stdio"
    }
  }
}
```

请查阅您所用应用程序的文档，了解如何手动设置 MCP servers。

## 验证连接

请参考相关章节以验证您的配置是否正常工作：

- [Claude Code](#claude-code)
- [Claude Desktop](#claude-desktop)
- [OpenAI Codex](#codex)
- [Continue](#continue)
- [Cursor](#cursor)
- [Gemini](#gemini)
- [Goose](#goose)
- [LM Studio](#lm-studio)
- [OpenCode](#opencode)
- [Sema4.ai](#sema4)
- [Visual Studio Code](#vscode)
- [Zed](#zed)

### Claude Code

如果您为特定项目配置了 MCP Toolkit，请导航到相应的项目目录。然后运行 `claude mcp list`。输出应显示 `MCP_DOCKER` 的状态为 “connected”：

```console
$ claude mcp list
Checking MCP server health...

MCP_DOCKER: docker mcp gateway run - ✓ Connected
```

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```console
$ claude "Use the GitHub MCP server to show me my open pull requests"
```

### Claude Desktop

重启 Claude Desktop，检查聊天输入框中的 **Search and tools** 菜单。您应该会看到 `MCP_DOCKER` 服务器已列出并启用：

![Claude Desktop](/ai/mcp-catalog-and-toolkit/get-started/images/claude-desktop.avif)

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```plaintext
Use the GitHub MCP server to show me my open pull requests
```

### Codex

运行 `codex mcp list` 查看活跃的 MCP servers 及其状态。`MCP_DOCKER` 服务器应出现在列表中，状态为 “enabled”：

```console
$ codex mcp list
Name        Command  Args             Env  Cwd  Status   Auth
MCP_DOCKER  docker   mcp gateway run  -    -    enabled  Unsupported
```

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```console
$ codex "Use the GitHub MCP server to show me my open pull requests"
```

### Continue

运行 `cn` 启动 Continue 终端界面。使用 `/mcp` 命令查看活跃的 MCP servers 及其状态。`MCP_DOCKER` 服务器应出现在列表中，状态为 “connected”：

```plaintext
   MCP Servers

   ➤ 🟢 MCP_DOCKER (🔧75 📝3)
     🔄 Restart all servers
     ⏹️ Stop all servers
     🔍 Explore MCP Servers
     Back

   ↑/↓ to navigate, Enter to select, Esc to go back
```

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```console
$ cn "Use the GitHub MCP server to show me my open pull requests"
```

### Cursor

打开 Cursor。如果您为特定项目配置了 MCP Toolkit，请打开相应的项目目录。然后导航到 **Cursor Settings > Tools & MCP**。您应该在 **Installed MCP Servers** 下看到 `MCP_DOCKER`：

![Cursor](/ai/mcp-catalog-and-toolkit/get-started/images/cursor.avif)

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```plaintext
Use the GitHub MCP server to show me my open pull requests
```

### Gemini

运行 `gemini mcp list` 查看活跃的 MCP servers 及其状态。`MCP_DOCKER` 应出现在列表中，状态为 “connected”。

```console
$ gemini mcp list
Configured MCP servers:

✓ MCP_DOCKER: docker mcp gateway run (stdio) - Connected
```

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```console
$ gemini "Use the GitHub MCP server to show me my open pull requests"
```

### Goose

**桌面应用**

打开 Goose 桌面应用程序，在侧边栏中选择 **Extensions**。在 **Enabled Extensions** 下，您应该会看到一个名为 `Mcpdocker` 的扩展：

![Goose 桌面应用](/ai/mcp-catalog-and-toolkit/get-started/images/goose.avif)

**CLI**

运行 `goose info -v`，在 extensions 下查找名为 `mcpdocker` 的条目。状态应显示 `enabled: true`：

```console
$ goose info -v
…
    mcpdocker:
      args:
      - mcp
      - gateway
      - run
      available_tools: []
      bundled: null
      cmd: docker
      description: The Docker MCP Toolkit allows for easy configuration and consumption of MCP servers from the Docker MCP Catalog
      enabled: true
      env_keys: []
      envs: {}
      name: mcpdocker
      timeout: 300
      type: stdio
```

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```plaintext
Use the GitHub MCP server to show me my open pull requests
```

### LM Studio

重启 LM Studio 并开始一个新的聊天。打开 integrations 菜单，查找名为 `mcp/mcp-docker` 的条目。使用开关启用该服务器：

![LM Studio](/ai/mcp-catalog-and-toolkit/get-started/images/lm-studio.avif)

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```plaintext
Use the GitHub MCP server to show me my open pull requests
```

### OpenCode

OpenCode 的配置文件（默认位于 `~/.config/opencode/opencode.json`）包含了 MCP Toolkit 的设置：

```json
{
  "mcp": {
    "MCP_DOCKER": {
      "type": "local",
      "command": ["docker", "mcp", "gateway", "run"],
      "enabled": true
    }
  },
  "$schema": "https://opencode.ai/config.json"
}
```

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```console
$ opencode "Use the GitHub MCP server to show me my open pull requests"
```

### Sema4.ai Studio {#sema4}

在 Sema4.ai Studio 中，选择侧边栏的 **Actions**，然后选择 **MCP Servers** 选项卡。您应该在列表中看到 Docker MCP Toolkit：

![Sema4.ai Studio 中的 Docker MCP Toolkit](/ai/mcp-catalog-and-toolkit/images/sema4-mcp-list.avif)

要在 Sema4.ai 中使用 MCP Toolkit，请将其添加为 agent action。找到要连接到 MCP Toolkit 的 agent，打开 agent 编辑器。选择 **Add Action**，在列表中启用 Docker MCP Toolkit，然后保存您的 agent：

![在 Sema4.ai Studio 中编辑 agent](/ai/mcp-catalog-and-toolkit/get-started/images/sema4-edit-agent.avif)

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```plaintext
Use the GitHub MCP server to show me my open pull requests
```

### Visual Studio Code {#vscode}

打开 Visual Studio Code。如果您为特定项目配置了 MCP Toolkit，请打开相应的项目目录。然后打开 **Extensions** 窗格。您应该在已安装的 MCP servers 下看到 `MCP_DOCKER` 服务器。

![Visual Studio Code 中已安装的 MCP_DOCKER](/ai/mcp-catalog-and-toolkit/get-started/images/vscode-extensions.avif)

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```plaintext
Use the GitHub MCP server to show me my open pull requests
```

### Zed

启动 Zed 并打开 agent settings：

![从命令面板打开 Zed agent 设置](/ai/mcp-catalog-and-toolkit/get-started/images/zed-cmd-palette.avif)

确保 `MCP_DOCKER` 在 MCP Servers 部分中列出并已启用：

![Zed agent 设置中的 MCP_DOCKER](/ai/mcp-catalog-and-toolkit/get-started/images/zed-agent-settings.avif)

通过提交一个调用您已安装的某个 MCP server 的提示来测试连接：

```plaintext
Use the GitHub MCP server to show me my open pull requests
```

## 延伸阅读

- [MCP Profiles](/ai/mcp-catalog-and-toolkit/profiles/)
- [MCP Toolkit](/ai/mcp-catalog-and-toolkit/toolkit/)
- [MCP Catalog](/ai/mcp-catalog-and-toolkit/catalog/)
- [MCP Gateway](/ai/mcp-catalog-and-toolkit/mcp-gateway/)