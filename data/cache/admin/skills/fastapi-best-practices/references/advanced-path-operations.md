# Advanced Path Operations

Customize OpenAPI `operationId`, exclude routes from docs, and control docstring parsing.

## Custom `operationId`

Set a unique ID for each path operation for better SDK generation:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/", operation_id="list_items")
async def read_items():
    return [{"item_id": "Foo"}]
```

### Auto-generate operationId from function names

Use function names as `operationId` for all routes:

```python
from fastapi import FastAPI
from fastapi.routing import APIRoute

app = FastAPI()

@app.get("/items/")
async def read_items():
    return [{"item_id": "Foo"}]

@app.post("/items/")
async def create_item():
    return {"item_id": "Foo"}

def use_route_names_as_operation_ids(app: FastAPI) -> None:
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name

use_route_names_as_operation_ids(app)
```

Result: `operationId` becomes `read_items` and `create_item`.

## Exclude from OpenAPI Schema

Hide an endpoint from the docs entirely:

```python
@app.get("/internal/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}
```

## Docstring for OpenAPI Descriptions

FastAPI reads function docstrings for OpenAPI descriptions:

```python
@app.post("/items/")
async def create_item(item: Item):
    """
    Create a new item.

    This endpoint accepts an Item model and stores it in the database.
    Returns the created item with its generated ID.
    """
    .
```

## Advanced OpenAPI Customization

Add arbitrary extensions to the OpenAPI schema:

```python
@app.get(
    "/items/",
    openapi_extra={
        "x-custom-extension": "some-value",
        "x-code-samples": [{"lang": "Python", "source": "import requests"}],
    },
)
async def read_items():
    return [{"item_id": "Foo"}]
```

## Key Rules

- `operation_id` must be unique across all routes — FastAPI enforces this.
- `include_in_schema=False` removes the route from `/docs`, `/redoc`, and `/openapi.json`.
- `openapi_extra` is merged directly into the OpenAPI path operation object — useful for custom tooling.
- When using `use_route_names_as_operation_ids`, ensure all function names are unique (even across modules).

## Common Pitfalls

### Duplicate operationId

```python
# WRONG: Both routes have the same operationId
@app.get("/items/", operation_id="items")
async def read_items(): .

@app.post("/items/", operation_id="items")  # Error!
async def create_item(): .
```

### Calling `use_route_names_as_operation_ids` too early

```python
# WRONG: Called before all routes are registered
app = FastAPI()
use_route_names_as_operation_ids(app)  # Too early!

@app.get("/items/")
async def read_items(): .
```

```python
# CORRECT: Call after all routes are added
app = FastAPI()

@app.get("/items/")
async def read_items(): .
@app.post("/items/")
async def create_item(): .

use_route_names_as_operation_ids(app)
```