---
name: docker-debug-guides
description: Docker debugging and troubleshooting for build failures, container crashes, networking issues, permission errors, volume problems, and daemon issues. Use when diagnosing or fixing Docker problems.
---

# Docker Debug Guides

Use this skill to diagnose and fix common Docker issues. Each issue maps to a reference document with diagnostic steps and solutions.

## Build Issues

- Build fails with exit code → See [build-failures](reference/build-failures.md)
- Build is unexpectedly slow → See [build-cache-debug](reference/build-cache-debug.md)
- "COPY failed: file not found" → See [build-failures](reference/build-failures.md)
- "no such file or directory" in Dockerfile → See [build-failures](reference/build-failures.md)

## Container Runtime Issues

- Container exits immediately after start → See [container-crash](reference/container-crash.md)
- Container is stuck in "Created" or "Restarting" → See [container-crash](reference/container-crash.md)
- OOM (Out of Memory) killed → See [resource-issues](reference/resource-issues.md)
- Container is unresponsive / high CPU → See [resource-issues](reference/resource-issues.md)
- "port is already allocated" → See [container-crash](reference/container-crash.md)

## Networking Issues

- Container cannot reach internet → See [networking-issues](reference/networking-issues.md)
- Service cannot connect to another container → See [networking-issues](reference/networking-issues.md)
- DNS resolution fails inside container → See [networking-issues](reference/networking-issues.md)
- Port mapping not working → See [networking-issues](reference/networking-issues.md)

## Volume & Data Issues

- Data lost after container restart → See [volume-issues](reference/volume-issues.md)
- Permission denied on mounted volume → See [permission-errors](reference/permission-errors.md)
- Volume not mounting as expected → See [volume-issues](reference/volume-issues.md)
- Disk space exhausted → See [resource-issues](reference/resource-issues.md)

## Permission Errors

- "Permission denied" inside container → See [permission-errors](reference/permission-errors.md)
- Cannot write to bind-mounted directory → See [permission-errors](reference/permission-errors.md)
- Docker commands require sudo → See [permission-errors](reference/permission-errors.md)

## Daemon & System Issues

- "Cannot connect to Docker daemon" → See [daemon-issues](reference/daemon-issues.md)
- Docker daemon won't start → See [daemon-issues](reference/daemon-issues.md)
- Docker Desktop not starting → See [daemon-issues](reference/daemon-issues.md)
- Image pull is very slow → See [daemon-issues](reference/daemon-issues.md)

## Diagnostic Commands Quick Reference

```console
# Container inspection
docker logs <container>               # View container output
docker logs -f <container>            # Follow logs
docker logs --tail 50 <container>     # Last 50 lines
docker inspect <container>            # Full container details
docker stats <container>              # Real-time resource usage
docker top <container>                # Running processes
docker exec -it <container> sh        # Enter container for debugging

# System information
docker info                           # Daemon configuration
docker system df                      # Disk usage
docker system events                  # Real-time events
docker version                        # Version info

# Network debugging
docker network inspect <network>      # Network details
docker run --rm alpine nslookup <host> # DNS test
docker run --rm alpine ping <host>    # Connectivity test
docker run --rm curlimages/curl <url> # HTTP test

# Volume inspection
docker volume inspect <volume>        # Volume details
docker run --rm -v <volume>:/data alpine ls -la /data  # Browse volume
```

## General Debugging Workflow

1. **Check container status**: `docker ps -a` → Is it running? Exited?
2. **Check logs**: `docker logs <container>` → Any error messages?
3. **Inspect configuration**: `docker inspect <container>` → Correct ports, volumes, env?
4. **Enter container**: `docker exec -it <container> sh` → Inspect from inside.
5. **Check resources**: `docker stats` → CPU/Memory limits reached?
6. **Check networking**: Test DNS and connectivity from another container.
7. **Check volumes**: Verify mounts with `docker inspect` and browse contents.
