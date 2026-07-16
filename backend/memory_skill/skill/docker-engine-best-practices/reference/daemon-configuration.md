---
title: Daemon Configuration
impact: HIGH
impactDescription: Docker daemon configuration controls fundamental behavior including networking, logging, storage, and security. Misconfiguration can cause service failures.
type: best-practice
tags: [docker, daemon, dockerd, configuration, daemon.json]
---

# Docker Daemon Configuration

**Impact: HIGH** - The daemon configuration file (`daemon.json`) controls Docker Engine's core behavior on the host system.

## Configuration File

Location: `/etc/docker/daemon.json` (Linux) or Docker Desktop Settings (Windows/Mac)

## Task Checklist

- [ ] Configure log rotation to prevent disk exhaustion.
- [ ] Set appropriate storage driver (overlay2 recommended).
- [ ] Configure registry mirrors for faster pulls.
- [ ] Enable live restore for zero-downtime daemon updates.
- [ ] Set data-root if custom storage location needed.
- [ ] Configure proxy settings if behind corporate firewall.

## Recommended Configuration

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "registry-mirrors": [
    "https://mirror.example.com"
  ],
  "data-root": "/var/lib/docker",
  "dns": ["8.8.8.8", "1.1.1.1"],
  "icc": true,
  "iptables": true,
  "ip-forward": true
}
```

## Key Settings Explained

| Setting | Purpose | Default |
|---------|---------|---------|
| `log-driver` | Default logging driver | `json-file` |
| `log-opts.max-size` | Max log file size before rotation | Unlimited |
| `log-opts.max-file` | Number of rotated log files to keep | Unlimited |
| `storage-driver` | Storage backend | `overlay2` |
| `live-restore` | Keep containers alive during daemon restart | `false` |
| `registry-mirrors` | Mirror registries (e.g., for China) | None |
| `data-root` | Docker data directory | `/var/lib/docker` |
| `icc` | Inter-container communication | `true` |

## Proxy Configuration

```json
{
  "proxies": {
    "http-proxy": "http://proxy.example.com:8080",
    "https-proxy": "http://proxy.example.com:8080",
    "no-proxy": "localhost,127.0.0.1,.local"
  }
}
```

## Apply Configuration

```console
# Validate configuration
dockerd --validate

# Restart daemon to apply changes
sudo systemctl restart docker

# Verify settings took effect
docker info | grep -A5 "Logging Driver"
```

## Reference

- [Docker daemon configuration](https://docs.docker.com/engine/daemon/)
- [Configure logging drivers](https://docs.docker.com/config/containers/logging/configure/)
