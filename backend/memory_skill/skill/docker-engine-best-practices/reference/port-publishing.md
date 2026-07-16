---
title: Port Publishing
impact: MEDIUM
impactDescription: Port publishing exposes container services to external networks. Misconfigured ports create security vulnerabilities.
type: best-practice
tags: [docker, ports, networking, publishing, expose]
---

# Port Publishing

**Impact: MEDIUM** - Only publish ports that need external access. Each published port is a potential attack surface.

## Task Checklist

- [ ] Only publish ports that need external network access.
- [ ] Bind to `127.0.0.1` when external access is not needed.
- [ ] Use `-P` (publish all) sparingly — prefer explicit port mappings.
- [ ] Avoid port conflicts by checking `docker ps` before publishing.

## Common Patterns

```console
# Map specific host port to container port
docker run -p 8080:80 nginx
# localhost:8080 → container port 80

# Map to specific interface only
docker run -p 127.0.0.1:8080:80 nginx
# Only accessible from localhost

# Map container port to random host port
docker run -p 80 nginx
# Random host port → container port 80

# Publish all EXPOSE'd ports to random ports
docker run -P nginx

# UDP port
docker run -p 53:53/udp bind9
```

## Compose Port Syntax

```yaml
services:
  web:
    ports:
      - "8080:80"                 # host:container
      - "127.0.0.1:8443:443"     # bind to localhost only
      - "53:53/udp"              # UDP port
      - "8000-8010:8000-8010"    # port range
```

## Listing Published Ports

```console
# See all published ports
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Filter by port
docker ps --filter "publish=8080"
```

## Security Best Practices

1. **Least privilege:** Only expose ports that must be externally accessible.
2. **Bind to localhost:** Use `127.0.0.1:port:port` for internal-only services.
3. **Avoid privileged ports:** Don't use ports < 1024 when not necessary.
4. **Firewall rules:** Complement Docker port mappings with host firewall rules.

## Reference

- [Container networking - published ports](https://docs.docker.com/engine/network/#published-ports)
