---
title: Compose File Structure
impact: HIGH
impactDescription: The compose.yaml file is the single source of truth for multi-container applications. Poor structure leads to configuration drift and deployment issues.
type: best-practice
tags: [docker, docker-compose, yaml, configuration]
---

# Compose File Structure

**Impact: HIGH** - A well-structured `compose.yaml` enables reproducible, maintainable multi-service deployments.

The Compose file (`compose.yaml` or `compose.yml`) defines your application's services, networks, volumes, configs, and secrets in a declarative YAML format.

## Task Checklist

- [ ] Use `compose.yaml` (preferred) or `compose.yml` as the filename.
- [ ] Set project name via top-level `name` field or `COMPOSE_PROJECT_NAME`.
- [ ] Define all services, volumes, and networks in one file.
- [ ] Use official images with pinned tags for external services.
- [ ] Validate configuration with `docker compose config`.
- [ ] Separate base config from environment-specific overrides.

## Complete Template

```yaml
name: myapp                    # Project name (optional, defaults to directory name)

services:
  # ---- Web Application ----
  web:
    build: .                   # Build from current directory
    # image: nginx:alpine      # Or use a pre-built image
    ports:
      - "8000:80"              # host:container
    environment:
      - DEBUG=false
      - DB_HOST=db
    env_file: .env             # Load from file
    depends_on:
      db:
        condition: service_healthy
        restart: true
    volumes:
      - ./src:/app/src         # Bind mount (dev only)
      - app_data:/app/data     # Named volume
    restart: always
    develop:                   # Compose Watch (dev only)
      watch:
        - action: sync
          path: ./src
          target: /app/src
          ignore:
            - node_modules/
        - action: rebuild
          path: package.json

  # ---- Database ----
  db:
    image: postgres:18-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d myapp"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # ---- Cache ----
  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data

# ---- Volumes ----
volumes:
  db_data:
  redis_data:
  app_data:

# ---- Secrets ----
secrets:
  db_password:
    file: ./secrets/db_password.txt

# ---- Networks ----
networks:
  default:
    driver: bridge
```

## Common Commands

```console
# Start all services
docker compose up -d

# Start with build and file watching
docker compose up --build --watch

# Stop and remove
docker compose down
docker compose down -v     # also remove volumes

# View logs
docker compose logs -f
docker compose logs -f web # specific service

# List services
docker compose ps

# Execute command in a running service
docker compose exec web bash

# View resolved configuration
docker compose config

# Build images
docker compose build
```

## Reference

- [Compose Specification](https://compose-spec.io/)
- [Docker Compose file reference](https://docs.docker.com/compose/compose-file/)
