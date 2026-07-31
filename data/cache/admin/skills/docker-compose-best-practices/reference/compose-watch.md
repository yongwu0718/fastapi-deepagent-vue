---
title: Compose Watch (Hot Reload)
impact: MEDIUM
impactDescription: Compose Watch enables automatic file sync and container updates during development, eliminating manual rebuild cycles.
type: capability
tags: [docker, docker-compose, watch, development, hot-reload]
---

# Compose Watch (Hot Reload)

**Impact: MEDIUM** - Dramatically improves development experience by automating file sync and container updates.

Compose Watch monitors local file changes and automatically applies them to running containers. No manual rebuild needed for code changes.

## Task Checklist

- [ ] Use `sync` action for source code changes (no restart needed).
- [ ] Use `sync+restart` for configuration file changes.
- [ ] Use `rebuild` for dependency manifest changes (package.json, requirements.txt).
- [ ] Add `ignore` patterns for large directories (node_modules, .git, dist).
- [ ] Remove `develop.watch` from production compose files.

## Correct Pattern

```yaml
services:
  web:
    build: .
    ports:
      - "3000:3000"
    develop:
      watch:
        # Sync source code without restart (for framework hot-reload)
        - action: sync
          path: ./src
          target: /app/src
          ignore:
            - node_modules/
            - .git/

        # Sync + restart for config changes
        - action: sync+restart
          path: ./nginx.conf
          target: /etc/nginx/conf.d/default.conf

        # Full rebuild for dependency changes
        - action: rebuild
          path: package.json
```

```console
# Start with watch mode
docker compose up --watch

# Or set in environment
COMPOSE_WATCH=true docker compose up
```

## Action Types

| Action | Behavior | When to Use |
|--------|----------|-------------|
| `sync` | Copy files without restart | Source code (app has hot-reload) |
| `sync+restart` | Copy files then restart | Config files, static files |
| `rebuild` | Full image rebuild | Dependencies changed |

## Reference

- [Compose Watch documentation](https://docs.docker.com/compose/how-tos/file-watch/)
