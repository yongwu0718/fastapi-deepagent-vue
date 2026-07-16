# Deep Agents 中的上下文工程

> 控制你的深度代理可以访问哪些上下文，以及在长时间运行的任务中如何管理这些上下文

上下文工程就是以正确的格式提供正确的信息和工具，让你的深度代理能够可靠地完成任务。

深度代理可以访问多种上下文。有些来源在代理启动时提供；另一些则在运行时可用，例如用户输入。深度代理包含用于在长时间运行的会话中管理上下文的内置机制。
## 上下文类型

| 上下文类型                                               | 你控制的内容                                                                  | 作用域                             |
| -------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------- |
| **输入上下文**                        | 代理启动时注入其提示的内容（系统提示、记忆、技能）                            | 静态，每次运行都会应用             |
| **运行时上下文**                    | 调用时传入的静态配置（用户元数据、API 密钥、连接）                            | 每次运行，会传播到子代理           |
| **上下文压缩**            | 内置的卸载和摘要功能，使上下文保持在窗口限制内                                | 自动，当接近限制时触发             |
| **上下文隔离** | 使用子代理隔离繁重工作，仅将结果返回给主代理                                  | 每个子代理，在被委派时             |
| **长期记忆**                  | 使用虚拟文件系统实现跨线程持久存储                                            | 跨会话持久化                       |

## 输入上下文

输入上下文是在代理启动时提供给它的信息，这些信息会成为其系统提示的一部分。最终的提示由几个来源组成：
**系统提示**
你提供的自定义指令加上内置的代理指导。
**记忆**
配置后始终加载的持久 `AGENTS.md` 文件。
**工具**
在相关时加载的按需能力（渐进式披露）。
**工具提示词**
使用内置工具或自定义工具的指令。

### 系统提示

你的自定义系统提示会被添加到内置系统提示之前，内置提示包含关于规划、文件系统工具和子代理的指导。用它来定义代理的角色、行为和知识：

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    system_prompt=(
        "You are a research assistant specializing in scientific literature. "
        "Always cite sources. Use subagents for parallel research on different topics."
    ),
)
```

`system_prompt` 参数是静态的，这意味着它不会因调用而改变。对于某些用例，你可能需要动态提示：
	例如，告诉模型“你拥有管理员访问权限”与“你拥有只读访问权限”，或者从长期记忆中注入用户偏好，如“用户更喜欢简洁的回答”。
如果你的提示依赖于上下文或 `runtime.store`，请使用 `@dynamic_prompt` 来构建感知上下文的指令。你的中间件可以读取 `request.runtime.context` 和 `request.runtime.store`。
有关添加自定义中间件，`@dynamic_prompt`放于中间件中使用。

当工具单独使用上下文或 `runtime.store` 时，你**不**需要中间件；工具直接接收 ToolRuntime 对象（包括 `runtime.context` 和 `runtime.store`）。仅当工具应与系统提示的更新一起打包时，才添加中间件。

**提示**
要针对特定提供商或模型调整组装好的系统提示，请使用框架配置文件：`base_system_prompt` 完全替换基础提示，`system_prompt_suffix` 则附加到其后。

### 记忆

记忆文件（`AGENTS.md`）提供持久上下文，这些上下文**始终加载**到系统提示中。使用记忆来存储项目惯例、用户偏好和应适用于每次对话的关键指南：

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    memory=["/project/AGENTS.md", "~/.deepagents/preferences.md"],
)
```

与技能不同，记忆总是被注入——没有渐进式披露。**保持记忆内容精简，以避免上下文过载；对于详细的工作流程和领域特定内容，请使用技能**。有关配置详情，请参见[记忆]。

### 技能

