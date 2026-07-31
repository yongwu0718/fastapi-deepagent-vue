---
title: Understanding Image Layers
impact: MEDIUM
impactDescription: Understanding how layers work is essential for optimizing image size, build speed, and layer reuse across images.
type: best-practice
tags: [docker, image-layers, union-filesystem, storage]
---

# Understanding Image Layers

**Impact: MEDIUM** - Understanding layers helps you make informed decisions about Dockerfile structure, leading to smaller images and faster builds.

Each instruction in a Dockerfile creates a new layer in the final image. Layers are immutable once created and can be shared across multiple images.

## How Layers Work

1. Each layer contains a set of filesystem changes (add, delete, modify).
2. Layers are stacked using a **union filesystem** to create a unified view.
3. When a container runs, a thin writable layer is added on top of the image layers.
4. All changes made by the container go to the writable layer.
5. When the container is deleted, the writable layer is also deleted — the image layers remain unchanged.

## Layer Example

A Dockerfile like:
```dockerfile
FROM ubuntu:22.04          # Layer 1: Base OS
RUN apt update             # Layer 2: Package list update
RUN apt install -y python3 # Layer 3: Python runtime
COPY requirements.txt ./   # Layer 4: Dependencies file
RUN pip install -r requirements.txt  # Layer 5: App dependencies
COPY src ./src             # Layer 6: Source code
```

Each instruction produces a distinct layer that can be:
- **Cached** individually
- **Reused** across different images (e.g., Python layers shared between multiple Python apps)
- **Inspected** with `docker image history <image>`

## Inspecting Layers

```console
$ docker image history my-app
IMAGE          CREATED BY                                      SIZE
abc123         COPY src ./src                                  15MB
def456         RUN pip install -r requirements.txt             45MB
ghi789         COPY requirements.txt ./                        1kB
jkl012         RUN apt install -y python3                      120MB
```

## Key Insights

1. **Layer reuse**: If you build multiple Python apps, the `FROM python` layers are shared — only downloaded once.
2. **Layer immutability**: Deleting a file in a later layer doesn't remove it from the earlier layer, it just "hides" it. The space is still consumed.
3. **Chain RUN commands**: To avoid bloated layers, chain related operations:

   ```dockerfile
   # ❌ Three layers, intermediate files persist
   RUN apt update
   RUN apt install -y curl
   RUN rm -rf /var/lib/apt/lists/*

   # ✅ One layer, cleaned up properly
   RUN apt update && apt install -y curl && rm -rf /var/lib/apt/lists/*
   ```

4. **Minimize layers, but don't over-optimize**: Too many layers can increase overhead; too few can hurt cache efficiency.

## Layer Optimization Strategy

| Priority | Strategy |
|----------|----------|
| 1 | Group related changes in a single RUN |
| 2 | Clean up temp files in the same layer |
| 3 | Order layers from stable → volatile |
| 4 | Use multi-stage builds to discard build-only layers |

## Reference

- [Docker image layers](https://docs.docker.com/get-started/docker-concepts/building-images/understanding-image-layers/)
- [Union filesystems](https://docs.docker.com/storage/storagedriver/)
