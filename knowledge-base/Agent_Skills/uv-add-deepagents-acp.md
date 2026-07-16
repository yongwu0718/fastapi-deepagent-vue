# 在技能中使用脚本

> 如何在你的技能中运行命令以及捆绑可执行脚本。

技能可以指示代理运行 shell 命令，并将可复用的脚本捆绑在 `scripts/` 目录中。本指南涵盖一次性命令、带有自身依赖的自包含脚本，以及如何为代理使用场景设计脚本接口。

## 一次性命令

当已有现成的包能完成你需要的工作时，你可以直接在 `SKILL.md` 指令中引用它，而无需使用 `scripts/` 目录。许多生态系统都提供了能在运行时自动解析依赖的工具。


[uvx](https://docs.astral.sh/uv/guides/tools/) 能在隔离环境中运行 Python 包，并具备积极的缓存策略。它随 [uv](https://docs.astral.sh/uv/) 一起提供。

```bash
uvx ruff@0.8.0 check .
uvx black@24.10.0 .
```

* 不随 Python 捆绑安装——需要单独安装。
* 速度很快。积极的缓存使重复运行几乎即时完成。


[npx](https://docs.npmjs.com/cli/commands/npx) 能够按需下载并运行 npm 包。它随 npm（npm 随 Node.js 一起提供）一起提供。

```bash
npx eslint@9 --fix .
npx create-vite@6 my-app
```

* 与 Node.js 捆绑——无需额外安装。
* 下载包、运行它，并缓存供将来使用。
* 使用 `npx package@version` 固定版本以确保可复现性。
  
**在技能中使用一次性命令的技巧：**

* **固定版本**（例如 `npx eslint@9.0.0`），以确保命令的行为不会随时间改变。
* **在 `SKILL.md` 中说明前提条件**（例如“需要 Node.js 18+”），而不是假设代理环境中已具备这些条件。对于运行时级别的要求，请使用 [`compatibility` 前言字段](/specification#compatibility-field)。
* **将复杂的命令移入脚本。** 当你只需要调用带几个参数的工具时，一次性命令很好用。但当命令变得复杂，以至于难以一次性正确执行时，放在 `scripts/` 目录中的、经过测试的脚本会更可靠。

## 从 `SKILL.md` 引用脚本

使用**相对于技能根目录的路径**来引用捆绑的文件。代理会自动解析这些路径——无需绝对路径。

在 `SKILL.md` 中列出可用的脚本，以便代理知道它们的存在：

```markdown
## 可用脚本

- **`scripts/validate.sh`** —— 验证配置文件
- **`scripts/process.py`** —— 处理输入数据
```

然后指示代理运行它们：

````markdown
## 工作流

1. 运行验证脚本：
   ```bash
   bash scripts/validate.sh "$INPUT_FILE"
   ```

2. 处理结果：
   ```bash
   python3 scripts/process.py --input results.json
   ```
````

***
同样的相对路径约定也适用于支持文件，如 `references/*.md`——代码块中的脚本执行路径都是相对于**技能根目录**的，因为代理会从该目录执行命令。
***

## 自包含脚本

当你需要可复用的逻辑时，将脚本捆绑在 `scripts/` 目录中，并在脚本内部声明其依赖项。这样代理就可以用一条命令运行脚本——无需单独的描述文件或安装步骤。

几种语言支持内联依赖声明：

[PEP 723](https://peps.python.org/pep-0723/) 定义了内联脚本元数据的标准格式。在 `# ///` 标记内的 TOML 块中声明依赖项：

```python scripts/extract.py theme={null}
# /// script
# dependencies = [
#   "beautifulsoup4",
# ]
# ///

from bs4 import BeautifulSoup

html = '<html><body><h1>Welcome</h1><p class="info">This is a test.</p></body></html>'
print(BeautifulSoup(html, "html.parser").select_one("p.info").get_text())
```

推荐使用 [uv](https://docs.astral.sh/uv/) 运行：

```bash theme={null}
uv run scripts/extract.py
```

`uv run` 会创建隔离环境，安装声明的依赖，并运行脚本。[pipx](https://pipx.pypa.io/)（`pipx run scripts/extract.py`）也支持 PEP 723。

* 使用 [PEP 508](https://peps.python.org/pep-0508/) 规范符固定版本：`"beautifulsoup4>=4.12,<5"`。
* 使用 `requires-python` 约束 Python 版本。
* 使用 `uv lock --script` 创建锁定文件以实现完全的可复现性。
  
## 为代理使用场景设计脚本

当代理运行你的脚本时，它会读取 stdout 和 stderr 来决定下一步操作。一些设计选择能让代理极大地简化脚本的使用。

### 避免交互式提示

这是代理执行环境的硬性要求。代理在非交互式 shell 中运行——它们无法响应 TTY 提示、密码对话框或确认菜单。一个在等待交互输入时阻塞的脚本会无限期挂起。

应通过命令行标志、环境变量或 stdin 接受所有输入：

```
# 坏：挂起等待输入
$ python scripts/deploy.py
目标环境：_

# 好：提供明确错误及指导
$ python scripts/deploy.py
错误：需要 --env。选项：development, staging, production。
用法：python scripts/deploy.py --env staging --tag v1.2.3
```

### 用 `--help` 记录用法

`--help` 输出是代理了解你脚本接口的主要方式。包含简短的描述、可用的标志和用法示例：

```
用法：scripts/process.py [选项] INPUT_FILE

处理输入数据并生成摘要报告。

选项：
  --format FORMAT    输出格式：json, csv, table (默认: json)
  --output FILE      将输出写入 FILE 而非 stdout
  --verbose          将进度信息打印到 stderr

示例：
  scripts/process.py data.csv
  scripts/process.py --format csv --output report.csv data.csv
```

保持简洁——这些输出会与代理正在处理的其他所有东西一同进入其上下文窗口。

### 编写有用的错误消息

当代理遇到错误时，消息内容会直接影响其下一次尝试。像“错误：无效输入”这样模糊的消息会浪费一轮交互。相反，应该说明什么出错了，期望的是什么，以及可以尝试什么：

```
错误：--format 必须是其中之一: json, csv, table。
       收到："xml"
```

### 使用结构化输出

优先选择结构化格式——JSON、CSV、TSV——而非自由格式的文本。结构化格式既可以供代理使用，也可以被标准工具（`jq`、`cut`、`awk`）消费，这使你的脚本可以在管道中组合使用。

```
# 空格对齐——难以程序化解析
NAME          STATUS    CREATED
my-service    running   2025-01-15

# 分隔符格式——字段边界明确
{"name": "my-service", "status": "running", "created": "2025-01-15"}
```

**将数据与诊断信息分离：** 将结构化数据发送到 stdout，将进度消息、警告和其他诊断信息发送到 stderr。这让代理既能捕获干净的、可解析的输出，又能在需要时访问诊断信息。

### 进一步的考虑事项

* **幂等性。** 代理可能会重试命令。“如果不存在则创建”比“创建并在重复时失败”更安全。
* **输入约束。** 拒绝模糊的输入并给出明确的错误，而不是猜测。尽可能使用枚举和封闭集合。
* **试运行支持。** 对于破坏性或状态性操作，`--dry-run` 标志可以让代理预览将要发生的操作。
* **有意义的退出码。** 为不同的失败类型（未找到、无效参数、身份验证失败）使用不同的退出码，并在 `--help` 输出中记录它们，以便代理知道每个代码的含义。
* **安全的默认值。** 考虑破坏性操作是否需要明确的确认标志（`--confirm`、`--force`），或者其他适合风险等级的防护措施。
* **可预测的输出大小。** 许多代理工具会自动截断超出阈值（例如 10-30K 字符）的工具输出，这可能会丢失关键信息。如果你的脚本可能产生大量输出，应默认提供摘要或合理的限制，并支持类似 `--offset` 的标志，以便代理在需要时请求更多信息。或者，如果输出很大且不适合分页，要求代理传递一个 `--output` 标志，指定一个输出文件，或使用 `-` 显式选择输出到 stdout。