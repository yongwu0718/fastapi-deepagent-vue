---
title: Overriding Dependencies in Tests
impact: HIGH
impactDescription: The key pattern for test isolation in FastAPI — replacing real dependencies with test doubles via dependency_overrides
type: pattern
tags: [fastapi, testing, dependency-injection, overrides, mocking]
---

# Overriding Dependencies in Tests

**Pattern: Essential** - `app.dependency_overrides` is the primary mechanism for test isolation in FastAPI. It replaces real dependencies with test doubles without modifying production code.

## The Problem

Production code uses real dependencies (DB, external APIs, auth):

```python
# dependencies.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme)):
    return verify_token(token)  # Calls real auth service
```

Tests should not hit real databases or auth services.

## Solution: Dependency Overrides

```python
# test dependencies
def get_test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_test_user():
    return User(id=1, username="testuser", is_active=True)

# In test or fixture
app.dependency_overrides[get_db] = get_test_db
app.dependency_overrides[get_current_user] = get_test_user
```

## Complete Fixture Pattern

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from main import app
from dependencies import get_db, get_current_user

TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

def get_test_db():
    with Session(test_engine) as session:
        yield session

def get_test_user():
    return {"id": 1, "username": "testuser", "is_active": True}

@pytest.fixture(autouse=True)
def setup_test_db():
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = get_test_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

## Key Rules

| Rule | Why |
|------|-----|
| Always `clear()` overrides after tests | Prevents test pollution between test modules |
| Use `autouse` fixtures for DB setup/teardown | Ensures clean state for every test |
| Override at the highest level needed | Override `get_db` not individual route dependencies |
| Keep test doubles in test files | Never modify production code for testing |
| Use `yield` in fixtures for setup/teardown | Ensures cleanup runs even on test failure |

## Partial Overrides

You can override only specific dependencies while keeping others:

```python
# Override only the DB, keep real auth
app.dependency_overrides[get_db] = get_test_db
# get_current_user still uses real auth (if that's what you want)
```

## Overriding Dependencies with Parameters

```python
def get_test_user_with_role(role: str = "user"):
    def _get_test_user():
        return User(id=1, username="testuser", role=role)
    return _get_test_user

@pytest.fixture
def client_as_admin():
    app.dependency_overrides[get_current_user] = get_test_user_with_role("admin")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```