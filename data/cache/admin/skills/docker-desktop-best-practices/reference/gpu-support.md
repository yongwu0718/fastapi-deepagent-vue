---
title: GPU Support in Docker Desktop
impact: MEDIUM
impactDescription: GPU passthrough enables containerized ML/AI workloads on Docker Desktop with near-native performance.
type: capability
tags: [docker, docker-desktop, gpu, nvidia, cuda, ai, ml]
---

# GPU Support in Docker Desktop

**Impact: MEDIUM** - Essential for running ML training, AI inference, or GPU-accelerated compute in containers.

## Prerequisites

- **Windows**: WSL2 backend + NVIDIA drivers with WSL support.
- **macOS**: Limited GPU support (primarily for Metal API via specific tools).
- **Linux**: NVIDIA drivers + NVIDIA Container Toolkit.

## Enabling GPU

1. Settings → Resources → Advanced → **Enable GPU acceleration**
2. Install NVIDIA Container Toolkit if needed:

```console
# Ubuntu/Debian
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

## Verifying GPU Access

```console
# Check if GPU is available
docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu22.04 nvidia-smi
```

Expected output shows GPU details:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 550.xx    Driver Version: 550.xx    CUDA Version: 12.9     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| ...
```

## Specifying GPUs

```console
# All GPUs
docker run --gpus all my-gpu-app

# Specific GPU
docker run --gpus '"device=0"' my-gpu-app

# Multiple specific GPUs
docker run --gpus '"device=0,1"' my-gpu-app
```

## Compose Configuration

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

## Troubleshooting

```console
# Check if nvidia runtime is registered
docker info | grep -i runtime

# Should show: nvidia

# If not, install nvidia-container-toolkit
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## Reference

- [Docker Desktop GPU support](https://docs.docker.com/desktop/gpu/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/)
