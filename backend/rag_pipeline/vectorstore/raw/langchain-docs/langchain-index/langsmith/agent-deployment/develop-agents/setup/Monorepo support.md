# Monorepo 支持

LangSmith 支持从 monorepo 结构中部署 agent，您的 agent 代码可能依赖于仓库中其他位置的共享包。本指南介绍如何组织 monorepo 以及如何配置 `langgraph.json` 文件以使用共享依赖项。

## 仓库结构

完整的可用示例请参考：

* Python monorepo 示例

```plaintext
my-monorepo/
├── shared-utils/           # 共享 Python 包
│   ├── __init__.py
│   ├── common.py
│   └── pyproject.toml      # 或 setup.py
├── agents/
│   └── customer-support/   # Agent 目录
│       ├── agent/
│       │   ├── __init__.py
│       │   └── graph.py
│       ├── langgraph.json  # Agent 目录中的配置文件
│       ├── .env
│       └── pyproject.toml  # Agent 依赖
└── other-service/
    └── ...
```
## LangGraph.json 配置

将 `langgraph.json` 文件放在 agent 的目录中（而不是 monorepo 根目录）。确保该文件遵循所需的结构：

```json
{
  "dependencies": [
    ".",                    # 当前 agent 包
    "../../shared-utils"    # 共享包的相对路径
  ],
  "graphs": {
    "customer_support": "./agent/graph.py:graph"
  },
  "env": ".env"
}
```

Python 实现通过以下方式自动处理父目录中的包：

* 检测以 `"."` 开头的相对路径。
* 根据需要将父目录添加到 Docker 构建上下文中。
* 同时支持真正的包（带有 `pyproject.toml`/`setup.py`）和简单的 Python 模块。

## 构建应用

运行 `langgraph build`：

```bash
cd agents/customer-support
langgraph build -t my-customer-support-agent
```

Python 构建过程：

1. 自动检测相对依赖路径。
2. 将共享包复制到 Docker 构建上下文中。
3. 按正确顺序安装所有依赖项。
4. 不需要特殊标志或命令。

## 提示与最佳实践

1. **将 agent 配置保留在 agent 目录中**：将 `langgraph.json` 文件放在具体的 agent 目录中，而不是 monorepo 根目录。这样您可以在同一个 monorepo 中支持多个 agent，而无需将它们全部部署在同一个 LangSmith 部署中。

2. **对 Python 使用相对路径**：对于 Python monorepo，在 `dependencies` 数组中使用类似 `"../../shared-package"` 的相对路径。

3. **先在本地测试**：在部署之前始终在本地测试构建，以确保所有依赖项都能正确解析。

4. **环境变量**：将环境文件（`.env`）放在您的 agent 目录中，用于环境特定的配置。
