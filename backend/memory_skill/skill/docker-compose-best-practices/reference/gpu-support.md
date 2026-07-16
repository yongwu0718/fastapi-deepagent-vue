---
title: GPU Support in Compose
impact: MEDIUM
impactDescription: GPU access enables containerized ML/AI workloads. Requires proper driver configuration and device reservation.
type: capability
tags: [docker, docker-compose, gpu, nvidia, cuda]
---

# GPU Support in Compose

**Impact: MEDIUM** - Essential for containerized machine learning, AI training, and GPU-accelerated applications.

## Prerequisites

- NVIDIA GPU with drivers installed on host.
- NVIDIA Container Toolkit (`nvidia-container-toolkit`).
- Docker configured with `nvidia` runtime.

## Correct Pattern

```yaml
services:
  trainer:
    image: nvidia/cuda:12.9.0-base-ubuntu22.04
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1                # Number of GPUs
              # Or specify specific GPUs:
              # device_ids: ['0', '3']
              capabilities: [gpu]
```

```console
# Verify GPU access
docker compose run --rm trainer nvidia-smi
```

## Options

| Option | Values | Description |
|--------|--------|-------------|
| `driver` | `nvidia` | GPU driver |
| `count` | `1`, `all` | Number of GPUs |
| `device_ids` | `['0', '3']` | Specific GPU IDs |
| `capabilities` | `[gpu]`, `[compute, utility]` | GPU capabilities |

## Reference

- [Enable GPU support](https://docs.docker.com/compose/how-tos/gpu-support/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/)
