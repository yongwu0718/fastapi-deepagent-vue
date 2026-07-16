# 后端

> 这是 Deep Agents 文件系统后端的**概念地图**，涵盖后端类型、路由策略、自定义实现、权限与安全模型、以及策略扩展。
> 阅读本文档可一次性掌握后端领域的全部概念及其关联，为选型和扩展提供决策支撑。

***

## 概念全景

Deep Agents 通过 `ls`、`read_file`、`write_file`、`edit_file`、`glob`、`grep` 等工具暴露虚拟文件系统，这些工具均基于**可插拔后端**运行。`read_file` 在所有后端中原生支持多模态图像（`.png`、`.jpg`、`.jpeg`、`.gif`、`.webp`）。沙箱后端与 `LocalShellBackend` 还提供 `execute` 工具。

| 工具           | 描述                                                       |
| ------------ | -------------------------------------------------------- |
| `ls`         | 列出目录中的文件及元数据（大小、修改时间）                                    |
| `read_file`  | 读取带行号的文件内容，支持对大文件进行偏移/限制。还支持为非文本文件（图像、视频、音频和文档）返回多模态内容块。 |
| `write_file` | 创建新文件                                                    |
| `edit_file`  | 在文件中执行精确的字符串替换（支持全局替换模式）                                 |
| `glob`       | 查找匹配模式的文件（例如 `**/*.py`）                                  |
| `grep`       | 搜索文件内容，支持多种输出模式（仅文件名、带上下文的内容或计数）                         |
| `execute`    | 在环境中运行 shell 命令（仅在沙箱后端可用）                                |

核心决策点：**后端决定了文件存储位置、持久化范围、安全隔离程度以及是否提供 Shell 执行。**

***

## 1. 内置后端类型与用途

| 后端                    | 持久化范围            | 核心特征                                                   | 适用场景                                                   |
| --------------------- | ---------------- | ------------------------------------------------------ | ------------------------------------------------------ |
| **StateBackend** (默认) | 单线程              | 存储于 LangGraph 状态，通过检查点跨回合持久化；不跨线程共享                    | 暂存中间结果，自动卸载大工具输出                                       |
| **FilesystemBackend** | 本机磁盘             | 可配置 `root_dir` 读写真实文件；支持 `virtual_mode` 路径沙箱化          | 本地开发 CLI、CI/CD 流水线（需严格限制根路径）                           |
| **LocalShellBackend** | 本机磁盘 + 系统 Shell  | 继承 `FilesystemBackend`，额外提供 `execute` 工具，直接在主机运行命令，无隔离 | 个人开发环境、受信任的编码助手；生产环境禁用                                 |
| **StoreBackend**      | 跨线程持久            | 存储于 LangGraph `BaseStore`，可实现跨会话长期记忆；需提供 `store` 参数    | 用户偏好、长期知识库，多用户部署需配置命名空间隔离                              |
| **ContextHubBackend** | LangSmith Hub 仓库 | 文件持久化在 Hub 仓库中，带提交历史；依赖 `LANGSMITH_API_KEY`            | 无外部存储时的持久化替代，利用 Hub 版本管理                               |
| **CompositeBackend**  | 组合路由             | 根据路径前缀将不同路径映射到不同后端，兼顾线程作用域与跨线程持久化                      | 混合存储策略（如 `/memories/` 用 StoreBackend，其余用 StateBackend） |
| **沙箱后端**              | 隔离环境             | 在 Modal、Daytona、Deno 等沙箱中提供文件系统 + `execute`            | 生产级隔离执行，适合不受信任代码或需要环境一致性场景                             |

### 关键关联

- 所有后端均遵循 `BackendProtocol`，确保工具层无感知切换。
- `CompositeBackend` 是连接短期状态与长期记忆的枢纽。
- 沙箱后端和 `LocalShellBackend` 是唯一提供任意命令执行的类型，与“代码执行”模块直接关联。
- `FilesystemBackend` 和 `LocalShellBackend` 存在显著安全风险，必须配合人机协同（HITL）或权限策略。

***

## 2. 后端选择与配置

### 默认行为

不显式指定时，代理使用 `StateBackend`（线程作用域，适合临时工作空间）。

