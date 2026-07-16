# Skills（技能）

> 了解如何通过 Skills 扩展你的 deep agent 的能力

Skills 将领域专业知识（如工作流、最佳实践、脚本、参考文档和模板）打包到可复用的目录中。Agent 在启动时会获得内容摘要，并仅在相关时发现和读取其中包含的文件。

Skills 可帮助你避免上下文膨胀，它只在启动时加载摘要，并在任务需要时读取完整指令。你可以在 agents 和项目之间共享 skills，也可以在单个 agent 中组合多个 skills，使每个 skill 覆盖不同的能力。

## Skills 仓库。

Agent Skills 规范:https://agentskills.io/home

langchain-skills 仓库：https://github.com/langchain-ai/langchain-skills

skillhub 仓库:https://skillhub.cloud.tencent.com/contest

hermes-skills 仓库:https://hermes-agent.nousresearch.com/docs/skills

claw-skills 仓库:https://clawhub.ai/skills

## Usage（用法）

1.创建顶级技能目录

为你的项目创建一个目录来存放所有 skills，例如后端根目录下的 `skills/`。

2.在您的技能目录中为您的技能创建一个子目录

每个 skill 是一个包含 `SKILL.md` 文件的目录：这是一个带有 YAML frontmatter（`name` 和 `description`）的 markdown 文件，后面跟着 skill 激活时 agent 要遵循的指令。Skill 目录还可以包含可选的辅助文件，例如脚本、参考文档和模板。

3.添加一个带有 YAML 前置元数据和使用说明的 `SKILL.md` 文件。

`SKILL.md` 以 YAML frontmatter 开头，后跟 markdown 指令：

```md
---
name: langgraph-docs
description: Use this skill for requests related to LangGraph in order to fetch relevant documentation to provide accurate, up-to-date guidance.
---

# langgraph-docs

## Overview

This skill explains how to access LangGraph documentation to help answer questions and guide implementation.

## Instructions

### 1. Fetch the documentation index

Use the fetch_url tool to read the following URL:
https://docs.langchain.com/llms.txt

This provides a structured list of all available documentation with descriptions.

### 2. Select relevant documentation

Based on the question, identify 2-4 most relevant documentation URLs from the index. Prioritize:

- Specific how-to guides for implementation questions
- Core concept pages for understanding questions
- Tutorials for end-to-end examples
- Reference docs for API details

### 3. Fetch and synthesize

Use the fetch_url tool to read the selected documentation URLs, then answer the user's question. Give a direct answer first, include the minimum necessary context, and link to the source pages rather than quoting long passages.
```

在你的 `SKILL.md` 中引用任何辅助资源，并描述每个文件包含的内容以及何时使用。Agent 通过 skill 指令中的引用发现这些文件。

4.在创建您的代理时，请传递技能路径

在创建 agent 时，通过 `skills` 参数传递顶级 skills 目录的路径：

```python
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

backend = FilesystemBackend(root_dir="./my-project")

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    backend=backend,
    skills=["./my-project/skills/"],
)
```

此示例使用 `FilesystemBackend` 从磁盘加载 skills。有关其他存储选项（包括从远程源加载 skills），请参阅 Backends and remote skill loading。

skill 源路径列表。

路径必须使用正斜杠，并且相对于 backend 的根目录。

* 如果省略，则不加载任何 skills。
* 使用 `StateBackend`（默认）时，通过 `invoke(files={...})` 提供 skill 文件。使用 `deepagents.backends.utils` 中的 `create_file_data()` 来格式化文件内容；不支持原始字符串。
* 使用 `FilesystemBackend` 时，skills 从相对于 backend 的 `root_dir` 的磁盘加载。

**对于同名 skill，后面的源会覆盖前面的源（后者优先）。**

当多个 skill 源包含同名 skill 时，`skills` 数组中列在后面的源中的 skill 优先（后者优先）。这使你可以分层处理来自不同来源的 skills，例如用项目特定版本覆盖基础 skills。


5.在调用您的代理时，请传递任务

