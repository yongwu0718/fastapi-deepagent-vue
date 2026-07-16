# Using Dataclasses

FastAPI supports standard library `dataclasses` as an alternative to Pydantic models, with full validation, serialization, and documentation support.

## Basic Usage

```python
from dataclasses import dataclass
from fastapi import FastAPI

@dataclass
class Item:
    name: str
    price: float
    description: str | None = None
    tax: float | None = None

app = FastAPI()

@app.post("/items/")
async def create_item(item: Item):
    return item
```

## Using Dataclasses with `response_model`

```python
from dataclasses import dataclass, field
from fastapi import FastAPI

@dataclass
class Item:
    name: str
    price: float
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    tax: float | None = None

app = FastAPI()

@app.get("/items/next", response_model=Item)
async def read_next_item():
    return {
        "name": "Island In The Moon",
        "price": 12.99,
        "description": "A place to be playin' and havin' fun",
        "tags": ["breater"],
    }
```

## How It Works

FastAPI uses Pydantic's built-in dataclass support under the hood. Standard dataclasses are automatically converted to Pydantic-style dataclasses, giving you:

- Data validation
- Data serialization
- OpenAPI schema generation
- Editor autocompletion

## Dataclasses vs Pydantic Models

| Feature | dataclass | Pydantic BaseModel |
|---|---|---|
| Validation | Yes (via Pydantic) | Yes (native) |
| `Field()` constraints | Yes | Yes |
| `model_config` | No | Yes |
| Custom validators | Limited | Full support |
| `model_dump()` | No | Yes |
| JSON Schema customization | Limited | Full support |

## Key Rules

- Use `field(default_factory=list)` for mutable defaults (lists, dicts, sets) — same as standard dataclass rules.
- Dataclasses can't do everything Pydantic models can. If you need custom validators, `model_config`, or advanced features, use Pydantic `BaseModel`.
- Dataclasses are great when you already have dataclasses in your codebase and want to expose them as FastAPI endpoints.

## Common Pitfalls

### Mutable default values

```python
# WRONG: Shared list across all instances
@dataclass
class Item:
    tags: list[str] = []
```

```python
# CORRECT: Use field(default_factory=list)
from dataclasses import field

@dataclass
class Item:
    tags: list[str] = field(default_factory=list)
```

### Missing Pydantic features

```python
# This won't work with dataclasses:
# - model_config for extra schema data
# - @field_validator / @model_validator
# - model_dump() / model_validate()

# Use BaseModel instead if you need these.
```