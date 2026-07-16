# OpenAPI Callbacks

您可以创建一个包含_路径操作_的 API，它会触发对别人创建的_外部 API_的请求（很可能就是那个会“使用”您 API 的同一个开发者）。

当您的 API 应用调用_外部 API_时，这个过程被称为“Callbacks”。因为外部开发者编写的软件会先向您的 API 发送请求，然后您的 API 再进行_Callbacks_，向_外部 API_发送请求（很可能也是该开发者创建的）。

此时，我们需要存档外部 API 的_信息_，比如应该有哪些_路径操作_，请求体应该是什么，应该返回什么响应等。

## 使用Callbacks的应用

示例如下。

假设要开发一个创建发票的应用。

发票包括 `id`、`title`（可选）、`customer`、`total` 等属性。

API 的用户（外部开发者）要在您的 API 内使用 POST 请求创建一条发票记录。

（假设）您的 API 将：

- 把发票发送至外部开发者的消费者
- 归集现金
- 把通知发送至 API 的用户（外部开发者）
    - 通过（从您的 API）发送 POST 请求至外部 API（即**Callbacks**）来完成

## 常规 **FastAPI** 应用

添加Callbacks前，首先看下常规 API 应用是什么样子。

常规 API 应用包含接收 `Invoice` 请求体的_路径操作_，还有包含Callbacks URL 的查询参数 `callback_url`。

这部分代码很常规，您对绝大多数代码应该都比较熟悉了：
```python
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class Invoice(BaseModel):
    id: str
    title: str | None = None
    customer: str
    total: float


class InvoiceEvent(BaseModel):
    description: str
    paid: bool


class InvoiceEventReceived(BaseModel):
    ok: bool


invoices_callback_router = APIRouter()


@invoices_callback_router.post(
    "{$callback_url}/invoices/{$request.body.id}", response_model=InvoiceEventReceived
)
def invoice_notification(body: InvoiceEvent):
    pass


@app.post("/invoices/", callbacks=invoices_callback_router.routes)
def create_invoice(invoice: Invoice, callback_url: HttpUrl | None = None):
    """
    Create an invoice.

    This will (let's imagine) let the API user (some external developer) create an
    invoice.

    And this path operation will:

    * Send the invoice to the client.
    * Collect the money from the client.
    * Send a notification back to the API user (the external developer), as a callback.
        * At this point is that the API will somehow send a POST request to the
            external API with the notification of the invoice event
            (e.g. "payment successful").
    """
    # Send the invoice, collect the money, send the notification (the callback)
    return {"msg": "Invoice received"}
```
***
提示

`callback_url` 查询参数使用 Pydantic 的 Url 类型。
***
此处唯一比较新的内容是_路径操作装饰器_中的 `callbacks=invoices_callback_router.routes` 参数，下文介绍。

## 存档Callbacks

实际的Callbacks代码高度依赖于您自己的 API 应用。

并且可能每个应用都各不相同。

Callbacks代码可能只有一两行，比如：
```python
callback_url = "https://example.com/api/v1/invoices/events/"
httpx.post(callback_url, json={"description": "Invoice paid", "paid": True})
```

但Callbacks最重要的部分可能是，根据 API 要发送给Callbacks请求体的数据等内容，确保您的 API 用户（外部开发者）正确地实现_外部 API_。

因此，我们下一步要做的就是添加代码，为从 API 接收Callbacks的_外部 API_存档。

这部分文档在 `/docs` 下的 Swagger UI 中显示，并且会告诉外部开发者如何构建_外部 API_。

本例没有实现Callbacks本身（只是一行代码），只有文档部分。
***
提示

实际的Callbacks只是 HTTP 请求。

实现Callbacks时，要使用 HTTPX 或 Requests。
***
## 编写Callbacks文档代码

app不执行这部分代码，只是用它来_记录 外部 API_ 。

但，您已经知道用 **FastAPI** 创建自动 API 文档有多简单了。

我们要使用与存档_外部 API_ 相同的知识...通过创建外部 API 要实现的_路径操作_（您的 API 要调用的）。
***
提示

编写存档Callbacks的代码时，假设您是_外部开发者_可能会用的上。并且您当前正在实现的是_外部 API_，不是_您自己的 API_。

临时改变（为外部开发者的）视角能让您更清楚该如何放置_外部 API_ 响应和请求体的参数与 Pydantic 模型等。
***
### 创建Callbacks的 `APIRouter`

首先，新建包含一些用于Callbacks的 `APIRouter`。
```python
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class Invoice(BaseModel):
    id: str
    title: str | None = None
    customer: str
    total: float


class InvoiceEvent(BaseModel):
    description: str
    paid: bool


class InvoiceEventReceived(BaseModel):
    ok: bool


invoices_callback_router = APIRouter()


@invoices_callback_router.post(
    "{$callback_url}/invoices/{$request.body.id}", response_model=InvoiceEventReceived
)
def invoice_notification(body: InvoiceEvent):
    pass


@app.post("/invoices/", callbacks=invoices_callback_router.routes)
def create_invoice(invoice: Invoice, callback_url: HttpUrl | None = None):
    """
    Create an invoice.

    This will (let's imagine) let the API user (some external developer) create an
    invoice.

    And this path operation will:

    * Send the invoice to the client.
    * Collect the money from the client.
    * Send a notification back to the API user (the external developer), as a callback.
        * At this point is that the API will somehow send a POST request to the
            external API with the notification of the invoice event
            (e.g. "payment successful").
    """
    # Send the invoice, collect the money, send the notification (the callback)
    return {"msg": "Invoice received"}
```
### 创建Callbacks_路径操作_