技能提供**按需**能力。代理在启动时读取每个 `SKILL.md` 的前置元数据（frontmatter），然后仅在其确定该技能相关时才加载完整的技能内容。这减少了令牌使用量，同时仍提供专业化的工作流程：

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    skills=["/skills/research/", "/skills/web-search/"],
)
```

让**每个技能专注于单个工作流程或领域**；宽泛或重叠的技能会稀释相关性，并在加载时使上下文膨胀。**在技能内部，保持主要内容简洁，并将详细的参考资料移至技能文件中引用的单独文件**。将始终相关的惯例放入记忆中。有关编写和配置，请参见技能。

### 工具提示

工具提示是指导模型如何使用工具的指令。所有工具都会暴露模型在其提示中看到的元数据——通常是模式和描述。你通过 `tools` 参数传递的工具会将工具元数据（模式和描述）展现给模型。深度代理的内置工具打包在中间件中，通常还会用更多针对这些工具的指导来更新系统提示。

**内置工具** – 添加框架能力（规划、文件系统、子代理）的中间件会自动将特定于工具的指令附加到系统提示，从而创建解释如何有效使用这些工具的工具提示：

- 规划提示 – 使用 `write_todos` 维护结构化任务清单的指令
- 文件系统提示 – `ls`、`read_file`、`write_file`、`edit_file`、`glob`、`grep`（以及使用沙箱后端时的 `execute`）的文档
- 子代理提示 – 使用 `task` 工具委派工作的指导
- 人机协同提示 – 在指定工具调用处暂停的用法（当设置了 `interrupt_on` 时）
- 本地上下文提示 – 当前目录和项目信息（仅限 CLI）

**你提供的工具** – 通过 `tools` 参数传递的工具会将其描述（来自工具模式）发送给模型。你还可以添加自定义中间件，该中间件添加工具并将自己的系统提示指令附加到系统提示中。

对于你提供的工具，请确保提供清晰的名称、描述和参数描述。这些会指导模型推理何时以及如何使用该工具。在描述中包括*何时*使用该工具，并描述每个参数的作用。

```python
@tool(parse_docstring=True)
def search_orders(
    user_id: str,
    status: str,
    limit: int = 10
) -> str:
    """按状态搜索用户订单。

    当用户询问订单历史或想要检查订单状态时使用此工具。
    始终按提供的状态进行筛选。

    参数：
        user_id: 用户的唯一标识符
        status: 订单状态：'pending'、'shipped' 或 'delivered'
        limit: 返回的最大结果数
    """
    # 实现在这里
    ...
```

要为特定提供商或模型覆盖内置或用户提供的工具的说明，请使用框架配置文件的 `tool_description_overrides`（按键名为工具名）。`excluded_tools` 则会将工具从可见的工具集中完全移除。

### 完整的系统提示

深度代理的系统消息——模型在运行开始时接收到的组装好的系统提示——由以下部分组成：

1. 自定义 `system_prompt`（如果提供）
2. 基础代理提示
3. 待办事项清单提示：关于如何使用待办事项清单进行规划的指令
4. 记忆提示：`AGENTS.md` + 记忆使用指南（仅当提供了 `memory` 时）
5. 技能提示：技能位置 + 带有前置元数据信息的技能列表 + 用法（仅当提供了技能时）
6. 虚拟文件系统提示（文件系统 + 执行工具文档，如果适用）
7. 子代理提示：任务工具用法
8. 用户提供的中间件提示（如果提供了自定义中间件）
9. 人机协同提示（当设置了 `interrupt_on` 时）

## 运行时上下文

**运行时上下文是你在调用代理时传入的每次运行时的配置**。它不会自动包含在模型提示中；只有当工具、中间件或其他逻辑读取它并将其添加到消息或系统提示中时，模型才会看到它。将运行时上下文用于用户元数据（ID、偏好、角色）、API 密钥、数据库连接、功能标志或你的工具和框架所需的其他值。

使用 `context_schema` 定义数据的形状：使用 `dataclasses.dataclass` 或 `typing.TypedDict` 类。通过 `invoke` / `ainvoke` 的 **`context`** 参数传递值。有关完整细节，请参见运行时和 LangGraph 运行时上下文。

在工具内部，从注入的 ToolRuntime 读取上下文：

```python
from dataclasses import dataclass

from deepagents import create_deep_agent
from langchain.tools import tool, ToolRuntime

@dataclass
class Context:
    user_id: str
    api_key: str

