---
title: Environment Variables in Compose
impact: MEDIUM
impactDescription: Environment variables control runtime behavior. Incorrect configuration leads to hard-to-debug runtime issues.
type: best-practice
tags: [docker, docker-compose, environment-variables, configuration]
---

# Environment Variables in Compose

**Impact: MEDIUM** - Proper environment variable management ensures consistent configuration across environments.

## Priority (High to Low)

```
docker compose run -e VAR=val
  >
environment/env_file with interpolation (${VAR})
  >
environment (hardcoded)
  >
env_file
  >
Dockerfile ENV
```

## Three Ways to Set Variables

### 1. Direct `environment` Directive

```yaml
services:
  app:
    environment:
      - DEBUG=true
      - NODE_ENV=production
```

### 2. `env_file`

```yaml
services:
  app:
    env_file: .env
```

```ini
# .env
DEBUG=true
NODE_ENV=production
API_KEY=abc123
```

### 3. Interpolation (Shell/`.env`)

```yaml
services:
  app:
    environment:
      - TAG=${TAG:-latest}           # Default value if not set
      - DB_PASS=${DB_PASS:?required} # Error if not set
    image: myapp:${TAG:-latest}
```

## Predefined Variables

| Variable | Purpose |
|----------|---------|
| `COMPOSE_PROJECT_NAME` | Project name (container prefix) |
| `COMPOSE_FILE` | Specify compose file(s) |
| `COMPOSE_PROFILES` | Enable specific profiles |

## Best Practices

1. **Use interpolation for deployment-specific values** (image tags, API keys).
2. **Use `env_file` for shared lists** of non-secret variables.
3. **Use `secrets` for passwords**, never hardcode or env_file them.
4. **Provide defaults** with `${VAR:-default}` to avoid startup failures.

## Correct Pattern

```yaml
services:
  app:
    image: myapp:${TAG:-latest}
    environment:
      - NODE_ENV=production
      - API_KEY=${API_KEY}          # Required, from shell
      - LOG_LEVEL=${LOG_LEVEL:-info} # Optional with default
    env_file: .env                   # Non-sensitive defaults
    secrets:
      - db_password                  # Sensitive data

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

## Reference

- [Compose environment variables](https://docs.docker.com/compose/how-tos/environment-variables/)
- [Environment variables precedence](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/)
