---
title: Build Cache Optimization
impact: HIGH
impactDescription: Proper cache usage can reduce build times from minutes to seconds. Incorrect layer ordering leads to unnecessary rebuilds.
type: best-practice
tags: [docker, build-cache, optimization, layers]
---

# Build Cache Optimization

**Impact: HIGH** - Effective cache usage can reduce subsequent build times by 90%+. Mismanaged cache leads to full rebuilds on every source code change.

Docker builds are incremental: each instruction creates a layer that can be cached and reused. When one layer is invalidated, all subsequent layers must be rebuilt.

## Task Checklist

- [ ] Order instructions from least-changing to most-changing.
- [ ] Copy dependency files (`package.json`, `requirements.txt`) before source code.
- [ ] Install dependencies in a separate instruction before `COPY . .`.
- [ ] Use `.dockerignore` to exclude files that change frequently but aren't needed.
- [ ] Group related `RUN` commands with `&&` and clean up in the same layer.

## Correct Pattern

```dockerfile
FROM node:22-alpine
WORKDIR /app

# Step 1: Copy dependency manifests first (rarely changes)
COPY package.json yarn.lock ./

# Step 2: Install dependencies (cached unless manifests change)
RUN yarn install --production

# Step 3: Copy source code last (changes frequently)
COPY . .

EXPOSE 3000
CMD ["node", "src/index.js"]
```

## Incorrect Pattern (Cache-busting)

```dockerfile
FROM node:22-alpine
WORKDIR /app

# ❌ Copy everything first - any source change invalidates this
COPY . .

# ❌ Dependency install re-runs on EVERY source code change
RUN yarn install --production

EXPOSE 3000
CMD ["node", "src/index.js"]
```

## Cache Invalidation Rules

1. **Changes to a `RUN` command** → that layer and all subsequent layers invalidated.
2. **Changes to files copied by `COPY`/`ADD`** → that layer and all subsequent layers invalidated.
3. **Changes to a base image** (`FROM`) → all layers invalidated.
4. **Using `--no-cache` flag** → all layers rebuilt.

## `.dockerignore` Usage

Create `.dockerignore` to exclude files from the build context:

```plaintext
node_modules
.git
.gitignore
*.md
.env
.env.*
dist
build
coverage
.vscode
.idea
Dockerfile
docker-compose*
```

## Build Verification

After optimizing, verify cache effectiveness:

```console
# First build - full build
$ docker build .
[+] Building 20.0s (10/10) FINISHED

# Second build (no changes) - fully cached
$ docker build .
[+] Building 1.0s (9/9) FINISHED
  => CACHED [2/4] WORKDIR /app
  => CACHED [3/4] COPY package.json yarn.lock ./
  => CACHED [4/4] RUN yarn install --production
```

## Reference

- [Optimizing builds with cache management](https://docs.docker.com/build/cache/)
- [Cache invalidation](https://docs.docker.com/build/cache/invalidation/)
