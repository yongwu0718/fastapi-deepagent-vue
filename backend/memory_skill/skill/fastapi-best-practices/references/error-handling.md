# Error Handling

FastAPI provides `HTTPException` for returning HTTP errors and supports custom exception handlers.

## HTTPException

```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

### Key Rules
- **Raise `HTTPException`**, never return it — it's an exception, not a response.
- Use appropriate status codes:
  - `400` Bad Request — client input is malformed
  - `401` Unauthorized — missing or invalid credentials
  - `403` Forbidden — valid credentials but insufficient permissions
  - `404` Not Found — resource doesn't exist
  - `409` Conflict — resource state conflict (e.g., duplicate)
  - `422` Unprocessable Entity — validation error (handled automatically by Pydantic)
- Add `headers` parameter for required response headers:

```python
raise HTTPException(
    status_code=401,
    detail="Invalid credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
```

## Custom Exception Handlers

For domain-specific exceptions, create custom handlers:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class ItemNotFoundError(Exception):
    def __init__(self, item_id: int):
        self.item_id = item_id

@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": f"Item {exc.item_id} not found"},
    )
```

## Overriding Default Validation Errors

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        },
    )
```

## Common Patterns

### Fail Fast
Validate at the earliest point — in dependencies or at the start of path operations:

```python
def get_current_active_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = decode_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user
```

### Consistent Error Response Format
Maintain a consistent error response structure across your API:

```python
# All error responses should follow this shape:
{
    "detail": "Human-readable error message",
    # Optional: "code": "ITEM_NOT_FOUND",
}
```