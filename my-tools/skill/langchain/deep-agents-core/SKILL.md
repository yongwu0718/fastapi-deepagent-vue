---
name: deep-agents-core
description: "INVOKE THIS SKILL when building ANY Deep Agents application. Covers create_deep_agent(), harness architecture, HarnessProfile, SKILL.md format, backends, permissions, and configuration options."
---

## overview
Deep Agents 是一个基于 LangChain/LangGraph 构建的 opinionated 代理框架（harness），内置以下能力：

- **规划能力（Planning）**: TodoListMiddleware — 将复杂任务分解为结构化步骤
- **虚拟文件系统（Virtual Filesystem）**: 可插拔后端（State/Filesystem/Store/Composite），提供 `ls`、`read_file`、`write_file`、`edit_file`、`glob`、`grep` 工具
- **文件系统权限（Permissions）**: 声明式权限规则，控制代理的文件读写范围
- **任务委派（Subagents）**: SubAgentMiddleware — 创建隔离的子代理执行专业化任务
- **上下文与令牌管理（Context Engineering）**: 自动处理上下文压缩与隔离
- **长期记忆（Memory）**: 跨会话持久存储，通过 Store 后端支持
- **人机协同（Human-in-the-loop）**: HumanInTheLoopMiddleware — 敏感操作需人工审批
- **技能（Skills）**: 按需加载领域专业知识（渐进式披露）
- **框架配置文件（HarnessProfile）**: 按模型定制框架行为

## when-to-use

| 使用 Deep Agents | 使用 LangChain create_agent |
|---|---:|
| 需要规划的多步骤任务 | 简单的单目标任务 |
| 大上下文需要文件管理 | 上下文适配单个 prompt |
| 需要专门的子代理 | 单一代理足够 |
| 跨会话持久记忆 | 临时单会话工作 |
| 按需加载领域技能 | 固定工具集 |

使用deepagents创建agent,使用参考配置工厂函数[deepagent](reference/create_deep_agent.md)),

使用langchain创建agent,使用参考配置工厂函数[langchain](reference/create_agent.md)),

## middleware-selection

| 需求 | 中间件 | 备注 |
|------|--------|------|
| 跟踪复杂任务 | TodoListMiddleware | 默认启用 |
| 管理文件上下文 | FilesystemMiddleware | 配置 backend|
| 委派工作 | SubAgentMiddleware | 添加自定义子代理 |
| 添加人工审批 | HumanInTheLoopMiddleware | 需要 checkpointer |
| 加载技能 | SkillsMiddleware | 提供技能目录 |
| 访问记忆 | MemoryMiddleware | 需要 Store 实例 |

## basic-agent

创建基本 Deep Agent，含自定义工具和调用示例。

```python
from deepagents import create_deep_agent
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气。"""
    return f"{city} 的天气总是晴天"

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="你是一个有帮助的助手"
)

config = {"configurable": {"thread_id": "user-123"}}
result = agent.invoke({
    "messages": [{"role": "user", "content": "东京的天气怎么样？"}]
}, config=config)
```

## ex-full-configuration

配置完整的 Deep Agent，包含子代理、技能、持久化和权限。

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

agent = create_deep_agent(
    name="my-assistant",
    model="claude-sonnet-4-6",
    tools=[custom_tool1, custom_tool2],
    system_prompt="自定义指令",
    subagents=[research_agent, code_agent],
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
    interrupt_on={"write_file": True},
    skills=["./skills/"],
    checkpointer=MemorySaver(),
    store=InMemoryStore(),
    permissions=[
        {"operations": ["read"], "paths": ["/workspace/**"], "mode": "allow"},
        {"operations": ["write"], "paths": ["/workspace/**"], "mode": "allow"},
        {"operations": ["read"], "paths": [".env"], "mode": "deny"},
    ]
)
```

## built-in-tools
每个 Deep Agent 都拥有以下内置工具：

1. **规划**: `write_todos` — 以状态（`pending`/`in_progress`/`completed`）跟踪多步骤任务，持久化在 agent 状态中
2. **文件系统**: `ls`、`read_file`、`write_file`、`edit_file`、`glob`、`grep` — 虚拟文件系统操作
3. **委派**: `task` — 生成专门的子代理执行隔离任务

---

## permissions

权限规则按声明顺序以"最先匹配优先"语义求值。每条规则由 `operations`（`"read"` 或 `"write"`）、`paths`（glob 模式）和 `mode`（`"allow"` 或 `"deny"`）组成。如果没有规则匹配，则允许操作。

权限不适用于沙箱后端（Sandbox Backend），因为沙箱支持通过 `execute` 工具执行任意命令。

---

## HarnessProfile（框架配置文件）

HarnessProfile 允许按模型定制框架行为：排除/替换内置工具、定制通用子代理等。

```python
from deepagents import HarnessProfile, register_harness_profile

# 隐藏文件系统工具（保留 FilesystemMiddleware，但不向模型暴露工具）
register_harness_profile(
    "anthropic:claude-sonnet-4-6",
    HarnessProfile(
        excluded_tools=frozenset(
            {"ls", "read_file", "write_file", "edit_file", "glob", "grep"}
        ),
    ),
)
```

注意：`excluded_middleware` 移除 `FilesystemMiddleware` 本身会被有意拒绝——请使用 `excluded_tools` 仅隐藏工具接口。

---

## SKILL.md 格式

Skills 使用**渐进式披露**——agents 仅在相关时加载内容。

### 目录结构

```
skills/
└── my-skill/
    ├── SKILL.md        # 必需：主技能文件
    ├── examples.py     # 可选：辅助文件
    └── templates/      # 可选：模板
```

### SKILL.md 格式

```markdown
---
name: my-skill
description: 清晰、具体地描述此技能的功能
---

