---
name: docker-desktop-best-practices
description: Docker Desktop configuration, settings, GUI management, Kubernetes integration, GPU support, networking features, and resource management. Use for Docker Desktop setup, settings changes, or exploring Docker Desktop features.
license: MIT
metadata:
  author: github.com/docker-ai
  version: "1.0.0"
---

# Docker Desktop Best Practices

Use this skill for Docker Desktop-specific configuration and feature usage.

## Core Features
- **GUI Dashboard**: Manage containers, images, volumes, and builds visually.
- **Settings Management**: Configure resources, networking, Kubernetes, and proxies.
- **Kubernetes Integration**: Run a local Kubernetes cluster for development.
- **GPU Support**: Pass-through GPU for ML/AI containers.
- **Extensions**: Browse and install extensions from the marketplace.
- **Resource Saver**: Auto-pause when idle to save resources.

## 1) Settings Configuration (required)

### Must-read reference
- `reference/settings-configuration.md`

### Key Settings Areas

| Setting | Purpose | Recommendation |
|---------|---------|---------------|
| **General** | Start behavior, updates | Start on login, auto-update |
| **Resources** | CPU, Memory, Disk, Swap | Adjust based on workload |
| **Docker Engine** | daemon.json config | Add log rotation, mirrors |
| **Kubernetes** | Enable k8s cluster | Enable for k8s dev |
| **Network** | Proxy, DNS | Corporate proxy settings |
| **File Sharing** | Shared directories | Add project directories |

## 2) GUI Management

### Container Management
- **Containers tab**: Start/stop/restart/delete, view logs, inspect, exec shell.
- **Container details**: Environment variables, port mappings, volumes, network settings.

### Image Management
- **Images tab**: Pull, build, push, scan for vulnerabilities.
- **Image details**: Layers, size, tags, usage.

### Volume Management
- **Volumes tab**: Create, delete, export, clone volumes.
- **Volume details**: Browse contents, see which containers use it.

### Build Monitoring
- **Builds tab**: Active build progress, build history, cache stats.

## 3) Kubernetes Integration

Enable from Settings → Kubernetes → Enable Kubernetes.

```console
# Switch context to Docker Desktop's k8s
kubectl config use-context docker-desktop

# Deploy an application
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=NodePort

# View in Docker Desktop
# Containers tab → Kubernetes section
```

## 4) GPU Support (NVIDIA)

Prerequisites:
- NVIDIA drivers installed on host.
- WSL2 backend (Windows) or native Linux.

Enable from Settings → Resources → Advanced → Enable GPU.

```console
# Verify GPU access
docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu22.04 nvidia-smi
```

### Compose Configuration

```yaml
services:
  trainer:
    image: nvidia/cuda:12.9.0-base-ubuntu22.04
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## 5) Extensions

### Marketplace Extensions

1. Open Docker Desktop → Extensions.
2. Browse marketplace.
3. Click Install on desired extension.

### Private Marketplace

For enterprise environments:

```console
# Configure private marketplace
docker extension marketplace configure \
  --marketplace-url https://your-company.com/extensions
```

## 6) Resource Saver

Docker Desktop can auto-pause when idle to save CPU/memory:

**Settings → Resources → Advanced → Resource Saver: ON**

## 7) Networking Features

### VPN/Proxy Compatible
- Docker Desktop automatically routes traffic through host's VPN.
- Configure proxy in Settings → Resources → Proxies if needed.

### Host Network Access
```console
# Access host services from container
# Linux: use --add-host
docker run --add-host host.docker.internal:host-gateway ...

# Windows/Mac: host.docker.internal is automatically available
curl host.docker.internal:8080   # From inside container
```

## 8) Troubleshooting

### Clean / Purge Data

Settings → Troubleshoot → Clean / Purge data:
- **Clean**: Remove stopped containers, unused images, volumes.
- **Purge**: Reset to factory defaults (removes everything).

### Reset to Factory Defaults

Settings → Troubleshoot → Reset to factory defaults.

**Warning:** This removes all containers, images, volumes, and settings.

## 9) Final self-check

- [ ] Docker Desktop starts automatically (if needed).
- [ ] Resources (CPU/Memory) allocated appropriately for workload.
- [ ] Log rotation configured via Docker Engine settings.
- [ ] Project directories added to File Sharing.
- [ ] GPU enabled if needed for ML/AI workloads.
- [ ] Kubernetes enabled if doing k8s development.
- [ ] Resource Saver configured for power saving.
- [ ] Extensions installed for relevant tooling.
