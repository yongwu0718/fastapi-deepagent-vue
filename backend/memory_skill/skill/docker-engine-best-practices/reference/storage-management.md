---
title: Storage Management
impact: HIGH
impactDescription: Choosing the wrong storage type leads to data loss, poor performance, or excessive disk usage.
type: best-practice
tags: [docker, storage, volumes, bind-mounts, tmpfs]
---

# Storage Management

**Impact: HIGH** - Docker provides three storage mechanisms. Using the wrong one for production data causes data loss or performance issues.

## Storage Comparison

| Feature | Volumes | Bind Mounts | tmpfs |
|---------|---------|-------------|-------|
| **Managed by** | Docker | Host filesystem | Memory |
| **Persistence** | Yes (survives container removal) | Yes (host path) | No (memory only) |
| **Performance** | High (native FS) | Host FS dependent | Very high (RAM) |
| **Portability** | Docker-managed, portable | Host-path dependent | Container only |
| **Sharing** | Multiple containers | Multiple containers | Single container |
| **Backup** | `docker volume` commands | File system tools | Not possible |
| **Use Case** | Production data | Development | Temp/secrets |

## Task Checklist

- [ ] Use named volumes for all production persistent data (databases, uploads).
- [ ] Use bind mounts only for development (source code, config files).
- [ ] Use tmpfs for temporary sensitive data.
- [ ] Never store stateful data in the container's writable layer.
- [ ] Use volume drivers for remote/cloud storage when needed.

## Volumes (Production)

```console
# Create a volume
docker volume create pg_data

# Use with --mount (explicit syntax, recommended)
docker run -d \
  --mount source=pg_data,target=/var/lib/postgresql/data \
  postgres:18

# Use with -v (shorthand)
docker run -d -v pg_data:/var/lib/postgresql/data postgres:18

# List volumes
docker volume ls

# Inspect volume
docker volume inspect pg_data

# Backup a volume
docker run --rm -v pg_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/pg_data_backup.tar.gz -C /data .

# Restore a volume
docker run --rm -v pg_data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/pg_data_backup.tar.gz -C /data

# Remove unused volumes
docker volume prune
```

## Bind Mounts (Development)

```console
# Mount local directory for hot-reload
docker run -d \
  --mount type=bind,source=$(pwd)/src,target=/app/src \
  my-app

# With -v shorthand
docker run -d -v $(pwd)/src:/app/src my-app

# Read-only bind mount
docker run -d -v $(pwd)/config:/etc/app:ro my-app
```

## tmpfs (Temporary)

```console
# In-memory mount (data lost on container stop)
docker run -d \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  my-app
```

## Volume Drivers

```console
# Create volume with specific driver
docker volume create --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.1,rw \
  --opt device=:/path/to/dir \
  nfs-volume
```

## Reference

- [Docker volumes](https://docs.docker.com/engine/storage/volumes/)
- [Bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
- [tmpfs mounts](https://docs.docker.com/engine/storage/tmpfs/)
