---
title: Volume Issues
impact: HIGH
impactDescription: Volume misconfiguration leads to data loss, missing data, or containers failing to start.
type: gotcha
tags: [docker, volumes, data-persistence, debugging]
---

# Volume Issues

**Impact: HIGH** - Volume problems can cause data loss. Always diagnose carefully before removing containers.

## Data Lost After Container Restart

**Symptom:** Data disappears when container is recreated.

**Diagnose:**
```console
# Check if volume is actually mounted
docker inspect <container> | jq '.[0].Mounts'

# Check if using --rm flag (removes container on exit)
docker ps -a | grep <container>
```

**Common causes:**
- Volume not specified in `docker run` command.
- Different volume name used on restart.
- `docker compose down -v` removed volumes.
- Using `--rm` flag removes container (and anonymous volumes).

**Fix:**
```console
# Always use named volumes
docker run -d -v my_named_volume:/data my-app

# Don't remove volumes unless needed
docker compose down           # Keeps volumes
docker compose down -v        # Removes volumes (caution!)

# Backup before risky operations
docker run --rm -v my_volume:/data -v $(pwd):/backup alpine \
  tar czf /backup/vol_backup.tar.gz -C /data .
```

## Volume Not Mounting As Expected

**Diagnose:**
```console
# Compare expected vs actual mounts
docker inspect <container> | jq '.[0].Mounts[] | {Source, Destination, Mode}'

# Check if volume exists
docker volume ls | grep <volume_name>

# Check volume contents
docker run --rm -v <volume_name>:/data alpine ls -la /data
```

**Common causes:**
- Path mismatch between host and container.
- Using Windows paths on Linux (or vice versa).
- Bind mount source directory doesn't exist.

**Fix:**
```console
# Absolute paths for bind mounts (Linux/Mac)
docker run -v /absolute/host/path:/container/path my-app

# Windows paths
docker run -v C:\Users\me\app:/container/path my-app

# Named volumes don't need paths
docker run -v my_volume:/container/path my-app
```

## Disk Space Exhausted

```console
# Check Docker disk usage
docker system df
docker system df -v   # Verbose, per-object

# Large volumes
docker system df -v | grep "Local Volumes"

# Clean up
docker volume prune          # Remove unused volumes
docker system prune -a       # Remove unused images, containers, networks
docker builder prune         # Remove build cache
```

## Reference

- [Docker volumes troubleshooting](https://docs.docker.com/engine/storage/volumes/)
- [docker system df](https://docs.docker.com/reference/cli/docker/system/df/)
