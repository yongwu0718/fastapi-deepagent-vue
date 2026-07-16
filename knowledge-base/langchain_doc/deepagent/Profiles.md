# 配置文件

> 打包 Deep Agents 在选定模型时应用的每个提供商和每个模型的默认设置

**框架配置文件**允许你打包 Deep Agents 在选定给定提供商或特定模型时应用的配置：系统提示调整、工具描述覆盖、排除的工具或中间件、额外的中间件，以及通用子代理编辑。它们是在不更改 `create_deep_agent` 调用点的情况下，针对特定模型调整框架行为的主要方式。在 Python 中构建配置文件时使用 `HarnessProfile`；加载或保存 YAML/JSON 文件时使用 `HarnessProfileConfig`。Deep Agents 为 OpenAI 和 Anthropic (Claude) 模型提供了内置的框架配置文件。

**提供商配置文件**是针对*模型构建*关键字的较窄辅助 API，不影响框架。大多数调用者不需要它们；当你想将 `init_chat_model` 默认值、凭据检查或运行时派生的关键字作为你选择的提供商的默认值时（例如，在打包提供商集成时），可以使用它。

## 框架配置文件

`HarnessProfile` 描述了 `create_deep_agent` 在聊天模型构建完成后应用的提示组装、工具可见性、中间件和默认子代理调整：

```python
from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    register_harness_profile,
)

register_harness_profile(
    "openai:gpt-5.4",
    HarnessProfile(
        system_prompt_suffix="用不超过 100 个单词回复。",
        excluded_tools={"execute"},
        excluded_middleware={"SummarizationMiddleware"},
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
)
```

替换基础的 Deep Agents 系统提示（提示组装中的 `CUSTOM`）。

将文本附加到组装好的基础提示之后（提示组装中的 `SUFFIX`）；应用于主代理、声明式子代理和自动添加的通用子代理。

覆盖单个工具的描述，按键名为工具名。

从工具集中移除特定的框架级工具。按工具名称（字符串）匹配，作为注入后过滤器应用，因此它可以删除用户提供的工具和由框架中间件添加的工具。有关工作示例，请参阅“在没有默认文件系统工具的情况下运行”。

从栈中剥离特定的中间件类。接受中间件类或字符串名称。

将中间件附加到此配置文件应用的每个栈。

禁用、重命名或重新提示通用子代理。当此字段的 `system_prompt` 与 `base_system_prompt` 一起设置时，通用子代理特定的提示获胜——请参阅通用子代理提示。

调用者提供的 `system_prompt=` 始终位于组装提示的最前面，`system_prompt_suffix` 始终位于最后——无论选择哪个模型。相同的覆盖规则适用于子代理：每个子代理针对自己的模型重新运行配置文件解析。有关每种情况的完整细分（主代理、子代理和通用子代理），请参阅提示组装。

要在没有 `task` 工具的情况下运行代理，请参阅“在没有子代理的情况下运行”——设置 `general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)`，并通过 `subagents=` 不传递任何同步子代理。仅当至少存在一个同步子代理时，才会附加 `SubAgentMiddleware`（以及 `task` 工具），因此此配置可以干净地将其排除。异步子代理不受影响。

  在 `excluded_middleware` 中列出 `FilesystemMiddleware`、`SubAgentMiddleware` 或内部权限中间件会引发 `ValueError`——它们是必需的脚手架。要在不移除中间件的情况下隐藏它们的工具，请改用 `excluded_tools`——请参阅“在没有默认文件系统工具的情况下运行”。

`excluded_middleware` 中的条目接受两种形式：

* 一个中间件*类*（按确切类型匹配），或者一个与 `AgentMiddleware.name` 匹配的纯字符串。对于内置和公共别名（如 `"SummarizationMiddleware"`），请使用纯字符串。
* 一个 `module:Class` 导入引用（例如 `"my_pkg.middleware:TelemetryMiddleware"`），用于从配置文件定位确切的中间件类。导入引用是惰性解析的，因此仅对受信任的本地配置使用它们——加载一个会导入 Python 代码。

当你传入一个预配置的聊天模型实例而不是 `provider:model` 字符串时，框架会从该实例合成规范的 `provider:identifier` 键，并按以下顺序查找它：

  1. 精确匹配 `provider:identifier`
  2. 仅标识符匹配（仅当标识符已包含 `:` 时）
  3. 仅提供商回退

## 注册键

两种配置文件类型都使用相同的键格式：

* **提供商级别**——一个裸的提供商名称，如 `"openai"`，适用于来自该提供商的每个模型。
* **模型级别**——一个完全限定的 `provider:model` 键，如 `"openai:gpt-5.4"`，仅适用于该特定模型。

当同时存在提供商级别和模型级别的配置文件时，它们会在解析时合并。未设置的模型级字段从提供商级配置文件继承；显式的模型级值会覆盖它们。

在现有键下重新注册会将新配置文件合并到先前的配置文件之上——它不会替换它。有关每个字段的规则，请参阅合并语义。

