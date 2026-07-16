# 权限

> 使用声明式权限规则为 Deep Agents 控制文件系统访问

使用声明式权限规则控制代理可以读取或写入哪些文件和目录。将规则列表传递给 `permissions=`，代理内置的文件系统工具就会遵守这些规则。

权限仅适用于内置文件系统工具（`ls`、`read_file`、`glob`、`grep`、`write_file`、`edit_file`）。自定义工具和访问文件系统的 MCP 工具不在覆盖范围内。权限也不适用于沙箱后端，因为沙箱后端通过 `execute` 工具支持任意命令执行。

当你需要在内置文件系统工具上实施**基于路径的允许/拒绝规则**时，请使用 `permissions`。当你需要自定义验证逻辑（速率限制、审计日志、内容检查）或需要控制自定义工具时，请使用后端策略钩子。

## 基本用法

将 `FilesystemPermission` 规则列表传递给 `create_deep_agent`。规则按声明顺序求值。第一个匹配的规则获胜。如果没有规则匹配，则允许该操作。

```python
from deepagents import FilesystemPermission, create_deep_agent

# 只读代理：拒绝所有写入
agent = create_deep_agent(
    model=model,
    backend=backend,
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/**"],
            mode="deny",
        ),
    ],
)
```

## 规则结构

每个 `FilesystemPermission` 都有三个字段：

| 字段           | 类型                        | 描述                                                                                         |
| ------------ | ------------------------- | ------------------------------------------------------------------------------------------ |
| `operations` | `list["read" \| "write"]` | 此规则适用的操作。`"read"` 涵盖 `ls`、`read_file`、`glob`、`grep`。`"write"` 涵盖 `write_file`、`edit_file`。 |
| `paths`      | `list[str]`               | 用于匹配文件路径的 Glob 模式（例如 `["/workspace/**"]`）。支持 `**` 进行递归匹配，支持 `{a,b}` 表示选择。                  |
| `mode`       | `"allow" \| "deny"`       | 允许还是拒绝匹配的操作。默认为 `"allow"`。                                                                 |

规则使用“先匹配获胜”的求值方式：第一个其 `operations` 和 `paths` 与当前调用匹配的规则决定结果。如果没有规则匹配，则调用被**允许**（宽松默认）。

**常见写法示例**

假设目录结构为：
```text
F:\agent\langchain-docs\index
├── doc1.md
├── doc2.md
├── subdir/
│   ├── note.txt
│   └── deep/
│       └── file.md
└── images/
    └── logo.png
```

|想要匹配的内容|`glob` 参数|
|---|---|
|该目录下所有文件（任意层级）|`"**/*"`|
|该目录下的所有 Markdown 文件（包括子目录）|`"**/*.md"`|
|根目录下的 Markdown 文件（不含子目录）|`"*.md"`|
|`subdir` 下的所有 `.txt` 文件（包括深层子目录）|`"subdir/**/*.txt"`|
|只匹配 `subdir` 根下的 `.txt`（不递归）|`"subdir/*.txt"`|
|匹配所有文件，但排除 `images` 文件夹|部分加载器支持 `exclude` 参数，或使用更复杂的 glob 如 `"!(images)/**/*"`（需开启扩展 glob）|

## 示例

### 隔离到工作区目录

仅允许在 `/workspace/` 下进行读写，拒绝其他所有操作：

```python
agent = create_deep_agent(
    model=model,
    backend=backend,
    permissions=[
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/workspace/**"],
            mode="allow",
        ),
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/**"],
            mode="deny",
        ),
    ],
)
```

### 保护特定文件

```python
agent = create_deep_agent(
    model=model,
    backend=backend,
    permissions=[
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/workspace/.env", "/workspace/examples/**"],
            mode="deny",
        ),
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/workspace/**"],
            mode="allow",
        ),
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/**"],
            mode="deny",
        ),
    ],
)
```

### 只读记忆

