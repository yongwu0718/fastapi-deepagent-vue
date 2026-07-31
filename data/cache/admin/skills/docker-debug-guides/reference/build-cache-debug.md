---
title: Build Cache Debugging
impact: MEDIUM
impactDescription: Slow builds waste developer time. Understanding why cache misses occur enables fast iterative development.
type: gotcha
tags: [docker, build, cache, performance, debugging]
---

# Build Cache Debugging

**Impact: MEDIUM** - Builds that should be fast are slow due to cache misses. Identify and fix the root cause.

## Why Is My Build Not Using Cache?

### Common Cache Miss Causes

1. **Source code COPY comes before dependency install** → Any source change busts dependency cache.
2. **`.dockerignore` is missing** → Build context includes unnecessary files that change frequently.
3. **`--no-cache` flag** → Explicitly bypasses cache.
4. **Build argument changes** → `ARG` values affect cache.
5. **Base image changed** → `FROM` layer is new.

### Debugging Steps

```console
# 1. Check if build is using cache (look for CACHED)
docker build --progress=plain . 2>&1 | grep -E "CACHED|RUN|COPY"

# 2. Check the exact file that changed in a COPY layer
docker build --progress=plain . 2>&1

# 3. Inspect what files are in the build context
docker build --no-cache . 2>&1 | grep "sending build context"

# 4. List files that Docker sees in context
docker run --rm -v $(pwd):/context alpine find /context -maxdepth 3
```

### Fix: Proper Layer Ordering

```dockerfile
# ❌ Cache breaks on every source change
FROM node:22-alpine
WORKDIR /app
COPY . .
RUN npm install

# ✅ Dependencies cached until package.json changes
FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
```

### Check `.dockerignore`

```plaintext
# Must exclude frequently-changing files
node_modules
.git
.env
*.log
dist
build
coverage
.DS_Store
```

## Reference

- [Build cache invalidation](https://docs.docker.com/build/cache/invalidation/)
- [Using the build cache](https://docs.docker.com/get-started/docker-concepts/building-images/using-the-build-cache/)
