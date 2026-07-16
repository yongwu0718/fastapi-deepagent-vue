# Middleware

Middleware wraps every request/response cycle. It runs before the request reaches the path operation and after the response is generated.

## Basic Middleware

```python
import time
from fastapi import FastAPI, Request

app = FastAPI()

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## Key Rules

- **Always call `await call_next(request)`** — the middleware must forward the request.
- **Always return the response** — modified or unmodified.
- Middleware executes in **reverse order** of registration.
- Code before `call_next` runs before the path operation; code after runs after.
- `yield`-based dependency cleanup runs **after** middleware.
- Background tasks run **after** all middleware.

## CORS Middleware

CORS is a special middleware for cross-origin access:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Middleware Execution Order

```python
app.add_middleware(MiddlewareA)  # Registered first
app.add_middleware(MiddlewareB)  # Registered second

# Execution order:
# Request → MiddlewareA (before) → MiddlewareB (before) → Path Operation
# Response → MiddlewareB (after) → MiddlewareA (after) → Client
```

## Common Pitfalls

### Don't consume the request body

```python
# WRONG: Reading body in middleware consumes it
@app.middleware("http")
async def log_body(request: Request, call_next):
    body = await request.body()  # Body is now consumed!
    print(body)
    response = await call_next(request)  # Path operation gets empty body
    return response
```

### Async middleware blocking

```python
# WRONG: Blocking call in async middleware
@app.middleware("http")
async def slow_middleware(request: Request, call_next):
    time.sleep(1)  # Blocks event loop!
    return await call_next(request)
```

### Middleware vs Dependency

| Use Case | Use |
|----------|-----|
| Run on every request globally | Middleware |
| Run on specific routes | Dependency |
| Need access to path operation result | Middleware (after call_next) |
| Need DI (sub-dependencies, yield) | Dependency |
| Response transformation | Middleware |