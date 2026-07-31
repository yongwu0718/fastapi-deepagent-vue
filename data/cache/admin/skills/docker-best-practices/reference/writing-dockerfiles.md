---
title: Writing Dockerfiles
impact: HIGH
impactDescription: Dockerfile is the foundation of all Docker images. Poorly written Dockerfiles lead to large images, slow builds, and security vulnerabilities.
type: best-practice
tags: [docker, dockerfile, image-building, best-practices]
---

# Writing Dockerfiles

**Impact: HIGH** - The Dockerfile defines how your container image is built. Following best practices ensures smaller images, faster builds, and better security.

A Dockerfile is a text-based document that provides instructions for building a container image. Each instruction creates a new layer in the final image.

## Task Checklist

- [ ] Start from an appropriate base image (prefer `alpine` or `slim` variants for production).
- [ ] Set `WORKDIR` explicitly at the top of the Dockerfile.
- [ ] Copy dependency manifests first, then install, then copy source code.
- [ ] Use `.dockerignore` to exclude files from build context.
- [ ] Run as non-root user (`USER` instruction).
- [ ] Use exec form for `CMD` and `ENTRYPOINT` (`["executable", "arg1"]`).
- [ ] `EXPOSE` only the ports your application actually uses.
- [ ] Keep secrets out of Dockerfile and image layers.

## Common Instructions

| Instruction | Purpose |
|------------|---------|
| `FROM image` | Specifies the base image to build from |
| `WORKDIR /path` | Sets working directory for subsequent instructions |
| `COPY host-path image-path` | Copies files from host into the image |
| `RUN command` | Executes a command during build |
| `ENV name value` | Sets an environment variable |
| `EXPOSE port` | Documents the port the container listens on |
| `USER name-or-uid` | Sets the default user for subsequent instructions |
| `CMD ["cmd", "arg1"]` | Default command when container starts |

## Correct Pattern

```dockerfile
# Use a specific, slim base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy dependency files first (for cache efficiency)
COPY requirements.txt ./

# Install dependencies (cached unless requirements.txt changes)
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src

# Document the port
EXPOSE 8080

# Create and switch to non-root user
RUN useradd --create-home appuser
USER appuser

# Default command (exec form)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Incorrect Pattern (Anti-pattern)

```dockerfile
# ❌ Using `latest` tag is unpredictable
FROM python:latest

# ❌ No WORKDIR set
# ❌ Copy everything before installing dependencies - breaks caching
COPY . .
RUN pip install -r requirements.txt  # ❌ Re-runs on every source change

# ❌ No non-root user - runs as root
# ❌ Shell form CMD
CMD uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Key Rules

1. **Layer ordering matters**: Instructions that change frequently (COPY source) should come last.
2. **Never use `latest` tag in production**: Pin exact versions for reproducibility.
3. **One `RUN` per logical group**: Chain related commands with `&&` and clean up in the same layer.
4. **Secrets in Dockerfile**: Use `--secret` flag or secrets management, never hardcode.

## Reference

- [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
- [Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
