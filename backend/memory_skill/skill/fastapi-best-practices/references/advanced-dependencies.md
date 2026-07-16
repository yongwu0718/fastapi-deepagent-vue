# Advanced Dependencies

Parameterized dependencies, callable class instances, and advanced dependency injection patterns.

## Parameterized Dependencies with Classes

Use callable class instances to create configurable dependencies:

```python
from typing import Annotated
from fastapi import Depends, FastAPI

app = FastAPI()

class FixedContentQueryChecker:
    def __init__(self, fixed_content: str):
        self.fixed_content = fixed_content

    def __call__(self, q: str = ""):
        if q:
            return self.fixed_content in q
        return False

checker = FixedContentQueryChecker("bar")

@app.get("/query-checker/")
async def read_query_check(
    fixed_content_included: Annotated[bool, Depends(checker)],
):
    return {"fixed_content_in_query": fixed_content_included}
```

## How It Works

- `__init__` receives your configuration parameters — FastAPI doesn't touch it.
- `__call__` is what FastAPI calls during request handling — it can have its own `Depends()` sub-dependencies.
- Create the instance once (at module level or in lifespan) and reuse it.

## Key Patterns

### Factory function for parameterized dependencies

For simpler cases, use a closure:

```python
def get_query_checker(fixed_content: str):
    def checker(q: str = ""):
        if q:
            return fixed_content in q
        return False
    return checker

@app.get("/query-checker/")
async def read_query_check(
    q_check: Annotated[bool, Depends(get_query_checker("bar"))],
):
    return {"fixed_content_in_query": q_check}
```

### Dependency with sub-dependencies in `__call__`

```python
class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if self.required_permission not in current_user.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

require_admin = PermissionChecker("admin")

@app.get("/admin/")
async def admin_panel(user: Annotated[User, Depends(require_admin)]):
    return {"message": f"Welcome, {user.username}"}
```

## Dependency Override for Testing

Override dependencies in tests (see [fastapi-testing](/fastapi-testing/SKILL.md) for full testing workflow):

```python
from fastapi.testclient import TestClient

async def override_get_current_user():
    return User(username="test_user", permissions=["admin"])

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)
response = client.get("/admin/")
assert response.status_code == 200
```

## Dependency Caching and Scope

FastAPI caches dependency results within a single request by default. Use `use_cache=False` to disable:

```python
def get_value():
    return random.random()

@app.get("/random/")
async def random_endpoint(
    v1: Annotated[float, Depends(get_value)],
    v2: Annotated[float, Depends(get_value, use_cache=False)],
):
    return {"v1": v1, "v2": v2}  # v1 == same value, v2 != v1
```

## Common Pitfalls

### Modifying shared mutable state

```python
# WRONG: Modifying a class-level list
class CounterDep:
    calls = []  # Shared across all requests!

    def __call__(self):
        self.calls.append(1)
        return len(self.calls)
```

```python
# CORRECT: Use request-scoped state or external storage
class CounterDep:
    def __call__(self):
        # Use a database or cache instead
        return increment_counter_in_db()
```