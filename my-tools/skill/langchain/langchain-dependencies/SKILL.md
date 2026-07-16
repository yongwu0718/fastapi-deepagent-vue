---
name: langchain-dependencies
description: "INVOKE THIS SKILL when setting up a new project or when asked about package versions, installation, or dependency management for LangChain, LangGraph, LangSmith, or Deep Agents. Covers required packages, minimum versions, environment requirements, versioning best practices, and common community tool packages for both Python and TypeScript."
---

<overview>
LangChain 生态系统分为独立版本化、专注的包。了解你需要的包及其版本约束可以防止不兼容问题并保持升级可预测。

**核心原则：**
- **LangChain 1.0 是当前 LTS 版本。** 始终使用 1.0+ 开始新项目。LangChain 0.3 仅用于遗留维护——不要在新工作中使用。
- **langchain-core** 是共享基础：始终与其他包一起显式安装。
- **langchain-community**（仅 Python）不遵循语义化版本控制；保守地固定版本。
- **LangGraph vs Deep Agents：** 根据你的用例选择一种编排方式——它们是替代品，而非必需的技术栈（见下方[框架选择](#framework-choice)）。
- Provider 集成（模型、向量存储、工具）单独安装，因此你只需引入使用的部分。
</overview>

---

## 环境要求

<environment-requirements>

| 要求 | Python | TypeScript / Node |
|------|--------|-------------------|
| 运行时最低版本 | **Python 3.10+** | **Node.js 20+** |
| LangChain | **1.0+ (LTS)** | **1.0+ (LTS)** |
| LangSmith SDK | >= 0.3.0 | >= 0.3.0 |

</environment-requirements>

---

## 框架选择

<framework-choice>
选择**一种** agent 编排层。你不需要两者都选。

| 框架 | 使用时机 | 核心额外包 |
|------|----------|------------|
| **LangGraph** | 需要精细的图控制、自定义工作流、循环或分支 | `langgraph` / `@langchain/langgraph` |
| **Deep Agents** | 想要电池全含的计划、记忆、文件上下文和技能 | `deepagents`（依赖 LangGraph 并作为传递依赖安装） |

两者都基于 `langchain` + `langchain-core` + `langsmith`。
</framework-choice>

---

## 核心包

<python-packages>

### Python — 始终需要

| 包 | 作用 | 最低版本 |
|----|------|----------|
| `langchain` | agent、链、检索 | 1.0 |
| `langchain-core` | 基础类型和接口（peer dep） | 1.0 |
| `langsmith` | 追踪、评估、数据集 | 0.3.0 |

### Python — 编排（选一个）

| 包 | 使用时机 | 最低版本 |
|----|----------|----------|
| `langgraph` | 直接构建自定义图 | 1.0 |
| `deepagents` | 使用 Deep Agents 框架 | latest |

### Python — 模型 provider（选择你使用的）

| 包 | Provider |
|----|----------|
| `langchain-openai` | OpenAI（GPT-4.1、GPT-5.4、GPT-5-nano、o3、o4-mini） |
| `langchain-anthropic` | Anthropic（Claude Sonnet 4.6、Claude Opus 4.6） |
| `langchain-google-genai` | Google（Gemini 2.5 Pro/Flash、Gemini 3.1 Pro） |
| `langchain-mistralai` | Mistral |
| `langchain-groq` | Groq（快速推理） |
| `langchain-cohere` | Cohere |
| `langchain-fireworks` | Fireworks AI |
| `langchain-together` | Together AI |
| `langchain-huggingface` | Hugging Face Hub |
| `langchain-ollama` | Ollama（本地模型） |
| `langchain-aws` | AWS Bedrock |
| `langchain-azure-ai` | Azure AI Foundry |

### Python — 常见工具和检索包

这些包有更严格的兼容性要求——使用最新可用版本，除非有特定原因不这样做。

| 包 | 增加 | 备注 |
|----|------|------|
| `langchain-tavily` | Tavily 网络搜索（`TavilySearch`） | 专用集成包；推荐最新版 |
| `langchain-text-splitters` | 文本分块工具 | 语义化版本，保持最新 |
| `langchain-community` | 1000+ 集成（回退） | **非语义化版本——固定到小版本系列** |
| `faiss-cpu` | FAISS 向量存储（本地） | 通过 `langchain-community`；使用最新版 |
| `langchain-chroma` | Chroma 向量存储 | 专用集成包；推荐最新版 |
| `langchain-pinecone` | Pinecone 向量存储 | 专用集成包；推荐最新版 |
| `langchain-qdrant` | Qdrant 向量存储 | 专用集成包；推荐最新版 |
| `langchain-weaviate` | Weaviate 向量存储 | 专用集成包；推荐最新版 |
| `langsmith[pytest]` | pytest 的 LangSmith 插件 | 需要 langsmith >= 0.3.4 |

> **langchain-community 稳定性说明：** 此包不遵循语义化版本控制。小版本可能包含破坏性更改。当存在专用集成包（如 `langchain-chroma`、`langchain-tavily`）时，优先使用它们——它们独立版本化且更稳定。

</python-packages>

<typescript-packages>

### TypeScript — 始终需要

| 包 | 作用 | 最低版本 |
|----|------|----------|
| `@langchain/core` | 基础类型和接口（peer dep） | 1.0 |
| `langchain` | agent、链、检索 | 1.0 |
| `langsmith` | 追踪、评估、数据集 | 0.3.0 |

### TypeScript — 编排（选一个）

| 包 | 使用时机 | 最低版本 |
|----|----------|----------|
| `@langchain/langgraph` | 直接构建自定义图 | 1.0 |
| `deepagents` | 使用 Deep Agents 框架 | latest |

### TypeScript — 模型 provider（选择你使用的）

| 包 | Provider |
|----|----------|
| `@langchain/openai` | OpenAI（GPT-4o、GPT-5.4、o3 等） |
| `@langchain/anthropic` | Anthropic（Claude） |
| `@langchain/google-genai` | Google（Gemini） |
| `@langchain/mistralai` | Mistral |
| `@langchain/groq` | Groq（快速推理） |
| `@langchain/cohere` | Cohere |
| `@langchain/aws` | AWS Bedrock |
| `@langchain/azure-openai` | Azure OpenAI |
| `@langchain/ollama` | Ollama（本地模型） |

### TypeScript — 常见工具和检索包

| 包 | 增加 | 备注 |
|----|------|------|
| `@langchain/tavily` | Tavily 网络搜索 | 专用集成包；推荐最新版 |
| `@langchain/community` | 广泛的社区集成 | 谨慎使用；优先使用专用包 |
| `@langchain/pinecone` | Pinecone 向量存储 | 专用集成包；推荐最新版 |
| `@langchain/qdrant` | Qdrant 向量存储 | 专用集成包；推荐最新版 |
| `@langchain/weaviate` | Weaviate 向量存储 | 专用集成包；推荐最新版 |

> **`@langchain/core` 必须在 yarn workspaces 和 monorepos 中显式安装**——它是 peer dependency，不会总是自动提升。

</typescript-packages>

---

## 最小项目模板

<ex-langgraph-python>
<python>
LangGraph 项目的最小依赖集（provider 无关）。

```
# requirements.txt
langchain>=1.0,<2.0
langchain-core>=1.0,<2.0
langgraph>=1.0,<2.0
langsmith>=0.3.0

# 添加你的模型 provider，例如：
# langchain-openai
# langchain-anthropic
# langchain-google-genai
```
</python>
</ex-langgraph-python>

<ex-langgraph-typescript>
<typescript>
LangGraph 项目的最小 package.json 依赖（provider 无关）。

```json
{
  "dependencies": {
    "@langchain/core": "^1.0.0",
    "langchain": "^1.0.0",
    "@langchain/langgraph": "^1.0.0",
    "langsmith": "^0.3.0"
  }
}
```
</typescript>
</ex-langgraph-typescript>

<ex-deepagents-python>
<python>
Deep Agents 项目的最小依赖集（provider 无关）。

```
# requirements.txt
deepagents            # 内部捆绑 langgraph
langchain>=1.0,<2.0
langchain-core>=1.0,<2.0
langsmith>=0.3.0

# 添加你的模型 provider，例如：
# langchain-anthropic
# langchain-openai
```
</python>
</ex-deepagents-python>

<ex-deepagents-typescript>
<typescript>
Deep Agents 项目的最小 package.json 依赖（provider 无关）。

```json
{
  "dependencies": {
    "deepagents": "latest",
    "@langchain/core": "^1.0.0",
    "langchain": "^1.0.0",
    "langsmith": "^0.3.0"
  }
}
```
</typescript>
</ex-deepagents-typescript>

<ex-with-tools-python>
<python>
向 LangGraph 项目添加 Tavily 搜索和向量存储。

```
# requirements.txt
langchain>=1.0,<2.0
langchain-core>=1.0,<2.0
langgraph>=1.0,<2.0
langsmith>=0.3.0

# 网络搜索
langchain-tavily          # 使用最新版；合作伙伴包，语义化版本

# 向量存储——选一个：
langchain-chroma          # 使用最新版；合作伙伴包，语义化版本
# langchain-pinecone      # 使用最新版；合作伙伴包，语义化版本
# langchain-qdrant        # 使用最新版；合作伙伴包，语义化版本

# 文本处理
langchain-text-splitters  # 使用最新版；语义化版本

# 你的模型 provider：
# langchain-openai / langchain-anthropic / 等
```
</python>
</ex-with-tools-python>

<ex-with-tools-typescript>
<typescript>
向 LangGraph 项目添加 Tavily 搜索和向量存储。

```json
{
  "dependencies": {
    "@langchain/core": "^1.0.0",
    "langchain": "^1.0.0",
    "@langchain/langgraph": "^1.0.0",
    "langsmith": "^0.3.0",
    "@langchain/tavily": "latest",
    "@langchain/pinecone": "latest"
  }
}
```
</typescript>
</ex-with-tools-typescript>

---

## 版本策略和升级策略

<versioning-policy>

| 包组 | 版本控制 | 安全升级策略 |
|------|----------|-------------|
| `langchain`、`langchain-core` | 严格语义化版本（1.0 LTS） | 允许小版本：`>=1.0,<2.0` |
| `langgraph` / `@langchain/langgraph` | 严格语义化版本（v1 LTS） | 允许小版本：`>=1.0,<2.0` |
| `langsmith` | 严格语义化版本 | 允许小版本：`>=0.3.0` |
| 专用集成包（如 `langchain-tavily`、`langchain-chroma`） | 独立版本化 | 允许小版本更新；使用最新版 |
| `langchain-community` | **非语义化版本** | 固定确切小版本：`>=0.4.0,<0.5.0` |
| `deepagents` | 跟随项目发布 | 生产环境固定到已测试版本 |

**破坏性更改仅在大版本中发生**（1.x → 2.x），适用于所有遵循语义化版本的包。弃用功能在整个 1.x 系列中保持功能运作并发出警告。

**优先使用专用集成包而非 langchain-community。** 当存在专用包（如 `langchain-chroma` 替代 `langchain-community` 的 Chroma 集成）时，使用专用包——它们独立版本化且经过更好测试。

**社区工具包（Tavily、向量存储等）应保持最新版本**，除非你的项目需要锁定环境。这些包频繁发布与 LangChain/LangGraph 更新配套的兼容性修复。

</versioning-policy>

---

## 环境变量

<environment-variables>
所有密钥在运行时从环境中读取。仅设置你实际使用的服务的密钥。

```bash
# LangSmith（始终推荐用于可观测性）
LANGSMITH_API_KEY=<your-key>
LANGSMITH_PROJECT=<project-name>   # 可选，默认 "default"

# 模型 provider——设置你使用的
OPENAI_API_KEY=<your-key>
ANTHROPIC_API_KEY=<your-key>
GOOGLE_API_KEY=<your-key>
MISTRAL_API_KEY=<your-key>
GROQ_API_KEY=<your-key>
COHERE_API_KEY=<your-key>
FIREWORKS_API_KEY=<your-key>
TOGETHER_API_KEY=<your-key>
HUGGINGFACEHUB_API_TOKEN=<your-key>

# 常见工具/检索服务
TAVILY_API_KEY=<your-key>          # Tavily 搜索
PINECONE_API_KEY=<your-key>        # Pinecone
```
</environment-variables>

---

## 常见错误

<fix-legacy-version>
绝不在新项目中使用 LangChain 0.3。它仅维护至 2026 年 12 月。

```
# 错误：遗留版本，无新功能，仅安全补丁
langchain>=0.3,<0.4

# 正确：LangChain 1.0 LTS
langchain>=1.0,<2.0
```
</fix-legacy-version>

<fix-community-unpinned>
`langchain-community` 可能在小版本升级时破坏——它不遵循语义化版本。

```
# 错误：允许可能是破坏性的小版本更新
langchain-community>=0.4

# 正确：固定到确切小版本系列
langchain-community>=0.4.0,<0.5.0
```
如果存在等效的专用集成包（如 `langchain-chroma` 替代社区 Chroma 集成），也应考虑切换。
</fix-community-unpinned>

<fix-community-tool-outdated>
像 `langchain-tavily` 和向量存储集成等社区工具包与 LangChain 更新配套发布兼容性修复。使用旧的固定版本可能导致导入错误或工具模式损坏。

```
# 风险：旧的固定版本可能与 LangChain 1.0 不兼容
langchain-tavily==0.0.1

# 更好：允许当前大版本内的最新版本
langchain-tavily>=0.1
```
</fix-community-tool-outdated>

<fix-community-import-deprecated>
许多以前存在于 `langchain-community` 中的工具现在有了专用包和更新的导入路径。始终优先使用专用包导入。

```python
# 错误——已弃用的社区导入路径
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores import Pinecone

# 正确——使用专用包导入
from langchain_tavily import TavilySearch                  # pip: langchain-tavily
from langchain_chroma import Chroma                       # pip: langchain-chroma
from langchain_pinecone import PineconeVectorStore        # pip: langchain-pinecone
```

在 https://python.langchain.com/docs/integrations/tools/ 搜索集成目录以查找每个集成的当前规范导入。
</fix-community-import-deprecated>

<fix-core-not-installed>
<typescript>
`@langchain/core` 是 peer dependency——必须在你的 package.json 中，尤其在 monorepos 中。

```json
// 错误：缺少 @langchain/core（在 yarn workspaces / 严格提升中会破坏）
{
  "dependencies": {
    "@langchain/langgraph": "^1.0.0"
  }
}

// 正确：始终显式列出 @langchain/core
{
  "dependencies": {
    "@langchain/core": "^1.0.0",
    "@langchain/langgraph": "^1.0.0"
  }
}
```
</typescript>
</fix-core-not-installed>

<fix-python-version>
<python>
Python 3.9 及以下不受 LangChain 1.0 支持。

```python
# 安装前验证
import sys
assert sys.version_info >= (3, 10), "LangChain 1.0 需要 Python 3.10+"
```
</python>
</fix-python-version>

<fix-node-version>
<typescript>
Node.js 20 以下不受官方支持。

```bash
# 安装前验证
node --version   # 必须是 v20.x 或更高
```
</typescript>
</fix-node-version>
