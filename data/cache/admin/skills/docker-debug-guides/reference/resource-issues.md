---
title: Resource Issues
impact: HIGH
impactDescription: Unconstrained resource usage causes OOM kills, CPU starvation, and disk exhaustion that bring down services.
type: gotcha
tags: [docker, resources, memory, cpu, disk, debugging]
---

# Resource Issues

**Impact: HIGH** - Without resource limits, one container can consume all host resources.

## Container Killed by OOM

**Symptom:** Container exits with code 137, or `dmesg` shows OOM killer.

**Diagnose:**
```console
# Check exit code
docker ps -a | grep <container>  # "Exited (137)"

# Check OOM events
docker inspect <container> | jq '.[0].State.OOMKilled'

# Check system OOM events
dmesg | grep -i oom
```

**Fix:**
```console
# Increase memory limit
docker run -d --memory="512m" --memory-swap="1g" my-app

# Monitor usage pattern first
docker stats <container>
```

## High CPU Usage

**Diagnose:**
```console
# Real-time stats
docker stats

# Check running processes
docker top <container>

# Enter container to inspect
docker exec -it <container> sh
# Inside: top, htop, ps aux
```

**Fix:**
```console
# Limit CPU usage
docker run -d --cpus="1.5" my-app

# Or relative shares
docker run -d --cpu-shares=512 my-app
```

## Disk Full

**Diagnose:**
```console
# Check overall Docker disk usage
docker system df

# Detailed breakdown
docker system df -v

# Check host disk
df -h
```

**Common disk consumers:**
- Container logs (no rotation configured)
- Old images (not pruned)
- Build cache
- Unused volumes

**Fix:**
```console
# Clean up in stages
docker container prune   # Remove stopped containers
docker image prune -a    # Remove unused images
docker volume prune      # Remove unused volumes
docker builder prune     # Remove build cache
docker system prune -a   # Aggressive cleanup

# Configure log rotation to prevent future issues
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## Reference

- [Runtime constraints](https://docs.docker.com/config/containers/resource_constraints/)
- [Prune unused Docker objects](https://docs.docker.com/config/pruning/)
