---
name: docker-compose-best-practices
description: Docker Compose patterns for multi-container applications. Covers compose.yaml structure, networking, environment variables, secrets, profiles, healthchecks, startup ordering, Compose Watch, multi-file merging, extends, and production deployment. Use when defining or modifying docker-compose services.
---

# Docker Compose Best Practices Workflow

Use this skill as an instruction set when working with Docker Compose configurations.

## Core Principles
- **Declarative over imperative:** define your stack in `compose.yaml`, don't script `docker run` commands.
- **Service names = hostnames:** containers discover each other via service names on the default network.
- **Keep secrets out of files:** use `secrets` top-level element, not plaintext in `environment`.
- **Health checks are mandatory:** use `healthcheck` + `depends_on` with `condition: service_healthy` for production services.
- **Separate dev from prod:** use multiple compose files to override settings per environment.

## 1) Compose file structure (required)

### 1.1 Must-read core references

- `reference/compose-file-structure.md`
- `reference/networking-in-compose.md`
- `reference/environment-variables.md`
- `reference/secrets-management.md`

### 1.2 Standard compose.yaml template

```yaml
name: myapp

services:
  web:
    build: .
    ports:
      - "8080:80"
    depends_on:
      db:
        condition: service_healthy
        restart: true
    environment:
      - DB_HOST=db
    env_file: .env
    restart: always

  db:
    image: postgres:18-alpine
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password

volumes:
  db_data:

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

## 2) Networking

- Must-read: [networking-in-compose](reference/networking-in-compose.md)
- Default: Compose creates `<project>_default` bridge network, service names resolve automatically.
- Custom networks: Create multiple networks for security isolation (frontend/backend split).
- External networks: Use `external: true` to join pre-existing networks for cross-project communication.
- Container ports vs host ports: Inter-service communication uses container ports, external access uses host ports.

## 3) Environment Variables

- Must-read: [environment-variables](reference/environment-variables.md)
- Three ways: `environment` directive, `env_file`, or interpolation `${VAR}`.
- Priority (high to low): CLI `-e` > interpolation > hardcoded `environment` > `env_file` > Dockerfile ENV.
- Use `${VAR:-default}` for optional values, `${VAR:?error}` for required values.

## 4) Secrets & Security

- Must-read: [secrets-management](reference/secrets-management.md)
- Secrets are mounted as files at `/run/secrets/<name>`, not as environment variables.
- Use `POSTGRES_PASSWORD_FILE` instead of `POSTGRES_PASSWORD` for official images.
- Never commit secret files to version control.
- Avoid `privileged: true` and `network_mode: host` unless absolutely necessary.

## 5) Health Checks & Startup Order

```yaml
services:
  web:
    depends_on:
      db:
        condition: service_healthy   # Wait for healthy, not just started
      redis:
        condition: service_started   # Just wait for start (no healthcheck)

  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mydb"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s    # Grace period before first check
```

## 6) Environment-specific Configuration

Use multiple compose files for dev/prod separation:

```yaml
# compose.yaml (base)
services:
  web:
    build: .
    ports: ["8080:80"]

# compose.prod.yaml (production overrides)
services:
  web:
    restart: always
    ports: ["80:80"]          # Override port
    volumes: []               # Clear dev mounts
```

```console
# Dev
docker compose up -d

# Production
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

## 7) Optional features

- **Profiles**: Activate optional services per environment → [profiles](reference/compose-profiles.md)
- **Compose Watch**: Auto-sync/reload during development → [compose-watch](reference/compose-watch.md)
- **Multi-file merging**: Extend/override configurations → [multi-file-compose](reference/multi-file-compose.md)
- **GPU support**: Configure NVIDIA GPU access → [gpu-support](reference/gpu-support.md)

## 8) Final self-check

- [ ] All services defined in `compose.yaml`.
- [ ] Health checks configured for stateful services (databases, queues).
- [ ] `depends_on` uses `condition: service_healthy` for dependencies.
- [ ] Secrets use `secrets` directive, not plaintext `environment`.
- [ ] Non-root users configured where possible.
- [ ] Production overrides in separate compose file (no source code mounts).
- [ ] `.env` and secrets files in `.gitignore`.
- [ ] Service names used for inter-service communication (no hardcoded IPs).
- [ ] `docker compose config` validates without errors.
