---
title: Route Order Priority — Fixed Path vs Parameterized Path
impact: HIGH
impactDescription: Wrong route order causes parameterized routes to capture requests intended for fixed routes, leading to 422 validation errors or wrong handler execution
type: gotcha
tags: [fastapi, routing, path-parameters, route-order]
---

# Route Order Priority — Fixed Path vs Parameterized Path

**Impact: HIGH** - FastAPI matches routes in declaration order. A parameterized route declared before a fixed route will capture requests meant for the fixed route.

## The Problem

```python
# WRONG: Parameterized route first
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}

@app.get("/users/me")
async def get_current_user():
    return {"username": "alice"}

# Request to /users/me → matches /users/{user_id} with user_id="me"
# Fails with 422: "Input should be a valid integer"
```

## Solution

**Always declare fixed routes BEFORE parameterized routes:**

```python
# CORRECT: Fixed routes first
@app.get("/users/me")
async def get_current_user():
    return {"username": "alice"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
```

## Same Issue with APIRouter

```python
# users.py router
router = APIRouter()

@router.get("/me")          # Fixed path FIRST
async def get_me(): .

@router.get("/{user_id}")   # Parameterized path AFTER
async def get_user(user_id: int): .
```

## General Rule

Order routes within each router/prefix from **most specific to least specific**:

```python
# Priority order (top to bottom):
@app.get("/items/latest")         # 1. Most specific fixed path
@app.get("/items/featured")       # 2. Another fixed path
@app.get("/items/{item_id}")      # 3. Single parameter
@app.get("/items/{item_id}/tags") # 4. Parameter + fixed suffix
```

## Diagnostics

If you see unexpected 422 validation errors on what should be a valid fixed route, check:
1. Are all fixed routes declared before parameterized routes?
2. Are paths with overlapping patterns ordered correctly?
3. Check the OpenAPI docs at `/docs` — routes are listed in declaration order.