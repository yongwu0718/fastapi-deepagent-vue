---
title: Container Crash & Exit Issues
impact: HIGH
impactDescription: Containers that crash or exit immediately block application availability. Quick diagnosis is essential.
type: gotcha
tags: [docker, container, crash, exit, debugging]
---

# Container Crash & Exit Issues

**Impact: HIGH** - A crashing container means zero availability. Diagnose and fix quickly.

## Container Exits Immediately

```console
# Check exit code
docker ps -a
# Look at the STATUS column: "Exited (1) 2 minutes ago"

# Exit codes:
# 0   - Normal exit (CMD finished)
# 1   - Application error
# 137 - Killed by SIGKILL (likely OOM)
# 143 - Killed by SIGTERM (graceful shutdown)
```

### Common Causes

1. **No foreground process**: The CMD command exits immediately.

   ```dockerfile
   # ❌ Script exits immediately
   CMD /app/start.sh   # Script might fork and exit

   # ✅ exec to keep foreground process
   CMD ["nginx", "-g", "daemon off;"]
   ```

2. **Application crash**: Check logs for stack traces.

   ```console
   docker logs <container>
   docker logs --tail 100 <container>
   ```

3. **Missing dependencies**: Application cannot find required libraries.

   ```console
   # Enter with override command to debug
   docker run -it --entrypoint sh <image>
   # Now inspect the filesystem
   ```

### Container in Restart Loop

```console
# Quickly check logs of restarting container
docker logs --tail 50 -f <container>

# Check restart policy
docker inspect <container> | grep -A5 RestartPolicy

# Stop the restart loop to debug
docker update --restart=no <container>
docker stop <container>
```

### "Port is already allocated"

```console
# Find what's using the port
docker ps --filter "publish=8080"
lsof -i :8080                 # Linux/Mac
netstat -ano | findstr :8080  # Windows

# Use a different port
docker run -p 8081:80 nginx

# Or remove the conflicting container
docker rm -f <conflicting-container>
```

### OOM (Out of Memory) Killed

Look for exit code 137:

```console
# Check if OOM killed the container
docker inspect <container> | grep -i oom

# Increase memory limit
docker run -d --memory="1g" --memory-swap="1g" my-app
```

## Debug Workflow

```console
# 1. Get container status
docker ps -a | grep <container>

# 2. Get logs (even from exited containers)
docker logs <container>

# 3. Inspect configuration
docker inspect <container> | jq '.[0].State'

# 4. Run with interactive shell to debug
docker run -it --entrypoint sh <image>

# 5. Run with strace for system call tracing
docker run --cap-add=SYS_PTRACE <image> strace -f <command>
```

## Reference

- [docker logs](https://docs.docker.com/reference/cli/docker/container/logs/)
- [docker inspect](https://docs.docker.com/reference/cli/docker/inspect/)
