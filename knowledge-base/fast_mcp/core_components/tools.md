# Tools

> 将函数公开为 MCP 客户端的可执行能力。

Tools 是让您的 LLM 与外部系统交互、执行代码以及访问其训练数据之外的数据的核心构建块。在 FastMCP 中，tools 是通过 MCP 协议公开给 LLM 的 Python 函数。

FastMCP 中的 Tools 将常规的 Python 函数转换为 LLM 在对话中可以调用的能力。当 LLM 决定使用一个 tool 时：

1. 它发送一个带有基于 tool schema 的参数的请求。
2. FastMCP 会根据您函数的签名验证这些参数。
3. 您的函数使用验证过的输入来执行。
4. 结果返回给 LLM，LLM 可以将其用于响应中。

这使得 LLM 能够执行诸如查询数据库、调用 API、进行计算或访问文件等任务——将其能力扩展到训练数据之外。

## `@tool` 装饰器

创建一个 tool 就像用 `@mcp.tool` 装饰一个 Python 函数一样简单：

```python
from fastmcp import FastMCP

mcp = FastMCP(name="CalculatorServer")

@mcp.tool
def add(a: int, b: int) -> int:
    """将两个整数相加。"""
    return a + b
```

当这个 tool 被注册时，FastMCP 会自动：

* 使用函数名（`add`）作为 tool 名称。
* 解析函数的 docstring 以获取 tool 描述，如果存在，还会获取每个参数的描述（见 Docstring 描述）。
* 根据函数的参数和类型注解生成 input schema。
* 处理参数验证和错误报告。

您定义 Python 函数的方式决定了该 tool 对于 LLM 客户端的外观和行为。

不支持带有 `*args` 或 `**kwargs` 的函数作为 tools。这一限制是因为 FastMCP 需要为 MCP 协议生成完整的参数 schema，而这对于可变参数列表是不可能的。

### 装饰器参数

虽然 FastMCP 会从您的函数推断名称和描述，但您可以使用 `@mcp.tool` 装饰器的参数来覆盖这些并添加额外的元数据：

```python
@mcp.tool(
    name="find_products",           # LLM 的自定义 tool 名称
    description="搜索产品目录，支持可选的类别过滤。", # 自定义描述
    tags={"catalog", "search"},      # 用于组织/过滤的可选 tags
    meta={"version": "1.2", "author": "product-team"}  # 自定义元数据
)
def search_products_implementation(query: str, category: str | None = None) -> list[dict]:
    """内部函数描述（如果上面提供了 description 则忽略）。"""
    # 实现...
    print(f"正在搜索 '{query}'，类别为 '{category}'")
    return [{"id": 2, "name": "Another Product"}]
```

`name`：设置通过 MCP 公开的显式 tool 名称。如果未提供，则使用函数名称。

`description`：提供通过 MCP 公开的描述。如果设置了，函数的 docstring 对于 tool 描述将被忽略，但从 docstring 派生的参数描述仍然适用（见 Docstring 描述）。

`tags`：用于对 tool 进行分类的一组字符串。服务器以及在某些情况下客户端可以使用它们来过滤或分组可用的 tools。

`enabled`：在 v3.0.0 中已弃用。请在服务器级别使用 `mcp.enable()` / `mcp.disable()` 代替。一个布尔值，用于启用或禁用 tool。推荐的方法见 Component Visibility。

`icons`：此 tool 的可选图标表示列表。详细示例见 Icons。

`annotations`：可选的 `ToolAnnotations` 对象或字典，用于添加关于 tool 的额外元数据。

*   `title`：一个人类可读的 tool 标题。
*   `readOnlyHint`：如果为 true，该 tool 不会修改其环境。
*   `destructiveHint`：如果为 true，该 tool 可能会对其环境执行破坏性更新。
*   `idempotentHint`：如果为 true，使用相同参数重复调用该 tool 将不会对其环境产生额外影响。
*   `openWorldHint`：如果为 true，此 tool 可能与外部实体的“开放世界”交互。如果为 false，则 tool 的交互域是封闭的。

`meta`：关于 tool 的可选元信息。这些数据会作为客户端侧 tool 对象的 `meta` 字段传递给 MCP 客户端，可用于自定义元数据、版本控制或其他特定于应用程序的目的。

`timeout`：以秒为单位的执行超时时间。如果 tool 完成时间超过此值，则会向客户端返回 MCP 错误。详情见 Timeouts。

`version`：此 tool 的可选版本标识符。详情见 Versioning。

`output_schema`：tool 输出的可选 JSON schema。当提供时，tool 必须返回与此 schema 匹配的 structured output。如果未提供，FastMCP 会根据函数的返回类型注解自动生成一个 schema。详情见 Output Schemas。

`run_in_thread`：仅适用于同步 tool 函数。当为 `True`（默认）时，同步函数被分派到线程池，以免阻塞 event loop。设置为 `False` 可在 event loop 线程上内联运行函数——这对于具有线程亲和性的库很有用，如 Windows COM (`pywin32`, `uiautomation`, `comtypes`), `tkinter`，或某些 GPU/驱动程序绑定。对于异步函数忽略，它们始终在 event loop 上运行。详情见 Thread affinity。

### 与方法一起使用

`@mcp.tool` 装饰器会立即注册 tools，这不适用于实例方法或类方法（您会看到 `self` 或 `cls` 作为必需参数）。对于方法，请使用独立的 `@tool` 装饰器附加元数据，然后注册绑定方法：

