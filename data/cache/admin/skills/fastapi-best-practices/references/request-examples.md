# Request Examples

Declare example data for your API endpoints so they appear in OpenAPI docs and auto-generated clients.

## Pydantic Model `json_schema_extra`

Add examples at the model level using `model_config`:

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Foo",
                    "description": "A very nice Item",
                    "price": 35.4,
                    "tax": 3.2,
                }
            ]
        }
    }
```

## Field-level `examples`

Use `Field(examples=[.])` for per-field examples:

```python
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(examples=["Foo"])
    description: str | None = Field(default=None, examples=["A very nice Item"])
    price: float = Field(examples=[35.4])
    tax: float | None = Field(default=None, examples=[3.2])
```

## Examples in `Body()`, `Query()`, `Path()`, `Header()`, `Cookie()`

```python
from typing import Annotated
from fastapi import Body, FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item: Annotated[
        Item,
        Body(
            examples=[
                {
                    "name": "Foo",
                    "description": "A very nice Item",
                    "price": 35.4,
                    "tax": 3.2,
                }
            ],
        ),
    ],
):
    results = {"item_id": item_id, "item": item}
    return results
```

## Key Rules

- Use `examples` (plural) for OpenAPI 3.1.0+ (FastAPI >= 0.99.0). The old `example` (singular) is deprecated.
- `json_schema_extra` is for arbitrary JSON Schema extensions — you can add custom metadata for frontend consumption.
- Examples in `Body()` / `Query()` / `Path()` take precedence over model-level examples in docs.

## Where to Declare

| Scope | Method | Best For |
|---|---|---|
| Per-field | `Field(examples=[.])` | Single field examples |
| Per-model | `model_config` → `json_schema_extra` | Full request body examples |
| Per-parameter | `Body(examples=[.])` | Override for specific endpoints |
| Per-query/path | `Query(examples=[.])` | Query/path parameter examples |