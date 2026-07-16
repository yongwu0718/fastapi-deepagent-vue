---
name: fastapi-testing
description: FastAPI testing patterns with TestClient, pytest, async tests, dependency overrides, and WebSocket testing. Use when writing tests for FastAPI applications.
license: MIT
metadata:
  author: github.com/fastapi-ai
  version: "1.0.0"
---

FastAPI testing best practices, patterns, and common gotchas.

### Testing Setup
- Setting up TestClient for FastAPI → See [testclient-setup](reference/testclient-setup.md)
- Organizing tests with pytest fixtures → See [pytest-fixtures](reference/pytest-fixtures.md)
- Testing with an actual database (test database) → See [test-database-setup](reference/test-database-setup.md)

### Dependency Overrides
- Overriding dependencies in tests → See [dependency-overrides](reference/dependency-overrides.md)
- Overriding the database session dependency → See [override-db-session](reference/override-db-session.md)
- Overriding auth/security dependencies → See [override-auth-dependency](reference/override-auth-dependency.md)

### Async Testing
- Testing async path operations → See [async-test-functions](reference/async-test-functions.md)
- Testing WebSocket endpoints → See [websocket-testing](reference/websocket-testing.md)
- Testing lifespan and startup/shutdown events → See [lifespan-testing](reference/lifespan-testing.md)

### Common Patterns
- Testing error responses (4XX, 5XX) → See [testing-error-responses](reference/testing-error-responses.md)
- Testing file uploads → See [testing-file-uploads](reference/testing-file-uploads.md)
- Testing background tasks → See [testing-background-tasks](reference/testing-background-tasks.md)
- Testing streaming responses → See [testing-streaming](reference/testing-streaming.md)

### Common Pitfalls
- TestClient returns 422 when data looks correct → See [testclient-422-debugging](reference/testclient-422-debugging.md)
- Test database not cleaned between tests → See [test-isolation](reference/test-isolation.md)
- Async test functions with pytest-asyncio issues → See [pytest-asyncio-setup](reference/pytest-asyncio-setup.md)
- Lifespan events not executing in tests → See [testclient-lifespan](reference/testclient-lifespan.md)