```python
from fastmcp import FastMCP
from fastmcp.tools import tool

class Calculator:
    def __init__(self, multiplier: int):
        self.multiplier = multiplier

    @tool()
    def multiply(self, x: int) -> int:
        """将 x 乘以实例的 multiplier。"""
        return x * self.multiplier

calc = Calculator(multiplier=3)
mcp = FastMCP()
mcp.add_tool(calc.multiply)  # 使用正确的 schema 注册（只有 'x'，没有 'self'）
```

### 异步支持

FastMCP 同时支持异步（`async def`）和同步（`def`）函数作为 tools。同步 tools 会自动在线程池中运行，以避免阻塞 event loop，因此即使单个 tool 执行阻塞操作，多个 tool 调用也可以并发执行。

```python
from fastmcp import FastMCP
import time

mcp = FastMCP()

@mcp.tool
def slow_tool(x: int) -> int:
    """此同步函数不会阻塞其他并发请求。"""
    time.sleep(2)  # 在线程池中运行，不在 event loop 上
    return x * 2
```

对于诸如网络请求或数据库查询等 I/O 密集型操作，异步 tools 仍然是首选，因为它们比线程池分派更高效。当使用同步库或对于线程开销无关紧要的简单操作时，请使用同步 tools。

### Thread affinity

本节仅适用于同步 tools。异步 tools 已经在 event loop 上运行，因此不受影响。

某些库会将状态绑定到首次使用它们的线程，并在从其他线程调用时中断。最常见的情况是 Windows COM —— 像 `uiautomation`、`comtypes` 以及部分 `pywin32` 这样的库要求在当前线程上调用 `CoInitialize`，而工作池线程默认不会初始化 COM。类似的约束也适用于 `tkinter`、某些 GPU 绑定（CUDA 上下文）以及特定硬件驱动程序。

对于这些情况，请传递 `run_in_thread=False`，这样 FastMCP 将在 event loop 线程上内联调用同步函数，而不是将其分派到工作线程：

```python
import uiautomation as auto

@mcp.tool(run_in_thread=False)
def list_windows() -> list[str]:
    """通过 Windows UI Automation (COM) 列出桌面窗口。"""
    desktop = auto.GetRootControl()
    return [w.Name for w in desktop.GetChildren()[:5]]
```

代价是 event loop 在调用期间被阻塞——其他正在进行中的请求会等待该 tool 返回。请将 `run_in_thread=False` 留给确实需要线程亲和性的 tools，并优先选择在该路径中运行时间较短的调用。

内联同步调用没有取消检查点，因此 `timeout` 无法中断它们。在同步函数上同时使用 `timeout` 和 `run_in_thread=False` 会在注册时被拒绝——请去掉其中一个。

## 参数

默认情况下，FastMCP 通过检查函数的签名和类型注解，将 Python 函数转换为 MCP tools。这允许您为 tools 使用标准的 Python 类型注解。总的来说，该框架力求“开箱即用”：符合语言习惯的 Python 行为，如参数默认值和类型注解，会自动转换为 MCP schemas。不过，有许多方法可以自定义 tools 的行为。

FastMCP 会自动取消引用 tool schemas 中的 `$ref` 条目，以确保与不完全支持 JSON Schema 引用的 MCP 客户端兼容（例如 VS Code Copilot, Claude Desktop）。这意味着使用共享类型的复杂 Pydantic 模型会在 schema 中被内联，而不是使用 `$defs` 引用。

  取消引用是在服务时通过 middleware 发生的，因此您的 schemas 存储时保留 `$ref` 完整，仅在发送给客户端时才内联。如果您知道您的客户端能正确处理 `$ref` 并且偏好更小的 schemas，可以选择退出：

  ```python
  mcp = FastMCP("my-server", dereference_schemas=False)
  ```

### 类型注解

MCP tools 具有类型化参数，FastMCP 使用类型注解来确定这些类型。因此，您应该为 tool 参数使用标准的 Python 类型注解：

```python
@mcp.tool
def analyze_text(
    text: str,
    max_tokens: int = 100,
    language: str | None = None
) -> dict:
    """分析提供的文本。"""
    # 实现...
```

FastMCP 支持广泛的类型注解，包括所有 Pydantic 类型：

| 类型注解           | 示例                                       | 描述                                                      |
| :----------------- | :----------------------------------------- | :-------------------------------------------------------- |
| 基本类型           | `int`, `float`, `str`, `bool`             | 简单的标量值                                              |
| 二进制数据         | `bytes`                                   | 二进制内容（原始字符串，非自动解码的 base64）              |
| 日期和时间         | `datetime`, `date`, `timedelta`           | 日期和时间对象（ISO 格式字符串）                           |
| 集合类型           | `list[str]`, `dict[str, int]`, `set[int]` | 项目集合                                                  |
| 可选类型           | `float \| None`, `Optional[float]`        | 可能为 null/省略的参数                                    |
| 联合类型           | `str \| int`, `Union[str, int]`           | 接受多种类型的参数                                        |
| 约束类型           | `Literal["A", "B"]`, `Enum`               | 具有特定允许值的参数                                      |
| 路径               | `Path`                                    | 文件系统路径（从字符串自动转换）                           |
| UUID               | `UUID`                                    | 通用唯一标识符（从字符串自动转换）                         |
| Pydantic 模型      | `UserData`                                | 具有验证的复杂结构化数据                                  |