### 显式传递后端实例

```python
agent = create_deep_agent(
    model="...",
    backend=FilesystemBackend(root_dir="/path", virtual_mode=True)
)
```

- 路径要求：`root_dir` 必须是绝对路径,是绝对路径指向的文件夹；`virtual_mode=True` 阻止 `..`、`~` 和根目录外访问。
- 安全铁律：即使设置了 `root_dir`，默认 `virtual_mode=False` 也不提供任何安全保障；生产环境务必启用 `virtual_mode` 或使用沙箱。

### 运行时上下文与命名空间

- `StoreBackend` 的 `namespace` 工厂接收 `Runtime` 对象，可按用户身份、助手ID、线程ID等组合构建隔离命名空间。
- `CompositeBackend` 中各路由后端的命名空间独立配置，可实现不同路径不同隔离策略。

***

## 3. 路由与混合存储 (CompositeBackend)

`CompositeBackend` 通过 `default` + `routes` 字典实现基于路径前缀的灵活分发：

- **路由规则**：前缀越长越优先；`"/memories/projects/"` 可覆盖 `"/memories/"`。
- **聚合表现**：`ls`、`glob`、`grep` 会透明地聚合多后端结果，并保留原始路径前缀，对代理表现为统一文件系统。
- **典型用例**：

```python
backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/workspace/": StateBackend(),#(临时工作区)
        "/memories/": StoreBackend(),#(跨会话长期记忆)
        "/policies/": StoreBackend()#(组织级只读策略)
    }
)
```

**重要注意**：若路由到 `StoreBackend`，必须通过 `create_deep_agent(store=...)` 提供存储实例，或由部署平台自动注入。

***

## 4. 自定义后端与虚拟文件系统

将远程存储（S3、Postgres 等）投影为文件系统，须实现 `BackendProtocol`：

- **路径映射**：内部绝对路径（`/a/b.txt`）映射到存储键/行。
- **性能考虑**：尽可能在服务端过滤（如 SQL 的 WHERE 子句），否则在本地过滤。
- **外部存储约定**：写入/编辑操作成功后，返回 `files_update=None`；仅内存状态后端需要返回 `files_update` 字典。
- **错误处理**：不要抛出异常，通过结果类型的 `error` 字段返回结构化错误。
- **必须实现的方法**：`ls`、`read`、`grep`、`glob`、`write`、`edit`，以及对应的结果类型（`LsResult`、`ReadResult` 等）。

示例模式请参考  原文的自定义后端 中的示例，它们展示了键构造、操作映射和错误处理范式。

***

## 5. 文件系统权限

权限是基于路径的声明式规则，在工具调用后端**之前**评估，先匹配先生效：

- 规则结构：`operations` (read/write)、`paths` (glob 模式)、`mode` (allow/deny)。
- 与后端的关系：权限适用于所有后端，但**不适用于沙箱后端的** **`execute`** **工具**（因沙箱内可绕过）。
- 子代理继承：子代理默认继承父代理权限，也可配置更窄的规则。
- 与 `CompositeBackend` 结合时，权限在路由分发之前统一评估，确保跨后端一致的安全策略。

更多细节请参见[权限深度文档](index/langchain-index/deepagent/concepts/permissions.md)。

***

## 6. 策略钩子 (Policy Hooks)

当权限规则无法满足复杂控制（如速率限制、审计日志、内容扫描）时，可通过**子类化或包装后端**注入自定义逻辑：

- **子类化**：覆盖 `write`、`edit` 等方法，在调用 `super()` 前后插入检查。
- **通用包装器**：实现 `BackendProtocol`，持有内部后端实例，在方法中插入前置/后置处理。
- **安全场景**：
  - 阻止特定目录的写入（如 `/policies/`）
  - 审计所有文件变更并记录日
  - 检查文件内容是否符合敏感信息扫描策略

策略钩子与权限声明结合，实现“白名单 + 行为控制”的完整安全体系。
更多细节请参见原文的策略钩子文档。

***
## 7. 关键约束与最佳实践

### 安全边界

