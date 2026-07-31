---
title: Build Failures
impact: HIGH
impactDescription: Build failures block deployment. Understanding common build errors and their solutions is critical for development velocity.
type: gotcha
tags: [docker, build, dockerfile, errors, debugging]
---

# Build Failures

**Impact: HIGH** - Build failures are the most common Docker issue. Most have simple root causes.

## Common Build Errors

### "COPY failed: file not found"

```text
COPY failed: file not found in build context or excluded by .dockerignore
```

**Causes:**
- The file doesn't exist at the specified path.
- The file is excluded by `.dockerignore`.
- Relative paths are resolved from the build context, not the Dockerfile location.

**Solutions:**
```console
# Verify the file exists
ls -la path/to/file

# Check .dockerignore for exclusions
cat .dockerignore

# If using -f with Dockerfile in a subdirectory, context is still the specified path
docker build -f subdir/Dockerfile .  # Context is ".", COPY paths relative to "."
```

### "exec: executable file not found"

**Causes:**
- Binary path in CMD/ENTRYPOINT is wrong.
- Binary doesn't have execute permissions.
- Missing shebang (`#!/bin/bash`) in scripts.

**Solutions:**
```dockerfile
# Verify binary path
RUN which node

# Set execute permission
RUN chmod +x /app/start.sh

# Use absolute path
CMD ["/usr/local/bin/node", "app.js"]
```

### "returned a non-zero code"

Each `RUN` instruction in a Dockerfile must succeed (exit code 0). Common failures:

```dockerfile
# ❌ apt update fails without -y
RUN apt update && apt install curl

# ✅ Always use -y
RUN apt update && apt install -y curl

# ❌ pip install fails due to missing dependencies
RUN pip install psycopg2

# ✅ Install build dependencies first
RUN apt update && apt install -y gcc python3-dev && \
    pip install psycopg2 && \
    apt remove -y gcc && apt autoremove -y
```

### Build Context Too Large

```console
# Check build context size
docker build --no-cache . 2>&1 | grep "sending build context"

# Add to .dockerignore
node_modules
.git
*.log
dist
build
```

## Debugging Builds

```console
# Build with progress output
docker build --progress=plain --no-cache .

# Build only up to a specific stage
docker build --target builder .

# Inspect a failed build layer
docker run -it <last-successful-image-id> sh
```

## Reference

- [Docker build troubleshooting](https://docs.docker.com/build/troubleshoot/)
