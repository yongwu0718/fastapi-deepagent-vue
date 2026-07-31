---
name: fastapi-security
description: FastAPI security patterns, OAuth2 authentication, JWT tokens, password hashing, and permission control. Use when implementing auth, login, or access control in FastAPI applications.
license: MIT
metadata:
  author: github.com/fastapi-ai
  version: "1.0.0"
---

FastAPI security best practices, authentication patterns, and common gotchas.

### Authentication Basics
- Quickstart: basic OAuth2 Password + Bearer token → See [oauth2-password-bearer](reference/oauth2-password-bearer.md)
- Get current user from token → See [get-current-user](reference/get-current-user.md)
- Full JWT + password hashing implementation → See [jwt-password-hashing](reference/jwt-password-hashing.md)
- HTTP Basic Authentication → See [http-basic-auth](reference/http-basic-auth.md)

### JWT Token Management
- Token expiration and refresh strategy → See [jwt-expiration-refresh](reference/jwt-expiration-refresh.md)
- Token stored insecurely (localStorage vs httpOnly cookie) → See [token-storage-security](reference/token-storage-security.md)
- Token blacklisting on logout → See [token-blacklist-logout](reference/token-blacklist-logout.md)

### OAuth2 Scopes
- Fine-grained permission control with scopes → See [oauth2-scopes](reference/oauth2-scopes.md)
- Scope-based dependency for route protection → See [scope-dependency-pattern](reference/scope-dependency-pattern.md)

### Password Handling
- Password hashing with bcrypt via passlib → See [password-hashing](reference/password-hashing.md)
- Password validation rules and strength checks → See [password-validation](reference/password-validation.md)

### Common Pitfalls
- `WWW-Authenticate` header missing on 401 → See [www-authenticate-header](reference/www-authenticate-header.md)
- Security dependency vs path operation dependency order → See [security-dependency-ordering](reference/security-dependency-ordering.md)
- Over-fetching user data in auth dependency (DB query per request) → See [auth-dependency-caching](reference/auth-dependency-caching.md)
- Exposing hashed_password or sensitive fields in responses → See [sensitive-field-exposure](reference/sensitive-field-exposure.md)

### Advanced
- API Key authentication (query/header based) → See [api-key-auth](reference/api-key-auth.md)
- Multi-tenancy with domain-based auth → See [multi-tenant-auth](reference/multi-tenant-auth.md)
- Rate limiting tied to authentication → See [rate-limiting-auth](reference/rate-limiting-auth.md)