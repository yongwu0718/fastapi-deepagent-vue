---
title: CORS Misconfiguration — Frontend Requests Blocked
impact: HIGH
impactDescription: Missing or incorrect CORS configuration causes browser to block frontend API requests, with no visible error in backend logs
type: gotcha
tags: [fastapi, cors, middleware, frontend, browser]
---

# CORS Misconfiguration — Frontend Requests Blocked

**Impact: HIGH** - The most common issue when connecting a frontend to a FastAPI backend. Browsers block cross-origin requests by default.

## The Problem

Browser console shows:
```
Access to fetch at 'http://localhost:8000/api/items' from origin 'http://localhost:3000'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
on the requested resource.
```

The backend receives no request (preflight OPTIONS fails). No error in FastAPI logs.

## Solution

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Key Rules

| Setting | Recommendation |
|---------|---------------|
| `allow_origins` | List specific origins, never `["*"]` in production |
| `allow_credentials` | `True` if using cookies/auth headers |
| `allow_methods` | `["*"]` or list specific methods |
| `allow_headers` | `["*"]` or list specific headers |

## Common Pitfalls

### 1. `allow_origins=["*"]` with `allow_credentials=True`

```python
# WRONG: This combination is forbidden by the CORS spec
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Wildcard
    allow_credentials=True,   # Can't use together!
)
```

**Fix:** List specific origins when using credentials.

### 2. Port mismatch

```python
# Frontend runs on port 3000
# Backend runs on port 8000

# Must include the exact origin:
allow_origins=["http://localhost:3000"]  # CORRECT
allow_origins=["http://localhost"]       # WRONG (missing port)
```

### 3. CORS middleware must be first

```python
# CORRECT: CORS middleware first
app.add_middleware(CORSMiddleware, .)
app.add_middleware(SomeOtherMiddleware, .)

# WRONG: Other middleware might reject preflight OPTIONS
app.add_middleware(SomeOtherMiddleware, .)  # This processes OPTIONS first
app.add_middleware(CORSMiddleware, .)
```

### 4. Custom headers not exposed

If you add custom response headers, browsers won't see them unless you add `expose_headers`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    expose_headers=["X-Process-Time", "X-Total-Count"],
)
```

## Testing CORS

```bash
# Simulate preflight request
curl -X OPTIONS http://localhost:8000/api/items \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v
```