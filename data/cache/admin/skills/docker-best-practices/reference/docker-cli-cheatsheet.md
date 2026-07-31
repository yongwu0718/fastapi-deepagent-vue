---
title: Docker CLI Cheatsheet
impact: MEDIUM
impactDescription: Quick reference for the most commonly used Docker CLI commands across image, container, network, and volume management.
type: efficiency
tags: [docker, cli, commands, reference]
---

# Docker CLI Cheatsheet

**Impact: MEDIUM** - Quick command reference for common Docker operations.

## Image Management

```console
# Search Docker Hub for an image
docker search <image-name>

# Pull an image from a registry
docker pull <image-name>:<tag>

# List local images
docker images
docker image ls

# View image layer history
docker image history <image-name>

# Remove an image
docker rmi <image-name>

# Remove unused images
docker image prune
```

## Container Lifecycle

```console
# Run a container (detached, with port mapping)
docker run -d -p 8080:80 --name myapp <image>

# Run interactively with a shell
docker run -it <image> /bin/bash

# Run with environment variables
docker run -d -e VAR=value -e VAR2=value2 <image>

# Run with volume mount
docker run -d -v myvolume:/data <image>

# List running containers
docker ps
docker ps -a          # all containers (including stopped)

# Stop a container
docker stop <container>

# Start a stopped container
docker start <container>

# Restart a container
docker restart <container>

# Remove a container
docker rm <container>
docker rm -f <container>  # force remove (even if running)

# Execute a command in a running container
docker exec -it <container> /bin/bash
docker exec <container> <command>

# View container logs
docker logs <container>
docker logs -f <container>  # follow (tail -f)

# Copy files between host and container
docker cp host/path <container>:/path
docker cp <container>:/path host/path
```

## Building & Publishing

```console
# Build an image
docker build -t <name>:<tag> .
docker build -t <name>:<tag> -f path/to/Dockerfile .

# Build with no cache
docker build --no-cache -t <name>:<tag> .

# Tag an image
docker tag <source-image> <target-name>:<tag>

# Push to registry
docker push <name>:<tag>

# Login to registry
docker login
docker login <registry-url>
```

## Network Management

```console
# List networks
docker network ls

# Create a network
docker network create <name>

# Connect container to network
docker network connect <network> <container>

# Disconnect container from network
docker network disconnect <network> <container>

# Inspect network details
docker network inspect <name>

# Remove a network
docker network rm <name>

# Remove unused networks
docker network prune
```

## Volume Management

```console
# List volumes
docker volume ls

# Create a volume
docker volume create <name>

# Inspect volume details
docker volume inspect <name>

# Remove a volume
docker volume rm <name>

# Remove unused volumes
docker volume prune
```

## System Cleanup

```console
# Show disk usage
docker system df

# Remove all unused data (containers, images, networks, volumes)
docker system prune

# Remove all unused data (including volumes)
docker system prune -a --volumes
```

## Compose Commands

```console
# Start services
docker compose up -d
docker compose up --build    # rebuild images before starting
docker compose up --watch    # with file watching enabled

# Stop services
docker compose down
docker compose down -v       # also remove volumes

# View logs
docker compose logs -f
docker compose logs -f web   # specific service only

# List services
docker compose ps

# Execute command in a service
docker compose exec <service> <command>

# Build images
docker compose build
docker compose build --no-cache

# View resolved configuration
docker compose config
```

## Reference

- [Docker CLI reference](https://docs.docker.com/reference/cli/docker/)
- [Docker Compose CLI reference](https://docs.docker.com/reference/cli/docker/compose/)
