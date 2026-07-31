# OpenAPI Advanced

Declare additional responses, webhooks, callbacks, and generate client SDKs from your OpenAPI schema.

## Additional Responses in OpenAPI

Document extra status codes and response models so they appear in API docs:

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

class Item(BaseModel):
    id: str
    value: str

class Message(BaseModel):
    message: str

app = FastAPI()

@app.get(
    "/items/{item_id}",
    response_model=Item,
    responses={
        404: {"model": Message, "description": "Item not found"},
        403: {"description": "Forbidden"},
    },
)
async def read_item(item_id: str):
    if item_id == "foo":
        return {"id": "foo", "value": "there goes my hero"}
    return JSONResponse(status_code=404, content={"message": "Item not found"})
```

### Additional Media Types

```python
responses={
    200: {
        "content": {"image/png": {}},
        "description": "Return an image",
    }
}
```

## OpenAPI Webhooks

Define webhooks that your API sends to external systems, documented in OpenAPI:

```python
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Subscription(BaseModel):
    username: str
    monthly_fee: float
    start_date: datetime

@app.webhooks.post("new-subscription")
def new_subscription(body: Subscription):
    """
    When a new user subscribes, we send a POST with this data
    to the URL you register for the `new-subscription` event.
    """

@app.get("/users/")
def read_users():
    return ["Rick", "Morty"]
```

### Key Rules for Webhooks

- `app.webhooks` is an `APIRouter` — you define webhook handlers the same way as path operations.
- The webhook name (e.g., `"new-subscription"`) is an event identifier, not a URL path.
- Webhooks appear in a separate section in `/docs`.
- Available since OpenAPI 3.1.0 / FastAPI 0.99.0.

## OpenAPI Callbacks

Document the external API your API will call back, so external developers know what to implement:

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
    "{$callback_url}/invoices/{$request.body.id}",
    response_model=InvoiceEventReceived,
)
def invoice_notification(body: InvoiceEvent):
    pass

@app.post("/invoices/", callbacks=invoices_callback_router.routes)
def create_invoice(invoice: Invoice, callback_url: HttpUrl | None = None):
    """
    Create an invoice. After processing, we'll send a POST callback
    to your callback_url with the invoice event.
    """
    # . process invoice .
    return {"msg": "Invoice received"}
```

## Generate Client SDKs

Since FastAPI produces OpenAPI, you can auto-generate client SDKs.

### OpenAPI Generator (multi-language)

```bash
# Generate TypeScript client
openapi-generator generate -i http://localhost:8000/openapi.json -g typescript-fetch -o ./client
```

### Hey API (TypeScript optimized)

```bash
npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o ./client -c @hey-api/client-fetch
```

### Key Rules

- FastAPI generates OpenAPI 3.1 — ensure your generator supports it.
- The OpenAPI schema is available at `/openapi.json` by default.
- Well-typed Pydantic models produce better generated clients.
- Use `operation_id` to control function names in generated SDKs.

## Common Pitfalls

### Extra status codes not appearing in docs

```python
# WRONG: 201 won't appear in docs
@app.post("/items/")
def create_item(item: Item):
    return JSONResponse(status_code=201, content=item)
```

```python
# CORRECT: Declare it in responses parameter
@app.post("/items/", responses={201: {"description": "Created"}})
def create_item(item: Item):
    return JSONResponse(status_code=201, content=item)
```

### Callback URLs and variable substitution

Use `{$callback_url}` and `{$request.body.id}` syntax in callback route paths to reference values from the request.