使用 `invoke()` 向 agent 发送任务。启动时，agent 将每个 skill 的 `name` 和 `description`（来自 frontmatter）加载到 system prompt 中。当你的任务与某个 skill 的 description 匹配时，agent 会读取该 skill 的 `SKILL.md` 并遵循其指令。

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is LangGraph?"}]},
    config={"configurable": {"thread_id": "1"}},
)
```

## How skills work（skills 工作原理）

随着 agents 承担更复杂的任务，它们所需的 context 也随之增长。将所有指令加载到 system prompt 会浪费 token 在与当前任务无关的信息上，而跨会话手动提供相同指导则无法扩展。

***
Skills 使用 **progressive disclosure**（渐进式披露）：agent 分层加载 skill 信息，而不是一次性全部加载。启动时，它只看到每个 skill 的 `name` 和 `description`。当 skill 被调用时，它会读取完整的 `SKILL.md` 指令。辅助文件仅在指令调用它们时才加载。
***

Skills 分三个级别加载，每个级别仅在任务需要时才增加更多细节：

| Level（级别）               | 加载内容    | 加载时机                                   |
| ------------------- | --------------- | ------------------------- |
| **1. Metadata（元数据）**     | `SKILL.md` frontmatter 中的 `name` 和 `description` | Agent 启动时，针对每个已配置的 skill                        |
| **2. Instructions（指令）** | `SKILL.md` 正文的全部内容  | Skill 被调用时  |
| **3. Resources（资源）**    | `scripts/`、`references/` 和 `assets/` 下的辅助文件  | 调用后按需，当指令引用它们时 |

下图显示了在给定时刻 agent context 中出现的内容。启动时，system prompt 中包含每个 skill 的 level 1 metadata。当 skill 被调用时，level 2 指令加入 context。Level 3 文件保留在 backend 中，直到 agent 在调用后读取它们。

![alt text](skills-composition.svg)

当 agent 处理任务时，它会分层加载 skill 信息：

![alt text](skills-progressive-disclosure.svg)

在 Deep Agents 中，`SkillsMiddleware`（当你传递 `skills` 时，它是默认 middleware 堆栈的一部分）处理前两个级别，第三级由 LLM 处理：

1.  **Discovery（发现，level 1）**：Agent 启动时，middleware 扫描配置的 skill 路径，解析每个 `SKILL.md` 的 frontmatter，并将 `name` 和 `description` 字段注入 system prompt。
2.  **Read（读取，level 2）**：当 agent 调用一个 skill 时，它通过 `read_file` 读取完整的 `SKILL.md` 内容。
3.  **Execute（执行，level 3）**：调用后，agent 遵循 skill 的指令，并仅在指令需要时读取辅助文件（scripts, references, assets）。

## When to use skills（何时使用 skills）

如果你发现自己反复向 agent 提供类似的指令，尤其是那些包含多个步骤的详细指令，请考虑将这些指令编纂成 skill。这样，将来当你想完成类似任务时，agent 就会知道该怎么做。

你也可以让你的 agent 为你曾和它一起完成的任务编写一个 skill。

Skills 特别适用于编纂：

*   **Step-by-step workflows（分步工作流）**：跨越多个步骤的工作流，类似于食谱。
*   **Domain-specific knowledge（领域特定知识）**：指导 agent 如何使用工具来完成工作流。例如，包含有关从哪里提取信息的信息，包括 skill 可能访问的其他参考信息或脚本。
*   **带有可执行代码的 Instructions（指令）**：将程序或模块与 agent 可以运行的脚本捆绑在一起，这样它就可以遵循经过测试的逻辑，而不是每次都根据指令重新生成。参见 Execute code with skills。
*   **Guidelines（指南）**：向 agent 提供需要遵守的 guardrails 的辅助指令。例如，遵循特定的格式或风格指南，或指定始终在 workflow 中运行测试。

## Write effective skills（编写有效的 skills）

Agent Skills 规范包含了关于构建 skills 以确保可靠发现和激活的指导。以下建议基于该基础，为 Deep Agents 提供了实用模式。

**保持 frontmatter 简洁**，并将 `SKILL.md` 正文控制在 5,000 tokens 以内。每个 skill 的 frontmatter 会在 discovery 时被添加到 system prompt 中，而完整的正文仅在激活时读取。保持这两层内容简短意味着你可以加载许多 skills 而不会挤占 context window。

**编写具体的 descriptions。** 在 discovery 期间，`description` 字段是 agent 对每个 skill 所能看到的唯一信息。一个好的 description 会告诉 agent 这个 skill 是做什么的，以及何时激活它，并包含 agent 可以匹配的关键词：

```yaml
# 好的：明确说明功能和适用场景
description: >-
  Extract text and tables from PDF files, fill PDF forms, and merge
  multiple PDFs. Use when working with PDF documents or when the user
  mentions PDFs, forms, or document extraction.

