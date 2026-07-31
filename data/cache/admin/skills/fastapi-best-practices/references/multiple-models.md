# Multiple Models (Input / Output / DB)

Separate Pydantic models for input, output, and database to avoid exposing sensitive fields and to keep concerns clean.

## Why Multiple Models

- **Input model** (`UserIn`) — includes `password` in plain text for creation.
- **Output model** (`UserOut`) — excludes `password` entirely.
- **Database model** (`UserInDB`) — stores `hashed_password` instead of plain text.

## Example

```python
from fastapi import FastAPI
from pydantic import BaseModel, EmailStr

app = FastAPI()

class UserIn(BaseModel):
    username: str
    password: str
    email: EmailStr
    full_name: str | None = None

class UserOut(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None

class UserInDB(BaseModel):
    username: str
    hashed_password: str
    email: EmailStr
    full_name: str | None = None

def fake_password_hasher(raw_password: str) -> str:
    return "hashed_" + raw_password

def fake_save_user(user_in: UserIn) -> UserInDB:
    hashed_password = fake_password_hasher(user_in.password)
    user_in_db = UserInDB(**user_in.model_dump(), hashed_password=hashed_password)
    return user_in_db

@app.post("/users/", response_model=UserOut)
async def create_user(user_in: UserIn):
    user_saved = fake_save_user(user_in)
    return user_saved
```

## Key Patterns

### `model_dump()` + unpacking for model conversion

```python
# user_in is a UserIn instance
user_dict = user_in.model_dump()
# {'username': 'john', 'password': 'secret', 'email': '.', 'full_name': None}

# Convert to DB model, replacing password with hashed_password
user_in_db = UserInDB(**user_dict, hashed_password=hashed_password)
```

### `response_model` filters output

The `response_model=UserOut` parameter ensures only `username`, `email`, and `full_name` are returned — `hashed_password` and `password` are never exposed.

## Recommended Model Layers

| Model | Purpose | Contains |
|---|---|---|
| `XxxIn` / `XxxCreate` | Request body for creation | All required fields, including secrets |
| `XxxOut` / `XxxResponse` | Response body | Public fields only |
| `XxxUpdate` | Partial update (PATCH) | All optional fields |
| `XxxInDB` | Database representation | DB-specific fields (hashed password, timestamps) |

## Common Pitfalls

### Reusing the same model for input and output

```python
# WRONG: password leaks in response
@app.post("/users/", response_model=UserIn)
async def create_user(user: UserIn):
    return user  # Returns the password!
```

### Not using `response_model` at all

```python
# WRONG: returns all fields including internal DB state
@app.post("/users/")
async def create_user(user_in: UserIn):
    user_db = save_to_db(user_in)
    return user_db  # Returns hashed_password, internal IDs, etc.
```