# Python 类型简介

Python 支持可选的“类型提示”（也称为“类型注解”）。

这些**“类型提示”**或注解是一种特殊语法，允许声明变量的 类型。

通过为变量声明类型，编辑器和工具可以为你提供更好的支持。

这仅仅是一个关于 Python 类型提示的**快速教程 / 复习**。它仅涵盖了与 **FastAPI** 一起使用它们所需的最低限度……实际上非常简单。

**FastAPI** 完全基于这些类型提示，它们为框架带来了许多优势和好处。

但即使你从不使用 **FastAPI**，了解一下它们也会让你受益匪浅。

注意

如果你是 Python 专家，并且已经完全掌握了类型提示，请直接跳到下一章。

## 动机

让我们从一个简单的例子开始

```Python
def get_full_name(first_name, last_name):     
	full_name = first_name.title() + " " + last_name.title()    
	return full_name 
	
print(get_full_name("john", "doe"))`
```
调用此程序会输出

```
John Doe
```

该函数执行以下操作

- 接收 `first_name` 和 `last_name`。
- 使用 `title()` 将每个名字的首字母转换为大写。
- 连接 它们，并在中间加一个空格。

```Python
def get_full_name(first_name, last_name):     
	full_name = first_name.title() + " " + last_name.title()    
	return full_name 
	
print(get_full_name("john", "doe"))`
```
### 编辑它

这是一个非常简单的程序。

但现在试想一下，如果你是从零开始编写它。

在某个时刻，你会开始定义函数，参数也都准备好了……

但接着你需要调用“那个将首字母转换为大写的函数”。

是 `upper` 吗？是 `uppercase` 吗？`first_uppercase`？还是 `capitalize`？

于是，你求助于程序员的老朋友：编辑器自动补全。

你输入函数的第一个参数 `first_name`，接着输入一个点 (`.`)，然后按下 `Ctrl+Space` 触发补全。

但是，遗憾的是，你没有得到任何有用的信息。