# 差的：过于模糊，难以可靠匹配
description: Helps with PDFs.
```

当你在相关领域有多个 skills 时，要清楚地区分它们的 descriptions。重叠的 descriptions 会导致 agent 激活错误的 skill 或在选项之间犹豫不决。如果两个 skills 服务于相似的目的，请将它们合并为一个。

**保持指令聚焦。** Agent Skills 规范建议将你的 `SKILL.md` 保持在 500 行以内。当指令变长时，将详细的参考资料移至辅助资源文件中，并在主 `SKILL.md` 中引用它们：

Agent 仅在指令调用时加载参考文件，从而保持 progressive disclosure 的每一层大小适当。保持从 `SKILL.md` 开始的引用深度为一层，避免深层嵌套的引用链，这会迫使 agent 通过多次读取来获取所需信息。

**为 agent 构建指令结构。** 将你的 `SKILL.md` 正文编写为 agent 可以遵循的清晰指令：

*   **Step-by-step procedures**（分步程序），适用于多步骤工作流
*   **Decision criteria**（决策标准），用于在不同方法之间选择
*   **期望输入和输出的 Examples**（示例），以便 agent 知道成功的样子
*   **Edge cases**（边缘情况），agent 应该处理或向用户标记

**管理 skill 数量。** 数量较少但范围明确的 skills 优于许多重叠的 skills。随着具有相似描述的 skills 数量的增加，agent 选择正确 skill 的能力会下降。如果你发现自己有很多相关的 skills，请考虑：

*   将相关能力合并到一个 skill 中，并为每个子任务设置不同的部分
*   使用参考文件保持主 `SKILL.md` 简洁，同时覆盖多个子任务

***
使用 `[skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref)` 验证工具检查你的 `SKILL.md` frontmatter 是否符合 Agent Skills 规范的命名和格式约定。
***

## Add supporting resources（添加辅助资源）

除了 `SKILL.md` 之外，skill 目录还可以包含任何额外的文件或目录。Agent Skills 规范为常见的资源类型定义了三个可选目录。Deep Agents 不会在 discovery 或 activation 时加载这些文件。Agent 仅在 `SKILL.md` 指令指示时才读取或执行它们。

### `scripts/`

`scripts/` 目录存放 agent 可以运行的可执行代码，例如 API 客户端、数据转换或验证检查。脚本应：

*   自包含或清晰记录依赖项
*   包含有用的错误消息
*   妥善处理边缘情况

支持的语言取决于你的 agent 设置。常见选项包括 Python、Bash 和 JavaScript 或 TypeScript。要执行脚本而不仅仅是读取它们，请参阅 Execute code with skills。当 agent 需要 shell 时，请使用 sandbox scripts。

### `references/`

`references/` 目录存放 agent 按需读取的补充文档。用于那些对 `SKILL.md` 来说过于详细但仍与任务相关的内容，例如：

*   `REFERENCE.md`，提供详细的技术参考
*   `FORMS.md`，提供表单模板或结构化数据格式
*   领域特定指南（`finance.md`、`legal.md` 等）

保持单个参考文件聚焦。Agent 仅在需要时才加载它们，因此较小的文件占用的 context 更少。

### `assets/`

`assets/` 目录存放 agent 使用但无需作为指令读取的静态资源，例如：

*   文档或配置模板
*   图片（图表、示例）
*   数据文件（查找表、模式）

在 `SKILL.md` 中描述 agent 何时应该打开或复制每个 asset。

### 在 `SKILL.md` 中引用文件

当你引用辅助文件时，请使用相对于 skill 根目录的路径：

```md
For API details, see the [reference guide](references/api-patterns.md).