FastMCP 支持 Pydantic 作为字段支持的所有类型，包括所有 Pydantic 自定义类型。需要注意的一些 FastMCP 特定行为：

**二进制数据**：`bytes` 参数接受原始字符串，没有自动的 base64 解码。对于 base64 数据，请使用 `str` 并手动用 `base64.b64decode()` 解码。

**枚举**：客户端发送枚举值（`"red"`），而不是名称（`"RED"`）。您的函数接收 Enum 成员（`Color.RED`）。

**路径和 UUID**：字符串输入会自动转换为 `Path` 和 `UUID` 对象。

**Pydantic 模型**：必须作为 JSON 对象（字典）提供，而不是字符串形式的 JSON。即使使用灵活验证，`{"user": {"name": "Alice"}}` 可以工作，但 `{"user": '{"name": "Alice"}'}` 不行。

### 可选参数

FastMCP 遵循 Python 的标准函数参数约定。没有默认值的参数是必需的，而有默认值的参数是可选的。

```python
@mcp.tool
def search_products(
    query: str,                   # 必需 - 无默认值
    max_results: int = 10,        # 可选 - 有默认值
    sort_by: str = "relevance",   # 可选 - 有默认值
    category: str | None = None   # 可选 - 可以为 None
) -> list[dict]:
    """搜索产品目录。"""
    # 实现...
```

在这个例子中，LLM 必须提供 `query` 参数，而 `max_results`、`sort_by` 和 `category` 如果没有明确提供，将使用它们的默认值。

### 验证模式

默认情况下，FastMCP 使用 Pydantic 的灵活验证，强制转换兼容的输入以匹配您的类型注解。这提高了与可能发送值的字符串表示形式（例如对于整数参数发送 `"10"`）的 LLM 客户端的兼容性。

如果您需要更严格的验证，拒绝任何类型不匹配，您可以启用严格输入验证。严格模式使用 MCP SDK 内置的 JSON Schema 验证，在将输入传递给您的函数之前，根据确切的 schema 验证输入：

```python
# 为此服务器启用严格验证
mcp = FastMCP("StrictServer", strict_input_validation=True)

@mcp.tool
def add_numbers(a: int, b: int) -> int:
    """将两个数字相加。"""
    return a + b

# 当 strict_input_validation=True 时，发送 {"a": "10", "b": "20"} 将失败
# 当 strict_input_validation=False（默认）时，它将被强制转换为整数
```

**验证行为对比：**

| 输入类型                                                   | strict\_input\_validation=False（默认） | strict\_input\_validation=True |
| :--------------------------------------------------------- | :-------------------------------------- | :----------------------------- |
| 字符串整数（对 `int` 使用 `"10"`）                        | ✅ 强制转换为整数                        | ❌ 验证错误                     |
| 字符串浮点数（对 `float` 使用 `"3.14"`）                  | ✅ 强制转换为浮点数                      | ❌ 验证错误                     |
| 字符串布尔值（对 `bool` 使用 `"true"`）                   | ✅ 强制转换为布尔值                      | ❌ 验证错误                     |
| 带有字符串元素的列表（对 `list[int]` 使用 `["1", "2"]`） | ✅ 元素被强制转换                        | ❌ 验证错误                     |
| Pydantic 模型字段类型不匹配                                | ✅ 字段被强制转换                        | ❌ 验证错误                     |
| 无效值（对 `int` 使用 `"abc"`）                            | ❌ 验证错误                              | ❌ 验证错误                     |

**关于 Pydantic 模型的说明：** 即使 `strict_input_validation=False`，Pydantic 模型参数也必须作为 JSON 对象（字典）提供，而不是作为字符串形式的 JSON。例如，`{"user": {"name": "Alice"}}` 可以工作，但 `{"user": '{"name": "Alice"}'}` 不行。

对于大多数用例，推荐使用默认的灵活验证模式，因为它能优雅地处理常见的 LLM 客户端行为，同时仍然通过 Pydantic 的验证提供强大的类型安全。

### 参数元数据

您可以通过几种方式提供关于参数的额外元数据：

#### Docstring 描述

FastMCP 会解析您函数的 docstring，以提取 tool 描述和每个参数的描述。支持 Google、NumPy 和 Sphinx 的 docstring 样式——解析器会依次尝试每种样式，并使用能找到参数描述的那种：

```python
@mcp.tool
def process_image(
    image_url: str,
    resize: bool = False,
    width: int = 800,
) -> dict:
    """处理图像，并可选择调整大小。

    Args:
        image_url: 要处理的图像的 URL。
        resize: 是否调整图像大小。
        width: 目标宽度（以像素为单位）。
    """
    # 实现...
```

`Args` 部分上方的自由格式文本——无论是单行还是多段——成为 tool 描述，每个参数的 docstring 条目成为生成 schema 中该参数的描述。像 `Returns`、`Raises` 和 `Example` 这样的部分会被从描述中排除，但其他部分忽略。

如果一个参数已经有明确的描述——通过 `Annotated[x, "..."]` 或 `Field(description=...)`——则该描述优先于 docstring。这使得逐步采用基于 docstring 的描述是安全的：现有的注解继续有效，而 docstring 填补了空白。

#### 简单的字符串描述

对于基本的参数描述，您可以使用带有 `Annotated` 的便捷简写：

