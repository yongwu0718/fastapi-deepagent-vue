# Studio 中的可观测性

LangSmith Studio 提供了超越执行本身的工具，用于检查、调试和改进您的应用。通过使用 traces、datasets 和 prompts，您可以详细了解应用的行为、测量其性能并优化其输出：

* 迭代 prompts：直接在 graph 节点内或使用 Playground 修改 prompts。
* 在 dataset 上运行实验：在 LangSmith dataset 上执行您的 assistant，以评分和比较结果。
* 调试 LangSmith traces：将跟踪的 runs 导入 Studio，并可选择将其克隆到您的本地代理中。
* 将节点添加到 dataset：将 thread 历史的部分内容转换为 dataset 示例，用于评估或进一步分析。

## 迭代 prompts

Studio 支持以下修改 graph 中 prompts 的方法：

* 直接节点编辑
* Playground 界面

### 直接节点编辑

Studio 允许您直接从 graph 界面编辑单个节点中使用的 prompts。

### Graph 配置

使用 `langgraph_nodes` 和 `langgraph_type` 键定义您的配置，以指定 prompt 字段及其关联的节点。

#### `langgraph_nodes`

* **描述**：指定配置字段与 graph 中的哪些节点关联。
* **值类型**：字符串数组，每个字符串是 graph 中一个节点的名称。
* **使用上下文**：包含在 Pydantic 模型的 `json_schema_extra` 字典中，或 dataclasses 的 `metadata["json_schema_extra"]` 字典中。
* **示例**：
```python
system_prompt: str = Field(
  default="You are a helpful AI assistant.",
  json_schema_extra={"langgraph_nodes": ["call_model", "other_node"]},
)
```

#### `langgraph_type`

* **描述**：指定配置字段的类型，决定它在 UI 中的处理方式。
* **值类型**：字符串
* **支持的值**：
  * `"prompt"`：表示该字段包含 prompt 文本，应在 UI 中特殊处理。
* **使用上下文**：包含在 Pydantic 模型的 `json_schema_extra` 字典中，或 dataclasses 的 `metadata["json_schema_extra"]` 字典中。
* **示例**：
```python
system_prompt: str = Field(
    default="You are a helpful AI assistant.",
    json_schema_extra={
        "langgraph_nodes": ["call_model"],
        "langgraph_type": "prompt",
    },
)
```
**示例：**
```python
## 使用 Pydantic
from pydantic import BaseModel, Field
from typing import Annotated, Literal

class Configuration(BaseModel):
    """The configuration for the agent."""

    system_prompt: str = Field(
        default="You are a helpful AI assistant.",
        description="The system prompt to use for the agent's interactions. "
        "This prompt sets the context and behavior for the agent.",
        json_schema_extra={
            "langgraph_nodes": ["call_model"],
            "langgraph_type": "prompt",
        },
    )

    model: Annotated[
        Literal[
            "anthropic/claude-sonnet-4-6",
            "anthropic/claude-haiku-4-5-20251001",
            "openai/o1",
            "openai/gpt-5.4-mini",
            "openai/o1-mini",
            "openai/o3-mini",
        ],
        {"__template_metadata__": {"kind": "llm"}},
    ] = Field(
        default="openai/gpt-5.4-mini",
        description="The name of the language model to use for the agent's main interactions. "
        "Should be in the form: provider/model-name.",
        json_schema_extra={"langgraph_nodes": ["call_model"]},
    )

## 使用 Dataclasses
from dataclasses import dataclass, field

@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    system_prompt: str = field(
        default="You are a helpful AI assistant.",
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent.",
            "json_schema_extra": {"langgraph_nodes": ["call_model"]},
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="anthropic/claude-3-5-sonnet-20240620",
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Should be in the form: provider/model-name.",
            "json_schema_extra": {"langgraph_nodes": ["call_model"]},
        },
    )

```

#### 在 UI 中编辑 prompts

1. 找到关联了配置字段的节点上的齿轮图标。
2. 点击打开配置模态框。
3. 编辑值。
4. 保存以更新当前 assistant 版本或创建一个新版本。

### Playground

Playground 界面允许测试单个 LLM 调用，而无需运行整个 graph：

