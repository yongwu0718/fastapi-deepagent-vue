# 规范

> Agent Skills 的完整格式规范。
## 目录结构

一个技能是一个目录，至少包含一个 `SKILL.md` 文件：

```
skill-name/
├── SKILL.md          # 必需：元数据 + 指令
├── scripts/          # 可选：可执行代码
├── references/       # 可选：文档
├── assets/           # 可选：模板、资源
└── ...               # 任何其他文件或目录
```

## `SKILL.md` 格式

`SKILL.md` 文件必须包含 YAML 前言，后跟 Markdown 内容。

### 前言

| 字段             | 必需   | 约束                                                                                               |
| ---------------- | ------ | -------------------------------------------------------------------------------------------------- |
| `name`           | 是     | 最多 64 个字符。仅允许小写字母、数字和连字符。不得以连字符开头或结尾。                             |
| `description`    | 是     | 最多 1024 个字符。非空。描述技能的功能以及何时使用。                                               |
| `license`        | 否     | 许可证名称或对捆绑的许可证文件的引用。                                                             |
| `compatibility`  | 否     | 最多 500 个字符。指明环境要求（预期产品、系统包、网络访问等）。                                    |
| `metadata`       | 否     | 任意键值对，用于附加元数据。                                                                       |
| `allowed-tools`  | 否     | 以空格分隔的、预批准技能可使用的工具的字符串。(实验性)                                             |


  **最小示例：**

```markdown SKILL.md
---
name: skill-name
description: 描述此技能的功能以及何时使用。
---
```

  **包含可选字段的示例：**

```markdown
---
name: pdf-processing
description: 提取 PDF 文本，填写表单，合并文件。处理 PDF 时使用。
license: Apache-2.0
metadata:
author: example-org
version: "1.0"
---
```
#### `name` 字段

必需的 `name` 字段：

* 必须为 1-64 个字符
* 只能包含 unicode 小写字母数字字符 (`a-z`, `0-9`) 和连字符 (`-`)
* 不得以连字符 (`-`) 开头或结尾
* 不得包含连续连字符 (`--`)
* 必须与父目录名称匹配


**有效示例：**

```yaml
name: pdf-processing
```

```yaml
name: data-analysis
```

```yaml
name: code-review
```

**无效示例：**

```yaml
name: PDF-Processing  # 不允许使用大写字母
```

```yaml
name: -pdf  # 不能以连字符开头
```

```yaml
name: pdf--processing  # 不允许使用连续连字符
```

#### `description` 字段

必需的 `description` 字段：

* 必须为 1-1024 个字符
* 应描述技能的功能以及何时使用
* 应包含有助于代理识别相关任务的关键词

**好的示例：**

```yaml

description: 从 PDF 文件中提取文本和表格，填写 PDF 表单，并合并多个 PDF 文件。在处理 PDF 文档时，或用户提到 PDF、表单或文档提取时使用。
```

  **不好的示例：**

```yaml
description: 帮助处理 PDF。
```

#### `license` 字段

可选的 `license` 字段：

* 指定应用于该技能的许可证
* 我们建议保持简短（许可证名称或捆绑的许可证文件名）

**示例：**

```yaml
license: 专有。完整条款见 LICENSE.txt
```
#### `compatibility` 字段

可选的 `compatibility` 字段：

* 如果提供，必须为 1-500 个字符
* 仅当你的技能有特定的环境要求时才应包含
* 可以指明预期产品、必需的系统包、网络访问需求等


  **示例：**

```yaml
compatibility: 专为 Claude Code（或类似产品）设计
```

```yaml
compatibility: 需要 git, docker, jq 和互联网访问
```

```yaml
compatibility: 需要 Python 3.14+ 和 uv
```

<Note>
  大多数技能不需要 `compatibility` 字段。
</Note>

#### `metadata` 字段

可选的 `metadata` 字段：

* 一个字符串键到字符串值的映射
* 客户端可以用它来存储 Agent Skills 规范未定义的其他属性
* 我们建议让你的键名保持合理的唯一性，以避免意外冲突

**示例：**

```yaml
metadata:
	author: example-org
	version: "1.0"
```

#### `allowed-tools` 字段

可选的 `allowed-tools` 字段：

* 一个以空格分隔的、预批准可运行的工具字符串
* 实验性。对此字段的支持可能因代理实现而异


**示例：**

```yaml
allowed-tools: Bash(git:*) Bash(jq:*) Read
```

### 正文内容

前言之后的 Markdown 正文包含技能指令。没有格式限制。编写任何有助于代理有效执行任务的内容即可。

推荐的章节：

* 分步指令
* 输入和输出示例
* 常见边缘情况

请注意，一旦决定激活某个技能，代理将加载整个文件。请考虑将较长的 `SKILL.md` 内容拆分到引用的文件中。

## 可选目录

### `scripts/`

包含代理可以运行的可执行代码。脚本应：

* 是自包含的，或清晰记录依赖关系
* 包含有用的错误消息
* 优雅地处理边缘情况

支持的语言取决于代理实现。常见选项包括 Python、Bash 和 JavaScript。

### `references/`

包含代理在需要时可以阅读的其他文档：

* `REFERENCE.md` - 详细的技术参考
* `FORMS.md` - 表单模板或结构化数据格式
* 领域特定文件（`finance.md`、`legal.md` 等）

保持单个[引用文件](#文件引用)内容集中。代理按需加载这些文件，因此文件越小，上下文占用越少。

### `assets/`

包含静态资源：

* 模板（文档模板、配置模板）
* 图片（图表、示例）
* 数据文件（查找表、模式）

## 渐进式披露

代理*渐进式*加载技能，仅在任务需要时才拉取更多细节。技能的结构应利用这一点：

1.  **元数据** (\~100 个 token)：所有技能的 `name` 和 `description` 字段在启动时加载
2.  **指令** (推荐 \< 5000 个 token)：完整的 `SKILL.md` 正文在技能被激活时加载
3.  **资源** (按需)：文件（例如 `scripts/`、`references/` 或 `assets/` 中的文件）仅在需要时加载

保持主 `SKILL.md` 在 500 行以内。将详细的参考资料移至单独的文件。

## 文件引用

在技能中引用其他文件时，使用从技能根目录开始的相对路径：

```markdown SKILL.md
详见 [参考指南](references/REFERENCE.md)。

运行提取脚本：
scripts/extract.py
```

文件引用应从 `SKILL.md` 开始保持一层深度。避免深层嵌套的引用链。

## 验证

使用 [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) 参考库来验证你的技能：

```bash
skills-ref validate ./my-skill
```

这将检查你的 `SKILL.md` 前言是否有效，并遵循所有命名约定。