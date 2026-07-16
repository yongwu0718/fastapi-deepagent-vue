# Using Request Directly

Access the raw Starlette `Request` object in path operations when you need request-level data not covered by FastAPI's parameter parsing.

## Basic Usage

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/items/{item_id}")
def read_root(item_id: str, request: Request):
    client_host = request.client.host
    return {"client_host": client_host, "item_id": item_id}
```

## Available Request Attributes

| Attribute | Description |
|---|---|
| `request.client.host` | Client IP address |
| `request.client.port` | Client port |
| `request.url` | Full URL object |
| `request.url.path` | URL path |
| `request.headers` | Request headers dict |
| `request.cookies` | Request cookies dict |
| `request.method` | HTTP method |
| `request.query_params` | Query parameters |
| `request.path_params` | Path parameters |

## Key Rules

- FastAPI still validates and converts other declared parameters (path, query, body) even when you use `Request`.
- Data extracted directly from `Request` is **not** validated, converted, or documented by FastAPI.
- Use `Request` only for edge cases — prefer FastAPI's parameter declarations for standard input.

## Common Use Cases

### Get client IP

```python
@app.get("/client-info/")
async def get_client_info(request: Request):
    return {"ip": request.client.host}
```

### Read raw request body

```python
@app.post("/raw-body/")
async def read_raw_body(request: Request):
    body = await request.body()
    return {"raw": body.decode()}
```

### Read custom headers

```python
@app.get("/headers/")
async def read_headers(request: Request):
    user_agent = request.headers.get("User-Agent")
    return {"user_agent": user_agent}
```

## Common Pitfalls

### Mixing Request body with Pydantic body

```python
# WRONG: Reading body in Request consumes it before Pydantic can parse it
@app.post("/items/")
async def create_item(request: Request, item: Item):  # item will be empty!
    body = await request.body()
    .
```

### Using Request when FastAPI parameters work

```python
# WRONG: Unnecessary use of Request
@app.get("/items/")
async def read_items(request: Request):
    q = request.query_params.get("q")
    skip = request.query_params.get("skip", 0)
    return {"q": q, "skip": skip}

# CORRECT: Use FastAPI query parameters
@app.get("/items/")
async def read_items(q: str | None = None, skip: int = 0):
    return {"q": q, "skip": skip}
```