To extract tables from a PDF, run:
scripts/extract.py
```

对于你引用的每个文件，说明它包含什么以及 agent 何时应该使用它。保持从 `SKILL.md` 开始的引用深度为一层。避免深层嵌套的引用链，这会迫使 agent 通过多次读取来获取所需信息。

## Backends and remote skill loading（后端与远程 skill 加载）

Deep Agents 支持不同的 backends，具体取决于你希望如何存储和管理 skill 文件：

*   `StateBackend`：将文件存储在 LangGraph agent state 中，用于当前线程。
*   `StoreBackend`：将文件存储在 LangGraph store 中，用于持久、跨线程存储。
*   `FilesystemBackend`：从可配置的 `root_dir` 下的磁盘读取和写入 skill 文件。

```python
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

# Checkpointer is REQUIRED for human-in-the-loop
checkpointer = MemorySaver()
root_dir = "/Users/user/{project}"
backend = FilesystemBackend(root_dir=root_dir)

agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    backend=backend,
    skills=[str(Path(root_dir) / "skills")],
    interrupt_on={
        "write_file": True,
        "read_file": False,
        "edit_file": True,
    },
    checkpointer=checkpointer, # Required!
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is langgraph?"}]},
    config={"configurable": {"thread_id": "12345"}},
)
```

## Load skills at runtime（在运行时加载 skills）

当你拥有大量 skills，但只有一部分与某次运行相关时，可以根据运行时 context（如用户角色、租户或请求类型）选择要加载的 skills。有两种主要方法：

### Dynamic skill lists（动态 skill 列表）

最简单的方法是在创建 agent 之前构建 `skills` 数组。根据你可用的任何运行时 context 选择要包含的 skill 路径：

```python
from deepagents import create_deep_agent

SKILLS_BY_ROLE = {
    "engineering": ["/skills/code-review/", "/skills/testing/", "/skills/deployment/"],
    "data": ["/skills/sql-analysis/", "/skills/visualization/", "/skills/data-pipeline/"],
    "support": ["/skills/ticket-triage/", "/skills/runbook/"],
}

def create_agent_for_user(user_role: str):
    return create_deep_agent(
        model="anthropic:claude-sonnet-4-6",
        skills=SKILLS_BY_ROLE.get(user_role, []),
    )
```

当 skills 位于磁盘或共享 backend 中，而你只需要控制 agent 能看到哪些时，这种方法很有效。Skills 本身不会重复——你只需维护一份副本，并为每次运行改变传递的路径。

***
SDK 仅加载你在 `skills` 中传递的源。它不会自动扫描 CLI 目录，例如 `~/.deepagents/...` 或 `~/.agents/...`。

有关 CLI 存储约定，请参阅 App data。

如果你想在 SDK 代码中实现 CLI 风格的分层，请按从低到高的优先级顺序显式传递所有所需的源：

```text
[
"/.deepagents/{agent}/skills/",
"/.agents/skills/",
"/.deepagents/skills/",
"/.agents/skills/",
]
```

然后在创建 agent 时，将该有序列表作为 `skills` 传递。
***

### Namespaced skills（命名空间 skills）

对于每个用户的 skill 集独立管理的多租户应用程序，将 `/skills/` 路由到带有 namespace 工厂的 `StoreBackend`。在每个 namespace 中只填充该用户应该有权访问的 skills，middleware 会在运行时解析到正确的集合：

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    skills=["/skills/"],
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/skills/": StoreBackend(
                namespace=lambda rt: (
                    rt.server_info.assistant_id,
                    rt.server_info.user.identity,
                ),
            ),
        },
    ),
)
```

当不同的用户或租户需要完全独立且可以单独更新的 skill 库时，此模式非常有用。有关开箱即用地处理 skill 访问、共享和工作空间级可见性的托管解决方案，请参阅 Fleet skills。

## Skills for subagents（子 agent 的 skills）

当你使用 subagents 时，你可以配置每种类型可以访问哪些 skills：

*   **通用子 agent (General-purpose subagent)**：当你向 `create_deep_agent` 传递 `skills` 时，自动从主 agent 继承 skills。无需额外配置。
*   **自定义子 agent (Custom subagents)**：不会继承主 agent 的 skills。在每个子 agent 定义中添加一个 `skills` 参数，并指定该子 agent 的 skill 源路径。

Skill 状态是完全隔离的：主 agent 的 skills 对 subagents 不可见，subagents 的 skills 对主 agent 也不可见。

