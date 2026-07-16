---
title: Networking Issues
impact: HIGH
impactDescription: Network connectivity problems prevent containers from communicating with each other and external services.
type: gotcha
tags: [docker, networking, dns, connectivity, debugging]
---

# Networking Issues

**Impact: HIGH** - Networking is the most complex part of container orchestration. Systematic diagnosis is essential.

## Container Cannot Reach Internet

**Diagnose:**
```console
# Test DNS resolution
docker run --rm alpine nslookup google.com

# Test internet connectivity
docker run --rm alpine ping -c 3 8.8.8.8

# Check DNS configuration
docker run --rm alpine cat /etc/resolv.conf
```

**Common causes:**
- Host firewall blocking Docker traffic.
- DNS misconfiguration in daemon.
- Proxy not configured.

**Fix:**
```json
// /etc/docker/daemon.json
{
  "dns": ["8.8.8.8", "1.1.1.1"]
}
```

## Service-to-Service Connection Refused

**Diagnose:**
```console
# From one container, test connection to another
docker exec web ping db
docker exec web nc -zv db 5432

# Check if containers are on the same network
docker network inspect <network>
```

**Common causes:**
- Containers on different networks.
- Using wrong port (host port instead of container port).
- Service hasn't started yet (no healthcheck/depends_on).

**Fix for Compose:**
```yaml
services:
  web:
    depends_on:
      db:
        condition: service_healthy   # Wait for ready

  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
```

## DNS Resolution Fails

**Diagnose:**
```console
# Test DNS from container
docker exec web nslookup db      # Fails?
docker exec web cat /etc/hosts   # Check local resolution

# Check if using default bridge (no DNS)
docker inspect web | grep NetworkMode
```

**Note:** Default bridge network (`docker run` without `--network`) does NOT provide automatic DNS. Use user-defined bridge networks or Compose.

**Fix:**
```console
# Create user-defined bridge (has DNS)
docker network create mynet
docker run -d --name web --network mynet nginx
docker run -d --name db --network mynet postgres
# web can now resolve "db"
```

## Port Mapping Not Working

**Diagnose:**
```console
# Check port mappings
docker ps --format "table {{.Names}}\t{{.Ports}}"
docker port <container>

# Test from host
curl localhost:8080
```

**Common causes:**
- Container not listening on `0.0.0.0` (only `127.0.0.1`).
- Firewall blocking the port.
- Port already in use.

**Fix:**
```dockerfile
# Ensure application listens on all interfaces
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
```

## Reference

- [Docker networking troubleshooting](https://docs.docker.com/network/)
- [Container networking](https://docs.docker.com/engine/network/)
