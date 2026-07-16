---
title: Multi-file Compose & Extends
impact: MEDIUM
impactDescription: Multiple compose files enable environment-specific configurations without duplication. Improper merging can lead to unexpected results.
type: best-practice
tags: [docker, docker-compose, merge, extend, multi-file]
---

# Multi-file Compose & Extends

**Impact: MEDIUM** - Separating base config from environment overrides reduces duplication and errors.

## Merge Rules

When using multiple files (`-f compose.yaml -f compose.prod.yaml`):

- **Single values** (`image`, `command`): **later file overwrites earlier**
- **Lists** (`ports`, `expose`): **appended** (concatenated)
- **Maps** (`environment`, `volumes`): **same key overwrites, new key appended**

## Base + Override Pattern

```yaml
# compose.yaml (base - development)
services:
  web:
    build: .
    ports:
      - "8000:80"
    volumes:
      - ./src:/app/src       # Dev-only bind mount
    environment:
      - DEBUG=true

# compose.prod.yaml (production overrides)
services:
  web:
    build: .                 # Or use image:
    ports:
      - "80:80"              # Override port
    restart: always
    volumes: []              # Clear dev mounts!
    environment:
      - DEBUG=false          # Override
```

```console
# Development
docker compose up -d

# Production
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

## Extends Pattern

Reuse common configuration across services:

```yaml
# common.yaml
services:
  base:
    build: .
    environment:
      - API_KEY=xxx
    cpu_shares: 5

# compose.yaml
services:
  web:
    extends:
      file: common.yaml
      service: base
    command: /code/run_web
    ports:
      - "8080:8080"

  worker:
    extends:
      file: common.yaml
      service: base
    command: /code/run_worker
```

## Include Pattern

Include external compose files:

```yaml
# compose.yaml
include:
  - path: ./database/compose.yaml
  - path: ./cache/compose.yaml

services:
  web:
    build: .
    ports:
      - "8080:80"
```

## Safety Checklist

- [ ] `docker compose config` to verify final merged output.
- [ ] Production file clears dev-specific volumes and ports.
- [ ] `extends` references use digests (not mutable tags) for remote files.
- [ ] Test merged configuration before deploying.

## Reference

- [Merge Compose files](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)
- [Extend services](https://docs.docker.com/compose/how-tos/multiple-compose-files/extends/)
- [Include files](https://docs.docker.com/compose/how-tos/multiple-compose-files/include/)
