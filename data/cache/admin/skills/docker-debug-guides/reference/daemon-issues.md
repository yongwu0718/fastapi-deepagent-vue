---
title: Daemon Issues
impact: HIGH
impactDescription: Docker daemon issues block all container operations. Quick diagnosis and recovery is critical.
type: gotcha
tags: [docker, daemon, dockerd, system, debugging]
---

# Daemon Issues

**Impact: HIGH** - When the Docker daemon is down, no container operations work. Diagnose and restart promptly.

## "Cannot connect to Docker daemon"

**Diagnose:**
```console
# Is the daemon running?
sudo systemctl status docker

# Check socket permissions
ls -la /var/run/docker.sock

# Try with sudo (permission issue)
sudo docker ps

# Check Docker Desktop (Windows/Mac)
# Is Docker Desktop running?
```

**Fix:**
```console
# Linux - start daemon
sudo systemctl start docker

# Linux - enable on boot
sudo systemctl enable docker

# Permission fix - add user to docker group
sudo usermod -aG docker $USER
# Log out and back in

# Windows/Mac - start Docker Desktop
```

## Daemon Won't Start

**Diagnose:**
```console
# Check daemon logs
sudo journalctl -u docker -f
# Or
sudo cat /var/log/docker.log

# Validate configuration
dockerd --validate

# Check for conflicting processes
sudo lsof -i :2375   # Default daemon port
```

**Common causes:**
- Invalid `daemon.json` configuration.
- Corrupted storage (overlay2 / data-root issues).
- Port conflict.
- Insufficient disk space.

**Fix:**
```console
# 1. Validate config
dockerd --validate

# 2. Check disk space
df -h /var/lib/docker

# 3. Start with verbose logging
sudo dockerd --debug
```

## Image Pull Is Very Slow

**Diagnose:**
```console
# Check pull speed
time docker pull alpine

# Check configured registry mirrors
docker info | grep -A5 "Registry Mirrors"
```

**Fix:**
```json
// /etc/docker/daemon.json - add mirrors
{
  "registry-mirrors": [
    "https://mirror.example.com"
  ]
}
```

```console
# Restart daemon to apply
sudo systemctl restart docker
```

## Reference

- [Docker daemon troubleshooting](https://docs.docker.com/engine/daemon/troubleshoot/)
- [Logs and troubleshooting](https://docs.docker.com/config/daemon/logs/)
