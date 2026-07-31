---
title: Multi-stage Builds
impact: HIGH
impactDescription: Multi-stage builds dramatically reduce image size and improve security by separating build tools from runtime environments.
type: best-practice
tags: [docker, multi-stage-build, image-size, security, optimization]
---

# Multi-stage Builds

**Impact: HIGH** - Multi-stage builds can reduce image sizes by 50-70% and significantly shrink the attack surface by excluding build tools from production images.

Multi-stage builds use multiple `FROM` statements in a single Dockerfile. Each stage has a specific purpose: the build stage contains compilers and tools, and the runtime stage contains only what's needed to run the application.

## Task Checklist

- [ ] Use at least two stages: one for building, one for running.
- [ ] Name each stage with `AS <stage-name>` for clarity.
- [ ] Use `COPY --from=<stage-name>` to copy artifacts between stages.
- [ ] Use slim/alpine base images for the final (runtime) stage.
- [ ] Verify the final image size reduction compared to single-stage build.

## Correct Pattern

```dockerfile
# Stage 1: Build
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn clean package -DskipTests

# Stage 2: Runtime
FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app
# Copy only the built JAR from the builder stage
COPY --from=builder /app/target/*.jar app.jar
# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

## Incorrect Pattern (Single Stage)

```dockerfile
# ❌ Single stage - build tools and JDK included in final image
FROM maven:3.9-eclipse-temurin-21
WORKDIR /app
COPY . .
RUN mvn clean package
# ❌ Final image includes JDK, Maven, source code - huge and insecure
CMD ["java", "-jar", "target/app.jar"]
```

## Benefits

| Aspect | Single Stage | Multi-stage |
|--------|-------------|-------------|
| Image Size | 800+ MB (with JDK + Maven) | ~200 MB (JRE only) |
| Security | Full JDK + build tools = large attack surface | Minimal runtime only |
| Deploy Speed | Slower push/pull | Faster push/pull |
| Cache Efficiency | Poor (source changes invalidate everything) | Better (build dependencies cached separately) |

## Patterns by Language

### Node.js / JavaScript
```dockerfile
# Build stage
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Runtime stage
FROM node:22-alpine AS runtime
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER node
CMD ["node", "dist/index.js"]
```

### Go
```dockerfile
# Build stage
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o server .

# Runtime stage
FROM alpine:3.19 AS runtime
RUN apk add --no-cache ca-certificates
COPY --from=builder /app/server /server
USER nobody
CMD ["/server"]
```

### Python
```dockerfile
# Build stage
FROM python:3.13-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.13-slim AS runtime
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY src ./src
ENV PATH=/root/.local/bin:$PATH
USER 1000
CMD ["python", "src/main.py"]
```

## Reference

- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Spring Boot Docker guide](https://spring.io/guides/topicals/spring-boot-docker)
