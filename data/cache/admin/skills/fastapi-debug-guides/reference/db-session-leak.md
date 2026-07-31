---
title: Database Session Leak / Connection Not Closed
impact: HIGH
impactDescription: Database sessions not properly closed after requests cause connection pool exhaustion, leading to application hangs under load
type: gotcha
tags: [fastapi, database, sqlmodel, sqlalchemy, session, connection-pool]
---

# Database Session Leak / Connection Not Closed

**Impact: HIGH** - Failing to close database sessions is the most common cause of connection pool exhaustion. Under load, the application eventually runs out of connections and hangs.

## The Problem

```python
# WRONG: Session never closed — connection leaks
def get_session():
    session = SessionLocal()
    return session  # No yield, no finally — session never closes

# WRONG: Session returned but not closed if exception occurs
def get_session():
    session = SessionLocal()
    yield session
    session.close()  # Won't run if exception occurs in path operation
```

## Solution: Always Use try/finally with yield

```python
# CORRECT: Session always closed, even on exceptions
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# CORRECT: Using context manager (SQLModel preferred)
def get_session():
    with Session(engine) as session:
        yield session
```

## Detection

### Symptom: Application hangs after N requests

```python
# Default SQLAlchemy pool size is 5 (for SQLite) or 10
# After 10 concurrent requests without session close,
# the 11th request hangs waiting for a connection
```

### Check with logging

```python
import logging
logging.basicConfig()
logging.getLogger("sqlalchemy.pool").setLevel(logging.DEBUG)
```

Watch for "Checked out" without corresponding "Checked in" messages.

## Connection Pool Configuration

```python
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Max connections in pool
    max_overflow=10,     # Extra connections beyond pool_size
    pool_timeout=30,     # Seconds to wait before timeout
    pool_recycle=3600,   # Recycle connections after 1 hour
    pool_pre_ping=True,  # Verify connection before using
)
```

## Key Rules

| Rule | Why |
|------|-----|
| Always use `yield` with `finally` or context manager | Guarantees session cleanup |
| One session per request | Use dependency caching (default) |
| Never share sessions across requests | Sessions are not thread-safe |
| Set `pool_pre_ping=True` | Handles disconnected connections gracefully |
| Monitor pool usage in production | Detect leaks before they cause outages |