```python
from typing import Annotated

@mcp.tool
def process_image(
    image_url: Annotated[str, "要处理的图像的 URL"],
    resize: Annotated[bool, "是否调整图像大小"] = False,
    width: Annotated[int, "目标宽度（以像素为单位）"] = 800,
    format: Annotated[str, "输出图像格式"] = "jpeg"
) -> dict:
    """处理图像，并可选择调整大小。"""
    # 实现...
```

这个简写语法等同于使用 `Field(description=...)`，但对于简单描述更简洁。

此简写语法仅适用于具有单个字符串描述的 `Annotated` 类型。

#### 使用 Field 的高级元数据

对于验证约束和高级元数据，请使用 Pydantic 的 `Field` 类与 `Annotated`：

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def process_image(
    image_url: Annotated[str, Field(description="要处理的图像的 URL")],
    resize: Annotated[bool, Field(description="是否调整图像大小")] = False,
    width: Annotated[int, Field(description="目标宽度（以像素为单位）", ge=1, le=2000)] = 800,
    format: Annotated[
        Literal["jpeg", "png", "webp"], 
        Field(description="输出图像格式")
    ] = "jpeg"
) -> dict:
    """处理图像，并可选择调整大小。"""
    # 实现...
```

您也可以将 Field 用作默认值，尽管推荐使用 Annotated 方法：

```python
@mcp.tool
def search_database(
    query: str = Field(description="搜索查询字符串"),
    limit: int = Field(10, description="最大结果数", ge=1, le=100)
) -> list:
    """使用提供的查询搜索数据库。"""
    # 实现...
```

Field 提供了几个验证和文档特性：

*   `description`：参数的人类可读解释（显示给 LLM）
*   `ge`/`gt`/`le`/`lt`：大于/大于等于/小于/小于等于约束
*   `min_length`/`max_length`：字符串或集合长度约束
*   `pattern`：用于字符串验证的正则表达式模式
*   `default`：如果省略参数时的默认值

### 对 LLM 隐藏参数

要在运行时注入值而不将其暴露给 LLM（例如 `user_id`、凭证或数据库连接），请使用带有 `Depends()` 的依赖注入。使用 `Depends()` 的参数会自动从 tool schema 中排除：

```python
from fastmcp import FastMCP
from fastmcp.dependencies import Depends

mcp = FastMCP()

def get_user_id() -> str:
    return "user_123"  # 在运行时注入

@mcp.tool
def get_user_details(user_id: str = Depends(get_user_id)) -> str:
    # user_id 由服务器注入，不是由 LLM 提供
    return f"{user_id} 的详细信息"
```

关于依赖注入的更多细节，请参见自定义依赖。

## 返回值

FastMCP tools 可以以两种互补的格式返回数据：**传统 content blocks**（如文本和图像）和 **structured outputs**（机器可读的 JSON）。当您添加返回类型注解时，FastMCP 会自动生成 **output schemas** 来验证结构化数据，并使客户端能够将结果反序列化回 Python 对象。

理解这三个概念如何协同工作：

*   **返回值**：您的 Python 函数返回的内容（决定了 content blocks 和结构化数据）
*   **Structured Outputs**：与传统内容一同发送的、用于机器处理的 JSON 数据
*   **Output Schemas**：描述和验证 structured output 格式的 JSON Schema 声明

以下章节详细解释每个概念。

### Content Blocks

FastMCP 会自动将 tool 返回值转换为适当的 MCP content blocks：

*   **`str`**：作为 `TextContent` 发送
*   **`bytes`**：Base64 编码后作为 `BlobResourceContents` 发送（在 `EmbeddedResource` 内）
*   **`fastmcp.utilities.types.Image`**：作为 `ImageContent` 发送
*   **`fastmcp.utilities.types.Audio`**：作为 `AudioContent` 发送
*   **`fastmcp.utilities.types.File`**：作为 base64 编码的 `EmbeddedResource` 发送
*   **MCP SDK content blocks**：原样发送
*   **上述任何内容的列表**：根据上述规则转换每个项目
*   **`None`**：结果为空响应

#### 媒体辅助类

FastMCP 提供了用于返回图像、音频和文件的辅助类。当您返回这些类之一时，无论是直接返回还是作为列表的一部分，FastMCP 都会自动将其转换为相应的 MCP content block。例如，如果您返回一个 `fastmcp.utilities.types.Image` 对象，FastMCP 会将其转换为具有正确 MIME 类型和 base64 编码的 MCP `ImageContent` block。

```python
from fastmcp.utilities.types import Image, Audio, File

@mcp.tool
def get_chart() -> Image:
    """生成一个图表图像。"""
    return Image(path="chart.png")

@mcp.tool
def get_multiple_charts() -> list[Image]:
    """返回多个图表。"""
    return [Image(path="chart1.png"), Image(path="chart2.png")]