1. 选择一个 thread。
2. 点击节点上的 **View LLM Runs**。这会列出节点内进行的所有 LLM 调用（如果有）。
3. 选择一个 LLM run 以在 Playground 中打开。
4. 修改 prompts 并测试不同的模型和工具设置。
5. 将更新后的 prompts 复制回您的 graph。

## 在 dataset 上运行实验

Studio 允许您通过在预定义的 LangSmith dataset 上执行 assistant 来运行评估。这使得您可以跨多种输入测试性能，将输出与参考答案进行比较，并使用配置的 evaluators 对结果进行评分。

本指南向您展示如何直接从 Studio 运行完整的端到端实验。

### 前提条件

在运行实验之前，请确保您具备以下条件：

* **一个 LangSmith dataset**：您的 dataset 应包含您要测试的 inputs，并可选择包含用于比较的参考 outputs。inputs 的 schema 必须与 assistant 所需的 input schema 匹配。有关 schemas 的更多信息，请参阅 graph API schema 文档。有关创建 datasets 的更多信息，请参阅如何管理 Datasets。
* **（可选）Evaluators**：您可以在 LangSmith 中为 dataset 附加 evaluators（例如 LLM-as-a-Judge、启发式或自定义函数）。这些 evaluators 将在 graph 处理完所有 inputs 后自动运行。
* **一个正在运行的应用**：实验可以针对以下环境运行：
  * 部署在 LangSmith 上的应用。
  * 通过 langgraph-cli 启动的本地运行应用。

Studio 实验遵循与其他实验相同的数据保留规则。默认情况下，traces 具有基础层保留期（14 天）。但是，如果向 traces 添加了反馈，traces 将自动升级到扩展层保留期（400 天）。可以通过以下两种方式之一添加反馈：

  * dataset 配置了 evaluators。
  * 手动向 trace 添加反馈。

  这种自动升级会增加保留期限和 trace 的成本。更多详情请参阅数据保留自动升级。

### 实验设置

1. 启动实验。点击 Studio 页面右上角的 **Run experiment** 按钮。
2. 选择您的 dataset。在出现的模态框中，选择要用于实验的 dataset（或特定的 dataset split），然后点击 **Start**。
3. 监控进度。dataset 中的所有 inputs 现在都将针对活动的 assistant 运行。通过右上角的徽章监控实验进度。
4. 实验在后台运行时，您可以继续在 Studio 中工作。随时点击箭头图标按钮导航到 LangSmith 并查看详细的实验结果。

## 调试 LangSmith traces

本指南说明如何在 Studio 中打开 LangSmith traces 以进行交互式调查和调试。

### 打开已部署的 threads

1. 打开 LangSmith trace，选择 root run。
2. 点击 **Run in Studio**。

这将打开 Studio，连接到关联的部署，并选中 trace 的父 thread。

### 使用远程 traces 测试本地代理

本节说明如何针对 LangSmith 的远程 traces 测试本地代理。这使得您可以将生产 traces 作为本地测试的输入，从而在开发环境中调试和验证代理的修改。

#### 前提条件

* 一个 LangSmith 跟踪的 thread
* 一个本地运行的代理

**本地代理要求**

  * langgraph>=0.3.18
  * langgraph-api>=0.0.32
  * 包含远程 trace 中存在的相同节点集

#### 克隆 thread

1. 打开 LangSmith trace，选择 root run。
2. 点击 **Run in Studio** 旁边的下拉箭头。
3. 输入本地代理的 URL。
4. 选择 **Clone thread locally**。
5. 如果存在多个 graphs，请选择目标 graph。

将在您的本地代理中创建一个新的 thread，该 thread 的历史记录从远程 thread 推断并复制而来，并且您将导航到本地运行应用的 Studio。

## 将节点添加到 dataset

从 thread 日志中的节点向 LangSmith datasets 添加示例。这对于评估代理的单个步骤非常有用。

1. 选择一个 thread。
2. 点击 **Add to Dataset**。
3. 选择要将其 input/output 添加到 dataset 的节点。
4. 对于每个选定的节点，选择要创建示例的目标 dataset。默认情况下，会为特定的 assistant 和节点选择一个 dataset。如果该 dataset 尚不存在，它将被创建。
5. 在将其添加到 dataset 之前，根据需要编辑示例的 input/output。
6. 选择页面底部的 **Add to dataset**，将所有选定的节点添加到它们各自的 datasets 中。

更多详情请参阅如何评估应用的中间步骤。