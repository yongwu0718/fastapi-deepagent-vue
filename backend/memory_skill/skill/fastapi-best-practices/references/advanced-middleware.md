# Advanced Middleware

Add ASGI middleware, built-in security middleware (HTTPS redirect, trusted host), and strict Content-Type checking.

## Adding ASGI Middleware

Any ASGI-compatible middleware can be added via `app.add_middleware()`:

```python
from fastapi import FastAPI
from unicorn import UnicornMiddleware

app = FastAPI()

app.add_middleware(UnicornMiddleware, some_config="rainbow")
```

## Built-in Middleware

### `HTTPSRedirectMiddleware`

Force all incoming requests to use `https` or `wss`:

```python
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)

@app.get("/")
async def main():
    return {"message": "Hello World"}
```

### `TrustedHostMiddleware`

Guard against HTTP Host header attacks:

```python
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["example.com", "*.example.com"],
)
```

## Strict Content-Type Checking

FastAPI enforces `Content-Type: application/json` for JSON endpoints by default. This protects against a CSRF attack vector in local-network scenarios.

### Disable strict checking

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(strict_content_type=False)

class Item(BaseModel):
    name: str
    price: float

@app.post("/items/")
async def create_item(item: Item):
    return item
```

### When to disable

- Your API is on the public internet with proper authentication (CSRF vector doesn't apply).
- You need to accept requests from clients that don't send `Content-Type` headers.

### When to keep enabled (default)

- Your API runs on `localhost` or an internal network without authentication.
- You trust network isolation as your only security boundary.

## Middleware Execution Order

```python
app.add_middleware(MiddlewareA)  # Registered first
app.add_middleware(MiddlewareB)  # Registered second

# Request flow:  MiddlewareA → MiddlewareB → Path Operation
# Response flow: MiddlewareB → MiddlewareA → Client
```

## Custom ASGI Middleware Class

```python
class CustomASGIMiddleware:
    def __init__(self, app, some_param: str):
        self.app = app
        self.some_param = some_param

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Pre-processing
            pass
        await self.app(scope, receive, send)
        if scope["type"] == "http":
            # Post-processing
            pass

app.add_middleware(CustomASGIMiddleware, some_param="value")
```

## Common Pitfalls

### Using `app = SomeMiddleware(app)` instead of `app.add_middleware()`

```python
# WRONG: Bypasses FastAPI's error handling and custom exception handlers
from brotli_asgi import BrotliMiddleware
app = BrotliMiddleware(app)
```

```python
# CORRECT: Integrates properly with FastAPI
app.add_middleware(BrotliMiddleware)
```

### Not forwarding headers behind a proxy

When running behind Nginx/Traefik, enable forwarded headers (see [behind-proxy](behind-proxy.md)) and ensure middleware correctly handles `X-Forwarded-*` headers.