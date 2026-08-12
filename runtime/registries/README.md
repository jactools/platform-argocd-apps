# Registry Runtime Stack

This directory holds the external Docker runtime for the shared `docker-registry` and `pypi-server` services.

The stack is separate from the cluster manifests on purpose: these services are expected to come up first, pass readiness checks, and only then allow ArgoCD bootstrap or application sync.

## Files

- `docker-compose.yml` starts the registry backends and two HTTPS gateways
- `registries.env.example` defines the runtime contract for one environment
- `nginx/docker-registry.conf` terminates HTTPS for the Docker registry on port `5000`
- `nginx/packages.conf` terminates HTTPS for the package index on port `443`

## Endpoint contract

Use one environment-specific env file per runtime host, for example:

- `runtime/registries/registries.dev.env`
- `runtime/registries/registries.test.env`
- `runtime/registries/registries.prod.env`

The expected DNS pattern is:

- Docker registry: `https://docker-registry.<env>.jac.dot:5000`
- Package index: `https://packages.<env>.jac.dot`

For dev, that becomes:

- `https://docker-registry.dev.jac.dot:5000`
- `https://packages.dev.jac.dot`

## Required inputs

The env file must define:

- container images and container names
- bind-mount paths for persistent registry data and package data
- htpasswd file locations for both services
- TLS certificate and key paths for both HTTPS gateways
- published host ports for the HTTPS endpoints

Use absolute paths for bind mounts. That avoids ambiguity when the stack is started from automation.

## Local files that must exist

Before startup, create these files on the runtime host:

- Docker registry htpasswd file at `REGISTRY_AUTH_FILE`
- PyPI htpasswd file at `PYPI_AUTH_FILE`
- Docker registry certificate and key at `REGISTRY_TLS_CERT_FILE` and `REGISTRY_TLS_KEY_FILE`
- Package index certificate and key at `PYPI_TLS_CERT_FILE` and `PYPI_TLS_KEY_FILE`
- Data directories at `REGISTRY_DATA_DIR` and `PYPI_DATA_DIR`

## Startup

Run the stack with an environment-specific env file:

```bash
docker compose \
  --env-file runtime/registries/registries.dev.env \
  -f runtime/registries/docker-compose.yml \
  up -d
```

## Readiness checks

The planned platform startup orchestration should block on these checks:

- Docker registry: `https://docker-registry.<env>.jac.dot:5000/v2/`
- Package index: `https://packages.<env>.jac.dot/simple/`

Expected results:

- Docker registry returns `200` or `401`
- Package index returns `200`

## Shutdown

```bash
docker compose \
  --env-file runtime/registries/registries.dev.env \
  -f runtime/registries/docker-compose.yml \
  down
```

## Notes

- The gateway containers terminate HTTPS so the backend containers stay simple and internal to the compose network.
- The compose stack assumes one environment per host. If multiple environments must share a host, adjust ports, certificate paths, and container names in separate env files.
- This stack is intended to be called by the future `scripts/start_platform_stack.sh` orchestration entrypoint.