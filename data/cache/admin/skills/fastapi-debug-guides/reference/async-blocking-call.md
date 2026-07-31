---
title: Async Path Operation Hangs with Synchronous Blocking Calls
impact: HIGH
impactDescription: Using synchronous blocking calls inside async def path operations blocks the entire event loop, causing all concurrent requests to hang
type: gotcha
tags: [fastapi, async, sync, blocking, event-loop]
---

# Async Path Operation Hangs with Synchronous Blocking Calls

**Impact: HIGH** - A synchronous blocking call inside an `async def` path operation blocks the entire asyncio event loop. All other concurrent requests will hang until the blocking call completes.

## The Problem

```python
# WRONG: time.sleep() blocks the event loop
@app.get("/slow")
async def slow_endpoint():
    time.sleep(10)  # Blocks ALL requests, not just this one
    return {"message": "done"}

# WRONG: Synchronous HTTP call inside async def
import requests

@app.get("/proxy")
async def proxy():
    resp = requests.get("https://slow-api.example.com")  # Blocks event loop
    return resp.json()
```

## Solution 1: Use `def` Instead of `async def` for Blocking Operations

FastAPI runs `def` path operations in a threadpool, so they won't block the event loop:

```python
# CORRECT: def runs in threadpool
@app.get("/slow")
def slow_endpoint():
    time.sleep(10)  # Runs in separate thread, doesn't block event loop
    return {"message": "done"}

@app.get("/proxy")
def proxy():
    resp = requests.get("https://slow-api.example.com")  # Safe in threadpool
    return resp.json()
```

## Solution 2: Use `run_in_threadpool` for Specific Calls

```python
from fastapi.concurrency import run_in_threadpool

@app.get("/mixed")
async def mixed_endpoint():
    # Do async things.
    data = await fetch_from_cache()  # This is async, fine
    
    # Offload blocking call to threadpool
    result = await run_in_threadpool(requests.get, "https://slow-api.example.com")
    
    return result.json()
```

## Solution 3: Use Async Libraries

```python
import httpx

@app.get("/proxy")
async def proxy():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://slow-api.example.com")
    return resp.json()
```

## Key Rules

| Situation | Use |
|-----------|-----|
| Async I/O library (httpx, asyncpg, aiofiles) | `async def` |
| Sync I/O library (requests, psycopg2, open) | `def` (threadpool) |
| CPU-bound computation | `def` (threadpool) or `run_in_threadpool` |
| Third-party lib requiring `await` | `async def` |