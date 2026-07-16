---
title: Networking in Compose
impact: HIGH
impactDescription: Compose networking is the backbone of multi-container communication. Misconfiguration leads to unreachable services and connectivity issues.
type: best-practice
tags: [docker, docker-compose, networking, service-discovery]
---

# Networking in Compose

**Impact: HIGH** - Understanding Compose networking is essential for reliable inter-service communication.

By default, Compose creates a bridge network for your application. Each service joins this network and is reachable by other services using its service name as hostname.

## Task Checklist

- [ ] Use service names (not IPs) for inter-container communication.
- [ ] Use container ports (not host ports) for service-to-service connections.
- [ ] Create custom networks for security isolation (frontend/backend).
- [ ] Use `external: true` for cross-project shared networks.
- [ ] Set `internal: true` for backend-only networks.
- [ ] Never rely on container IPs (they change on restart).

## Default Networking (Zero Config)

```yaml
# No network configuration needed — it just works
services:
  web:
    image: nginx
    # Code connects to: postgres://db:5432
  db:
    image: postgres:18
```

Compose automatically:
1. Creates a network named `<project>_default`
2. Connects all services to it
3. Enables DNS resolution by service name

## Custom Network Isolation

```yaml
services:
  proxy:
    networks:
      - frontend                     # Only frontend

  app:
    networks:
      - frontend
      - backend                      # Both networks

  db:
    networks:
      - backend                      # Only backend — inaccessible from outside

networks:
  frontend:
  backend:
    internal: true                   # No external internet access
```

## External Networks (Cross-project)

```console
# Create shared network first
docker network create shared
```

```yaml
# In multiple projects
networks:
  shared:
    external: true                   # Use existing network, don't create
```

## Network Modes

| Mode | Behavior | When to Use |
|------|----------|-------------|
| `bridge` (default) | Isolated network with DNS | Standard applications |
| `host` | Shares host network stack | System monitoring tools |
| `none` | No networking | Highly isolated services |

```yaml
services:
  monitor:
    image: netdata/netdata
    network_mode: host               # Access all host ports directly
```

## Port Mapping

```yaml
services:
  db:
    ports:
      - "8001:5432"   # HOST_PORT:CONTAINER_PORT
```

- **Container port** (5432): Used by other services on the network → `postgres://db:5432`
- **Host port** (8001): Used from outside → `postgres://localhost:8001`

## Incorrect Pattern

```yaml
# ❌ Hardcoding container IPs
services:
  web:
    environment:
      - DB_HOST=172.17.0.3   # IP changes on restart!
```

## Reference

- [Compose networking](https://docs.docker.com/compose/how-tos/networking/)
- [Docker networking overview](https://docs.docker.com/engine/network/)
