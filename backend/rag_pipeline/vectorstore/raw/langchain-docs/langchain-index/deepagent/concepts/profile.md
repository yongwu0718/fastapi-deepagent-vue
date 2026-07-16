# 配置文件深度索引

> 这是 Deep Agents 配置文件系统的**概念地图**，涵盖框架配置文件 (HarnessProfile) 与提供商配置文件 (ProviderProfile) 的用途、注册键、合并语义、持久化与插件发布。  
> 阅读本文档可一次性掌握配置文件如何让你在不修改代码的情况下，针对不同模型或提供商精细化调整代理行为。

---

## 概念全景

配置文件是 Deep Agents 针对特定模型或提供商调整行为的声明式机制。分为两类：

- **框架配置文件 (HarnessProfile)**：控制代理在模型构建*之后*的行为：系统提示、工具可见性、中间件和通用子代理。
- **提供商配置文件 (ProviderProfile)**：控制*模型构建*时的初始化关键字，如 `temperature`、凭据检查等。仅当使用 `provider:model` 字符串时生效，对预配置模型实例无效。

配置文件通过注册键（`"openai"` 或 `"openai:gpt-5.4"`）关联，在创建代理时自动解析并合并。

---

## 1. 框架配置文件 (HarnessProfile)

用于调整提示组装、工具和中间件，无需修改 `create_deep_agent` 调用点。

### 可配置字段与行为

| 字段 | 作用 | 备注 |
|------|------|------|
| `base_system_prompt` | 替换基础 Deep Agents 系统提示 | 位于自定义 `system_prompt` 之后 |
| `system_prompt_suffix` | 附加到组装完成的提示末尾 | 应用于主代理、声明式子代理、通用子代理 |
| `tool_description_overrides` | 覆盖特定工具的描述（按键名） | 辅助模型正确使用工具 |
| `excluded_tools` | 移除指定的工具（按名称） | 可隐藏内置或用户工具；严禁在此列出 `FilesystemMiddleware` 或 `SubAgentMiddleware`（会引发错误），移除工具应使用此字段而非排除中间件 |
| `excluded_middleware` | 剥离指定的中间件（按类/名称/导入路径） | 只能排除非核心中间件；核心中间件被保护 |
| `extra_middleware` | 附加额外的中间件 | 按类合并，新实例替换旧实例 |
| `general_purpose_subagent` | 禁用、重命名或重新提示通用子代理 | 设置 `enabled=False` 可完全移除 `task` 工具（需同时不传入同步子代理） |

### 提示组装顺序

最终系统消息由以下部分组成（有配置文件时可能调整）：
1. 自定义 `system_prompt`
2. 基础代理提示（可被 `base_system_prompt` 替换）
3. 待办事项提示、记忆提示、技能提示、文件系统提示、子代理提示等
4. 用户自定义中间件提示
5. 人机协同提示
6. `system_prompt_suffix`（始终在最后）

子代理会针对自己的模型重新运行配置文件解析。

---

## 2. 提供商配置文件 (ProviderProfile)

用于设置模型构建时的参数。主要字段：

- `init_kwargs`：转发给 `init_chat_model` 的静态参数（如 `temperature`、`max_tokens`）。
- `pre_init`：构建前执行的副作用，如凭据验证。
- `init_kwargs_factory`：从运行时状态派生的关键字参数。

提供商配置文件仅在提供 `provider:model` 字符串时应用，预配置模型实例不触发。

---

## 3. 注册键与合并

- **键格式**：`"openai"`（提供商级）或 `"openai:gpt-5.4"`（模型级）。
- **查找顺序**：精确匹配 `provider:model` → 仅标识符匹配（含 `:` 时）→ 提供商回退。
- **合并**：模型级配置文件继承并覆盖提供商级配置，各字段遵循特定合并语义（字符串替换、集合合并、字典按键合并、中间件按类合并）。
- **重新注册**：在已有键上再注册会合并到现有配置之上，不会完全替换。
- **无通配符**：没有匹配所有提供商的万能键；通用调整需在每个提供商键下重复注册，或直接在 `create_deep_agent` 处设置。

---

## 4. 持久化与插件化

### HarnessProfileConfig（YAML/JSON 支持）
声明式子集，支持文件加载，方便存储和跨项目共享。

```yaml
# openai.yaml
base_system_prompt: 你很乐于助人。
system_prompt_suffix: 简要回复。
excluded_tools:
  - execute
excluded_middleware:
  - SummarizationMiddleware
general_purpose_subagent:
  enabled: false
```

加载方式：`HarnessProfileConfig.from_dict(yaml.safe_load(...))`。也可用 `from_harness_profile` 将运行时配置导出，但动态中间件或 `__main__` 中的类无法序列化。

### 入口点插件
通过 `pyproject.toml` 的 `[project.entry-points."deepagents.harness_profiles"]` 注册零参数可调用对象，包被导入时自动执行注册。顺序：内置 → 插件 → 用户直接调用，后者叠加在前者上。

---

## 5. 关键约束与最佳实践

- **工具隐藏的正确路径**：用 `excluded_tools` 隐藏工具，用 `general_purpose_subagent.enabled=False` 禁用子代理，**严禁**通过 `excluded_middleware` 移除 `FilesystemMiddleware` 或 `SubAgentMiddleware`。
- **全局调整**：无论模型如何都需要的配置，应直接在 `create_deep_agent` 参数中设置，而非通过配置文件。
- **模型实例化差异**：框架配置文件始终生效；提供商配置文件仅对字符串模型生效。
- **子代理与通用子代理提示**：自定义 `system_prompt_suffix` 会影响所有代理；通用子代理的专属提示可通过 `GeneralPurposeSubagentProfile` 设置，且优先级更高。

---

## 与全局概念的关联

- **模型**：配置文件与模型选择紧密耦合，根据 `provider:model` 键自动激活；`ProviderProfile` 直接影响模型实例化。
- **系统提示组装**：配置文件是调整提示内容的核心入口，与记忆、技能、工具提示等输入上下文共同决定代理行为。
- **子代理**：通用子代理的启用/禁用和重提示完全由 `HarnessProfile` 控制。
- **中间件与工具管理**：配置文件可安全地裁剪或扩展中间件栈和工具集，是框架能力定制的安全阀。
- **上下文工程**：通过动态提示、工具过滤等间接参与上下文工程，但配置文件本身是静态声明。
- **插件生态**：通过入口点支持第三方分发，与技能、后端等形成可插拔生态。

详细实现请参见：
- [模型配置与选择](./models.md)
- [子代理深度索引](./subagents.md)
- [上下文工程深度索引](index/langchain-index/deepagent/concepts/context_engineering.md)
