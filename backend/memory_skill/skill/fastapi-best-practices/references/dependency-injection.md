# Dependency Injection

FastAPI's dependency injection system is the primary mechanism for sharing logic, managing resources, and enforcing security across path operations.

## Basic Dependency

```python
from typing import Annotated
from fastapi import Depends

async def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: Annotated[dict, Depends(common_parameters)]):
    return commons
```

### Key Rules
- **Use `Annotated[Type, Depends(callable)]`** syntax — cleaner and IDE-friendly.
- Dependencies can themselves have dependencies (sub-dependencies).
- Dependencies execute in order; FastAPI caches results within the same request.
- A dependency can return any type — it's injected as the parameter value.

## Class-based Dependencies

```python
class CommonQueryParams:
    def __init__(self, q: str | None = None, skip: int = 0, limit: int = 100):
        self.q = q
        self.skip = skip
        self.limit = limit

@app.get("/items/")
async def read_items(commons: Annotated[CommonQueryParams, Depends(CommonQueryParams)]):
    .
```

## Sub-dependencies (Dependency Chains)

```python
def get_token_header(x_token: Annotated[str, Header()]):
    if x_token != "secret":
        raise HTTPException(status_code=400, detail="Invalid token")
    return x_token

def get_current_user(token: Annotated[str, Depends(get_token_header)]):
    user = decode_token(token)
    return user

@app.get("/users/me")
async def read_user_me(user: Annotated[User, Depends(get_current_user)]):
    return user
```

## Dependencies with Yield (Setup/Teardown)

Use `yield` for resources that need cleanup:

```python
async def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@app.get("/items/")
async def read_items(session: Annotated[Session, Depends(get_db_session)]):
    items = session.execute(select(Item)).scalars().all()
    return items
```

### Yield Dependency Rules
- Only **one** `yield` per dependency.
- Code before `yield` runs before the path operation (setup).
- Code after `yield` runs after the response (teardown/cleanup).
- Use `try/finally` to guarantee cleanup even on exceptions.

## Path Operation Decorator Dependencies

When you don't need the return value:

```python
@app.get("/items/", dependencies=[Depends(verify_token)])
async def read_items():
    .
```

## Global Dependencies

Applied to every path operation:

```python
app = FastAPI(dependencies=[Depends(verify_api_key)])
```

## Dependency Overrides (Testing)

```python
app.dependency_overrides[get_db_session] = get_test_db_session
```

Use `dependency_overrides` in tests to replace real dependencies with mocks/stubs.