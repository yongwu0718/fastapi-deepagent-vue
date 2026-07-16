# 使用 LangSmith Deployment 和 Evaluation 实现 CI/CD 流水线

本指南演示如何为部署在 LangSmith Deployment 中的 AI agent 应用实现一个完整的 CI/CD 流水线。在本示例中，您将使用 LangGraph 开源框架来编排和构建 agent，使用 LangSmith 进行可观测性和评估。该流水线基于 cicd-pipeline-example 仓库。

## 概述

CI/CD 流水线提供：

* **自动化测试**：单元测试、集成测试和端到端测试。
* **离线评估**：使用 AgentEvals、OpenEvals 和 LangSmith 进行性能评估。
* **预览和生产部署**：使用 Control Plane API 实现自动化 staging 环境和有质量门禁的生产发布。
* **监控**：持续评估和告警。

## 流水线架构

CI/CD 流水线由几个关键组件组成，它们协同工作以确保代码质量和可靠部署：

```mermaid
graph TD
    A1[Code or Graph Change] --> B1[Trigger CI Pipeline]
    A2[Prompt Commit in PromptHub] --> B1
    A3[Online Evaluation Alert] --> B1
    A4[PR Opened] --> B1

    subgraph "Testing"
        B1 --> C1[Run Unit Tests]
        B1 --> C2[Run Integration Tests]
        B1 --> C3[Run End to End Tests]
        B1 --> C4[Run Offline Evaluations]

        C4 --> D1[Evaluate with OpenEvals or AgentEvals]
        C4 --> D2[Assertions: Hard and Soft]

        C1 --> E1[Run LangGraph Dev Server Test]
        C2 --> E1
        C3 --> E1
        D1 --> E1
        D2 --> E1
    end

    E1 --> F1[Push to Staging Deployment - Deploy to LangSmith as Development Type]

    F1 --> G1[Run Online Evaluations on Live Data]
    G1 --> H1[Attach Scores to Traces]

    H1 --> I1[If Quality Below Threshold]
    I1 --> J1[Send to Annotation Queue]
    I1 --> J2[Trigger Alert via Webhook]
    I1 --> J3[Push Trace to Golden Dataset]

    F1 --> K1[Promote to Production if All Pass - Deploy to LangSmith Production]

    J2 --> L1[Slack or PagerDuty Notification]

    subgraph Manual Review
        J1 --> M1[Human Labeling]
        M1 --> J3
    end

    classDef trigger fill:#F6FFDB,stroke:#6E8900,stroke-width:2px,color:#2E3900
    classDef process fill:#E5F4FF,stroke:#006DDD,stroke-width:2px,color:#030710
    classDef decision fill:#FDF3FF,stroke:#7E65AE,stroke-width:2px,color:#504B5F
    classDef output fill:#EBD0F0,stroke:#885270,stroke-width:2px,color:#441E33
    classDef alert fill:#F8E8E6,stroke:#B27D75,stroke-width:2px,color:#634643
    classDef neutral fill:#F2FAFF,stroke:#40668D,stroke-width:2px,color:#2F4B68

    class A1,A2,A3,A4 trigger
    class B1,C1,C2,C3,C4,D1,D2,E1 process
    class H1,I1 decision
    class F1,G1,K1 output
    class J2,L1 alert
    class J1,J3,M1 neutral
```

### 触发源

有多种方式可以触发此流水线，无论是在开发期间还是在应用已上线之后。流水线可以由以下事件触发：

* **代码变更**：推送到 main/development 分支，您可以修改 LangGraph 架构、尝试不同模型、更新 agent 逻辑或进行任何代码改进。
* **PromptHub 更新**：LangSmith PromptHub 中存储的提示模板发生变更——每当有新的提示提交时，系统会触发 webhook 来运行流水线。
* **在线评估告警**：来自生产部署的性能下降通知。
* **LangSmith traces webhooks**：基于 trace 分析和性能指标的自动触发。
* **手动触发**：为测试或紧急部署手动启动流水线。

### 测试层次

