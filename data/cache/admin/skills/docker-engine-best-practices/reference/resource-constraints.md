---
title: Resource Constraints
impact: HIGH
impactDescription: Containers without resource limits can consume all host resources, causing system instability and noisy-neighbor problems.
type: best-practice
tags: [docker, resource-limits, cpu, memory, performance]
---

# Resource Constraints

**Impact: HIGH** - Always set CPU and memory limits on production containers. A single runaway container can bring down the entire host.

## Task Checklist

- [ ] Set `--memory` limit on every production container.
- [ ] Set `--cpus` limit to prevent CPU exhaustion.
- [ ] Use `--memory-swap` to control swap behavior.
- [ ] Use reservations for soft limits in orchestrated environments.
- [ ] Monitor container resource usage with `docker stats`.

## CPU Constraints

```console
# Limit to 1.5 CPU cores
docker run -d --cpus="1.5" my-app

# CPU shares (relative weight, default 1024)
docker run -d --cpu-shares=512 slow-service
docker run -d --cpu-shares=1024 normal-service

# Pin to specific CPUs
docker run -d --cpuset-cpus="0-3" my-app  # CPUs 0,1,2,3
```

## Memory Constraints

```console
# Hard memory limit
docker run -d --memory="512m" my-app

# Memory + swap limit (swap = memory+swap, so 1g total = 512m ram + 512m swap)
docker run -d --memory="512m" --memory-swap="1g" my-app

# No swap (memory-swap = memory)
docker run -d --memory="512m" --memory-swap="512m" my-app

# Unlimited swap (not recommended)
docker run -d --memory="512m" --memory-swap="-1" my-app
```

## Compose Configuration

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

## Monitoring

```console
# Real-time resource usage for all containers
docker stats

# Resource usage for a specific container
docker stats <container-name>

# Inspect resource configuration
docker inspect <container> | jq '.[0].HostConfig'
```

## Reference

- [Runtime options with memory, CPUs, and GPUs](https://docs.docker.com/config/containers/resource_constraints/)
- [Resource constraints in Compose](https://docs.docker.com/compose/compose-file/deploy/#resources)
