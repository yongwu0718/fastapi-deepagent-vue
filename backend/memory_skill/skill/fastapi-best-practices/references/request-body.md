# Request Body

Use Pydantic models to declare request bodies. FastAPI automatically validates, parses, and documents them.

## Basic Request Body

```python
from pydantic import BaseModel

class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.post("/items/")
async def create_item(item: ItemCreate) -> ItemCreate:
    return item
```

### Key Rules
- **Always use Pydantic `BaseModel`** for request bodies — never raw `dict`.
- Fields without defaults are **required**; fields with `None` default are **optional**.
- Use `Field()` for per-field validation and metadata:

```python
from pydantic import BaseModel, Field

class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Widget"])
    price: float = Field(gt=0, description="Price must be positive")
    tags: list[str] = Field(default_factory=list, max_length=10)
```

## Multiple Body Parameters

```python
@app.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item: ItemUpdate,
    user: User,
    importance: int = Body(gt=0),
):
    .
```

FastAPI distinguishes body parameters (Pydantic models + `Body()`) from path/query parameters by type.

## Nested Models

```python
class Image(BaseModel):
    url: str
    name: str

class ItemCreate(BaseModel):
    name: str
    image: Image | None = None        # Single nested model
    images: list[Image] = []           # List of nested models
    metadata: dict[str, str] = {}      # Dict with value type
```

## Partial Updates (PATCH)

```python
class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None

@app.patch("/items/{item_id}")
async def update_item(item_id: int, item: ItemUpdate):
    stored = get_item(item_id)
    update_data = item.model_dump(exclude_unset=True)  # Only sent fields
    updated = stored.model_copy(update=update_data)
    return updated
```

## Response Model

Control the output shape with `response_model`:

```python
class ItemOut(BaseModel):
    id: int
    name: str
    price: float

@app.post("/items/", response_model=ItemOut)
async def create_item(item: ItemCreate):
    # Even if internal object has extra fields,
    # only ItemOut fields are returned
    .
```

### Excluding fields from response

```python
class UserOut(BaseModel):
    username: str
    email: str
    hashed_password: str  # This is in the model.

@app.get("/users/me", response_model=UserOut)
async def read_user_me():
    .

# Better: separate output model without sensitive fields
class UserPublic(BaseModel):
    username: str
    email: str
```

## Separate Models by Responsibility

Always use different Pydantic models for different concerns:

| Model | Purpose | Example |
|-------|---------|---------|
| `ItemCreate` | Input: POST request body | No `id`, no `created_at` |
| `ItemUpdate` | Input: PATCH request body | All optional fields |
| `ItemOut` | Output: response body | No `hashed_password` |
| `ItemDB` | Database table model | `id`, `created_at`, all fields |