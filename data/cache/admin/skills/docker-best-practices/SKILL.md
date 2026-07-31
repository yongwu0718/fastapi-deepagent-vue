---
name: docker-best-practices
description: MUST be used for Docker tasks. Covers Dockerfile best practices, multi-stage builds, image layer optimization, build cache, container data persistence, and multi-container applications. Load for any Docker, Dockerfile, container image building, or docker run/docker build work.
---

# Docker Best Practices Workflow

Use this skill as an instruction set. Follow the workflow in order unless the user explicitly asks for a different order.

## Core Principles
- **One container, one responsibility:** each container should do one thing and do it well.
- **Minimize image size:** use multi-stage builds, slim base images, and clean up build artifacts.
- **Layer efficiently:** order instructions from least to most frequently changing to maximize cache reuse.
- **Run as non-root:** always switch to a non-root user for security.
- **Use .dockerignore:** exclude unnecessary files from the build context.
- **Prefer official images:** use trusted, maintained base images from Docker Hub.

## 1) Confirm project requirements before coding (required)

- Identify the tech stack (Node.js, Python, Java, Go, etc.).
- Determine if it's a single service or multi-container application.
- If multi-container, load `docker-compose-best-practices` skill if available.
- If dealing with networking/storage/daemon config, load `docker-engine-best-practices` skill if available.
- For debugging issues, load `docker-debug-guides` skill if available.

### 1.1 Must-read core references (required)

- Before implementing any Docker task, make sure to read and apply these core references:
  - `reference/writing-dockerfiles.md`
  - `reference/multi-stage-builds.md`
  - `reference/build-cache-optimization.md`
  - `reference/image-layers.md`
- Keep these references in active working context for the entire task.

## 2) Apply essential Docker foundations (required)

### Dockerfile Writing

- Must-read reference from `1.1`: [writing-dockerfiles](reference/writing-dockerfiles.md)
- Start from an appropriate base image (prefer slim/alpine variants).
- Set WORKDIR explicitly and early.
- Copy dependency files first, then install dependencies, then copy source.
- Use ENV for runtime configuration.
- EXPOSE only the needed ports (documentation purpose).
- Use USER to switch from root.
- CMD for default command, ENTRYPOINT for mandatory wrappers.

### Multi-stage Builds

- Must-read reference from `1.1`: [multi-stage-builds](reference/multi-stage-builds.md)
- Use multiple FROM statements to separate build and runtime environments.
- Name each stage with AS for clarity.
- Copy only the final artifacts (not build tools) into the runtime stage.
- For compiled languages: compile in stage 1, copy binary to stage 2.
- For interpreted languages: build/minify in stage 1, copy output to stage 2.

### Layer Optimization & Caching

- Must-read references from `1.1`: [image-layers](reference/image-layers.md) and [build-cache-optimization](reference/build-cache-optimization.md)
- Order Dockerfile instructions: least-changing first, most-changing last.
- Copy dependency manifests (package.json, requirements.txt) before source code.
- Install dependencies in a separate layer before COPY source.
- Use .dockerignore to exclude node_modules, .git, build artifacts.
- One layer invalidated means all subsequent layers must rebuild.

### Container Data Persistence

- Use volumes for data that must survive container lifecycle.
- Use bind mounts for development hot-reload (source code sync).
- Use tmpfs for temporary/sensitive data that shouldn't persist.
- Reference: [container-data-persistence](reference/container-data-persistence.md)

## 3) Advanced patterns when requirements call for them

### Multi-container Applications

- Use Docker Compose instead of multiple `docker run` commands.
- Create custom networks for container-to-container communication.
- Use service names as hostnames for service discovery.
- Reference: [multi-container-apps](reference/multi-container-apps.md)

### Docker CLI Essentials

- Use `docker build -t name:tag .` to build images.
- Use `docker run -d -p host:container --name name image` to run containers.
- Use `docker ps -a`, `docker stop`, `docker rm` for lifecycle management.
- Use `docker images`, `docker rmi`, `docker image prune` for image cleanup.
- Use `docker exec -it container command` to enter running containers.
- Reference: [docker-cli-cheatsheet](reference/docker-cli-cheatsheet.md)

## 4) Dockerfile quality checklist (required)

Before finalizing any Dockerfile:
- [ ] Uses multi-stage builds for production images.
- [ ] Starts from a slim/alpine base image when possible.
- [ ] Dependency installation is cached (COPY manifests before RUN install).
- [ ] Source code COPY is after dependency installation.
- [ ] Runs as non-root user.
- [ ] .dockerignore excludes unnecessary files.
- [ ] Only necessary ports are EXPOSE'd.
- [ ] CMD/ENTRYPOINT uses exec form (JSON array).
- [ ] No sensitive data (secrets, passwords) hardcoded in Dockerfile.
- [ ] Image size is reasonable for the tech stack.
- [ ] WORKDIR is set and consistent.

## 5) Final self-check before finishing

- Dockerfile follows best practices from all must-read references.
- Multi-stage build is used where applicable.
- Layer ordering maximizes cache efficiency.
- Container runs as non-root.
- Data persistence strategy is appropriate (volumes for DB, bind mounts for dev).
- Image size has been verified (`docker images`).
- Build time is optimized through proper caching.