@tool
def fetch_user_data(query: str, runtime: ToolRuntime[Context]) -> str:
    """获取当前用户的数据。"""
    user_id = runtime.context.user_id
    return f"Data for user {user_id}: {query}"

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    tools=[fetch_user_data],
    context_schema=Context,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "获取我最近的活动"}]},
    context=Context(user_id="user-123", api_key="sk-..."),
)
```

运行时上下文**会传播到所有子代理**。当子代理运行时，它会接收与父代理相同的运行时上下文。有关每个子代理的上下文（命名空间键），请参见子代理。

## 上下文压缩

长时间运行的任务会产生大量的工具输出和很长的对话历史。上下文压缩可以减少代理工作记忆中信息的大小，同时保留与任务相关的细节。以下技术是确保传递给 LLM 的上下文保持在其上下文窗口限制内的内置机制：
**卸载**
大的工具输入和结果存储在文件系统中，并用引用替换。
**摘要**
当接近限制时，旧消息会被压缩成 LLM 生成的摘要。
### 卸载

Deep Agents 使用内置的**文件系统工具自动卸载内容**，并根据需要搜索和检索已卸载的内容。
当工具调用的输入或结果超过令牌阈值（默认为 20,000）时，就会发生内容卸载：

1. **工具调用输入超过 20,000 令牌**：文件写入和编辑操作会在代理的对话历史中留下包含完整文件内容的工具调用。
   由于这些内容已持久化到文件系统，因此通常是多余的。
   当会话上下文超过模型可用窗口的 85% 时，深度代理会截断较旧的工具调用，将它们替换为指向磁盘上文件的指针，从而减少活跃上下文的大小。
![[offloading-inputs.avif]]
2. **工具调用结果超过 20,000 令牌**：发生这种情况时，深度代理会将响应卸载到配置的后端，并用文件路径引用和前十行的预览来替换它。然后代理可以根据需要重新读取或搜索内容。
![[offloading-results.avif]]
### 摘要

当上下文大小超过模型的上下文窗口限制（例如 `max_input_tokens` 的 85%）时，并且没有更多上下文可用于卸载，深度代理会对消息历史进行摘要。

此过程包含两个部分：

- **上下文内摘要**：LLM 生成对话的结构化摘要，包括会话意图、创建的工件和后续步骤——这将替换代理工作记忆中的完整对话历史。
- **文件系统保存**：完整的原始对话消息作为规范记录写入文件系统。

这种双重方法确保代理通过摘要保持对其目标和进度的认知，同时在需要时保留恢复特定细节的能力（通过文件系统搜索）。
![[summarization.avif]]
**配置：**

- 从模型配置文件中模型的 `max_input_tokens` 的 85% 时触发
- 保留 10% 的令牌作为近期上下文
- 如果模型配置文件不可用，则回退到 170,000 令牌触发 / 保留 6 条消息
- 如果任何模型调用引发标准的 ContextOverflowError，深度代理会立即回退到摘要，并使用摘要 + 保留的近期消息进行重试
- 较早的消息由模型进行摘要

从代理流式传输的令牌通常会包含摘要步骤生成的令牌。你可以使用它们关联的元数据过滤掉这些令牌：

```python
for chunk in agent.stream(
    {"messages": [...]},
    stream_mode="messages",
    version="v2",
):
    token, metadata = chunk["data"]
    if metadata.get("lc_source") == "summarization":  # 检查来源
        continue
    else:
        ...
```

##### 摘要工具

深度代理包含一个可选的摘要工具，使代理能够在合适的时机——例如在任务之间——触发摘要，而不是在固定的令牌间隔触发。

你可以通过将其附加到中间件列表来启用此工具：

```python
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware.summarization import (
    create_summarization_tool_middleware,
)

backend = StateBackend  # 如果使用默认后端

