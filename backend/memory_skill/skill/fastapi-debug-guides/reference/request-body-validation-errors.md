---
title: Pydantic Request Body Validation Errors (422)
impact: HIGH
impactDescription: FastAPI returns 422 Unprocessable Entity when Pydantic validation fails. Understanding the error structure is key to debugging client issues quickly
type: gotcha
tags: [fastapi, pydantic, validation, 422, request-body]
---

# Pydantic Request Body Validation Errors (422)

**Impact: HIGH** - When a client sends invalid data, FastAPI automatically returns 422 with detailed validation errors. Understanding the error format helps with debugging.

## The Problem

```python
from pydantic import BaseModel, Field

class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    quantity: int = Field(ge=1)

@app.post("/items/")
async def create_item(item: ItemCreate):
    return item
```

Client sends:
```json
{"name": "", "price": -5, "quantity": 0}
```

Response (422):
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character",
      "input": ""
    },
    {
      "type": "greater_than",
      "loc": ["body", "price"],
      "msg": "Input should be greater than 0",
      "input": -5
    },
    {
      "type": "greater_than_equal",
      "loc": ["body", "quantity"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0
    }
  ]
}
```

## Common Validation Error Types

| Error Type | Cause |
|------------|-------|
| `missing` | Required field not sent |
| `string_type` | Expected string, got number/bool |
| `int_type` / `float_type` | Expected number, got string |
| `string_too_short` / `string_too_long` | `min_length` / `max_length` violation |
| `greater_than` / `less_than` | `gt` / `lt` violation |
| `greater_than_equal` | `ge` violation |
| `value_error` | Custom validator error |
| `json_invalid` | Request body is not valid JSON |

## Debugging Tips

### 1. Check `loc` for the exact field path

```json
{"loc": ["body", "items", 0, "name"]}
// Means: request body → items array → index 0 → name field
```

### 2. Use `model_dump()` to see what Pydantic receives

```python
@app.post("/items/")
async def create_item(item: ItemCreate):
    print(item.model_dump())  # Only prints if validation passes
    return item
```

### 3. Test with TestClient to see raw errors

```python
def test_invalid_item(client):
    response = client.post("/items/", json={"name": ""})
    assert response.status_code == 422
    print(response.json())  # See full error details
```

## Customizing Validation Errors

```python
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def custom_validation_handler(request, exc):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
        })
    return JSONResponse(status_code=422, content={"errors": errors})
```