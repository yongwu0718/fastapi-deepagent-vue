---
title: Permission Errors
impact: HIGH
impactDescription: Permission errors in containers block file access, service startup, and data persistence. They're especially common with bind mounts.
type: gotcha
tags: [docker, permissions, bind-mounts, security, debugging]
---

# Permission Errors

**Impact: HIGH** - Permission errors in containers prevent file operations and can break application startup.

## "Permission Denied" Inside Container

### Common Causes

1. **Running as non-root without proper file ownership.**
2. **Bind-mounted files owned by different UID on host.**
3. **Read-only filesystem on mounted volumes.**

### Diagnose

```console
# Check current user
docker exec <container> whoami
docker exec <container> id

# Check file ownership
docker exec <container> ls -la /path/to/file

# Check mount permissions
docker inspect <container> | jq '.[0].Mounts'
```

### Fix: Align User IDs

```dockerfile
# Option 1: Create user with matching UID
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID appgroup && \
    useradd -u $UID -g appgroup appuser
USER appuser
```

```console
# Build with host's UID
docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) -t myapp .
```

### Fix: Change Ownership at Build

```dockerfile
# Copy files then change ownership
COPY --chown=appuser:appgroup . /app
```

### Fix: Use Docker's userns-remap

```json
// /etc/docker/daemon.json
{
  "userns-remap": "default"
}
```

## Bind Mount Permission Denied

```console
# Files created by container are owned by root on host
docker run -v /host/path:/data alpine touch /data/test
ls -la /host/path/test  # Owned by root!

# Fix: Use --user to match host UID
docker run --user $(id -u):$(id -g) -v /host/path:/data alpine touch /data/test
```

## "Docker Permission Denied" on Host

```console
# User not in docker group
docker ps
# Got permission denied while trying to connect to the Docker daemon socket

# Fix: Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in, or:
newgrp docker
```

## Reference

- [Docker security - user](https://docs.docker.com/engine/security/#docker-daemon-attack-surface)
- [Linux capabilities in Docker](https://docs.docker.com/engine/security/#linux-kernel-capabilities)