# Skill Name

## Overview
简要说明技能的目的。

## When to Use
此技能适用的条件。

## Instructions
给 agent 的逐步指导。
```

## skills-vs-memory

| Skills | Memory (AGENTS.md) |
|--------|-------------------|
| 按需加载 | 启动时始终加载 |
| 任务特定指令 | 通用偏好设置 |
| 大型文档 | 紧凑上下文 |
| 目录中的 SKILL.md | 单个 AGENTS.md 文件 |


## ex-skills-with-filesystem-backend

创建一个有技能目录和文件系统后端的 agent，实现按需技能加载。

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
    skills=["./skills/"],
    checkpointer=MemorySaver()
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "使用 python-testing 技能"}]
}, config={"configurable": {"thread_id": "session-1"}})
```

## ex-skills-with-store-backend

将技能内容加载到 Store 后端，适用于没有文件系统访问的环境。

```python
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# 将技能内容加载到 store
skill_content = """---
name: python-testing
description: Python 测试最佳实践，含 pytest
---
# Python Testing Skill
..."""

store.put(
    namespace=("filesystem",),
    key="/skills/python-testing/SKILL.md",
    value=create_file_data(skill_content)
)

agent = create_deep_agent(
    backend=lambda rt: StoreBackend(rt),
    store=store,
    skills=["/skills/"]
)
```

## ex-harness-profile-customize

使用 HarnessProfile 定制通用子代理的行为。

```python
from deepagents import (
    create_deep_agent, HarnessProfile,
    register_harness_profile, GeneralPurposeSubagentProfile,
)

# 重命名通用子代理并自定义其系统提示
register_harness_profile(
    "anthropic:claude-sonnet-4-6",
    HarnessProfile(
        general_purpose_subagent=GeneralPurposeSubagentProfile(
            name="helper",
            system_prompt="你是一个专注的代码助手。",
        ),
    ),
)

# 完全禁用通用子代理（需要同时不传 sync subagents）
register_harness_profile(
    "anthropic:claude-sonnet-4-6",
    HarnessProfile(
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
)

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    subagents=[],  # 不传任何同步子代理
)
```

## bound

### Agent 可以配置的内容

- 模型选择和参数
- 额外的自定义工具
- 系统提示自定义
- 后端存储策略
- 哪些工具需要审批（interrupt_on）
- 带有专用工具的自定义子代理
- 文件系统权限规则
- 通过 HarnessProfile 定制框架行为（排除工具、定制通用子代理）

### Agent 不能配置的内容

- 通过 excluded_middleware 移除核心中间件（TodoList、Filesystem、SubAgent）
- 修改 write_todos、task 或文件系统工具名称
- 修改 SKILL.md frontmatter 格式

## fix-checkpointer-for-interrupts

中断需要 checkpointer。

```python
# 错误
agent = create_deep_agent(interrupt_on={"write_file": True})

# 正确
agent = create_deep_agent(interrupt_on={"write_file": True}, checkpointer=MemorySaver())
```

## fix-store-for-memory

StoreBackend 需要 Store 实例才能实现跨线程持久记忆。

```python
# 错误
agent = create_deep_agent(backend=lambda rt: StoreBackend(rt))

# 正确
agent = create_deep_agent(backend=lambda rt: StoreBackend(rt), store=InMemoryStore())
```

## fix-thread-id-for-conversations
使用一致的 thread_id 来在多次调用间保持对话上下文。

```python
# 错误：每次调用都是隔离的
agent.invoke({"messages": [{"role": "user", "content": "你好"}]})
agent.invoke({"messages": [{"role": "user", "content": "我之前说了什么？"}]})

# 正确
config = {"configurable": {"thread_id": "user-123"}}
agent.invoke({"messages": [...]}, config=config)
agent.invoke({"messages": [...]}, config=config)
```

## fix-frontmatter-required

```markdown
# 错误：SKILL.md 缺少 frontmatter
# My Skill
这是我的技能...

# 正确：包含 YAML frontmatter
---
name: my-skill
description: Python 测试最佳实践，含 pytest fixtures 和 mocking
---
# My Skill
这是我的技能...
```

## fix-backend-for-skills

Skills 需要合适的后端才能从文件系统加载。

```python
# 错误：没有合适的后端，Skills 无法加载
agent = create_deep_agent(skills=["./skills/"])

# 正确：使用 FilesystemBackend 加载本地 skills
agent = create_deep_agent(
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
    skills=["./skills/"]
)
```

## fix-specific-skill-descriptions
使用具体的描述帮助 agent 决定何时使用技能。

```markdown
# 错误：模糊的描述
---
name: helper
description: 有帮助的技能
---

# 正确：具体的描述
---
name: python-testing
description: Python 测试最佳实践，含 pytest fixtures、mocking 和异步模式
---
```

##fix-subagent-skills
技能不会被自定义子代理继承——需要显式提供。通用子代理（general-purpose）会继承主 agent 的技能。

```python
# 错误：自定义子代理不继承技能
agent = create_deep_agent(
    skills=["/main-skills/"],
    subagents=[{"name": "helper", ...}]  # 没有技能
)

# 正确：显式提供技能
agent = create_deep_agent(
    skills=["/main-skills/"],
    subagents=[{"name": "helper", "skills": ["/helper-skills/"], ...}]
)
```

## fix-harness-profile-excluded-tools
使用 excluded_tools 隐藏工具，而不是 excluded_middleware。

```python
# 正确：通过 HarnessProfile 排除工具
from deepagents import HarnessProfile, register_harness_profile

register_harness_profile(
    "anthropic:claude-sonnet-4-6",
    HarnessProfile(
        excluded_tools=frozenset({"ls", "read_file", "write_file", "edit_file", "glob", "grep"}),
    ),
)
```
