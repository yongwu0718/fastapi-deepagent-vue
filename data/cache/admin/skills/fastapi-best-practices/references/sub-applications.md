# Sub-Applications & WSGI Mounting

Mount independent FastAPI or WSGI (Flask, Django) applications at sub-paths under a main app.

## Mounting a FastAPI Sub-Application

Each sub-app has its own OpenAPI docs and routes:

### Main App

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/app")
def read_main():
    return {"message": "Hello World from main app"}
```

### Sub App

```python
from fastapi import FastAPI

subapi = FastAPI()

@subapi.get("/sub")
def read_sub():
    return {"message": "Hello World from sub API"}
```

### Mount

```python
app.mount("/subapi", subapi)
```

Now:
- Main docs: `http://127.0.0.1:8000/docs`
- Sub-app docs: `http://127.0.0.1:8000/subapi/docs`
- Main route: `GET /app`
- Sub-app route: `GET /subapi/sub`

## Mounting WSGI Apps (Flask, Django)

Use `a2wsgi` to wrap WSGI applications:

```bash
pip install a2wsgi
```

```python
from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from flask import Flask, request
from markupsafe import escape

flask_app = Flask(__name__)

@flask_app.route("/")
def flask_main():
    name = request.args.get("name", "World")
    return f"Hello, {escape(name)} from Flask!"

app = FastAPI()

@app.get("/v2")
def read_main():
    return {"message": "Hello World"}

app.mount("/v1", WSGIMiddleware(flask_app))
```

- `GET /v1/` → handled by Flask
- `GET /v2` → handled by FastAPI

## Key Rules

- Sub-apps are completely independent — they have their own OpenAPI schemas, docs, and middleware.
- `root_path` is automatically managed by FastAPI for sub-apps.
- For WSGI, install `a2wsgi`. The old `fastapi.middleware.wsgi.WSGIMiddleware` is deprecated.
- Sub-apps can have their own sub-apps — nesting works recursively.

## Common Pitfalls

### Sub-app routes not showing in main docs

This is by design. Each sub-app has its **own** docs at its sub-path (e.g., `/subapi/docs`).

### WSGI middleware alternatives

If you need to migrate from Flask/Django piece by piece, mount the WSGI app and gradually replace routes with FastAPI endpoints.

### Static files with sub-apps

Each sub-app can mount its own static files independently:

```python
from fastapi.staticfiles import StaticFiles

subapi.mount("/static", StaticFiles(directory="subapi_static"), name="subapi_static")
```