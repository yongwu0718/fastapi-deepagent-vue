# Path Operations

Path operations are the core of any FastAPI application. They define the URL routes and HTTP methods your API exposes.

## Path Parameters

Declare path parameters with Python format string syntax:

```python
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
```

### Key Rules
- **Always type-annotate** path parameters — FastAPI uses the type hint for automatic parsing and validation.
- Path parameters are **required** by default (no default value = required).
- Use `Path()` for additional validation constraints:

```python
from fastapi import Path

@app.get("/items/{item_id}")
async def read_item(
    item_id: int = Path(gt=0, le=1000, description="The item ID")
):
    return {"item_id": item_id}
```

### Enum path parameters

```python
from enum import Enum

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    return {"model_name": model_name}
```

### Path operation configuration

```python
@app.get(
    "/items/",
    tags=["items"],
    summary="List all items",
    description="Returns a paginated list of items",
    response_description="The list of items",
)
async def list_items(skip: int = 0, limit: int = 10):
    .
```

## Query Parameters

Non-path function parameters automatically become query parameters:

```python
@app.get("/items/")
async def read_items(skip: int = 0, limit: int = 10, q: str | None = None):
    return {"skip": skip, "limit": limit, "q": q}
```

### Query Validation

```python
from fastapi import Query

@app.get("/items/")
async def read_items(
    q: str = Query(
        default=None,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        alias="search-query",
        deprecated=True,
    )
):
    .
```

### Query Parameter Models (Pydantic)

```python
from pydantic import BaseModel
from fastapi import Query

class FilterParams(BaseModel):
    q: str | None = Query(None, min_length=3)
    skip: int = Query(0, ge=0)
    limit: int = Query(10, ge=1, le=100)
    sort_by: str = Query("created_at")

@app.get("/items/")
async def read_items(filters: FilterParams = Depends()):
    .
```

## Path vs Query: Route Order Matters

FastAPI matches routes in order. Put fixed paths before parameterized paths:

```python
@app.get("/users/me")          # Fixed path FIRST
async def read_user_me(): .

@app.get("/users/{user_id}")   # Parameterized path AFTER
async def read_user(user_id: int): .
```

If reversed, `/users/me` would match `user_id="me"` (and fail int parsing).