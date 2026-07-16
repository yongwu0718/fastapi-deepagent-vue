# Custom Responses

Beyond the default JSON response, FastAPI lets you return HTML, streaming, files, and set cookies, headers, and status codes dynamically.

## Returning a Response Directly

When you return a `Response` (or subclass), FastAPI passes it through without any transformation:

```python
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

@app.get("/legacy/")
def get_legacy_data():
    data = """<?xml version="1.0"?>
    <shampoo>
    <Header>Apply shampoo here.</Header>
    </shampoo>"""
    return Response(content=data, media_type="application/xml")
```

### Key Rule: Use `jsonable_encoder` with custom `JSONResponse`

```python
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

@app.put("/items/{id}")
def update_item(id: str, item: Item):
    json_compatible_item_data = jsonable_encoder(item)
    return JSONResponse(content=json_compatible_item_data)
```

## Available Response Types

| Response Class | Use Case |
|---|---|
| `JSONResponse` | Default JSON responses |
| `HTMLResponse` | Return HTML content |
| `PlainTextResponse` | Return plain text |
| `StreamingResponse` | Stream large files or real-time data |
| `FileResponse` | Serve files for download |
| `RedirectResponse` | HTTP redirects |
| `ORJSONResponse` | Faster JSON (requires `orjson`) |

## HTML Response

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/items/", response_class=HTMLResponse)
async def read_items():
    return """
    <html>
        <head><title>Items</title></head>
        <body><h1>Items Page</h1></body>
    </html>
    """
```

## Setting Cookies

### Via `Response` parameter (recommended)

```python
from fastapi import FastAPI, Response

@app.post("/cookie-and-object/")
def create_cookie(response: Response):
    response.set_cookie(key="fakesession", value="fake-cookie-session-value")
    return {"message": "Come to the dark side, we have cookies"}
```

### Via direct `Response` return

```python
from fastapi.responses import JSONResponse

@app.post("/cookie/")
def create_cookie():
    content = {"message": "Come to the dark side, we have cookies"}
    response = JSONResponse(content=content)
    response.set_cookie(key="fakesession", value="fake-cookie-session-value")
    return response
```

## Setting Response Headers

### Via `Response` parameter (recommended)

```python
@app.get("/headers-and-object/")
def get_headers(response: Response):
    response.headers["X-Cat-Dog"] = "alone in the world"
    return {"message": "Hello World"}
```

### Via direct `Response` return

```python
@app.get("/headers/")
def get_headers():
    content = {"message": "Hello World"}
    headers = {"X-Cat-Dog": "alone in the world", "Content-Language": "en-US"}
    return JSONResponse(content=content, headers=headers)
```

### Custom Headers

Use `X-` prefix for custom proprietary headers. Expose them via CORS `expose_headers` if browsers need to read them:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    expose_headers=["X-Custom-Header"],
)
```

## Dynamic Status Codes

Use `response.status_code` to override the default status code:

```python
from fastapi import FastAPI, Response, status

tasks = {"foo": "Listen to the Bar Fighters"}

@app.put("/get-or-create-task/{task_id}", status_code=200)
def get_or_create_task(task_id: str, response: Response):
    if task_id not in tasks:
        tasks[task_id] = "This didn't exist before"
        response.status_code = status.HTTP_201_CREATED
    return tasks[task_id]
```

## Returning Extra Status Codes

For multiple possible status codes, return `Response` objects directly:

```python
from fastapi.responses import JSONResponse

@app.put("/items/{item_id}")
async def upsert_item(item_id: str, name: str | None = None, size: int | None = None):
    if item_id in items:
        items[item_id] = {"name": name, "size": size}
        return items[item_id]  # 200
    else:
        items[item_id] = {"name": name, "size": size}
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=items[item_id])
```

## `response_class` vs `Response` Return

| Method | When to Use |
|---|---|
| `response_class=HTMLResponse` | All responses from this endpoint use the same type, still want `response_model` filtering |
| Direct `return Response(.)` | Need full control, no automatic filtering/conversion |

## Key Rules

- When you return a `Response` directly, FastAPI does **no** automatic conversion — you must handle serialization yourself.
- When you use `response_class` with a Pydantic `response_model`, FastAPI still filters/converts data before passing to the response class.
- `jsonable_encoder` is your friend when returning custom `JSONResponse` with complex types.
- Cookies and headers set via `Response` parameter work with `response_model` filtering.
- Extra status codes returned directly won't appear in OpenAPI docs — use `responses` parameter to document them (see [openapi-advanced](openapi-advanced.md)).