---
name: fastapi-debug-guides
description: FastAPI debugging and error handling for runtime errors, validation failures, async issues, and dependency injection problems. Use when diagnosing or fixing FastAPI issues.
license: MIT
metadata:
  author: github.com/fastapi-ai
  version: "1.0.0"
---

FastAPI debugging and error handling for runtime issues, validation failures, async pitfalls, and dependency problems.
For development best practices, use `fastapi-best-practices`.

### Path Operations
- Path parameter validation fails with 422 → See [path-param-type-validation](reference/path-param-type-validation.md)
- Route order causing wrong handler to match → See [route-order-priority](reference/route-order-priority.md)
- Enum path parameter not accepting valid values → See [enum-path-param-case-sensitivity](reference/enum-path-param-case-sensitivity.md)

### Query Parameters
- Query parameter not being parsed correctly → See [query-param-type-coercion](reference/query-param-type-coercion.md)
- Multiple query params with same name → See [query-param-list-values](reference/query-param-list-values.md)
- Optional query param defaulting wrong → See [query-param-none-vs-ellipsis](reference/query-param-none-vs-ellipsis.md)

### Request Body
- Pydantic validation error with 422 → See [request-body-validation-errors](reference/request-body-validation-errors.md)
- Request body is null/empty when expected → See [request-body-missing-content-type](reference/request-body-missing-content-type.md)
- Nested model fields not being validated → See [nested-model-validation](reference/nested-model-validation.md)
- Extra fields silently ignored or rejected → See [extra-fields-configuration](reference/extra-fields-configuration.md)

### Dependency Injection
- Dependency not being called / cached incorrectly → See [dependency-cache-scope](reference/dependency-cache-scope.md)
- Circular dependency causing infinite recursion → See [circular-dependency-detection](reference/circular-dependency-detection.md)
- Yield dependency cleanup not executing → See [yield-dependency-cleanup-failure](reference/yield-dependency-cleanup-failure.md)
- Dependency override not working in tests → See [dependency-override-not-applied](reference/dependency-override-not-applied.md)

### Async / Await
- Path operation hanging or timing out → See [async-blocking-call](reference/async-blocking-call.md)
- `async def` with synchronous DB library → See [async-with-sync-libraries](reference/async-with-sync-libraries.md)
- Background task never executes → See [background-task-missing-await](reference/background-task-missing-await.md)

### Response & Serialization
- Response model excludes fields unexpectedly → See [response-model-field-filtering](reference/response-model-field-filtering.md)
- datetime/serialized incorrectly in response → See [datetime-serialization-format](reference/datetime-serialization-format.md)
- Custom JSON encoder not being used → See [custom-json-encoder-setup](reference/custom-json-encoder-setup.md)

### Middleware & CORS
- CORS errors from frontend requests → See [cors-misconfiguration](reference/cors-misconfiguration.md)
- Middleware order causing unexpected behavior → See [middleware-execution-order](reference/middleware-execution-order.md)
- Request body consumed before path operation → See [middleware-consuming-body](reference/middleware-consuming-body.md)

### Database
- Session not closed / connection leak → See [db-session-leak](reference/db-session-leak.md)
- Object accessed after session closed (lazy load) → See [detached-instance-error](reference/detached-instance-error.md)
- SQLModel relationship not loading → See [sqlmodel-relationship-lazy](reference/sqlmodel-relationship-lazy.md)

### Application Architecture
- APIRouter routes not showing in docs → See [apirouter-not-registered](reference/apirouter-not-registered.md)
- Lifespan events not executing → See [lifespan-not-called](reference/lifespan-not-called.md)
- Import errors with circular module dependencies → See [circular-import-fastapi](reference/circular-import-fastapi.md)

### WebSocket
- WebSocket connection rejected → See [websocket-not-accepted](reference/websocket-not-accepted.md)
- WebSocket disconnects silently → See [websocket-disconnect-handling](reference/websocket-disconnect-handling.md)
- Mixed HTTP and WebSocket on same route → See [websocket-http-route-conflict](reference/websocket-http-route-conflict.md)

### Testing
- TestClient returns 422 on valid data → See [testclient-validation-differences](reference/testclient-validation-differences.md)
- Lifespan not running in tests → See [testclient-lifespan-setup](reference/testclient-lifespan-setup.md)
- Async test functions failing → See [async-test-anyio-backend](reference/async-test-anyio-backend.md)