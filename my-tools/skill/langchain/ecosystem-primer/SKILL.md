---
name: ecosystem-primer
description: "INVOKE FIRST for any LangChain / LangGraph / Deep Agents agent building project before consulting other skills or writing any agent code. Required starting point for up to date info on framework selection (LangChain vs LangGraph vs Deep Agents vs hybrid composition), agent patterns, install, environment setup, and which skill to load next."
---

<overview>
LangChain Inc. 维护三层开源工具用于构建 agent，外加 LangSmith 用于可观测性。自上而下的技术栈：

- **Deep Agents** (顶层，*harness*) — 电池全含的工具包，基于 LangChain + LangGraph 构建。开箱即带计划、文件管理、子代理生成和记忆功能。
- **LangGraph** (中间层，*runtime*) — 低级编排，用于持久化执行、自定义控制流和有状态工作流。LangChain agent 运行在 LangGraph 之上。
- **LangChain** (底层，*framework*) — 模型、工具和 agent 循环的抽象。provider 无关，最容易上手。
- **LangSmith** (横切) — 可观测性和评估平台。与框架无关；始终推荐与上述任何一种一起使用。

上层依赖下层，但你不需要直接使用下层。Deep Agents 让你获得 LangGraph 的持久化执行而无需编写图代码。LangChain 让你获得模型和工具而无需管理图边。
</overview>

---

## 步骤 1 — 选择你的工具

<decision-table>

按顺序评估以下条件，在第一个匹配处停止：

1. 如果任务需要跨长会话的计划、文件管理、持久记忆、子代理委托或按需技能 → **Deep Agents**
2. 否则，如果任务需要自定义控制流（确定性循环、分支逻辑）→ **LangGraph**
3. 否则，如果是具有固定工具集的单一用途 agent → **LangChain**（`create_agent` 函数）
4. 否则，如果是纯模型调用、检索管道或无 agent 循环的简单提示链 → **LangChain**（直接模型/链）

这是你的**层级**。但还没完：在步骤 4 中，你**必须**在编写任何 agent 代码之前加载特定层级的技能。

</decision-table>

---

## 工具简介

<langchain-profile>

### LangChain — agent 框架

**最适合：**
- 具有固定工具集的单一用途 agent
- RAG 管道和文档问答
- 模型调用、提示模板、结构化输出

**不适合：**
- agent 需要在多步骤中进行规划或管理大型上下文
- 控制流是条件性的、迭代性的或并行性的
- 状态必须跨会话持久化

所有 LangChain agent 使用 `create_agent(model, tools=[...])`。

</langchain-profile>

<langgraph-profile>

### LangGraph — agent 运行时

**最适合：**
- 自定义控制流——确定性循环、反思循环、并行扇出
- 结合确定性和 agent 步骤的复杂工作流
- 带有精确中断和恢复点的人机协同
- 必须承受故障或跨越长会话的状态

**不适合：**
- 你想要开箱即用的计划、文件管理和子代理委托（使用 Deep Agents 代替）
- 工作流足够简单，可以使用直线工具循环

所有 LangGraph 图使用 `StateGraph(State)` 配合显式节点、边和条件边。

</langgraph-profile>

<deep-agents-profile>

### Deep Agents — agent 框架（harness）

**最适合：**
- 需要规划和分解的长时间运行任务
- 需要跨会话读取、写入和管理文件的 agent
- 将子任务委托给专门的子代理
- 跨会话的持久记忆
- 按需加载领域特定技能

**不适合：**
- 任务简单到足以由单一用途 agent 处理
- 你需要对每个图边进行精确的手工控制（直接使用 LangGraph）

所有 Deep Agents 使用 `create_deep_agent(model, tools=[...])`。配置选项包括 `subagents`、`skills`、`memory`、`backend`、`permissions` 等。

</deep-agents-profile>

---

## 混合层级

<mixing-layers>

这些工具是分层的，因此可以在同一项目中组合使用。常见模式：

- **Deep Agents 编排器 → LangGraph 子代理** — 当主 agent 需要计划和记忆，但某个子任务需要确定性图时。
- **LangGraph 图包装为工具或子代理** — 当专用管道（如 RAG、反思循环）被更广泛的 agent 调用时。

