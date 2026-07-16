---
title: Settings Configuration
impact: HIGH
impactDescription: Docker Desktop settings control resource allocation, networking, and overall Docker behavior. Incorrect settings cause performance issues.
type: best-practice
tags: [docker, docker-desktop, settings, configuration]
---

# Settings Configuration

**Impact: HIGH** - Docker Desktop settings directly affect performance, network behavior, and development experience.

## Key Settings

### General

| Setting | Purpose | Recommendation |
|---------|---------|---------------|
| Start Docker Desktop on login | Auto-start | Enable for development machines |
| Send usage statistics | Telemetry | Personal preference |
| Choose container terminal | Shell in containers | Default (integrated terminal) |
| Auto-check updates | Keep up to date | Enable |

### Resources

| Setting | Purpose | Recommendation |
|---------|---------|---------------|
| CPUs | CPU cores available to Docker | 50-75% of host cores |
| Memory | RAM available to Docker | 25-50% of host RAM |
| Swap | Swap memory | 1-2 GB |
| Disk image size | Virtual disk size | 64+ GB for heavy usage |
| Disk image location | Where VM disk is stored | Default or dedicated SSD |

### Docker Engine (daemon.json)

```json
{
  "registry-mirrors": [
    "https://mirror.example.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "experimental": false
}
```

### Kubernetes

- **Enable Kubernetes**: Creates a single-node k8s cluster.
- **Show system containers**: Show k8s infrastructure containers.
- **Reset Kubernetes Cluster**: Clear and recreate cluster.

### Network

- **Network type**: NAT (recommended), Bridge, or Host.
- **DNS server**: Automatic or manual (e.g., `8.8.8.8`).
- **Proxy**: HTTP/HTTPS proxy if behind corporate firewall.

### File Sharing

Add directories that need to be accessible via bind mounts:
- Project source code directories.
- Configuration directories.
- Avoid sharing large directories not used by containers.

## Accessing Settings

1. Open Docker Desktop.
2. Click the gear icon (⚙) in the top-right.
3. Navigate through the settings tabs.

Or edit directly:

```console
# Windows
notepad %APPDATA%\Docker\settings.json

# Mac
open ~/Library/Group\ Containers/group.com.docker/settings.json

# Linux
cat ~/.docker/daemon.json
```

## After Changing Settings

Click **Apply & Restart** to apply changes. Docker Desktop will restart.

## Reference

- [Docker Desktop settings](https://docs.docker.com/desktop/settings/)
