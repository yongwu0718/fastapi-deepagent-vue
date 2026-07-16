# 如何使用 pyproject.toml 设置应用

一个应用必须通过配置文件进行配置，才能部署到 LangSmith（或自托管）。本操作指南介绍了使用 `pyproject.toml` 定义包依赖来设置部署应用的基本步骤。

本示例基于这个仓库，该仓库使用了 LangGraph 框架。

最终的仓库结构大致如下：

```bash
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

LangSmith Deployment 支持部署 LangGraph **graph**。但是，**graph** 中某个 **node** 的实现可以包含任意代码。这意味着任何框架都可以实现在一个 **node** 内部，并部署到 LangSmith Deployment 上。这样，您可以在不额外使用 LangGraph OSS API 的情况下实现核心应用逻辑，同时仍然利用 LangSmith 进行部署、扩缩和可观测性。更多详情请参阅“将任意框架与 LangSmith Deployment 结合使用”。

您也可以使用以下方式设置：

* `requirements.txt`：如需依赖管理，请查看这篇关于为 LangSmith 使用 `requirements.txt` 的操作指南。
* monorepo：如需部署位于 monorepo 内部的 graph，请参考此仓库中的示例。

在每个步骤之后，都会提供一个示例文件目录，以演示代码的组织方式。

## 指定依赖项

依赖项可以选择性地在以下文件之一中指定：`pyproject.toml`、`setup.py` 或 `requirements.txt`。如果这些文件都没有创建，那么可以在配置文件中稍后指定依赖项。

以下依赖项将包含在镜像中，您也可以在代码中使用它们，只要版本范围兼容即可：

```
langgraph>=0.4.10,<2
langgraph-sdk>=0.3.5
langgraph-checkpoint>=3.0.1,<5
langchain-core>=0.3.66
langsmith>=0.7.31
orjson>=3.9.7
httpx>=0.25.0
tenacity>=8.0.0
uvicorn>=0.26.0
sse-starlette>=2.1.3,<3.4.0
uvloop>=0.18.0
httptools>=0.5.0
jsonschema-rs>=0.20.0
structlog>=24.1.0
cloudpickle>=3.0.0
truststore>=0.1
protobuf>=6.32.1,<7.0.0
grpcio>=1.80.0,<1.81.0
grpcio-tools>=1.80.0,<1.81.0
grpcio-health-checking>=1.80.0,<1.81.0
opentelemetry-api>=0.0.1
opentelemetry-sdk>=0.0.1
opentelemetry-exporter-otlp-proto-http>=0.0.1
```

`pyproject.toml` 文件示例：

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-agent"
version = "0.0.1"
description = "An excellent agent build for LangSmith."
authors = [
    {name = "Assistant", email = "1223+assistant@users.noreply.github.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "langgraph>=0.6.0",
    "langchain-fireworks>=0.1.3"
]

[tool.hatch.build.targets.wheel]
packages = ["my_agent"]
```

示例文件目录：

```bash
my-app/
└── pyproject.toml   # graph 所需的 Python 包
```

## 指定环境变量

环境变量可以选择性地在一个文件（例如 `.env`）中指定。请参阅环境变量参考文档，为部署配置更多变量。

`.env` 文件示例：

```
MY_ENV_VAR_1=foo
MY_ENV_VAR_2=bar
FIREWORKS_API_KEY=key
```

示例文件目录：

```bash
my-app/
├── .env # 包含环境变量的文件
└── pyproject.toml
```

默认情况下，LangSmith 遵循 `uv`/`pip` 的行为：**不**安装预发布版本，除非明确允许。如果您想使用预发布版本，有以下选项：

  * 使用 `pyproject.toml`：在 `[tool.uv]` 部分添加 `allow-prereleases = true`。
  * 使用 `requirements.txt` 或 `setup.py`：您必须显式指定每一个预发布依赖项，包括传递依赖。例如，如果您声明 `a==0.0.1a1`，并且 `a` 依赖 `b==0.0.1a1`，那么您也必须显式地将 `b==0.0.1a1` 包含在依赖项中。

## 定义 Graphs

实现您的 graph。graph 可以在单个文件或多个文件中定义。记下要包含在应用中的每个 `CompiledStateGraph` 的变量名。这些变量名将在后续创建配置文件时使用。

`agent.py` 文件示例，演示了如何从您定义的其他模块导入（此处未显示模块的代码，请参阅此仓库查看其实现）：

```python
# my_agent/agent.py
from typing import Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END, START
from my_agent.utils.nodes import call_model, should_continue, tool_node # import nodes
from my_agent.utils.state import AgentState # import state

# Define the runtime context
class GraphContext(TypedDict):
    model_name: Literal["anthropic", "openai"]

workflow = StateGraph(AgentState, context_schema=GraphContext)
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END,
    },
)
workflow.add_edge("action", "agent")

graph = workflow.compile()
```

示例文件目录：

```bash
my-app/
├── my_agent # 所有项目代码都在这里
│   ├── utils # graph 用到的工具
│   │   ├── __init__.py
│   │   ├── tools.py # graph 用到的工具
│   │   ├── nodes.py # graph 的节点函数
│   │   └── state.py # graph 的状态定义
│   ├── __init__.py
│   └── agent.py # 构建 graph 的代码
├── .env
└── pyproject.toml
```

## 创建配置文件

创建一个名为 `langgraph.json` 的配置文件。有关配置文件中 JSON 对象每个键的详细说明，请参阅配置文件参考。

`langgraph.json` 文件示例：

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./my_agent/agent.py:graph"
  },
  "env": ".env"
}
```

请注意，`CompiledGraph` 的变量名出现在顶层 `graphs` 键中每个子键值的末尾（即 `:` 之后）。

**配置文件位置**
  配置文件必须放在与包含已编译 graph 及相关依赖项的 Python 文件相同层级或更高层级的目录中。

示例文件目录：

```bash
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

## 下一步

在您设置好项目并将其放入 GitHub 仓库后，就可以部署您的应用了。