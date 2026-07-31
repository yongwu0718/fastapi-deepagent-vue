---
title: Compose Profiles
impact: MEDIUM
impactDescription: Profiles enable selective service activation for different environments (dev, debug, test) without maintaining separate compose files.
type: capability
tags: [docker, docker-compose, profiles, environment]
---

# Compose Profiles

**Impact: MEDIUM** - Profiles let you activate subsets of services based on the environment or purpose.

Services without a `profiles` attribute are always started. Services with profiles only start when their profile is explicitly enabled.

## Task Checklist

- [ ] Define optional services with `profiles` (debug tools, admin UIs).
- [ ] Keep core services (app, db) without profiles — always start.
- [ ] Use `COMPOSE_PROFILES` env var or `--profile` flag to activate.

## Correct Pattern

```yaml
services:
  # Always starts — no profile
  app:
    image: myapp
    ports:
      - "8080:80"

  # Only starts with --profile debug
  debug-tools:
    image: phpmyadmin
    profiles: [debug]
    ports:
      - "8081:80"

  # Only starts with --profile monitoring
  prometheus:
    image: prom/prometheus
    profiles: [monitoring]
    ports:
      - "9090:9090"
```

## Usage Commands

```console
# Start with debug tools
docker compose --profile debug up

# Start with multiple profiles
docker compose --profile debug --profile monitoring up

# Set via environment variable
COMPOSE_PROFILES=debug docker compose up

# Start only the always-active services
docker compose up
```

## Reference

- [Using profiles with Compose](https://docs.docker.com/compose/how-tos/profiles/)