```

辅助类只有在**直接**返回或作为**列表**的一部分返回时才会自动转换为 MCP content blocks。对于更复杂的容器（如字典），您可以手动将它们转换为 MCP 类型：

  ```python
  # ✅ 自动转换
  return Image(path="chart.png")
  return [Image(path="chart1.png"), "文本内容"]

  # ❌ 不会被自动转换
  return {"image": Image(path="chart.png")}

  # ✅ 用于嵌套使用的手动转换
  return {"image": Image(path="chart.png").to_image_content()}
  ```

每个辅助类接受 `path=` 或 `data=`（互斥）：

*   **`path`**：文件路径（字符串或 Path 对象）—— 根据扩展名检测 MIME 类型
*   **`data`**：原始字节 —— 需要 `format=` 参数来指定 MIME 类型
*   **`format`**：可选的格式覆盖（例如 "png", "wav", "pdf"）
*   **`name`**：使用 `data=` 时 `File` 的可选名称
*   **`annotations`**：内容的可选 MCP annotations

### Structured Output

2025年6月18日的 MCP 规范更新引入了结构化内容，这是一种从 tools 返回数据的新方式。结构化内容是一个与传统内容一同发送的 JSON 对象。当您的 tool 返回的数据具有 JSON 对象表示时，FastMCP 会自动在传统内容之外创建 structured outputs。这提供了机器可读的 JSON 数据，客户端可以将其反序列化回 Python 对象。

**自动结构化内容规则：**

*   **类对象结果**（`dict`、Pydantic 模型、dataclasses）→ 始终成为结构化内容（即使没有 output schema）
*   **非对象结果**（`int`、`str`、`list`）→ 仅当有 output schema 来验证/序列化它们时才成为结构化内容
*   **所有结果** → 始终成为传统的 content blocks，以保持向后兼容性

这种自动行为使得客户端能够在不需要为类对象返回显式 output schemas 的情况下接收机器可读数据。

#### 字典和对象

当您的 tool 返回字典、dataclass 或 Pydantic 模型时，FastMCP 会自动从中创建结构化内容。结构化内容包含实际的对象数据，使得客户端可以轻松反序列化回原生对象。

```python
  @mcp.tool
  def get_user_data(user_id: str) -> dict:
      """获取用户数据。"""
      return {"name": "Alice", "age": 30, "active": True}
  ```

  ```json
  {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"name\": \"Alice\",\n  \"age\": 30,\n  \"active\": true\n}"
      }
    ],
    "structuredContent": {
      "name": "Alice",
      "age": 30,
      "active": true
    }
  }
  ```

#### 原始类型和集合

当您的 tool 返回原始类型（int、str、bool）或集合（list、set）时，FastMCP 需要返回类型注解来生成结构化内容。注解告诉 FastMCP 如何验证和序列化结果。

没有类型注解，tool 只会产生 `content`：

```python
  @mcp.tool
  def calculate_sum(a: int, b: int):
      """计算总和，没有返回注解。"""
      return a + b  # 返回 8
  ```

  ```json
  {
    "content": [
      {
        "type": "text",
        "text": "8"
      }
    ]
  }
  ```

当您添加返回注解时，例如 `-> int`，FastMCP 通过将原始值包装在一个 `{"result": ...}` 对象中来生成 `structuredContent`，因为 JSON schemas 要求结构化输出的根类型为对象：

```python
  @mcp.tool
  def calculate_sum(a: int, b: int) -> int:
      """计算总和，带返回注解。"""
      return a + b  # 返回 8
  ```

  ```json
  {
    "content": [
      {
        "type": "text",
        "text": "8"
      }
    ],
    "structuredContent": {
      "result": 8
    }
  }
  ```

#### 类型化模型

返回类型注解适用于任何可以转换为 JSON schema 的类型。Dataclasses 和 Pydantic 模型特别有用，因为 FastMCP 提取它们的字段定义来创建详细的 schemas。

```python
  from dataclasses import dataclass
  from fastmcp import FastMCP

  mcp = FastMCP()

  @dataclass
  class Person:
      name: str
      age: int
      email: str

  @mcp.tool
  def get_user_profile(user_id: str) -> Person:
      """获取用户的个人资料信息。"""
      return Person(
          name="Alice",
          age=30,
          email="alice@example.com",
      )
  ```

  ```json
  {
    "properties": {
      "name": {"title": "Name", "type": "string"},
      "age": {"title": "Age", "type": "integer"},
      "email": {"title": "Email", "type": "string"}
    },
    "required": ["name", "age", "email"],
    "title": "Person",
    "type": "object"
  }
  ```

  ```json
  {
    "content": [
      {
        "type": "text",
        "text": "{\"name\": \"Alice\", \"age\": 30, \"email\": \"alice@example.com\"}"
      }
    ],
    "structuredContent": {
      "name": "Alice",
      "age": 30,
      "email": "alice@example.com"
    }
  }
  ```

`Person` dataclass 变成了一个 output schema（第二个选项卡），描述了预期的格式。执行时，客户端会收到带有 `content` 和 `structuredContent` 字段的结果（第三个选项卡）。

### Output Schemas

2025年6月18日的 MCP 规范更新引入了 output schemas，这是一种描述 tool 预期输出格式的新方式。当提供 output schema 时，tool *必须* 返回与该 schema 匹配的 structured output。

当您为函数添加返回类型注解时，FastMCP 会自动生成 JSON schemas 来描述预期的输出格式。这些 schemas 帮助 MCP 客户端理解并验证它们接收到的结构化数据。

#### 原始类型包装

对于原始返回类型（如 `int`、`str`、`bool`），FastMCP 会自动将结果包装在 `"result"` 键下，以创建有效的 structured output：

```python
  @mcp.tool
  def calculate_sum(a: int, b: int) -> int:
      """将两个数字相加。"""
      return a + b
  ```

  ```json
  {
    "type": "object",
    "properties": {
      "result": {"type": "integer"}
    },
    "x-fastmcp-wrap-result": true
  }
  ```

  ```json
  {
    "result": 8
  }
  ```

#### 手动 Schema 控制

您可以通过提供自定义的 `output_schema` 来覆盖自动生成的 schema：

```python
@mcp.tool(output_schema={
    "type": "object", 
    "properties": {
        "data": {"type": "string"},
        "metadata": {"type": "object"}
    }
})
def custom_schema_tool() -> dict:
    """具有自定义 output schema 的 tool。"""
    return {"data": "Hello", "metadata": {"version": "1.0"}}