```python
from deepagents import create_deep_agent

research_subagent = {
    "name": "researcher",
    "description": "Research assistant with specialized skills",
    "system_prompt": "You are a researcher.",
    "tools": [web_search],
    "skills": ["/skills/research/", "/skills/web-search/"],  # 子 agent 特有的 skills
}

agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    skills=["/skills/main/"],  # 主 agent 和通用子 agent 获得这些
    subagents=[research_subagent],  # Researcher 只获得它自己的 skills
)
```

有关子 agent 配置和 skills 继承的更多信息，请参阅 Subagents。

## Skill permissions（Skill 权限）

生产部署通常需要控制三件事：每个用户能看到哪些 skills，agent 是否可以修改 skill 文件，以及写入是否需要人工批准。你可以通过 `skills` 参数和 backend 路由来控制可见性，通过文件系统权限来控制访问，并通过 `interrupt_on` 或 `mode="interrupt"` 的权限规则来控制批准。

### 跨用户共享 skills

为了让每个用户都能访问同一个经过筛选的库，请将 `/skills/` 路由到共享的 `StoreBackend`，并从你的应用程序代码或管理工作流中为其播种。使用组织范围的 namespace，以便该组织中的所有 agents 都解析到同一个 store：

*   按组织 ID 设置 namespace，以实现工作空间级 skills（参见 Enforce read-only skills）。
*   当每个用户需要独立的库时，按用户 ID 设置 namespace（namespaced skills）。

用诸如 `/company-policies/SKILL.md` 的 key 和包含 `content` 及 `encoding` 字段的 value 来播种 store。在从 store 读取记录之前，`/skills/` 路由前缀会被移除。

有关处理 skill 访问、共享和工作空间级可见性的托管解决方案，请参阅 Fleet skills。

你也可以组合共享库和个人库：将 `/skills/shared/` 路由到组织范围的 `StoreBackend`，将 `/skills/personal/` 路由到用户范围的 backend，并在 `skills` 中传递这两个路径。参见 Allow agents to edit personal skills。

### 按用户 context 限制 skills

并非每个用户都应该看到所有 skills。根据角色、租户或其他请求 context 控制在运行时加载哪些 skills。有两种主要方法：

*   **Dynamic skill lists** — 在创建 agent 之前构建 `skills` 数组。为不同的角色或请求类型传递不同的路径列表。当 skills 位于共享 backend 中，并且你按路径过滤时，此方法有效。
*   **Namespaced skills** — 将 `/skills/` 路由到 `StoreBackend`，并使用基于用户或租户 ID 的 namespace 工厂。在每个 namespace 中只填充该身份应该访问的 skills。

这些模式与下面的读写控制配合使用。例如，你可以为管理员提供比工程师更大的 skill 集，同时保持两个库都是只读的。

### 实施只读 skills

要在不允 agents 修改的情况下共享 skills，请将 `/skills/` 路由到共享 store，并使用 filesystem permissions 拒绝 `/skills/**` 下的写入操作。Agent 可以发现和读取 skills；只有你的应用程序代码或管理工作流可以更新 store。

```python
from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()  # Good for local dev; omit for LangSmith Deployment

agent = create_deep_agent(
    model="openai:gpt-5.4",
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/skills/": StoreBackend(
                namespace=lambda rt: ("curated-skills", rt.context.org_id),
            ),
        },
    ),
    skills=["/skills/"],
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/skills/**"],
            mode="deny",
        ),
    ],
    store=store,
)
```

将此用于企业知识库、已批准的工具说明或共享 skill 包，其中 agent 应从集中管理的 context 中受益，但不应重写真实数据源。

### 要求对 skill 写入进行批准

如果 agents 可以写入 skill 文件，但你希望先有 human in the loop，请使用 `interrupt_on` 或带有 `mode="interrupt"` 的权限规则。两者都会在运行 `write_file` 或 `edit_file` 之前暂停，并使用相同的恢复流程。

```python
from deepagents import FilesystemPermission, create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    skills=["/skills/personal/"],
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/skills/**"],
            mode="interrupt",
        ),
    ],
    checkpointer=MemorySaver(),  # 需要此选项才能暂停和恢复
)
```

或者，配置 `interrupt_on={"write_file": True, "edit_file": True}` 以要求对所有文件系统写入进行批准，而不仅仅是 skills 路径。有关处理并恢复中断，请参阅 Human-in-the-loop。

