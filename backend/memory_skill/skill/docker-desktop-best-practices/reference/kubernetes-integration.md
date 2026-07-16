---
title: Kubernetes Integration in Docker Desktop
impact: MEDIUM
impactDescription: Docker Desktop's built-in Kubernetes enables local k8s development without complex cluster setup.
type: capability
tags: [docker, docker-desktop, kubernetes, k8s, local-cluster]
---

# Kubernetes Integration

**Impact: MEDIUM** - Docker Desktop includes a production-grade Kubernetes distribution for local development and testing.

## Enabling Kubernetes

1. Settings → Kubernetes → **Enable Kubernetes**
2. Click **Apply & Restart**
3. Wait for the Kubernetes cluster to start (status shows "Kubernetes is running")

## Switching Context

```console
# Verify contexts
kubectl config get-contexts

# Switch to Docker Desktop's cluster
kubectl config use-context docker-desktop

# Verify cluster is running
kubectl cluster-info
kubectl get nodes
```

## Deployment Example

```console
# Deploy nginx
kubectl create deployment nginx --image=nginx

# Expose as NodePort service
kubectl expose deployment nginx --port=80 --type=NodePort

# Check service
kubectl get svc nginx

# Access: http://localhost:<node-port>

# Clean up
kubectl delete deployment nginx
kubectl delete svc nginx
```

## Compose to Kubernetes

Convert compose.yaml to k8s manifests:

```console
# Enable Compose Bridge
docker compose bridge convert

# Deploy to Docker Desktop k8s
kubectl apply -k out/overlays/desktop/
```

## Reset Kubernetes Cluster

If the cluster becomes unstable:
1. Settings → Kubernetes → **Reset Kubernetes Cluster**
2. This removes all k8s resources and creates a fresh cluster.

## Reference

- [Docker Desktop Kubernetes](https://docs.docker.com/desktop/kubernetes/)
- [Compose Bridge](https://docs.docker.com/compose/bridge/)