```

Schema 生成适用于大多数常见类型，包括基本类型、集合、联合类型、Pydantic 模型、TypedDict 结构和 dataclasses。

**重要约束**：

  * Output schemas 必须是对象类型（`"type": "object"`）
  * 如果您提供了一个 output schema，您的 tool **必须** 返回与之匹配的 structured output
  * 然而，您可以在没有 output schema 的情况下提供 structured output（使用 `ToolResult`）

### ToolResult 和元数据

为了完全控制 tool 响应，请返回一个 `ToolResult` 对象。这使您可以明确控制 tool 输出的各个方面：传统内容、结构化数据和元数据。

```python
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

@mcp.tool
def advanced_tool() -> ToolResult:
    """具有完全输出控制的 tool。"""
    return ToolResult(
        content=[TextContent(type="text", text="人类可读的摘要")],
        structured_content={"data": "value", "count": 42},
        meta={"execution_time_ms": 145}
    )
```

`ToolResult` 接受三个字段：

**`content`** - 客户端向用户显示的传统 MCP content blocks。可以是一个字符串（自动转换为 `TextContent`）、一个 MCP content blocks 列表，或任何可序列化的值（转换为 JSON 字符串）。必须提供 `content` 或 `structured_content` 中的至少一个。

```python
# 简单的字符串
ToolResult(content="Hello, world!")

# content blocks 列表
ToolResult(content=[
    TextContent(type="text", text="结果: 42"),
    ImageContent(type="image", data="base64...", mimeType="image/png")
])
```

**`structured_content`** - 一个包含与您的 tool 的 output schema 匹配的结构化数据的字典。这使客户端能够以编程方式处理结果。如果您提供了 `structured_content`，它必须是一个字典或 `None`。如果只提供了 `structured_content`，它也将被用作 `content`（转换为 JSON 字符串）。

```python
ToolResult(
    content="找到 3 个用户",
    structured_content={"users": [{"name": "Alice"}, {"name": "Bob"}]}
)
```

**`meta`**

关于 tool 执行的运行时元数据。将其用于性能指标、调试信息或任何不属于内容或结构化输出的客户端特定数据。

```python
ToolResult(
    content="分析完成",
    structured_content={"result": "positive"},
    meta={
        "execution_time_ms": 145,
        "model_version": "2.1",
        "confidence": 0.95
    }
)
```

`ToolResult` 中的 `meta` 字段是关于 tool 执行的运行时元数据（例如，执行时间、性能指标）。这与 `@mcp.tool(meta={...})` 中的 `meta` 参数不同，后者提供关于 tool 定义本身的静态元数据。

当返回 `ToolResult` 时，您拥有完全控制权——FastMCP 不会自动包装或转换您的数据。`ToolResult` 可以在有或没有 output schema 的情况下返回。

### 自定义序列化

当您需要自定义序列化时（如 YAML、Markdown 表格或专门的格式），请返回带有您序列化内容的 `ToolResult`。这使得序列化在您的 tool 代码中明确且可见：

```python
import yaml
from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult

mcp = FastMCP("MyServer")

@mcp.tool
def get_config() -> ToolResult:
    """以 YAML 格式返回配置。"""
    data = {"api_key": "abc123", "debug": True, "rate_limit": 100}
    return ToolResult(
        content=yaml.dump(data, sort_keys=False),
        structured_content=data
    )
```

对于跨多个 tools 的可重用序列化，请创建一个返回 `ToolResult` 的包装装饰器。这使您可以将序列化器与其他行为（日志记录、验证、缓存）组合在一起，并使序列化在 tool 定义处可见。有关完整实现，请参见 examples/custom\_tool\_serializer\_decorator.py。

## 错误处理

如果您的 tool 遇到错误，您可以引发标准的 Python 异常（`ValueError`, `TypeError`, `FileNotFoundError`, 自定义异常等）或 FastMCP 的 `ToolError`。

默认情况下，所有异常（包括其详细信息）都会被记录并转换为 MCP 错误响应，以发送回客户端 LLM。这有助于 LLM 理解失败并做出适当的反应。

如果您出于安全原因想掩盖内部错误细节，可以：

1. 在创建 `FastMCP` 实例时使用 `mask_error_details=True` 参数：

```python
mcp = FastMCP(name="SecureServer", mask_error_details=True)
```

2. 或使用 `ToolError` 来明确控制发送给客户端的错误信息：

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

@mcp.tool
def divide(a: float, b: float) -> float:
    """将 a 除以 b。"""

    if b == 0:
        # ToolError 的错误消息始终会发送给客户端，
        # 无论 mask_error_details 设置如何
        raise ToolError("不允许除以零。")
    
    # 如果 mask_error_details=True，此消息将被掩盖
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("两个参数都必须是数字。")
        
    return a / b
```

当 `mask_error_details=True` 时，只有来自 `ToolError` 的错误消息会包含详细信息，其他异常将被转换为通用消息。

## Timeouts