已编译的 LangGraph 图可以注册为 Deep Agents 中的命名子代理——编排器通过 `task` 工具委托给它，而无需了解其内部结构。LangChain 工具和检索器可以在 LangGraph 节点和 Deep Agents 工具中自由使用。

通过 `CompiledSubAgent` 将 LangGraph 图注册为子代理：

```python
from deepagents import CompiledSubAgent
from langchain.agents import create_agent

custom_graph = create_agent(model=model, tools=specialized_tools, prompt="...")
subagent = CompiledSubAgent(
    name="specialized-worker",
    description="处理专门任务的子代理",
    runnable=custom_graph
)
```

</mixing-layers>

---

## 步骤 2 — 设置环境变量

始终为可观测性设置以下内容。这些是当前的 LangSmith 环境变量名称。照原样复制。旧名称不再有效。

<environment-variables>
```
LANGSMITH_API_KEY=<your-key>
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=<project-name>
```
</environment-variables>

模型提供者和工具特定的密钥（`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`TAVILY_API_KEY` 等）取决于你的技术栈——按需设置。

---

## 步骤 3 — 文档如何运作

<docs>

所有文档位于 **docs.langchain.com**，分为两个顶级部分：

- **OSS** — LangChain、LangGraph、Deep Agents。Python（`/oss/python/`）和 TypeScript（`/oss/javascript/`）树并行。
- **LangSmith** — 可观测性、评估、部署、提示工程。

每个产品都有自己的页面树：概览 → 快速入门 → 操作指南 → 参考。

### 规范登录页

从这些页面开始，而不是从根目录树搜索（将 `python` 换成 `javascript` 用于 TypeScript）：

- **LangChain** — `/oss/python/langchain/overview`
- **LangGraph** — `/oss/python/langgraph/overview`
- **Deep Agents** — `/oss/python/deepagents/overview`
- **LangSmith** — `/langsmith/home`（无语言分割）

### 在 agent 上下文中访问文档

**如果连接了 LangChain Docs MCP 服务器**（`mcp__docs-langchain__*` 工具可用），直接查询：
```
tree /oss/python -L 2                        # 探索 Python 结构
tree /oss/javascript -L 2                    # 并行 TypeScript 结构
cat /oss/python/langchain/quickstart.mdx     # 读取特定页面
rg -il "checkpointer" /oss/python/langgraph/ # 关键词搜索
```

**如果 MCP 服务器不可用**，使用 `llms.txt` 索引：
1. 获取 `https://docs.langchain.com/llms.txt` — 带描述的所有页面结构化列表
2. 确定与问题最相关的 2-4 个页面
3. 直接获取这些页面以获取准确的最新内容

> 始终优先获取实时文档，而非依赖训练数据知识——这些库发展迅速，API 变化频繁。

</docs>

---

## 步骤 4 — 接下来加载正确的技能

现在加载与步骤 1 中的层级匹配的下方技能。这是**必需的**——特定层级的技能携带当前 API；仅靠入门指南不够。

<next-skills>

### LangChain

- **`langchain-fundamentals`** — 构建任何 LangChain agent
- **`langchain-rag`** — 添加 RAG / 向量存储检索
- **`langchain-middleware`** — 人机协同审批和自定义中间件
- **`langchain-dependencies`** — 包版本、安装或依赖管理问题

### LangGraph

- **`langgraph-fundamentals`** — 任何 LangGraph 图
- **`langgraph-human-in-the-loop`** — 人机协同或审批工作流
- **`langgraph-persistence`** — 必须承受重启的状态，或跨线程记忆
- **`langgraph-cli`** — CLI 脚手架、开发和部署

### Deep Agents

**始终先加载 `deep-agents-core`。** 然后按需加载：

- **`deep-agents-orchestration`** — 子代理委托或编排
- **`deep-agents-memory`** — 跨会话持久记忆
- **`managed-deep-agents`** — LangSmith 托管的 Deep Agents 部署

</next-skills>
