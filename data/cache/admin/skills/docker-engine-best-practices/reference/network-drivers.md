---
title: Network Drivers
impact: HIGH
impactDescription: Choosing the wrong network driver can cause connectivity issues, performance problems, or security vulnerabilities.
type: best-practice
tags: [docker, networking, bridge, host, overlay, macvlan, ipvlan]
---

# Network Drivers

**Impact: HIGH** - The network driver determines how containers communicate with each other, the host, and external networks.

## Driver Summary

| Driver | Scope | Isolation | DNS | Use Case |
|--------|-------|-----------|-----|----------|
| **bridge** | Single host | Yes | Yes | Default for standalone containers |
| **host** | Single host | No (shares host) | No | Performance-critical, system tools |
| **overlay** | Multi-host (Swarm) | Yes | Yes | Multi-host container communication |
| **ipvlan** | Single host | MAC/IP at L2 | Optional | Legacy app migration |
| **macvlan** | Single host | MAC at L2 | Optional | Physical network appearance |
| **none** | Single host | Maximum | No | Air-gapped containers |

## Task Checklist

- [ ] Use user-defined bridge networks (not default bridge) for DNS and isolation.
- [ ] Use `host` network only for system tools and monitoring.
- [ ] Use `overlay` for Swarm multi-host deployments.
- [ ] Use `macvlan`/`ipvlan` only for legacy applications requiring direct physical network access.
- [ ] Create separate networks for different security zones (frontend/backend).

## Bridge Network (Recommended Default)

User-defined bridges provide better isolation and automatic DNS than the default bridge:

```console
# Create a user-defined bridge
docker network create --driver bridge app-network

# Run containers
docker run -d --name web --network app-network nginx
docker run -d --name api --network app-network my-api

# web can ping api by name
docker exec web ping api  # ✓ works on user-defined bridge
```

## Host Network (Caution)

```console
# Container uses host's network directly
docker run --network host nginx

# Pros: No NAT overhead, maximum performance
# Cons: No isolation, port conflicts, no DNS between containers
# Use only for: network monitoring, packet capture, system tools
```

## Overlay Network (Swarm Only)

```yaml
# Requires Docker Swarm mode
networks:
  app-overlay:
    driver: overlay
    attachable: true      # Allow standalone containers to connect
```

```console
# Create attachable overlay for standalone containers
docker network create --driver overlay --attachable app-overlay
```

## IPvlan / Macvlan (Legacy/L3 Access)

```console
# Macvlan — each container gets its own MAC and IP on physical network
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  macvlan-net

# IPvlan — containers share host MAC but get unique IPs
docker network create -d ipvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  ipvlan-net
```

## Network Inspection

```console
# List networks
docker network ls

# Inspect network details (subnet, connected containers)
docker network inspect app-network

# Check container's network settings
docker inspect --format '{{.NetworkSettings.Networks}}' web
```

## Reference

- [Docker network drivers](https://docs.docker.com/engine/network/drivers/)
- [Bridge network](https://docs.docker.com/engine/network/drivers/bridge/)