![](https://fastapi.org.cn/img/python-types/image01.png)

### 添加类型

让我们修改上一版本中的一行代码。

我们将修改这一部分，即函数的参数，从

```python
first_name, last_name
```


变为
```python
first_name: str, last_name: str
```

就是这样。

这就是“类型提示”。

```python
def get_full_name(first_name: str, last_name: str):     
	full_name = first_name.title() + " " + last_name.title()    
	return full_name 
	
print(get_full_name("john", "doe"))`
```

这与声明默认值不同，例如：

```python
first_name="john", last_name="doe"
```

这是两码事。

我们使用的是冒号 (`:`)，而不是等号 (`=`)。

而且添加类型提示通常不会改变程序的运行逻辑。

但现在，试想一下你再次编写该函数，但这次加上了类型提示。

在相同的位置，你再次尝试通过 `Ctrl+Space` 触发自动补全，你会看到

![](https://fastapi.org.cn/img/python-types/image02.png)

有了它，你可以滚动查看选项，直到找到那个“让你有印象”的方法。

![](https://fastapi.org.cn/img/python-types/image03.png)

## 更多动机

看看这个函数，它已经有了类型提示

```python
def get_name_with_age(name: str, age: int):     
	name_with_age = name + " is this old: " + age    
	return name_with_age
```

因为编辑器知道变量的类型，你不仅能获得补全，还能获得错误检查。

![](https://fastapi.org.cn/img/python-types/image04.png)

现在你知道需要修复它，用 `str(age)` 将 `age` 转换为字符串。

```python
def get_name_with_age(name: str, age: int):     
	name_with_age = name + " is this old: " + str(age)    
	return name_with_age
```

## 声明类型

你刚刚看到了声明类型提示的主要位置：函数参数。

这也是你在 **FastAPI** 中使用它们的主要场景。
### 简单类型

你可以声明所有标准 Python 类型，不仅是 `str`。

例如，你可以使用：

- `int`
- `float`
- `bool`
- `bytes`

```python
def get_items(item_a: str, item_b: int, item_c: float, item_d: bool, item_e: bytes):     
	return item_a, item_b, item_c, item_d, item_e
```

``
### `typing` 模块

对于某些特殊用例，你可能需要从标准库的 `typing` 模块导入一些内容。例如，当你想要声明某个东西为“任意类型”时，可以使用 `typing` 中的 `Any`。

```python
from typing import Any 

def some_function(data: Any):     
	print(data)
```

### 泛型

某些类型可以在方括号内接收“类型参数”，以定义其内部类型。例如，“字符串列表”可以声明为 `list[str]`。

这些可以接收类型参数的类型被称为**泛型 (Generic types)** 或 **Generics**。

你可以将内置类型作为泛型使用（在方括号内填入类型）：

- `list`
- `tuple`
- `set`
- `dict`

#### List

例如，让我们定义一个 `list`，其中包含 `str`。

使用同样的冒号 (`:`) 语法声明变量。

类型使用 `list`。

由于 `list` 是一个包含内部类型的类型，将其放在方括号中：

```python
def process_items(items: list[str]):     
	for item in items:        
		print(item)
```

注意

方括号内的那些内部类型被称为“类型参数”。

在本例中，`str` 是传递给 `list` 的类型参数。

这意味着：“变量 `items` 是一个 `list`，且列表中的每一项都是 `str`”。

通过这样做，即使在处理列表中的元素时，编辑器也能提供支持。

![](https://fastapi.org.cn/img/python-types/image05.png)

如果没有类型提示，这是几乎无法实现的。

请注意，变量 `item` 是列表 `items` 中的一个元素。

即便如此，编辑器仍然知道它是一个 `str`，并提供相应的支持。

#### Tuple 和 Set

声明 `tuple` 和 `set` 的方式相同：

```python
def process_items(items_t: tuple[int, int, str], items_s: set[bytes]):     
	return items_t, items_s
```

这意味着：

- 变量 `items_t` 是一个包含 3 项的 `tuple`，分别为 `int`、`int` 和 `str`。
- 变量 `items_s` 是一个 `set`，且其中的每一项都是 `bytes` 类型。

#### Dict

要定义 `dict`，需传入 2 个用逗号分隔的类型参数。

第一个类型参数用于 `dict` 的键 (keys)。

第二个类型参数用于 `dict` 的值 (values)。

```python
def process_items(prices: dict[str, float]):     
	for item_name, item_price in prices.items():        
	print(item_name)        
	print(item_price)
```

这意味着：

- 变量 `prices` 是一个 `dict`。
    - 该 `dict` 的键是 `str` 类型（比如物品名称）。
    - 该 `dict` 的值是 `float` 类型（比如物品价格）。

#### Union

你可以声明一个变量可以是**多种类型**中的任意一种，例如 `int` 或 `str`。

定义时使用 竖线 (`|`) 来分隔这两种类型。

这被称为“联合类型 (union)”，因为该变量可以是这两个类型集合并集中的任何值。
```python
def process_item(item: int | str):     
	print(item)
```

这意味着 `item` 可以是 `int` 或 `str`。

#### 可能为 `None`

你可以声明一个值可以是某种类型（如 `str`），但也可能为 `None`。

```python
def say_hi(name: str | None = None):     
	if name is not None:        
		print(f"Hey {name}!")    
	else:        
		print("Hello World")
```

使用 `str | None` 而不是仅仅 `str`，可以让编辑器帮助你检测错误。如果你假设某个值总是 `str`，但它实际上也可能是 `None`，编辑器就会提示。

### 类作为类型

你还可以声明一个类作为变量的类型。

假设你有一个带有名为 name 属性的 `Person` 类。

```python
class Person:     
	def __init__(self, name: str):        
		self.name = name 

def get_person_name(one_person: Person):     
	return one_person.name
```

然后你可以将变量声明为 `Person` 类型。

```python
class Person:     
	def __init__(self, name: str):        
	self.name = name 
	
def get_person_name(one_person: Person):     
	return one_person.name
```

接着，你再次获得了所有的编辑器支持。

![](https://fastapi.org.cn/img/python-types/image06.png)

注意，这意味着“`one_person` 是 `Person` 类的一个**实例**”。

并不意味着“`one_person` 是名为 `Person` 的**类**本身”。

## Pydantic 模型

[Pydantic](https://docs.pydantic.org.cn/) 是一个执行数据验证的 Python 库。

你将数据的“形态”声明为带有属性的类。

并且每个属性都有一个类型。

然后你使用一些值创建该类的实例，它会验证这些值，将它们转换为适当的类型（如果需要），并为你提供一个包含所有数据的对象。

并且你可以在生成的对象上获得完整的编辑器支持。

官方 Pydantic 文档中的一个示例

```python
from datetime import datetime 
from pydantic import BaseModel 

class User(BaseModel):     
	id: int    
	name: str = "John Doe"    
	signup_ts: datetime | None = None    
	friends: list[int] = [] 

external_data = {     
	"id": "123",    
	"signup_ts": "2017-06-01 12:22",    
	"friends": [1, "2", b"3"], 
}

user = User(**external_data) 
print(user) 
# > User id=123 name='John Doe' signup_ts=datetime.datetime(2017, 6, 1, 12, 22) friends=[1, 2, 3]
print(user.id) 
# > 123
```

注意

要了解关于 [Pydantic 的更多信息，请查阅其文档](https://docs.pydantic.org.cn/)。

**FastAPI** 完全基于 Pydantic。

你将在 [教程 - 用户指南](https://fastapi.org.cn/tutorial/) 中看到更多实际应用。

## 带有元数据注解的类型提示

Python 还有一个特性，允许使用 `Annotated` 在类型提示中放置**额外的 元数据**。

你可以从 `typing` 导入 `Annotated`。

```python
from typing import Annotated 

def say_hello(name: Annotated[str, "this is just metadata"]) -> str:     
	return f"Hello {name}"
```

Python 本身不会对 `Annotated` 做任何处理。对于编辑器和其他工具，类型依然是 `str`。

但你可以利用 `Annotated` 中的空间，为 **FastAPI** 提供关于你希望应用程序如何运行的额外元数据。

需要记住的重要一点是，传递给 `Annotated` 的第一个_类型参数_ 是 **实际类型**。其余部分只是给其他工具使用的元数据。

现在你只需要知道 `Annotated` 的存在，并且它是标准 Python。 😎

稍后你将看到它有多么**强大**。

提示

它是**标准 Python**这一事实意味着，你仍然可以在编辑器中获得**最佳的开发者体验**，以及用于分析和重构代码的工具支持等。 ✨

同时，你的代码也将与许多其他 Python 工具和库高度兼容。 🚀

## **FastAPI** 中的类型提示

**FastAPI** 利用这些类型提示来完成多项工作。

使用 **FastAPI**，你可以通过类型提示声明参数，从而获得：

- **编辑器支持**.
- **类型检查**.

……且 **FastAPI** 使用相同的声明来：

- **定义需求**：从请求路径参数、查询参数、请求头、请求体、依赖项等。
- **转换数据**：将请求数据转换为所需的类型。
- **验证数据**：对每个请求进行验证。
    - 当数据无效时，自动生成**错误信息**并返回给客户端。
- 使用 OpenAPI **记录** API
    - 该 OpenAPI 文档随后会被自动交互式 API 文档界面所使用。

这一切听起来可能很抽象。别担心，你将在 [教程 - 用户指南](https://fastapi.org.cn/tutorial/) 中看到所有这些功能的实际操作。

最重要的一点是，通过在同一个地方使用标准 Python 类型（而不是添加更多的类、装饰器等），**FastAPI** 可以为你完成大量工作。

注意

如果你已经完成了所有教程并回来查看更多类型相关内容，[`mypy` 的“备忘清单 (cheat sheet)”](https://mypy.readthedocs.io/en/latest/cheat_sheet_py3.html) 是一个很好的资源。