Tools 可以指定一个 `timeout` 参数来限制执行所需的时间。当超时被触发时，客户端会收到一个 MCP 错误，并且 tool 会停止处理。这保护您的服务器免受意外缓慢操作的困扰，这些操作可能阻塞资源或让客户端无限期等待。

```python
from fastmcp import FastMCP

mcp = FastMCP()

@mcp.tool(timeout=30.0)
async def fetch_data(url: str) -> dict:
    """获取数据，30 秒超时。"""
    # 如果这花费超过 30 秒，
    # 客户端会收到 MCP 错误
    ...
```

超时时间以秒为单位指定为浮点数。当 tool 超过其超时时间时，FastMCP 会返回一个 MCP 错误，代码为 `-32000`，并附带一条消息指示哪个 tool 超时及其运行了多长时间。同步和异步 tools 都支持超时——同步函数在线程池中运行，因此无论执行模型如何，超时都适用于整个操作。

Tools 必须明确选择加入超时机制。没有服务器级别的默认超时设置。

### Timeouts 与后台任务

Timeouts 适用于**前台执行**——当 tool 直接响应客户端请求运行时。它们保护您的服务器免受由于网络问题、资源争用或其他临时问题而意外挂起的 tools 的影响。

`timeout` 参数**不**适用于后台任务。当 tool 作为后台任务运行时（`task=True`），执行发生在 Docket worker 中，其中不强制执行 FastMCP 超时。

  对于任务超时，请直接在您的函数签名中使用 Docket 的 `Timeout` 依赖：

  ```python
  from datetime import timedelta
  from docket import Timeout

  @mcp.tool(task=True)
  async def long_running_task(
      data: str,
      timeout: Timeout = Timeout(timedelta(minutes=10))
  ) -> str:
      """由 Docket 强制执行 10 分钟超时的任务。"""
      ...
  ```

  有关任务超时和重试的更多信息，请参见 Docket 文档。

当一个 tool 超时时，FastMCP 会记录一条警告，建议使用任务模式。对于您知道将会长时间运行的操作，请改用 `task=True`——后台任务将工作卸载到分布式 worker，并让客户端轮询进度。

## Component Visibility

您可以使用服务器级别的启用控制来控制哪些 tools 对客户端可用。被禁用的 tools 不会出现在 `list_tools` 中，也无法被调用。

```python
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool(tags={"admin"})
def admin_action() -> str:
    """仅限管理员的操作。"""
    return "Done"

@mcp.tool(tags={"public"})
def public_action() -> str:
    """公开操作。"""
    return "Done"

# 通过 key 禁用特定的 tools
mcp.disable(keys={"tool:admin_action"})

# 通过 tag 禁用 tools
mcp.disable(tags={"admin"})

# 或使用允许列表模式 - 仅启用具有特定 tags 的 tools
mcp.enable(tags={"public"}, only=True)
```

有关完整的可见性控制 API，包括 key 格式、基于 tag 的过滤和 provider 级别的控制，请参见 Visibility。

## MCP Annotations

FastMCP 允许您通过 annotations 为 tools 添加专门的元数据。这些 annotations 向客户端应用程序传达 tools 的行为方式，而不会在 LLM 提示中消耗 token 上下文。

Annotations 在客户端应用程序中有几个用途：

*   添加用户友好的标题以供显示
*   指示 tools 是否修改数据或系统
*   描述 tools 的安全配置文件（破坏性与非破坏性）
*   指示 tools 是否与外部系统交互

您可以使用 `@mcp.tool` 装饰器中的 `annotations` 参数为 tool 添加 annotations。FastMCP 接受普通的 dict 或 `ToolAnnotations`；为了保持一致性并获得更好的编辑器/类型支持，下面的示例使用 `ToolAnnotations`。

```python
from mcp.types import ToolAnnotations

@mcp.tool(
    annotations=ToolAnnotations(
        title="计算总和",
        readOnlyHint=True,
        openWorldHint=False,
    )
)
def calculate_sum(a: float, b: float) -> float:
    """将两个数字相加。"""
    return a + b
```

FastMCP 支持以下标准 annotations：

| Annotation        | 类型    | 默认值 | 用途                                                          |
| :---------------- | :------ | :----- | :------------------------------------------------------------ |
| `title`           | string  | -      | 用于用户界面的显示名称                                        |
| `readOnlyHint`    | boolean | false   | 指示 tool 是否仅读取而不进行更改                              |
| `destructiveHint` | boolean | true    | 对于非只读 tools，指示更改是否具有破坏性                      |
| `idempotentHint`  | boolean | false   | 指示重复的相同调用是否与单次调用具有相同的效果                |
| `openWorldHint`   | boolean | true    | 指定 tool 是否与外部系统交互                                |

请记住，annotations 有助于创造更好的用户体验，但应被视为咨询性提示。它们帮助客户端应用程序呈现适当的 UI 元素和安全控制，但本身不会强制执行安全边界。始终专注于使您的 annotations 准确反映您的 tool 的实际行为。

### 使用 Annotation Hints

像 Claude 和 ChatGPT 这样的 MCP 客户端使用 annotation hints 来确定何时跳过确认提示以及如何向用户呈现 tools。最常用的 hint 是 `readOnlyHint`，它表示 tool 仅读取数据而不进行更改。

**只读 tools** 通过以下方式改善用户体验：