Filesystem permission 中断需要 `deepagents>=0.6.8`。

### 允许 agents 编辑个人 skills

默认情况下，如果 backend 允许并且没有权限规则阻止该路径，agents 可以写入 skill 文件。要让 agents 创建或完善 skills 而不触及共享库：

1.  将可写路径（例如 `/skills/personal/`）路由到用户范围的 `StoreBackend`。
2.  在 `skills` 中传递该路径（以及任何共享路径）。
3.  不要为可写路径添加 `deny` 规则。如果你混合使用共享路径和个人路径，请将更具体的规则放在更宽泛的拒绝规则之前（规则排序）。

```python
from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/skills/shared/": StoreBackend(
                namespace=lambda rt: ("curated-skills", rt.context.org_id),
            ),
            "/skills/personal/": StoreBackend(
                namespace=lambda rt: (
                    "user-skills",
                    rt.server_info.user.identity,
                ),
            ),
        },
    ),
    skills=["/skills/shared/", "/skills/personal/"],
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/skills/shared/**"],
            mode="deny",
        ),
    ],
)
```

Agent 使用 `write_file` 和 `edit_file` 在可写路径下创建或更新 `SKILL.md` 及辅助文件。要捕获 skills 格式之外的一般学习经验，请将单独的路径（例如 `/memories/`）路由到另一个可写的 backend。有关路由和 store 设置，请参见 Backends。

## Execute code with skills（使用 skills 执行代码）

如果没有代码执行，skills 是被动的：agent 读取指令并使用其可用的 tools 遵循它们。代码执行将 skills 转变为主动能力。一个 skill 可以搭载一个经过测试的脚本来调用 API、转换数据、验证输出或运行管道——agent 可以确定性地执行它，而不是每次都根据指令重新生成逻辑。这对于需要精确行为（数据转换、API 集成、合规性检查）或依赖于 agent 仅通过 tool 调用无法使用的库的工作流特别有价值。

Skills 通过 sandbox scripts 执行代码：当 agent 需要安装依赖项、运行测试、调用 CLI 或使用操作系统文件系统时，它会运行捆绑的脚本。

### Sandbox scripts（沙盒脚本）

Skills 可以在 `SKILL.md` 文件旁边包含脚本。在你的 `SKILL.md` 中引用脚本，以便 agent 知道它们的存在以及何时运行它们：

```md
---
name: arxiv-search
description: Search the arXiv preprint repository for research papers. Use when the user asks about academic papers, recent research, or scientific literature.
---

# arxiv-search

Search arXiv for papers matching the user's query.

## Instructions

1. Run `scripts/search.py` with the user's query as an argument.
2. Parse the results and present them with title, authors, abstract summary, and link.
3. If the user asks for more detail on a specific paper, fetch the full abstract.
```

Agent 可以从任何 backend *读取* 脚本，但要 *执行* 它们，agent 需要访问 shell，而这仅由 sandbox backends 提供。

Sandbox backends 在隔离的容器中运行。存储在外部的 skill 文件在内部不可用，这意味着 agent 无法执行 skill 脚本或访问 skill 资源，除非先将它们传输进去。使用自定义 middleware 来处理此传输：

*   **`before_agent`**：从 backend 读取 skill 文件并将其上传到 sandbox 中，以便 agent 从一开始就能执行脚本。
*   **`after_agent`**：从 sandbox 下载任何更新或新创建的 skill 文件，并将其写回 backend，以便更改在多次运行之间持久化。


