# 权限深度索引

> 这是 Deep Agents 文件系统权限的**概念地图**，涵盖规则结构、匹配语义、子代理继承、组合后端约束及与策略钩子的配合。  
> 阅读本文档可一次性掌握权限模型的全部概念及其在全局安全体系中的定位。

---

## 概念全景

Deep Agents 提供声明式权限规则，控制agent对内置文件系统工具（`ls`、`read_file`、`glob`、`grep`、`write_file`、`edit_file`）的读写访问。规则按声明顺序以“先匹配优先”语义求值，无匹配则默认允许（宽松默认）。权限在工具调用后端**之前**评估，形成第一道防线。

**权限适用的边界：**
- ✅ 适用于内置文件系统工具
- ❌ 不适用于自定义工具、MCP 工具
- ❌ 不适用于沙箱后端的 `execute` 工具（因沙箱内可绕过路径限制）
- 需要自定义验证逻辑时，使用后端策略钩子。

---

## 1. 规则结构

每条规则包含三个字段：

| 字段 | 类型 | 描述 |
|------|------|------|
| `operations` | `list["read" \| "write"]` | 适用的操作类别：`read` 涵盖 `ls`、`read_file`、`glob`、`grep`；`write` 涵盖 `write_file`、`edit_file` |
| `paths` | `list[str]` | Glob 模式，支持 `**` 递归匹配、`{a,b}` 选择 |
| `mode` | `"allow" \| "deny"` | 匹配时的判定结果 |

**匹配原则**：先匹配优先——第一个 `operations` 和 `paths` 均匹配的规则决定结果；无匹配规则则默认允许。

---

## 2. 常见模式与示例

### 隔离工作区（白名单模式）
```python
# 仅允许 /workspace/ 下读写，拒绝其他所有
permissions=[
    FilesystemPermission(operations=["read","write"], paths=["/workspace/**"], mode="allow"),
    FilesystemPermission(operations=["read","write"], paths=["/**"], mode="deny"),
]
```

### 保护特定文件（黑名单叠加）
```python
# 拒绝 .env 和 examples/，允许 workspace，拒绝其他
permissions=[
    FilesystemPermission(operations=["read","write"], paths=["/workspace/.env","/workspace/examples/**"], mode="deny"),
    FilesystemPermission(operations=["read","write"], paths=["/workspace/**"], mode="allow"),
    FilesystemPermission(operations=["read","write"], paths=["/**"], mode="deny"),
]
```

### 只读记忆
```python
# 阻止对 /memories/ 和 /policies/ 的写入
permissions=[
    FilesystemPermission(operations=["write"], paths=["/memories/**","/policies/**"], mode="deny"),
]
```

### 拒绝所有（最小权限基线）
```python
permissions=[
    FilesystemPermission(operations=["read","write"], paths=["/**"], mode="deny"),
]
```

### 规则顺序至关重要
始终将**更具体**的规则放在**更宽泛**的规则之前，否则宽泛规则会提前匹配，导致具体规则失效。

---

## 3. 子代理权限

- **默认继承**：子代理继承父代理的所有权限规则。
- **显式覆盖**：在子代理规范中设置 `permissions` 字段将**完全替换**父代理规则，为子代理赋予更窄（或不同）的访问边界。

```python
# 父代理：工作区读写
# 子代理 auditor：只读工作区，拒绝所有写入
subagents=[{
    "name": "auditor",
    "permissions": [
        FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
        FilesystemPermission(operations=["read"], paths=["/workspace/**"], mode="allow"),
        FilesystemPermission(operations=["read"], paths=["/**"], mode="deny"),
    ]
}]
```

---

## 4. 组合后端约束

当使用 `CompositeBackend` 且默认后端为沙箱时，权限路径必须限定在已知路由前缀下，否则会引发 `NotImplementedError`。原因：沙箱支持任意命令执行，基于路径的限制无法阻止通过 shell 命令绕过文件系统访问，因此权限必须针对可控的非沙箱路由。

**有效示例**（仅对 `/memories/` 路由施加权限）：
```python
CompositeBackend(default=sandbox, routes={"/memories/": memories_backend})
permissions=[FilesystemPermission(operations=["write"], paths=["/memories/**"], mode="deny")]
```

**无效示例**（路径 `/workspace/**` 或 `/**` 触及沙箱默认值）将引发 `NotImplementedError`。

---

## 5. 权限 vs 策略钩子

| 机制 | 适用场景 | 粒度 |
|------|---------|------|
| **权限 (Permissions)** | 基于路径的声明式允许/拒绝，适用于内置工具 | 路径级 |
| **策略钩子 (Policy Hooks)** | 自定义验证逻辑（速率限制、审计、内容检查），可控制自定义工具 | 任意逻辑 |

两者可互补：权限作为第一层快速路径过滤，策略钩子实现更复杂的业务规则。

---

## 与全局概念的关联

- **[虚拟文件系统与后端](index/langchain-index/deepagent/concepts/backends.md)**：权限在后端调用前统一评估，适用于除沙箱 `execute` 外的所有后端操作；`CompositeBackend` 下的路径限制需避开沙箱默认值。
- **[子代理](index/langchain-index/deepagent/concepts/subagent.md)**：权限继承与覆盖为委派任务提供独立的安全边界。
- **[人机协同](./human_in_the_loop.md)**：对于高风险操作，可结合 `interrupt_on` 与权限，实现“路径允许 + 人工审批”双重防护。
- **[[index/langchain-index/deepagent/concepts/backends#6. 策略钩子 (Policy Hooks)]]**：当权限声明不足以满足需求时，策略钩子提供完全自定义的验证通道。
- **安全最佳实践**：对 `LocalShellBackend` 等高风险后端，应通过 `permissions` 严格限制文件系统访问，并配合 HITL。

## 链接原文

当本索引中的概要无法满足你（例如需要完整代码实现、方法签名、罕见配置示例）时，请通过以下方式从原始文档中获取精确信息。

### 语义检索（聚焦查询）

原始文档已按 `#` 级别标题切分并向量化。构造查询时，**使用当前索引章节的标题或段落内出现的关键概念、特殊术语作为锚点**，而不是全文反复出现的通用词。有效的查询往往短而具体。

例如，当你在本索引的“组合后端约束”一节需要更多细节时：

- **好的查询**：`CompositeBackend 默认后端为沙箱 NotImplementedError`、`权限路径限定在已知路由前缀 沙箱绕过`
- **差的查询**：`如何使用权限`（整个文档都在讲权限，无法聚焦）

将标题词和段落内的特有术语组合，可以快速锁定目标段落。

### 利用索引页提升检索精度

如果单靠关键术语检索结果仍不够集中，从本索引中提取**所在章节的标题**或**当前段落的特有表述**作为附加上下文，与你的问题组合成更完整的查询。索引页的标题本身就是高质量的语义锚点。例如：

- 想了解“隔离工作区”白名单模式的完整规则顺序，用 `隔离工作区 白名单模式 规则顺序 先匹配优先` 组合查询。
- 想了解“子代理权限”完全替换父代理规则的具体行为，用 `子代理权限 显式覆盖 完全替换 父代理` 定位。
- 想查询“只读记忆”中拒绝写入的具体 paths 写法，用 `只读记忆 deny write /memories/**` 找到示例。

### 标题路径兜底

语义检索返回的每个片段都携带其**原文标题和文件路径**。若需读取该章节的完整内容或进入相邻段落，可直接用返回结果中的标题坐标通过 `read_file` 精确定位——标题始终精确，因为它来自原文本身。