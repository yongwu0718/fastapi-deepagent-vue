---
title: Multi-container Applications
impact: HIGH
impactDescription: Managing multiple containers with raw docker commands is error-prone. Docker Compose simplifies multi-container orchestration.
type: best-practice
tags: [docker, docker-compose, multi-container, orchestration, networking]
---

# Multi-container Applications

**Impact: HIGH** - Using `docker run` for each service is unsustainable for any non-trivial application. Docker Compose provides declarative, versioned multi-service management.

## Why Not Raw `docker run`?

- Multiple `docker run` commands with different configurations are error-prone.
- Services depend on each other — manual startup ordering is fragile.
- Each service needs its own network/volume/env-var configuration.
- Scaling individual services requires manual command orchestration.

## Task Checklist

- [ ] Define all services in `compose.yaml`.
- [ ] Use service names (not IPs) for inter-container communication.
- [ ] Create custom networks for service isolation.
- [ ] Use `depends_on` with `condition: service_healthy` for startup ordering.
- [ ] Use named volumes for persistent data.
- [ ] Use `.env` files for environment configuration.

## Correct Pattern (Docker Compose)

```yaml
# compose.yaml
services:
  # Nginx reverse proxy
  nginx:
    build: ./nginx
    ports:
      - "80:80"
    networks:
      - app-net
    depends_on:
      web:
        condition: service_started

  # Node.js web app
  web:
    build: ./web
    networks:
      - app-net
    environment:
      - REDIS_HOST=redis
      - NODE_ENV=production

  # Redis cache
  redis:
    image: redis:alpine
    networks:
      - app-net
    volumes:
      - redis_data:/data

networks:
  app-net:
    driver: bridge

volumes:
  redis_data:
```

```console
# Single command to start everything
docker compose up -d

# View logs for all services
docker compose logs -f

# Scale web service
docker compose up -d --scale web=3

# Stop and clean up
docker compose down
```

## Incorrect Pattern (Raw Commands)

```console
# ❌ Multiple manual commands, easy to get wrong
docker network create app-net
docker run -d --name redis --network app-net redis
docker run -d --name web1 -h web1 --network app-net web
docker run -d --name web2 -h web2 --network app-net web
docker run -d --name nginx --network app-net -p 80:80 nginx
```

## Service Discovery

In Docker Compose, service names act as DNS hostnames:

```javascript
// In web container: connect to redis using service name
const redis = require('redis');
const client = redis.createClient({ url: 'redis://redis:6379' });
```

The service name `redis` resolves to the container's IP automatically. No hardcoded IPs needed.

## Reference

- [Docker Compose overview](https://docs.docker.com/compose/)
- [Multi-container apps guide](https://docs.docker.com/get-started/docker-concepts/running-containers/multi-container-applications/)