与传统软件相比，测试 AI agent 应用还需要评估响应质量，因此测试工作流的每个部分都很重要。该流水线实现了多个测试层次：

1. **单元测试**：测试单个 node 和工具函数。
2. **集成测试**：测试组件之间的交互。
3. **端到端测试**：测试完整的 graph 执行。
4. **离线评估**：使用真实场景进行性能评估，包括端到端评估、单步评估、agent 轨迹分析和多轮模拟。
5. **LangGraph dev server 测试**：使用 [langgraph-cli](/langsmith/cli) 工具在 GitHub Action 内部启动一个本地服务器来运行 LangGraph agent。该工具会轮询服务器的 `/ok` API 端点，直到可用，超时 30 秒后抛出错误。

## GitHub Actions 工作流

CI/CD 流水线使用 GitHub Actions，结合 Control Plane API 和 LangSmith API 来自动化部署。一个辅助脚本管理 API 交互和部署：https://github.com/langchain-ai/cicd-pipeline-example/blob/main/.github/scripts/langgraph_api.py

工作流包括：

* **新 agent 部署**：当打开新的 PR 且测试通过时，使用 Control Plane API 在 LangSmith Deployment 中创建一个新的预览部署。这使得您可以在提升到生产之前在 staging 环境中测试 agent。

* **Agent 部署修订**：当找到具有相同 ID 的现有部署，或者当 PR 合并到 main 分支时，就会发生修订。在合并到 main 的情况下，预览部署会被删除，并创建一个生产部署。这确保了对 agent 的任何更新都能正确部署并集成到生产基础设施中。

* **测试和评估工作流**：除了更传统的测试阶段（单元测试、集成测试、端到端测试等）之外，流水线还包括离线评估和 Agent dev server 测试，因为您需要测试 agent 的质量。这些评估使用真实场景和数据对 agent 的性能进行全面评估。


<AccordionGroup>
<Accordion title="最终响应评估" icon="circle-check">
    根据预期结果评估 agent 的最终输出。这是最常见的评估类型，检查 agent 的最终响应是否符合质量标准并正确回答用户的问题。
</Accordion>

<Accordion title="单步评估" icon="player-skip-forward">
    测试 LangGraph 工作流中的单个步骤或 node。这允许您在测试完整流水线之前，独立验证 agent 逻辑的特定组件是否正常运作。
</Accordion>

<Accordion title="Agent 轨迹评估" icon="route">
    分析 agent 在 graph 中经过的完整路径，包括所有中间步骤和决策点。这有助于识别 agent 工作流中的瓶颈、不必要的步骤或次优的路由。它还评估 agent 是否以正确的顺序或在正确的时间调用了正确的工具。
</Accordion>

<Accordion title="多轮评估" icon="messages">
    测试 agent 在多次交互中保持上下文的对话流。这对于处理后续问题、澄清或与用户进行扩展对话的 agent 至关重要。
</Accordion>
</AccordionGroup>

有关具体的测试方法，请参阅 LangGraph 测试文档；有关离线评估的全面概述，请参阅评估方法指南。

### 前提条件

在设置 CI/CD 流水线之前，请确保您具备：

* 一个 AI agent 应用程序（本例中使用 LangGraph 构建）
* 一个 LangSmith 账户（提供免费试用）
* 一个 LangSmith API key（用于部署 agent 和获取实验结果的必要凭证）
* 在仓库 secrets 中配置的项目特定环境变量（例如 LLM 模型 API key、向量存储凭证、数据库连接）

<Note>
  虽然本示例使用 GitHub，但 CI/CD 流水线也适用于其他 Git 托管平台，包括 GitLab、Bitbucket 等。
</Note>

## 部署选项

LangSmith 支持多种部署方法，具体取决于您的 LangSmith 实例的托管方式：

* **Cloud LangSmith**：直接的 GitHub 集成。
* **Self-Hosted/Hybrid**：基于容器镜像仓库的部署。

