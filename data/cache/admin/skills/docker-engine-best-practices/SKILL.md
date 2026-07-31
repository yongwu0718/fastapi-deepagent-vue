---
name: docker-engine-best-practices
description: Docker Engine operations, networking, storage, daemon configuration, resource management, and logging. Use for Docker daemon setup, network driver configuration, storage driver selection, resource constraints, or container logging configuration.
license: MIT
metadata:
  author: github.com/docker-ai
  version: "1.0.0"
---

# Docker Engine Best Practices Workflow

Use this skill for Docker Engine-level configuration and operations tasks.

## Core Principles
- **Understand the daemon:** Docker Engine runs as a daemon (`dockerd`) managing all container operations.
- **Network isolation first:** Design networks to limit service exposure and control traffic flow.
- **Volumes for persistence:** Use named volumes for stateful data; understand the trade-offs between volume types.
- **Resource limits prevent chaos:** Set CPU/memory limits on all production containers.
- **Logs are critical:** Configure appropriate log drivers and rotation to prevent disk exhaustion.

## 1) Network Drivers (required)

### Must-read references
- `reference/network-drivers.md`
- `reference/port-publishing.md`

### Driver Selection Guide

| Driver | Use Case | Key Feature |
|--------|----------|-------------|
| **Bridge** | Default, single-host containers | Isolated network, DNS resolution |
| **Host** | System tools, high-performance networking | Shares host network stack |
| **Overlay** | Multi-host (Swarm) | Cross-host container communication |
| **IPvlan/Macvlan** | Legacy app migration, specific MAC/IP | Direct physical network access |
| **None** | Maximum isolation | No networking |

### Bridge Network (Default)

```console
# Create a user-defined bridge (better than default)
docker network create --driver bridge my-bridge

# Run containers on the bridge
docker run -d --name web --network my-bridge nginx
docker run -d --name db --network my-bridge postgres:18
# web can now reach db via hostname "db"
```

### Host Network

```console
# Container shares host's network namespace — no port mapping needed
docker run --network host nginx  # Accessible on localhost:80 directly
```

## 2) Storage (required)

### Must-read reference
- `reference/storage-management.md`

### Storage Type Selection

| Type | Persistence | Performance | Use Case |
|------|-------------|-------------|----------|
| **Volumes** | Docker-managed | High | Production data (DB, app state) |
| **Bind mounts** | Host path | Depends on host FS | Development, config files |
| **tmpfs** | Memory only | Very high | Temporary sensitive data |

```console
# Named volume (recommended for production)
docker volume create app_data
docker run -v app_data:/data my-app

# Bind mount (development)
docker run -v $(pwd)/src:/app/src my-app

# tmpfs (temporary)
docker run --tmpfs /tmp:rw,noexec,nosuid my-app
```

## 3) Resource Constraints (required)

### Must-read reference
- `reference/resource-constraints.md`

```console
# Limit CPU and memory
docker run -d \
  --cpus="1.5" \
  --memory="512m" \
  --memory-swap="1g" \
  my-app

# CPU shares (relative weight)
docker run -d --cpu-shares=512 web
docker run -d --cpu-shares=256 worker
```

### Docker Compose equivalent

```yaml
services:
  app:
    image: myapp
    deploy:
      resources:
        limits:
          cpus: '1.5'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

## 4) Daemon Configuration

### Must-read reference
- `reference/daemon-configuration.md`

Key daemon settings in `/etc/docker/daemon.json`:
- `log-driver`: Set default logging driver
- `log-opts`: Log rotation settings
- `storage-driver`: Overlay2 (default, recommended)
- `registry-mirrors`: Add mirror registries
- `insecure-registries`: Allow HTTP registries
- `data-root`: Change Docker data directory

## 5) Container Logging

```console
# View logs
docker logs <container>
docker logs -f <container>        # Follow
docker logs --tail 100 <container> # Last 100 lines
docker logs --since 10m <container># Last 10 minutes
```

Configure log rotation:

```json
// /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## 6) Port Publishing

```console
# Map specific host port to container port
docker run -p 8080:80 nginx           # localhost:8080 → container:80

# Map to random host port
docker run -p 80 nginx                 # Random host port → container:80

# Map to specific interface
docker run -p 127.0.0.1:8080:80 nginx  # Only localhost

# Publish all EXPOSE'd ports to random host ports
docker run -P nginx
```

## 7) Final self-check

- [ ] Network drivers selected appropriately for each service.
- [ ] Storage uses volumes for production data, bind mounts only for dev.
- [ ] CPU and memory limits set on all production containers.
- [ ] Log rotation configured to prevent disk exhaustion.
- [ ] Port mappings are explicit and minimal.
- [ ] Daemon configuration validated (`dockerd --validate`).
- [ ] Firewall rules allow necessary ports only.