```python
import asyncio
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StoreBackend
from deepagents.backends.langsmith import LangSmithSandbox
from deepagents.backends.utils import create_file_data
from langchain.agents.middleware import AgentMiddleware, AgentState

from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore
from langsmith.sandbox import SandboxClient

# 每个用户的 skill 包都相同：一个共享的 store namespace。
SKILLS_SHARED_NAMESPACE = ("skills", "builtin")

class SkillSandboxSyncMiddleware(AgentMiddleware[AgentState, Any, Any]):
    """在每次 agent 运行之前，将共享的 skill 文件从 store 复制到 sandbox 中。"""

    def __init__(self, backend: CompositeBackend) -> None:
        super().__init__()
        self.backend = backend

    async def abefore_agent(self, state: AgentState, runtime: Runtime[Any]) -> None:
        store = runtime.store

        files: list[tuple[str, bytes]] = []
        for item in await store.asearch(SKILLS_SHARED_NAMESPACE):
            key = str(item.key)
            if ".." in key or any(c in key for c in ("*", "?")):
                msg = f"Invalid key: {key}"
                raise ValueError(msg)
            normalized = key if key.startswith("/") else f"/{key}"
            # CompositeBackend 路由路径并将上传请求批量发送到正确的 backend。
            files.append((f"/skills{normalized}", item.value["content"].encode()))

        if files:
            await self.backend.aupload_files(files)

async def seed_skill_store(store: InMemoryStore) -> None:
    """将规范的 skill 文件从磁盘加载到共享 store namespace（在部署时运行一次）。
    你可以从任何来源（本地文件系统、远程 URL 等）获取 skills。
    """
    skills_dir = Path(__file__).resolve().parent / "skills"
    for file_path in sorted(p for p in skills_dir.rglob("*") if p.is_file()):
        rel = file_path.relative_to(skills_dir).as_posix()
        key = f"/{rel}"
        await store.aput(
            SKILLS_SHARED_NAMESPACE,
            key,
            create_file_data(file_path.read_text(encoding="utf-8")),
        )

async def main() -> None:
    store = InMemoryStore()
    await seed_skill_store(store)

    client = SandboxClient()
    ls_sandbox = client.create_sandbox()
    sandbox_backend = LangSmithSandbox(sandbox=ls_sandbox)

    backend = CompositeBackend(
        default=sandbox_backend,
        routes={
            "/skills/": StoreBackend(
                store=store,
                namespace=lambda _rt: SKILLS_SHARED_NAMESPACE,
            ),
        },
    )

    try:
        agent = create_deep_agent(
            model="openai:gpt-5.4",
            backend=backend,
            skills=["/skills/"],
            store=store,
            middleware=[SkillSandboxSyncMiddleware(backend)],
        )

    finally:
        client.delete_sandbox(ls_sandbox.name)

if __name__ == "__main__":
    asyncio.run(main())
```

有关在执行前播种 skills 和 memories，并在执行后将两者同步回来的完整示例，请参阅 syncing skills and memories with custom middleware。

## Troubleshooting（故障排除）

使用 LangSmith traces 来调试 skill discovery、`SKILL.md` 上的 `read_file` 调用以及辅助资源访问。按照 tracing 快速入门进行设置。我们还建议你设置 LangSmith Engine，它可以监控你的 traces，检测问题并提出修复建议。

### Skill not activated（Skill 未被激活）

**问题**：Agent 在没有读取 skill 的 `SKILL.md` 的情况下处理任务。

**解决方案**：

1.  **使 description 更具体。** Agent 在 discovery 时仅根据 `description` 字段选择 skills。说明 skill 的作用、何时使用以及 agent 可以匹配的关键词：

```yaml
# 好的
description: >-
    Search the arXiv preprint repository for research papers. Use when the
    user asks about academic papers, recent research, or scientific literature.

# 差的
description: Helps with research.
```

2.  **减少 skills 之间的重叠。** 如果多个 skills 具有相似的 descriptions，agent 可能会跳过正确的 skill 或选择错误的 skill。区分 descriptions 或合并相关的 skills。

3.  **确认 skill 在 `skills` 数组中。** Skills 仅从你在创建 agent 时传递的路径或从子 agent 特定的 `skills` 参数加载。

### Skills missing at startup（启动时缺少 Skills）

**问题**：Agent 在其 system prompt 中没有列出某个 skill，或者对 `SKILL.md` 的 `read_file` 调用失败。

**解决方案**：

1.  **检查 skill 路径。** 路径必须使用正斜杠，并且相对于 backend 根目录。使用 `FilesystemBackend` 时，路径相对于 `root_dir`。使用 `StateBackend` 时，使用 `create_file_data()` 在 `invoke(files={...})` 中传递 skill 文件。

2.  **验证 `SKILL.md` frontmatter。** `name` 必须与父目录名匹配，并遵循 Agent Skills 规范。使用 `skills-ref` 验证工具检查格式。

3.  **检查文件大小。** 在 discovery 期间，Deep Agents 会跳过超过 10 MB 的 `SKILL.md` 文件。

