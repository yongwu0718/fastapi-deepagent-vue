---
name: fastapi-best-practices
description: MUST be used for FastAPI tasks. Covers path operations, request/response models, dependency injection, error handling, middleware, application architecture, custom responses, OpenAPI, sub-applications, proxy configuration, and advanced patterns. Load for any FastAPI, Python API, or backend service work.
---

# FastAPI Best Practices Workflow

Use this skill as an instruction set. Follow the workflow in order unless the user explicitly asks for a different order.

## Core Principles
- **Explicit over implicit:** type hints drive validation, serialization, and documentation.
- **Pydantic models as the single source of truth:** define request/response shapes once, reuse everywhere.
- **Dependency injection for shared logic:** keep path operations thin, extract reusable logic into dependencies.
- **Fail fast with HTTPException:** validate early, return clear error responses.
- **Async by default, sync when needed:** use `async def` for I/O-bound path operations, `def` for CPU-bound or non-async libraries.

## 1) Confirm architecture before coding (required)

- Default stack: FastAPI + Pydantic v2 + async path operations.
- Use `APIRouter` for modular application structure.
- Use `lifespan` context manager for startup/shutdown resource management.

### 1.1 Must-read core references (required)

- Before implementing any FastAPI task, read and apply these core references:
  - `references/path-operations.md`
  - `references/request-body.md`
  - `references/dependency-injection.md`
  - `references/error-handling.md`
- Keep these references in active working context for the entire task.

### 1.2 Plan route structure before coding (required)

Create a brief route map before implementation for any non-trivial feature.

- Define each route's path, method, request model, and response model.
- Group related routes into `APIRouter` modules by domain (users, items, orders, etc.).
- Define dependency chains: what each route needs injected (DB session, current user, etc.).
- Keep root `main.py` thin: app creation, lifespan, router inclusion, middleware wiring.

## 2) Apply essential FastAPI foundations (required)

### Path Operations

- Must-read reference: [path-operations](references/path-operations.md)
- Declare path parameters with Python format string syntax: `/items/{item_id}`.
- Always type-annotate path parameters for automatic parsing and validation.
- Use `Path()` for additional validation constraints (gt, lt, regex, etc.).
- Configure tags, summary, and description via `@app.get(., tags=["items"])`.

### Request Body

- Must-read reference: [request-body](references/request-body.md)
- Use Pydantic `BaseModel` subclasses for all request bodies.
- Use `Field()` for per-field validation and metadata (`min_length`, `gt`, `examples`).
- Keep input models separate from output models and database models.
- Use `response_model` to control output shape and filter sensitive fields.
- For partial updates, use `Optional` fields with `exclude_unset`.

### Query Parameters

- Non-path function parameters automatically become query parameters.
- Use default values for optional parameters; `None` makes a parameter optional.
- Use `Query()` for string validation, aliases, and deprecation.
- Consider `QueryModel` (Pydantic model with `Query()` fields) for complex query parameter sets.

### Dependency Injection

- Must-read reference: [dependency-injection](references/dependency-injection.md)
- Use `Depends()` for reusable logic: auth checks, DB sessions, permission validation.
- Prefer `Annotated[Type, Depends(callable)]` syntax over bare `Depends()`.
- Use `yield` in dependencies for setup/teardown (DB sessions, file handles).
- Keep dependencies focused: one responsibility per dependency function.
- Chain dependencies with sub-dependencies when needed.

### Error Handling

- Must-read reference: [error-handling](references/error-handling.md)
- Use `HTTPException(status_code=., detail=.)` for client errors.
- Use appropriate status codes: 400 for bad input, 401 for unauthorized, 403 for forbidden, 404 for not found, 422 for validation errors.
- Register custom exception handlers for domain-specific exceptions.
- Add `headers` to `HTTPException` when needed (e.g., `WWW-Authenticate` for 401).

### Modeling & Documentation

- **Multiple models** — separate input, output, and DB models to avoid exposing sensitive fields → [multiple-models](references/multiple-models.md)
- **Extra data types** — use `UUID`, `datetime`, `Decimal`, `frozenset`, `bytes` with automatic validation → [extra-data-types](references/extra-data-types.md)
- **Request examples** — declare examples in models, `Field()`, `Body()`, `Query()` for auto-generated docs → [request-examples](references/request-examples.md)
- **JSON compatible encoder** — use `jsonable_encoder` for DB storage or custom `Response` objects → [json-encoder](references/json-encoder.md)
- **Metadata & docs URLs** — customize API title, description, version, contact, license, and docs paths → [metadata-docs](references/metadata-docs.md)

