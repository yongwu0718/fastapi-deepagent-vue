# Metadata and Docs URLs

Customize your API's title, description, version, contact info, license, and documentation URLs.

## Basic Metadata

```python
from fastapi import FastAPI

description = """
My API helps you do awesome stuff.

## Items

You can **read items**.

## Users

* **Create users**
* **Read users**
"""

app = FastAPI(
    title="My API",
    description=description,
    summary="A short summary of the API.",
    version="0.0.1",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "API Support",
        "url": "http://example.com/contact/",
        "email": "support@example.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)
```

## Available Metadata Fields

| Parameter | Type | Description |
|---|---|---|
| `title` | `str` | API title shown in docs |
| `summary` | `str` | Short summary (OpenAPI 3.1.0+, FastAPI >= 0.99.0) |
| `description` | `str` | Long description, supports Markdown |
| `version` | `str` | Your application version (not OpenAPI version) |
| `terms_of_service` | `str` | URL to terms of service |
| `contact` | `dict` | `name`, `url`, `email` |
| `license_info` | `dict` | `name`, `url`, or `identifier` (SPDX) |

## License Identifier (SPDX)

Since OpenAPI 3.1.0 / FastAPI 0.99.0, use SPDX identifiers:

```python
app = FastAPI(
    license_info={
        "name": "MIT",
        "identifier": "MIT",
    },
)
```

## Custom Docs URLs

Override the default `/docs` and `/redoc` paths:

```python
app = FastAPI(
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
```

Disable docs entirely:

```python
app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
```

## Key Rules

- `description` supports Markdown — use headings, lists, bold, etc.
- `summary` is a short plain-text alternative to `description` (appears in OpenAPI `info.summary`).
- Metadata appears in the auto-generated docs at `/docs` and `/redoc`.
- `license_info.identifier` and `license_info.url` are mutually exclusive.