4.  **检查分层源。** 当同一 skill 名称出现在多个源中时，最后一个源优先。来自后面路径的较旧或空的 skill 可能会覆盖你期望的那个。

### Supporting files not found（找不到辅助文件）

**问题**：Agent 读取了 `SKILL.md`，但无法访问 scripts、references 或 assets。

**解决方案**：

1.  **从 `SKILL.md` 引用文件。** Agent 不会自动发现辅助文件。说明每个文件包含什么以及何时使用它。使用相对于 skill 根目录的路径。

2.  **将路径保持在 skill 目录内。** 文件路径相对于 backend 解析。确认辅助文件存在于你的指令所引用的路径中。

3.  **将 skills 同步到 sandboxes 中。** 如果你使用 sandbox backends，容器外的 skill 文件在你将其复制进去之前是不可用的。参见 Sandbox scripts 和 syncing skills and memories with custom middleware。

### Scripts fail to run（脚本无法运行）

**问题**：Agent 读取了脚本但无法运行它。

**解决方案**：Agent 可以从任何 backend 读取脚本，但运行它们需要 sandbox backend。参见 Execute code with skills。

### Subagent 无法访问 skill

**问题**：一个自定义 subagent 看不到主 agent 使用的 skills。

**解决方案**：自定义 subagents 不会继承主 agent 的 skills。在子 agent 定义中添加一个 `skills` 参数，并指定该子 agent 的 skill 源路径。通用子 agent 会自动从 `create_deep_agent` 继承 skills。

## Reference（参考）

### Skills, memory, and tools（Skills、memory 和 tools）

Skills、memory（`AGENTS.md` 文件）和 tools 都为 agent 提供 context 或能力。下表总结了何时使用每种：

|              | Skills    | Memory            | Tools            |
| ------------ | ------- | -------- | ----------- |
| **目的**  | 通过 progressive disclosure 发现的按需能力 | 在启动时加载的持久 context      | Agent 可以调用的程序化操作           |
| **加载**  | 仅在 agent 确定相关时读取          | 在 agent 启动时加载                 | 每一轮都可用               |
| **格式**   | 命名目录中的 `SKILL.md`         | `AGENTS.md` 文件             | 绑定到 agent 的函数         |
| **分层** | 用户，然后是项目（后者优先）     | 用户，然后是项目（组合）        | 在创建 agent 时定义               |
| **何时使用** | 指令是任务特定的且可能很庞大  | Context 始终相关（项目约定、偏好） | Agent 需要程序化操作，或无权访问文件系统 |

这些是指导原则，而非严格的界限。在实践中，skills 和 memory 处于一个谱系上。Agent 可以在工作过程中更新自己的 skills，捕获新的程序并逐步完善指令。通过这种方式，skills 可以作为 progressive-disclosure memory 的一种形式：agent 构建并按需检索的 context，而不是在每次提示时都加载。

### Frontmatter 字段

Agent Skills 规范定义了以下 frontmatter 字段：

| 字段           | 必需 | 描述        |
| --------------- | -------- | ------------------- |
| `name`          | 是      | 小写字母数字和连字符，1-64 个字符。必须与父目录名匹配。 |
| `description`   | 是      | Skill 的功能和何时使用。最多 1,024 个字符。                               |
| `license`       | 否       | 许可证名称或对捆绑许可证文件的引用。                                        |
| `compatibility` | 否       | 环境要求（系统包、网络访问）。最多 500 个字符。             |
| `metadata`      | 否       | 任意键值对，用于附加属性。                                        |
| `allowed-tools` | 否       | 以空格分隔的预批准 tools 列表，skill 可以使用。实验性。                 |

```md
---
name: langgraph-docs
description: Use this skill for requests related to LangGraph in order to fetch relevant documentation to provide accurate, up-to-date guidance.
license: MIT
compatibility: Requires internet access for fetching documentation URLs
metadata:
  author: langchain
  version: "1.0"
allowed-tools: fetch_url
---

# langgraph-docs

在此处放置给 agent 的指令。有关 skill 指令的完整示例，请参阅 Usage。
```

有关详细约束和验证规则，请参阅完整的 Agent Skills 规范。在 Deep Agents 中，`SKILL.md` 文件必须小于 10 MB。超过此限制的文件在 skill 加载期间会被跳过。

有关更多示例 skills，请参阅 Deep Agents example skills。