没有匹配所有提供商的通配符键。要普遍应用相同的覆盖——例如，无论选择哪个模型都丢弃 `TodoListMiddleware`——请在每个你使用的提供商键下注册该配置文件。配置文件旨在用于依赖于所选模型的调整。无论模型如何都应该应用的全局调整应该在 `create_deep_agent` 调用点进行。

## 合并语义

| 字段                                        | 合并行为                                                                                 |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `base_system_prompt`、`system_prompt_suffix` | 设置时新值获胜；否则继承                                                    |
| `tool_description_overrides`                 | 映射按键合并；共享键上新值获胜                                         |
| `excluded_tools`、`excluded_middleware`      | 集合并                                                                                      |
| `extra_middleware`                           | 按具体类合并：新实例在其位置替换现有实例，新类附加 |
| `general_purpose_subagent`                   | 逐字段合并（未设置的字段继承）                                                       |
| `init_kwargs` (提供商)                     | 字典按键合并；共享键上新值获胜                                           |
| `pre_init` (提供商)                        | 可调用对象链：先运行现有的，然后运行新的                                         |
| `init_kwargs_factory` (提供商)             | 工厂链，每次 `resolve_model` 调用时合并其输出                           |

## 提供商配置文件

`ProviderProfile` 声明了 Deep Agents 应如何为给定的提供商或特定的模型规范构建聊天模型。它仅在你创建深度代理时提供 `provider:model` 字符串时适用，而当你通过 `init_chat_model` 传入预配置的模型时不适用：

```python
from deepagents import ProviderProfile, register_provider_profile

register_provider_profile(
    "openai",
    ProviderProfile(init_kwargs={"temperature": 0}),
)
```

转发给 `init_chat_model` 的静态初始化参数。

在构建之前运行的副作用（例如凭据验证）。

从运行时状态派生的关键字参数（例如从环境变量中提取的请求头）。

## 从配置文件加载配置文件

对于 YAML/JSON 支持的工作流，请使用 `HarnessProfileConfig`。它镜像了 `HarnessProfile` 的声明式子集（提示文本、工具描述覆盖、排除的工具和中间件、通用子代理编辑），并拥有 `to_dict` / `from_dict`。仅运行时状态——中间件实例、工厂和类形式的 `excluded_middleware` 条目——保留在 `HarnessProfile` 上。

`register_harness_profile` 接受任一类型，因此基于配置的调用者不需要手动转换步骤：

```yaml
# openai.yaml
base_system_prompt: 你很乐于助人。
system_prompt_suffix: 简要回复。
excluded_tools:
  - execute
  - grep
excluded_middleware:
  - SummarizationMiddleware
  - my_pkg.middleware:TelemetryMiddleware
general_purpose_subagent:
  enabled: false
```

```python
import yaml
from deepagents import HarnessProfileConfig, register_harness_profile

with open("openai.yaml") as f:
    register_harness_profile(
        "openai",
        HarnessProfileConfig.from_dict(yaml.safe_load(f)),
    )
```

反过来，`HarnessProfileConfig.from_harness_profile(...)` 在仅使用可序列化功能时，将运行时配置文件导出回声明式形式：

* 类形式的 `excluded_middleware` 条目序列化为公共别名（当类通过 `serialized_name: ClassVar[str]` 暴露一个别名时），或作为 `module:Class` 导入引用。
* 非空的 `extra_middleware` 和在 `__main__` 中或函数作用域内声明的中间件类无法序列化——导出会引发 `ValueError`。

## 作为插件发布配置文件

可分发的配置文件可以通过 `importlib.metadata` 入口点自行注册，而不需要调用者手动运行 `register_*_profile`。加载顺序是**内置配置文件优先，然后是入口点插件，然后是用户代码中的任何直接 `register_*_profile` 调用**；所有三条路径都通过相同的附加注册进行汇集，因此后注册的内容在同一键下会叠加在较早注册的内容之上。

在分发包自己的 `pyproject.toml` 中的相应组下声明一个入口点：

```toml
[project.entry-points."deepagents.harness_profiles"]
my_provider = "my_pkg.profiles:register_harness"

[project.entry-points."deepagents.provider_profiles"]
my_provider = "my_pkg.profiles:register_provider"
```

每个目标解析为一个零参数可调用对象，当 `deepagents.profiles` 被导入时执行注册：

```python
from deepagents import (
    HarnessProfile,
    ProviderProfile,
    register_harness_profile,
    register_provider_profile,
)

def register_harness() -> None:
    register_harness_profile(
        "my_provider",
        HarnessProfile(system_prompt_suffix="并行批处理独立的工具调用。"),
    )

def register_provider() -> None:
    register_provider_profile(
        "my_provider",
        ProviderProfile(init_kwargs={"temperature": 0}),
    )
```

## 相关

* 框架 — 框架能力概述
* 模型 — 配置模型提供商和参数
* 自定义 — `create_deep_agent` 的完整配置界面