创建Callbacks_路径操作_也使用之前创建的 `APIRouter`。

它看起来和常规 FastAPI _路径操作_差不多：

- 声明要接收的请求体，例如，`body: InvoiceEvent`
- 还要声明要返回的响应，例如，`response_model=InvoiceEventReceived`

```python
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class Invoice(BaseModel):
    id: str
    title: str | None = None
    customer: str
    total: float


class InvoiceEvent(BaseModel):
    description: str
    paid: bool


class InvoiceEventReceived(BaseModel):
    ok: bool


invoices_callback_router = APIRouter()


@invoices_callback_router.post(
    "{$callback_url}/invoices/{$request.body.id}", response_model=InvoiceEventReceived
)
def invoice_notification(body: InvoiceEvent):
    pass


@app.post("/invoices/", callbacks=invoices_callback_router.routes)
def create_invoice(invoice: Invoice, callback_url: HttpUrl | None = None):
    """
    Create an invoice.

    This will (let's imagine) let the API user (some external developer) create an
    invoice.

    And this path operation will:

    * Send the invoice to the client.
    * Collect the money from the client.
    * Send a notification back to the API user (the external developer), as a callback.
        * At this point is that the API will somehow send a POST request to the
            external API with the notification of the invoice event
            (e.g. "payment successful").
    """
    # Send the invoice, collect the money, send the notification (the callback)
    return {"msg": "Invoice received"}
```

Callbacks_路径操作_与常规_路径操作_有两点主要区别：

- 它不需要任何实际的代码，因为应用不会调用这段代码。它只是用于存档_外部 API_。因此，函数的内容只需要 `pass` 就可以了
- _路径_可以包含 OpenAPI 3 表达式（详见下文），可以使用带参数的变量，以及发送至您的 API 的原始请求的部分

### Callbacks路径表达式

Callbacks_路径_支持包含发送给您的 API 的原始请求的部分的 OpenAPI 3 表达式。

本例中是 `str`：
```python
"{$callback_url}/invoices/{$request.body.id}"
```

因此，如果您的 API 用户（外部开发者）发送请求到您的 API：

`https://yourapi.com/invoices/?callback_url=https://www.external.org/events`

使用如下 JSON 请求体：

```python
{
    "id": "2expen51ve",
    "customer": "Mr. Richie Rich",
    "total": "9999"
}
```

然后，您的 API 就会处理发票，并在某个点之后，发送Callbacks请求至 `callback_url`（外部 API）：

`https://www.external.org/events/invoices/2expen51ve`

JSON 请求体包含如下内容：
```python
{
    "description": "Payment celebration",
    "paid": true
}
```

它会预期_外部 API_ 的响应包含如下 JSON 请求体：
```python
{
    "ok": true
}
```
***
提示

注意，Callbacks URL 包含 `callback_url`（`https://www.external.org/events`）中的查询参数，还有 JSON 请求体内部的发票 ID（`2expen51ve`）。

### 添加Callbacks路由

至此，在上文创建的Callbacks路由里就包含了_Callbacks路径操作_（外部开发者要在外部 API 中实现）。

现在使用 API _路径操作装饰器_的参数 `callbacks`，从Callbacks路由传递属性 `.routes`（实际上只是路由/路径操作的**列表**）：
```python
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class Invoice(BaseModel):
    id: str
    title: str | None = None
    customer: str
    total: float


class InvoiceEvent(BaseModel):
    description: str
    paid: bool


class InvoiceEventReceived(BaseModel):
    ok: bool


invoices_callback_router = APIRouter()


@invoices_callback_router.post(
    "{$callback_url}/invoices/{$request.body.id}", response_model=InvoiceEventReceived
)
def invoice_notification(body: InvoiceEvent):
    pass


@app.post("/invoices/", callbacks=invoices_callback_router.routes)
def create_invoice(invoice: Invoice, callback_url: HttpUrl | None = None):
    """
    Create an invoice.

    This will (let's imagine) let the API user (some external developer) create an
    invoice.

    And this path operation will:

    * Send the invoice to the client.
    * Collect the money from the client.
    * Send a notification back to the API user (the external developer), as a callback.
        * At this point is that the API will somehow send a POST request to the
            external API with the notification of the invoice event
            (e.g. "payment successful").
    """
    # Send the invoice, collect the money, send the notification (the callback)
    return {"msg": "Invoice received"}
```
***
提示

注意，不能把路由本身（`invoices_callback_router`）传递给 `callbacks=`，要传递 `invoices_callback_router.routes` 中的 `.routes` 属性。
***
### 查看文档

现在，启动应用并打开 http://127.0.0.1:8000/docs。

就能看到文档的_路径操作_已经包含了**Callbacks**的内容以及_外部 API_：

![](https://fastapi.tiangolo.com/img/tutorial/openapi-callbacks/image01.png)