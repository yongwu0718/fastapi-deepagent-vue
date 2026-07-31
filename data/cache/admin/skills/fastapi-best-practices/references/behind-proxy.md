# Behind a Proxy

Configure FastAPI to run correctly behind reverse proxies (Nginx, Traefik, Caddy, etc.) with proper URL generation, HTTPS redirects, and forwarded headers.

## The Problem

Proxies add headers (`X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`) that tell your app about the original request. By default, Uvicorn/FastAPI ignores these for security.

Without proxy configuration:
- Redirects may point to `http://localhost:8000/` instead of `https://mysuperapp.com/`.
- Client IP addresses appear as the proxy's IP, not the real client.
- Generated URLs (in responses, docs) use the wrong scheme/host.

## Enabling Forwarded Headers

### Via FastAPI CLI

```bash
# Trust all proxy IPs
fastapi run main.py --forwarded-allow-ips="*"

# Trust specific IPs
fastapi run main.py --forwarded-allow-ips="10.0.0.1,10.0.0.2"
```

### Via Uvicorn directly

```bash
uvicorn main:app --proxy-headers --forwarded-allow-ips="*"
```

## Example: Redirect Fix

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/")
def read_items():
    return ["plumbus", "portal gun"]
```

Without `--forwarded-allow-ips`, accessing `/items` redirects to `http://localhost:8000/items/`.
With the flag set, it redirects to `https://mysuperapp.com/items/`.

## How Forwarded Headers Work

```
Client → Proxy (adds X-Forwarded-*) → FastAPI Server
```

Headers the proxy sets:
| Header | Value |
|---|---|
| `X-Forwarded-For` | Original client IP |
| `X-Forwarded-Proto` | `https` or `http` |
| `X-Forwarded-Host` | Original hostname |

## NGINX Configuration Example

```nginx
server {
    listen 443 ssl;
    server_name mysuperapp.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Key Rules

- Only use `--forwarded-allow-ips="*"` when your server is behind a trusted proxy and only the proxy can reach it.
- In production, specify exact proxy IPs instead of `*` for better security.
- The `root_path` mechanism (used by sub-apps) works with forwarded headers automatically.

## Common Pitfalls

### Swagger UI trying to reach localhost

If Swagger UI at `/docs` tries to call `http://localhost:8000/openapi.json` instead of your public URL, check that `--forwarded-allow-ips` is set.

### Mixed HTTP/HTTPS in responses

Generated links (pagination, redirects) using `http://` when behind HTTPS proxy — enable forwarded headers.

### Multiple proxies (load balancer + reverse proxy)

Use `X-Forwarded-For` chain: each proxy appends to the list. Set `--forwarded-allow-ips` to the IP of the last proxy before your app.