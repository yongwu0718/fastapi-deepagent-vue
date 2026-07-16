# 应用结构

要在 LangSmith 上部署，一个应用必须包含一个或多个 **graph**、一个配置文件（`langgraph.json`）、一个指定依赖项的文件，以及一个可选的用于指定环境变量的 `.env` 文件。

本页说明 LangSmith 应用的组织方式，以及如何提供部署所需的配置详情。

## 核心概念

使用 LangSmith 部署时，需要提供以下信息：

1. 一个配置文件（`langgraph.json`），用于指定应用的依赖项、**graph** 和环境变量。
2. 实现应用逻辑的 **graph**。
3. 指定运行应用所需依赖项的文件。
4. 应用运行所需的环境变量。

**框架无关**

LangSmith Deployment 支持部署 LangGraph **graph**。但是，**graph** 中某个 **node** 的实现可以包含任意代码。这意味着任何框架都可以实现在一个 **node** 内部，并部署到 LangSmith Deployment 上。这样，您可以在不额外使用 LangGraph OSS API 的情况下实现核心应用逻辑，同时仍然利用 LangSmith 进行部署、扩缩和可观测性。更多详情请参阅“将任意框架与 LangSmith Deployment 结合使用”。

## 文件结构

以下是 Python 和 JavaScript 应用目录结构的示例：

**Python pyproject.toml**
```plaintext
my-app/
├── my_agent # 所有项目代码都在这里
│   ├── utils # graph 用到的工具
│   │   ├── __init__.py
│   │   ├── tools.py # graph 用到的工具
│   │   ├── nodes.py # graph 的节点函数
│   │   └── state.py # graph 的状态定义
│   ├── __init__.py
│   └── agent.py # 构建 graph 的代码
├── .env # 环境变量
├── langgraph.json  # LangGraph 配置文件
└── pyproject.toml # 项目的依赖
```
应用的目录结构可能因编程语言和使用的包管理工具而有所不同。

## 配置文件

`langgraph.json` 文件是一个 JSON 文件，用于指定部署应用所需的依赖项、**graph**、环境变量以及其他设置。

关于 JSON 文件中所有支持的键的详细信息，请参考 LangGraph 配置文件参考。

LangGraph CLI 默认使用当前目录下的配置文件 `langgraph.json`。

### 示例

* 依赖项包括一个自定义本地包和 `langchain_openai` 包。
* 将从文件 `./your_package/your_file.py` 中加载一个名为 `agent` 的 **graph**。
* 环境变量从 `.env` 文件加载。

```json
{
"dependencies": [
    "langchain_openai",
    "./your_package"
],
"graphs": {
    "my_agent": "./your_package/your_file.py:agent"
},
"env": "./.env"
}
```

## 依赖项

一个应用可能依赖于其他的 Python 包或 JavaScript 库（取决于应用所使用的编程语言）。

通常需要指定以下信息来正确设置依赖项：

1. 目录中指定依赖项的文件（例如 `requirements.txt`、`pyproject.toml` 或 `package.json`）。
2. 配置文件中的 `dependencies` 键，用于指定运行应用所需的依赖项。
3. 任何额外的二进制文件或系统库可以使用 LangGraph 配置文件中的 `dockerfile_lines` 键指定。

## Graphs

使用配置文件中的 `graphs` 键来指定哪些 **graph** 将在部署的应用中可用。

您可以在配置文件中指定一个或多个 **graph**。每个 **graph** 由一个唯一名称和一个路径标识，路径指向 (1) 一个已编译的 **graph**，或者 (2) 一个定义 **graph** 的函数。

### 将任意框架与 LangSmith Deployment 结合使用

虽然 LangSmith Deployment 要求应用结构化为一个 LangGraph **graph**，但 **graph** 中各个 **node** 的内部可以包含任意代码。这意味着您可以在 **node** 内部使用任何框架或库，同时仍然受益于 LangSmith 的部署基础设施。

**graph** 结构充当部署接口，而您的核心应用逻辑可以使用最适合您需求的任何工具和框架。

使用 LangSmith 部署时需要：

1. **一个 LangGraph graph 结构**：使用 `StateGraph` 配合 `add_node` / `addNode` 和 `add_edge` / `addEdge` 定义 graph。
2. **包含任意逻辑的 node 函数**：您的 node 函数可以调用任何框架或库。
3. **一个已编译的 graph**：编译 graph 以创建可部署的应用。

以下示例演示了如何将您现有的应用逻辑包装在一个最小的 LangGraph 结构中：

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# 您现有的使用任意框架的应用逻辑
from app_logic import process_data
from app_logic import fetch_data

class State(TypedDict):
    input: str
    result: str

def my_app_node(state: State) -> State:
    """包含任意框架代码的节点。"""
    # 在这里使用任何框架或库
    raw_data = fetch_data(state["input"])
    processed = process_data(raw_data)
    return {"result": processed}

# 定义 graph 结构
graph = StateGraph(State)
graph.add_node("process", my_app_node)  # 添加包含您逻辑的节点
graph.add_edge(START, "process")        # 将 START 连接到您的节点
graph.add_edge("process", END)          # 将您的节点连接到 END

# 编译以供部署
app = graph.compile()
```

## 环境变量

如果您在本地处理已部署的 LangGraph 应用，可以在配置文件的 `env` 键中配置环境变量。

对于生产部署，通常需要在部署环境中配置环境变量。