- **LocalShellBackend** 是最大风险项——任何具有该后端的代理等同于拥有主机 Shell 权限；**严禁**暴露给不受信输入或网络服务。
- **FilesystemBackend** 必须启用 `virtual_mode=True` 并设置受限的 `root_dir`；使用 HITL 中间件审查破坏性操作。
- 对于生产级 Shell 执行，使用沙箱后端（Modal/Daytona/Deno）替代本地 Shell。

### 迁移与兼容性

- 后端已从工厂模式迁移为直接实例传递（`StateBackend()` 而非 `lambda rt: StateBackend(rt)`）。
- `StoreBackend` 的命名空间工厂现在直接接收 `Runtime`，而不再是 `BackendContext`；旧版访问器即将在 v0.7 移除。

### 存储选型原则

- 临时工作文件 → `StateBackend`
- 项目文件持久化（本地开发）→ `FilesystemBackend`
- 用户偏好/长期知识（多会话）→ `StoreBackend` 或 `ContextHubBackend`
- 隔离执行环境 → 沙箱后端
- 混合需求 → `CompositeBackend` 按路径路由

***
一节，想了解“通用包装器”的完整实现。单独搜索“包装器”可能返回不相关的内容。但将章节标题和术语组合——`策略钩子 通用包装器 PolicyWrapper`——就能精准命中原文的 `## 添加策略钩子` 章节中关于 `PolicyWrapper` 类的完整代码。
- 你读到索引中“后端选择与配置”一节，想了解 `FilesystemBackend` 的 `virtual_mode` 参数细节。用 `后端选择 virtual_mode 安全铁律` 组合查询，可以定位到原文 `### FilesystemBackend（本地磁盘）` 中的安全说明段落。

索引页不仅是你当前获取概念的来源，同时也是引导语义检索走向更精确结果的“导航提示”——索引中的标题和术语已经为你预先标注了原文中最关键的路标。

---
## 与全局概念的关联

- **虚拟文件系统** 是后端实例化后的直接产物，被权限、技能、记忆、上下文压缩等功能复用。
虚拟文件系统被权限限制，防止直接访问物理文件系统。
虚拟文件系统被技能调用，如 `read`、`write`、`grep` 等。
虚拟文件系统是记忆的持久化存储的路径地址和空间，用于存储和检索文件内容。
上下文压缩是将文件内容压缩到虚拟文件系统中，以减少存储需求和传输成本。
- **[上下文工程中的长期记忆](index/langchain-index/deepagent/concepts/context_engineering.md)** 依赖 `StoreBackend` 或 `CompositeBackend` 中的持久路由。
- **代码执行** 双路径（[沙箱](sandboxs.md)/[解释器](index/langchain-index/deepagent/concepts/Interpreters.md) ）直接对应沙箱后端和解释器，后端决定了代码执行的安全等级。
- **[框架配置文件](profile.md)** 可通过 `excluded_tools` 隐藏文件系统工具，但无法移除后端本身；后端选择决定了可用工具集（例如 `execute` 是否存在）。

## 链接原文

当本索引中的概要无法满足你（例如需要完整代码实现、方法签名、罕见配置示例）时，请通过以下方式从原始文档中获取精确信息。

### 语义检索（聚焦查询）

原始文档已按 `#` 级别标题切分并向量化。构造查询时，**使用当前索引章节的标题或段落内出现的关键概念、特殊术语作为锚点**，而不是全文反复出现的通用词。有效的查询往往短而具体。

例如，当你在本索引的“策略钩子”一节需要更多细节时：

- **好的查询**：`策略钩子`、`GuardedBackend`、`PolicyWrapper`
- **差的查询**：`如何使用后端`（整个文档都在讲后端，无法聚焦）

将标题词和段落内的特有术语组合，可以快速锁定目标段落。

### 利用索引页提升检索精度

如果单靠关键术语检索结果仍不够集中，从本索引中提取**所在章节的标题**或**当前段落的特有表述**作为附加上下文，与你的问题组合成更完整的查询。索引页的标题本身就是高质量的语义锚点。

### 标题路径兜底

语义检索返回的每个片段都携带其**原文标题和文件路径**。若需读取该章节的完整内容或进入相邻段落，可直接用返回结果中的标题坐标通过 `read_file` 精确定位——标题始终精确，因为它来自原文本身。