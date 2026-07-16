---
title: Secrets Management in Compose
impact: HIGH
impactDescription: Hardcoding passwords in environment variables or compose files is a security vulnerability. Secrets provide secure credential management.
type: best-practice
tags: [docker, docker-compose, secrets, security, credentials]
---

# Secrets Management in Compose

**Impact: HIGH** - Never put passwords, API keys, or certificates in plaintext compose files or environment variables.

Secrets are mounted as files at `/run/secrets/<name>` inside containers. They are not exposed as environment variables and cannot be read from `docker compose config` output.

## Task Checklist

- [ ] Use `secrets` top-level element for all sensitive data.
- [ ] Use `*_FILE` variants for database passwords (e.g., `POSTGRES_PASSWORD_FILE`).
- [ ] Add secret files to `.gitignore`.
- [ ] Never use `environment` for passwords.
- [ ] Use environment variables with low priority for non-sensitive config only.

## Correct Pattern

```yaml
services:
  db:
    image: postgres:18
    secrets:
      - db_password
    environment:
      # Official images support *_FILE variants
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

```plaintext
# ./secrets/db_password.txt
MySecretPassword123!
```

```plaintext
# .gitignore
secrets/
```

## Incorrect Pattern

```yaml
# ❌ Password in plaintext environment variable
services:
  db:
    image: postgres:18
    environment:
      POSTGRES_PASSWORD: MySecretPassword123!   # Visible in docker inspect
```

## Secret Lifecycle

- **Creation**: File content is read at `docker compose up` time.
- **Mounting**: Mounted read-only at `/run/secrets/<name>`.
- **Access**: Application reads the file at the mounted path.
- **Cleanup**: Secrets are removed when containers stop (tmpfs).

## Docker Compose Healthcheck Warning

Avoid leaking secrets via healthchecks:

```yaml
# ❌ Secret visible in process list
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-p${MYSQL_ROOT_PASSWORD}"]

# ✅ Use *_FILE variant or socket auth
healthcheck:
  test: ["CMD-SHELL", "mysqladmin ping --socket=/run/mysqld/mysqld.sock"]
```

## Reference

- [Compose secrets](https://docs.docker.com/compose/how-tos/secrets/)
- [Docker secrets](https://docs.docker.com/engine/swarm/secrets/)
