---
title: Container Data Persistence
impact: HIGH
impactDescription: Containers are ephemeral by nature. Without proper data persistence, all data is lost when a container is removed.
type: best-practice
tags: [docker, volumes, bind-mounts, data-persistence, storage]
---

# Container Data Persistence

**Impact: HIGH** - Data loss from improperly configured persistence is a critical production issue. Always use volumes for stateful workloads.

Containers are ephemeral: when a container is deleted, all files created inside it are lost. To persist data beyond a container's lifecycle, Docker provides three storage mechanisms.

## Storage Types

| Type | Persistence | Use Case | Performance |
|------|-------------|----------|-------------|
| **Volumes** | Yes (managed by Docker) | Database data, app data that must survive | High |
| **Bind mounts** | Yes (any host path) | Development hot-reload, config files | Depends on host FS |
| **tmpfs** | No (in memory only) | Temporary data, secrets, caches | Very high |

## Task Checklist

- [ ] Use volumes for database and persistent application data.
- [ ] Use bind mounts for development (hot-reload of source code).
- [ ] Use tmpfs for sensitive temporary data (credentials, tokens).
- [ ] Don't store data in the container filesystem for anything stateful.
- [ ] Name volumes explicitly for clarity.
- [ ] Use `docker volume prune` periodically to clean up unused volumes.

## Correct Pattern (Volumes)

```console
# Create a named volume
docker volume create postgres_data

# Mount it to the container
docker run -d \
  --name db \
  -e POSTGRES_PASSWORD=secret \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:18
```

```yaml
# Docker Compose equivalent
services:
  db:
    image: postgres:18
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Correct Pattern (Bind Mount for Development)

```console
# Mount local directory for hot-reload
docker run -d \
  --name app \
  -v $(pwd)/src:/app/src \
  -p 3000:3000 \
  my-app
```

```yaml
# Docker Compose equivalent
services:
  app:
    build: .
    volumes:
      - ./src:/app/src  # Development only!
    ports:
      - "3000:3000"
```

## Incorrect Pattern

```console
# ❌ No volume mount - data lost when container is removed
docker run -d --name db -e POSTGRES_PASSWORD=secret postgres:18
```

## Volume Management Commands

```console
# List all volumes
docker volume ls

# Remove a specific volume (must not be in use)
docker volume rm postgres_data

# Remove all unused volumes
docker volume prune

# Inspect volume details
docker volume inspect postgres_data
```

## Verifying Data Persistence

```console
# 1. Start database with volume
docker run --name=db -e POSTGRES_PASSWORD=secret \
  -d -v pgdata:/var/lib/postgresql/data postgres:18

# 2. Create data
docker exec -ti db psql -U postgres -c \
  "CREATE TABLE test(id int); INSERT INTO test VALUES(1);"

# 3. Remove container
docker stop db && docker rm db

# 4. Start new container with SAME volume
docker run --name=db2 -d -v pgdata:/var/lib/postgresql/data postgres:18

# 5. Verify data still exists
docker exec -ti db2 psql -U postgres -c "SELECT * FROM test;"
```

## Reference

- [Docker volumes](https://docs.docker.com/engine/storage/volumes/)
- [Bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
- [tmpfs mounts](https://docs.docker.com/engine/storage/tmpfs/)
