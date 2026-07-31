---
title: Dependency Cache Scope and Caching Issues
impact: MEDIUM
impactDescription: Dependencies may be cached unexpectedly across the same request, or re-executed when caching was expected, leading to performance issues or stale data
type: gotcha
tags: [fastapi, dependency-injection, caching, scope]
---

# Dependency Cache Scope and Caching Issues

**Impact: MEDIUM** - FastAPI caches dependency results within a single request by default. Understanding when and why dependencies are cached (or not) is critical for correct behavior.

## The Problem

```python
# This dependency is called ONCE per request (cached)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# If used in multiple places within the same request:
@app.get("/items/")
async def read_items(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # get_current_user also uses get_db internally
    # Both get the SAME db session instance (cached)
    .
```

**This is usually DESIRED** — same DB session throughout the request.

## When Caching Causes Problems

### Problem 1: Non-deterministic Dependency

```python
import random

def get_random_value():
    return random.random()  # Called only ONCE per request

@app.get("/test")
async def test(
    a: Annotated[float, Depends(get_random_value)],
    b: Annotated[float, Depends(get_random_value)],
):
    return {"a": a, "b": b}  # a == b always! (cached)
```

**Fix: Disable caching with `use_cache=False`**

```python
@app.get("/test")
async def test(
    a: Annotated[float, Depends(get_random_value, use_cache=False)],
    b: Annotated[float, Depends(get_random_value, use_cache=False)],
):
    return {"a": a, "b": b}  # Different values now
```

### Problem 2: Sub-dependency Returned from Parent Cache

```python
def get_db():
    return SessionLocal()

def get_user(db: Annotated[Session, Depends(get_db)]):
    return db.query(User).first()

def get_items(db: Annotated[Session, Depends(get_db)]):
    return db.query(Item).all()

# Both get_user and get_items share the same db session (cached sub-dependency)
# This is CORRECT behavior for DB sessions
```

## Cache Scope Rules

- **Default**: One dependency instance per request (within the same `Depends()` chain).
- **`use_cache=False`**: Forces re-execution every time it's used in the request.
- **Sub-dependencies**: Cached at the level they're declared, shared by all parents in the request.
- **Yield dependencies**: The cached object is yielded once; cleanup runs once when response is done.

## Best Practices

1. Keep `use_cache=True` (default) for DB sessions, config objects — resources that should be shared.
2. Use `use_cache=False` for non-deterministic values or when you explicitly need re-execution.
3. Never mutate cached dependency state in a way that affects other consumers in the same request.