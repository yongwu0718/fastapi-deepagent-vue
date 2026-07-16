# JSON Compatible Encoder

Use `jsonable_encoder` to convert Pydantic models and complex types (datetime, UUID, etc.) into JSON-compatible dicts before storing in databases or returning custom responses.

## Basic Usage

```python
from datetime import datetime
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

fake_db = {}

class Item(BaseModel):
    title: str
    timestamp: datetime
    description: str | None = None

app = FastAPI()

@app.put("/items/{id}")
def update_item(id: str, item: Item):
    json_compatible_item_data = jsonable_encoder(item)
    fake_db[id] = json_compatible_item_data
    return json_compatible_item_data
```

## Key Rules

- `jsonable_encoder` returns a Python `dict` (not a JSON string) — use `json.dumps()` if you need a string.
- It recursively converts all nested objects, including `datetime`, `UUID`, `Decimal`, etc.
- FastAPI uses `jsonable_encoder` internally when you don't specify a `response_model`.

## Common Use Cases

### Storing Pydantic models in non-Pydantic databases

```python
# Convert before storing in a dict-based or NoSQL DB
json_compatible = jsonable_encoder(item)
db.insert(json_compatible)
```

### Using with custom Response objects

When returning a custom `Response`, you must manually convert data:

```python
from fastapi.responses import JSONResponse

@app.put("/items/{id}")
def update_item(id: str, item: Item):
    json_compatible_item_data = jsonable_encoder(item)
    return JSONResponse(content=json_compatible_item_data)
```

## Conversion Examples

| Python Type | Converted To |
|---|---|
| `datetime` | ISO 8601 string |
| `UUID` | string |
| `Decimal` | `float` |
| `set` | `list` |
| Pydantic model | `dict` |

## Common Pitfalls

### Don't use it when you don't need to

```python
# UNNECESSARY: FastAPI handles this automatically
@app.post("/items/")
def create_item(item: Item) -> Item:
    return jsonable_encoder(item)  # Wrong — return the model directly
```

```python
# CORRECT: Let FastAPI handle serialization
@app.post("/items/")
def create_item(item: Item) -> Item:
    return item
```

### jsonable_encoder vs response_model

- Use `response_model` for automatic JSON serialization in responses.
- Use `jsonable_encoder` only when you need the raw dict (e.g., for database storage or custom responses).