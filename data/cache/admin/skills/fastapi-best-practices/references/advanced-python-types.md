# Advanced Python Types

Use `Union`, `Optional`, and best practices for type annotations in FastAPI.

## `Union` vs `|` Syntax

Both are equivalent. Prefer `|` in type annotations, use `Union` in `response_model=` parameters:

```python
from typing import Union

# These are equivalent
def say_hi(name: str | None): .
def say_hi(name: Union[str, None]): .

# Use Union when | isn't available (e.g., in response_model)
@app.get("/items/", response_model=Union[Item, None])
```

## `Optional` vs `Union[., None]`

`Optional[SomeType]` is equivalent to `Union[SomeType, None]`. The recommendation:

- **Avoid `Optional[SomeType]`** — the word "optional" misleadingly suggests the value isn't required.
- **Use `SomeType | None`** (or `Union[SomeType, None]`) — explicitly states "it can be `None`".

```python
# AVOID: Misleading — name is still required, just can be None
from typing import Optional
def say_hi(name: Optional[str]):
    print(f"Hey {name}!")

say_hi()  # Error! name is required

# PREFER: Clear intent
def say_hi(name: str | None):
    print(f"Hey {name}!")

say_hi(name=None)  # Works
```

## Type Aliases

Simplify complex types:

```python
type UserID = int
type ItemDict = dict[str, int | str]
type CallbackUrl = str | None
```

## Generic Types

```python
from typing import TypeVar, Generic

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int

@app.get("/items/", response_model=PaginatedResponse[Item])
async def list_items():
    return {"items": [.], "total": 100, "page": 1, "size": 10}
```

## `Annotated` for Metadata

FastAPI + Pydantic recommended pattern:

```python
from typing import Annotated
from fastapi import Depends, Query

# Preferred over bare Depends()
CurrentUser = Annotated[User, Depends(get_current_user)]

@app.get("/me/")
async def read_me(current_user: CurrentUser):
    return current_user

# With Query validation
@app.get("/items/")
async def read_items(
    q: Annotated[str, Query(min_length=3, max_length=50)],
):
    .
```

## Key Rules

- Use `|` syntax for type unions in annotations (Python 3.10+).
- Use `Union` in `response_model=` and other non-annotation contexts.
- Use `Annotated` for dependency injection and query/path/body validation.
- `Optional[X]` is just `Union[X, None]` — prefer explicit `X | None`.