部署流程从修改您的 agent 实现开始。您的项目中至少必须有一个 `langgraph.json` 和一个依赖文件（`requirements.txt` 或 `pyproject.toml`）。使用 `langgraph dev` CLI 工具检查错误——修复所有错误；否则，部署到 LangSmith Deployment 时会失败。

```mermaid
graph TD
    A[Agent Implementation] --> B[langgraph.json + dependencies]
    B --> C[Test Locally with langgraph dev]
    C --> D{Errors?}
    D -->|Yes| E[Fix Issues]
    E --> C
    D -->|No| F[Choose LangSmith Instance]

    F --> G[Cloud LangSmith]
    F --> H[Self-Hosted/Hybrid LangSmith]

    subgraph "Cloud LangSmith"
        G --> I[Method 1: Connect GitHub Repo in UI]
        G --> J[Method 2: Control Plane API with GitHub Repo]
        I --> K[Deploy via LangSmith UI]
        J --> L[Deploy via Control Plane API]
    end

    subgraph "Self-Hosted/Hybrid LangSmith"
        H --> S[Build Docker Image langgraph build]
        S --> T[Push to Container Registry]
        T --> U{Deploy via?}
        U -->|UI| V[Specify Image URI in UI]
        U -->|API| W[Use Control Plane API]
        V --> X[Deploy via LangSmith UI]
        W --> Y[Deploy via Control Plane API]
    end

    K --> AA[Agent Ready for Use]
    L --> AA
    X --> AA
    Y --> AA

    AA --> BB{Connect via?}
    BB -->|LangGraph SDK| CC[Use LangGraph SDK]
    BB -->|RemoteGraph| DD[Use RemoteGraph]
    BB -->|REST API| EE[Use REST API]
    BB -->|LangGraph Studio UI| FF[Use LangGraph Studio UI]

    classDef trigger fill:#F6FFDB,stroke:#6E8900,stroke-width:2px,color:#2E3900
    classDef process fill:#E5F4FF,stroke:#006DDD,stroke-width:2px,color:#030710
    classDef decision fill:#FDF3FF,stroke:#7E65AE,stroke-width:2px,color:#504B5F
    classDef output fill:#EBD0F0,stroke:#885270,stroke-width:2px,color:#441E33

    class A trigger
    class B,C process
    class D,U,BB decision
    class E process
    class F decision
    class G,H process
    class I,J,S,T process
    class K,L,V,W process
    class X,Y,AA output
    class CC,DD,EE,FF output
```

### 手动部署的前提条件

在部署 agent 之前，请确保您具备：

1. **LangGraph graph**：您的 agent 实现（例如 `./agents/simple_text2sql.py:agent`）。
2. **依赖项**：包含所有必需包的 `requirements.txt` 或 `pyproject.toml`。
3. **配置文件**：`langgraph.json` 文件，指定：
   * agent graph 的路径
   * 依赖项位置
   * 环境变量
   * Python 版本

`langgraph.json` 示例：

```json
{
    "graphs": {
        "simple_text2sql": "./agents/simple_text2sql.py:agent"
    },
    "env": ".env",
    "python_version": "3.11",
    "dependencies": ["."],
    "image_distro": "wolfi"
}
```

### 本地开发和测试

首先，使用 Studio 在本地测试您的 agent：

```bash
# 启动带有 Studio 的本地开发服务器
langgraph dev
```

这将：

* 启动一个带有 Studio 的本地服务器。
* 允许您可视化和交互您的 graph。
* 在部署前验证您的 agent 是否正确工作。

<Note>
  如果您的 agent 在本地运行没有任何错误，则意味着部署到 LangSmith 很可能会成功。这种本地测试有助于在尝试部署之前发现配置问题、依赖问题和 agent 逻辑错误。
</Note>

更多详情请参阅 LangGraph CLI 文档。

### 方法 1：LangSmith Deployment UI

使用 LangSmith 部署界面部署您的 agent：

1. 转到您的 LangSmith 仪表板。
2. 导航到 **Deployments** 部分。
3. 点击右上角的 **+ New Deployment** 按钮。
4. 从下拉菜单中选择包含您 LangGraph agent 的 GitHub 仓库。