*   对于安全操作跳过确认提示
*   允许在没有安全问题的情况下更广泛的访问
*   启用更积极的批处理和缓存

当 tool 检索数据、执行计算或检查状态而不修改状态时，将其标记为只读：

```python
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("Data Server")

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_user(user_id: str) -> dict:
    """通过 ID 检索用户信息。"""
    return {"id": user_id, "name": "Alice"}

@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,  # 重复调用结果相同
        openWorldHint=False   # 仅内部数据
    )
)
def search_products(query: str) -> list[dict]:
    """搜索产品目录。"""
    return [{"id": 1, "name": "Widget", "price": 29.99}]

# 写操作 - 没有 readOnlyHint
@mcp.tool()
def update_user(user_id: str, name: str) -> dict:
    """更新用户信息。"""
    return {"id": user_id, "name": name, "updated": True}

@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def delete_user(user_id: str) -> dict:
    """永久删除用户账户。"""
    return {"deleted": user_id}
```

对于写入数据库、发送通知、创建/更新/删除资源或触发工作流的 tools，请省略 `readOnlyHint` 或将其设置为 `False`。对于无法撤消的操作，使用 `destructiveHint=True`。

客户端特定行为：

*   **ChatGPT**：在 Chat 模式下跳过只读 tools 的确认提示（见 ChatGPT 集成）
*   **Claude**：使用 hints 来理解 tool 安全配置文件并做出更好的执行决策

## 通知

当 tools 被添加、移除、启用或禁用时，FastMCP 会自动向已连接的客户端发送 `notifications/tools/list_changed` 通知。这使得客户端无需手动轮询更改，即可与最新的 tool 集合保持同步。

```python
@mcp.tool
def example_tool() -> str:
    return "Hello!"

# 这些操作会触发通知：
mcp.add_tool(example_tool)              # 发送 tools/list_changed 通知
mcp.disable(keys={"tool:example_tool"}) # 发送 tools/list_changed 通知
mcp.enable(keys={"tool:example_tool"})  # 发送 tools/list_changed 通知
mcp.local_provider.remove_tool("example_tool")  # 发送 tools/list_changed 通知
```

仅当这些操作在活动的 MCP 请求上下文中发生时（例如，从 tool 或其他 MCP 操作中调用时），才会发送通知。在服务器初始化期间执行的操作不会触发通知。

客户端可以使用消息处理器处理这些通知，以自动刷新其 tool 列表或更新其界面。

## 访问 MCP Context

Tools 可以通过 `Context` 对象访问 MCP 功能，如日志记录、读取资源或报告进度。要使用它，请在 tool 函数中添加一个带有 `Context` 类型提示的参数。

```python
from fastmcp import FastMCP, Context

mcp = FastMCP(name="ContextDemo")

@mcp.tool
async def process_data(data_uri: str, ctx: Context) -> dict:
    """处理来自资源的数据，并报告进度。"""
    await ctx.info(f"正在处理来自 {data_uri} 的数据")
    
    # 读取一个资源
    resource = await ctx.read_resource(data_uri)
    data = resource[0].content if resource else ""
    
    # 报告进度
    await ctx.report_progress(progress=50, total=100)
    
    # 向客户端的 LLM 请求帮助的示例
    summary = await ctx.sample(f"用 10 个词总结一下: {data[:200]}")
    
    await ctx.report_progress(progress=100, total=100)
    return {
        "length": len(data),
        "summary": summary.text
    }
```

Context 对象提供以下访问权限：

*   **日志记录**：`ctx.debug()`, `ctx.info()`, `ctx.warning()`, `ctx.error()`
*   **进度报告**：`ctx.report_progress(progress, total)`
*   **资源访问**：`ctx.read_resource(uri)`
*   **LLM 采样**：`ctx.sample(...)`
*   **请求信息**：`ctx.request_id`, `ctx.client_id`

有关 Context 对象及其所有功能的完整文档，请参见 Context 文档。

## 服务器行为

### 重复 Tools

您可以控制在尝试注册多个同名 tools 时 FastMCP 服务器的行为。这可以通过在创建 `FastMCP` 实例时使用 `on_duplicate_tools` 参数来配置。

```python
from fastmcp import FastMCP

mcp = FastMCP(
    name="StrictServer",
    # 配置重复 tool 名称的行为
    on_duplicate_tools="error"
)

@mcp.tool
def my_tool(): return "版本 1"

# 现在这会引发 ValueError，因为 'my_tool' 已经存在
# 并且 on_duplicate_tools 设置为 "error"。
# @mcp.tool
# def my_tool(): return "版本 2"
```

重复行为选项有：

*   `"warn"`（默认）：记录一个警告，新 tool 取代旧 tool。
*   `"error"`：引发 `ValueError`，阻止重复注册。
*   `"replace"`：静默地用新 tool 替换现有 tool。
*   `"ignore"`：保留原始 tool 并忽略新的注册尝试。

### 移除 Tools

您可以通过服务器的本地 provider 动态地移除 tools：

```python
from fastmcp import FastMCP

mcp = FastMCP(name="DynamicToolServer")

@mcp.tool
def calculate_sum(a: int, b: int) -> int:
    """将两个数字相加。"""
    return a + b

mcp.local_provider.remove_tool("calculate_sum")
```

## Versioning

Tools 支持版本控制，允许您在相同名称下维护多个实现，同时客户端会自动接收最高版本。有关版本比较、检索和迁移模式的完整文档，请参见 Versioning。