## 3) Consider optional features only when requirements call for them

### 3.1 Standard optional features

Do not add these by default. Load the matching reference only when the requirement exists.

- Form data: receiving `application/x-www-form-urlencoded` → [form-data](references/form-data.md)
- File uploads: receiving `UploadFile` or `bytes` → [file-uploads](references/file-uploads.md)
- Header/Cookie parameters: reading custom headers or cookies → [header-cookie-params](references/header-cookie-params.md)
- Background tasks: post-response processing (email, cleanup) → [background-tasks](references/background-tasks.md)
- Middleware: cross-cutting request/response processing → [middleware](references/middleware.md)
- CORS: frontend cross-origin access → [cors](references/cors.md)
- Static files: serving CSS, JS, images → [static-files](references/static-files.md)

### 3.2 Advanced optional features

Use only when there is explicit product or technical need.

- WebSockets: bidirectional persistent communication → [websockets](references/websockets.md)
- Server-Sent Events: server-to-client streaming → [sse](references/sse.md)
- Streaming responses: large file downloads, real-time data → [streaming](references/streaming.md)
- Templates: server-side HTML rendering with Jinja2 → [templates](references/templates.md)
- Sub-applications: mounting independent FastAPI/WSGI apps → [sub-applications](references/sub-applications.md)
- OpenAPI webhooks/callbacks/SDK generation: event-driven patterns and client generation → [openapi-advanced](references/openapi-advanced.md)
- Settings management: environment variables, config files → [settings](references/settings.md)

### 3.3 Response customization

Load when the endpoint needs non-JSON responses, dynamic status codes, cookies, or custom headers.

- Custom responses: HTML, streaming, files, cookies, response headers, dynamic status codes → [custom-responses](references/custom-responses.md)

### 3.4 Advanced patterns

Load when requirements exceed basic patterns covered in section 2.

- Advanced dependencies: parameterized dependencies, callable class instances, caching control → [advanced-dependencies](references/advanced-dependencies.md)
- Advanced middleware: ASGI middleware, HTTPS redirect, trusted host, strict Content-Type → [advanced-middleware](references/advanced-middleware.md)
- Behind a proxy: configure Nginx/Traefik forwarded headers, `root_path`, HTTPS redirects → [behind-proxy](references/behind-proxy.md)
- Advanced path operations: custom `operationId`, exclude from schema, OpenAPI extensions → [advanced-path-operations](references/advanced-path-operations.md)
- Advanced Python types: `Union` vs `Optional` vs `|`, `Annotated`, generics → [advanced-python-types](references/advanced-python-types.md)
- Using dataclasses: standard library `@dataclass` as alternative to Pydantic models → [dataclasses](references/dataclasses.md)
- Using Request directly: access raw Starlette `Request` for edge cases → [direct-request](references/direct-request.md)
- Base64 bytes: handling `bytes` in JSON via Base64 encoding → [base64-bytes](references/base64-bytes.md)

## 4) Database integration

When the application needs persistence:

- Use **SQLModel** (recommended) or **SQLAlchemy** for relational databases.
- Define table models separately from API models (input/output).
- Use `yield`-based dependencies for session lifecycle management.
- Always close/rollback sessions in `finally` blocks within yield dependencies.
- Use `select()` with `where()` for queries; avoid raw SQL unless necessary.
- See [database](references/database.md) for detailed patterns.

## 5) Security integration

When the application needs authentication/authorization:

- Use `fastapi.security` modules for standard auth schemes.
- Start with OAuth2 Password Bearer flow for simple username/password auth.
- Use JWT tokens with expiration for stateless authentication.
- Hash passwords with `passlib` (bcrypt).
- Implement scoped permissions with dependency chains.
- See [fastapi-security](/fastapi-security/SKILL.md) skill for full security workflow.

## 6) Final self-check before finishing

- Core behavior works and matches requirements.
- All must-read references were read and applied.
- Path operations are properly typed with response models.
- Dependency injection is used for shared logic, not code duplication.
- Error handling covers 4XX and 5XX scenarios.
- Route structure is modular with `APIRouter`.
- Database sessions are properly managed with yield dependencies.
- API documentation is auto-generated and accurate at `/docs`.