允许代理读取记忆文件，但阻止其修改它们。这对于组织范围内的策略或只能由应用程序代码更新的共享知识库很有用。更多上下文请参阅只读与可写记忆。

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model=model,
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(
                namespace=lambda rt: (rt.server_info.user.identity,),
            ),
            "/policies/": StoreBackend(
                namespace=lambda rt: (rt.context.org_id,),
            ),
        },
    ),
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/memories/**", "/policies/**"],
            mode="deny",
        ),
    ],
)
```

### 拒绝所有访问

阻止所有读写。这是一个你可以在此基础上叠加更具体的允许规则的限制性基线：

```python
agent = create_deep_agent(
    model=model,
    backend=backend,
    permissions=[
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/**"],
            mode="deny",
        ),
    ],
)
```

### 规则排序

由于是“先匹配获胜”，规则顺序很重要。将更具体的规则放在较宽泛的规则之前：

```python
# 正确：拒绝 .env，允许工作区，拒绝其他所有
correct_permissions = [
    FilesystemPermission(
        operations=["read", "write"],
        paths=["/workspace/.env"],
        mode="deny",
    ),
    FilesystemPermission(
        operations=["read", "write"],
        paths=["/workspace/**"],
        mode="allow",
    ),
    FilesystemPermission(
        operations=["read", "write"],
        paths=["/**"],
        mode="deny",
    ),
]

# 错误：/workspace/** 首先匹配 .env，因此拒绝永远不会触发
incorrect_permissions = [
    FilesystemPermission(
        operations=["read", "write"],
        paths=["/workspace/**"],
        mode="allow",
    ),
    FilesystemPermission(
        operations=["read", "write"],
        paths=["/workspace/.env"],
        mode="deny",  # 永远不会到达
    ),
    FilesystemPermission(
        operations=["read", "write"],
        paths=["/**"],
        mode="deny",
    ),
]
```

## 子代理权限

默认情况下，子代理继承父代理的权限。要给予子代理不同的权限，请在其规范中设置 `permissions` 字段。这将**完全替换**父代理的规则。

```python
agent = create_deep_agent(
    model=model,
    backend=backend,
    permissions=[
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/workspace/**"],
            mode="allow",
        ),
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/**"],
            mode="deny",
        ),
    ],
    subagents=[
        {
            "name": "auditor",
            "description": "只读代码审查员",
            "system_prompt": "审查代码中的问题。",
            "permissions": [
                FilesystemPermission(
                    operations=["write"],
                    paths=["/**"],
                    mode="deny",
                ),
                FilesystemPermission(
                    operations=["read"],
                    paths=["/workspace/**"],
                    mode="allow",
                ),
                FilesystemPermission(
                    operations=["read"],
                    paths=["/**"],
                    mode="deny",
                ),
            ],
        }
    ],
)
```

## 组合后端

当使用带有沙箱默认值的 `CompositeBackend` 时，每个权限路径都必须限定在已知的路由前缀下。沙箱支持任意命令执行，因此仅靠基于路径的限制无法阻止通过 shell 命令访问文件系统。将权限限定到特定路由的后端可以避免此冲突。

```python
from deepagents.backends import CompositeBackend

composite = CompositeBackend(
    default=sandbox,
    routes={"/memories/": memories_backend},
)

# 有效：权限限定在 /memories/ 路由
agent = create_deep_agent(
    model=model,
    backend=composite,
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/memories/**"],
            mode="deny",
        ),
    ],
)
```

包含任何路由之外路径的权限会引发 `NotImplementedError`：

```python
# 引发 NotImplementedError：/workspace/** 命中沙箱默认值
try:
    create_deep_agent(
        model=model,
        backend=composite,
        permissions=[
            FilesystemPermission(
                operations=["write"],
                paths=["/workspace/**"],
                mode="deny",
            ),
        ],
    )
except NotImplementedError:
    pass

# 同样会引发：/** 同时覆盖了路由和默认值
try:
    create_deep_agent(
        model=model,
        backend=composite,
        permissions=[
            FilesystemPermission(
                operations=["read"],
                paths=["/**"],
                mode="deny",
            ),
        ],
    )
except NotImplementedError:
    pass
```