model = "google_genai:gemini-3.1-pro-preview"
agent = create_deep_agent(
    model=model,
    middleware=[  # 你的其他中间件
        create_summarization_tool_middleware(model, backend),  # 添加摘要工具中间件
    ],
)
```

启用此功能不会禁用在模型上下文限制的 85% 时的默认摘要动作。

详情请参见 `SummarizationToolMiddleware` API 参考。

## 使用子代理进行上下文隔离

子代理解决了**上下文膨胀问题**。当主代理使用具有大量输出的工具（网络搜索、文件读取、数据库查询）时，上下文窗口会迅速被填满。子代理隔离了这些工作——主代理仅接收最终结果，而不是产生这些结果的数十个工具调用。你还可以将每个子代理与主代理分开配置（例如，模型、工具、系统提示和技能）。

**工作原理：**

- 主代理拥有一个 `task` 工具来委派工作
- 子代理使用自己全新的上下文运行
- 子代理自主执行直至完成
- 子代理向主代理返回一份最终报告
- 主代理的上下文保持干净

**最佳实践：**

1. **委派复杂任务**：对于会扰乱主代理上下文的多步骤工作，使用子代理。

2. **保持子代理响应简洁**：指示子代理返回摘要，而不是原始数据：

   ```python
   research_subagent = {
       "name": "researcher",
       "description": "对某个主题进行研究",
       "system_prompt": """你是一个研究助手。
       重要提示：只返回必要的摘要（500 字以内）。
       不要包含原始搜索结果或详细的工具输出。""",
       "tools": [web_search],
   }
   ```

3. **使用文件系统处理大数据**：子代理可以将结果写入文件；主代理读取它所需的内容。

有关配置和上下文管理（运行时上下文传播和每个子代理的命名空间），请参见子代理。

## 长期记忆

使用默认文件系统时，你的深度代理会将其工作记忆文件存储在代理状态中，这仅在单个线程内持久化。长期记忆使你的深度代理能够将信息跨不同线程和对话持久化。深度代理可以使用长期记忆来存储用户偏好、积累的知识、研究进展或任何应该在单个会话之外持久化的信息。

要使用长期记忆，你必须使用 `CompositeBackend`，它将特定路径（通常是 `/memories/`）路由到 LangGraph Store，后者提供持久的跨线程持久化。`CompositeBackend` 是一个混合存储系统，其中一些文件无限期持久化，而另一些文件则限定在单个线程范围内。

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

def make_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={"/memories/": StoreBackend(runtime)},
    )

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    store=InMemoryStore(),
    backend=make_backend,
    system_prompt="""当用户告诉你他们的偏好时，将它们保存到
    /memories/user_preferences.txt，以便你在未来的对话中记住它们。""",
)
```

你不需要预先用文件填充 `/memories/`。你需要提供后端配置、存储和系统提示指令，告诉代理*保存什么*以及*保存在哪里*。
例如，你可以提示代理将偏好存储在 `/memories/preferences.txt` 中。
该路径开始时为空，代理会使用其文件系统工具（`write_file`、`edit_file`），在用户分享值得记住的信息时按需创建文件。

有关设置和用例，请参见长期记忆。

## 最佳实践

1. **从正确的输入上下文开始** – 对于始终相关的惯例，保持记忆精简；对于特定于任务的能力，使用专注的技能。
2. **利用子代理处理繁重工作** – 委派多步骤、输出繁重的任务，以保持主代理的上下文干净。
3. **在配置中调整子代理输出** – 如果你在调试时发现子代理生成了很长的输出，可以在子代理的 `system_prompt` 中添加指导，以创建摘要和综合调查结果。
4. **使用文件系统** – 将大的输出持久化到文件中（例如子代理写入或自动卸载），这样活跃上下文保持较小；模型在需要细节时可以通过 `read_file` 和 `grep` 拉取片段。
5. **记录长期记忆结构** – 告诉代理 `/memories/` 中存放了什么以及如何使用它。
6. **为工具传递运行时上下文** – 对用户元数据、API 密钥以及工具所需的其他静态配置，使用 `context`。

## 相关资源

- 框架 – 上下文管理概述、卸载、摘要
- 子代理 – 上下文隔离、运行时上下文传播
- 长期记忆 – 跨线程持久化
- 技能 – 渐进式披露和技能编写
- 后端 – 文件系统后端和 CompositeBackend
- 上下文概念概述 – 上下文类型和生命周期