**支持的部署方式：**

* **Cloud LangSmith**：直接 GitHub 集成，通过下拉菜单选择。
* **Self-Hosted/Hybrid LangSmith**：在 Image Path 字段中指定您的镜像 URI（例如 `docker.io/username/my-agent:latest`）。

<Info>
  **优势：**

  * 基于 UI 的简单部署
  * 与您的 GitHub 仓库直接集成（云版）
  * 无需手动管理 Docker 镜像（云版）
</Info>

### 方法 2：Control plane API

使用 Control Plane API 进行部署，针对不同部署类型采用不同方式：

**对于 Cloud LangSmith：**

* 使用 Control Plane API，通过指向您的 GitHub 仓库来创建部署。
* 云部署无需构建 Docker 镜像。

**对于 Self-Hosted/Hybrid LangSmith：**

```bash
# 构建 Docker 镜像
langgraph build -t my-agent:latest

# 推送到您的容器镜像仓库
docker push my-agent:latest
```

您可以推送到部署环境有权访问的任何容器镜像仓库（Docker Hub、AWS ECR、Azure ACR、Google GCR 等）。

**支持的部署方式：**

* **Cloud LangSmith**：使用 Control Plane API 从您的 GitHub 仓库创建部署。
* **Self-Hosted/Hybrid LangSmith**：使用 Control Plane API 从您的容器镜像仓库创建部署。

更多详情请参阅 LangGraph CLI build 文档。

### 连接到已部署的 Agent

* **LangGraph SDK**：使用 LangGraph SDK 进行程序化集成。
* **RemoteGraph**：使用 RemoteGraph 连接远程 graph（以便在其他 graph 中使用您的 graph）。
* **REST API**：通过 HTTP 与已部署的 agent 进行交互。
* **Studio**：访问可视化界面进行测试和调试。

### 环境配置

#### 数据库和缓存配置

默认情况下，LangSmith Deployment 会为您创建 PostgreSQL 和 Redis 实例。要使用外部服务，请在您的新部署或修订中设置以下环境变量：

```bash
# 为外部服务设置环境变量
export POSTGRES_URI_CUSTOM="postgresql://user:pass@host:5432/db"
export REDIS_URI_CUSTOM="redis://host:6379/0"
```

更多详情请参阅环境变量文档。

## 故障排除

### 错误的 API 端点

如果您遇到连接问题，请验证您是否为 LangSmith 实例使用了正确的端点格式。有两个不同的 API，具有不同的端点：

#### LangSmith API（Traces、数据摄入等）

对于 LangSmith API 操作（traces、评估、数据集）：

| 区域      | URL                                                          |
| ------- | ------------------------------------------------------------ |
| GCP US  | `https://api.smith.langchain.com`                           |
| GCP EU  | `https://eu.api.smith.langchain.com`                        |
| GCP APAC| `https://apac.api.smith.langchain.com`                      |
| AWS US  | `https://aws.api.smith.langchain.com`                       |

对于自托管的 LangSmith 实例，使用 `http(s)://<langsmith-url>/api`，其中 `<langsmith-url>` 是您自托管实例的 URL。

<Note>
  如果您在 `LANGSMITH_ENDPOINT` 环境变量中设置端点，需要在末尾添加 `/v1`（例如，`https://api.smith.langchain.com/v1`；如果是自托管，则为 `http(s)://<langsmith-url>/api/v1`）。
</Note>

#### LangSmith Deployment API（部署）

对于 LangSmith Deployment 操作（deployments、revisions）：

| 区域      | URL                                                          |
| ------- | ------------------------------------------------------------ |
| GCP US  | `https://api.smith.langchain.com`                           |
| GCP EU  | `https://eu.api.smith.langchain.com`                        |
| GCP APAC| `https://apac.api.smith.langchain.com`                      |
| AWS US  | `https://aws.api.smith.langchain.com`                       |

对于自托管的 LangSmith 实例，使用 `http(s)://<langsmith-url>/api-host`，其中 `<langsmith-url>` 是您自托管实例的 URL。

***