---
title: TestClient Setup and Basic Usage
impact: MEDIUM
impactDescription: The standard approach for testing FastAPI applications with TestClient and pytest
type: pattern
tags: [fastapi, testing, testclient, pytest]
---

# TestClient Setup and Basic Usage

**Pattern: Standard** - Use `TestClient` from `fastapi.testclient` (built on Starlette/HTTPX) for synchronous API testing.

## Installation

```bash
pip install httpx pytest
```

## Basic Setup

```python
# test_main.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_read_item():
    response = client.get("/items/42?q=test")
    assert response.status_code == 200
    assert response.json() == {"item_id": 42, "q": "test"}

def test_read_item_not_found():
    response = client.get("/items/abc")
    assert response.status_code == 422  # Validation error
```

## Key Rules

- Test functions are `def`, not `async def` — TestClient is synchronous.
- `client.get/post/put/delete()` methods return a response object.
- `response.json()` parses JSON body; `response.text` for raw text.
- `response.status_code` for HTTP status; `response.headers` for headers.

## pytest Fixtures Pattern

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

# test_api.py
def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
```

## Testing with Dependency Overrides

```python
# conftest.py
from dependencies import get_db, get_test_db

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = get_test_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

## Testing POST/PUT/PATCH with JSON

```python
def test_create_item(client: TestClient):
    response = client.post(
        "/items/",
        json={"name": "Widget", "price": 9.99},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Widget"
    assert data["price"] == 9.99
    assert "id" in data
```

## Testing with Headers

```python
def test_authenticated_request(client: TestClient):
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
```

## Reference

- [FastAPI Testing Docs](https://fastapi.tiangolo.com/tutorial/testing/)
- [Starlette TestClient](https://www.starlette.io/testclient/)
- [pytest Documentation](https://docs.pytest.org/)