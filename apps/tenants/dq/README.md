# Tenant: dq (dq-made-easy)

Tenant overlay and service mapping for the `dq-made-easy` consumer.

## Namespace convention

| Environment | Namespace | Owner |
|---|---|---|
| dev | `dq-dev` | dq-made-easy |
| test | `dq-test` | dq-made-easy |

## Service mapping

Each row maps a docker-compose service to its Kubernetes representation. The `workload-kind` column determines MaaS registration behaviour: `service` instances register with MaaS on startup, `job` instances do not.

| Service | workload-kind | MaaS register | Description | Image (Dockerfile) |
|---|---|---|---|---|
| `dq-api` | service | true | Main FastAPI backend | `dq-api/Dockerfile.fastapi` |
| `dq-ui` | service | true | React frontend (nginx) | `dq-ui/Dockerfile.frontend` |
| `dq-engine` | service | true | Spark engine + REST API | `dq-engine/Dockerfile.engine` |

### Ephemeral workloads (no MaaS registration)

| Workload | workload-kind | Description |
|---|---|---|
| Spark jobs | job | Ephemeral jobs spawned by `dq-engine` |
| Airflow DAGs | job | Ephemeral jobs managed by platform Airflow |
| DQ profiling workers | job | Ephemeral workers consuming Redis queues |

These ephemeral workloads emit telemetry events (`job.runner.*`) to the observability pipeline but never register with MaaS.

## Ingress hostnames

| Service | dev | test |
|---|---|---|
| dq-api | `dq-api.dev.jac.dot` | `dq-api.jacloud.nl` |
| dq-ui | `dq-ui.dev.jac.dot` | `dq-ui.jacloud.nl` |
| dq-engine | `dq-engine.dev.jac.dot` | `dq-engine.jacloud.nl` |

## MaaS target mapping

For the 16-target model, `dq-made-easy` services run in a single logical target per cluster. The target_id is determined by the environment overlay:

| Environment | target_id | Region | Provider |
|---|---|---|---|
| dev | `DEV-LOCAL` | N/A | Kind (local) |
| test | `TEST-REMOTE` | N/A | Kind (Debian) |

Each running pod registers its instance as:
```
dq-api-DEV-LOCAL-0
dq-ui-DEV-LOCAL-0
dq-engine-DEV-LOCAL-0
```

## Shared platform services

The following services are **platform-managed** and consumed by `dq-made-easy` but **not** owned by the tenant:

| Service | Namespace | Consumed by |
|---|---|---|
| Kong (API Gateway) | `platform-kong` | All tenant services (ingress) |
| Keycloak (SSO) | `platform-keycloak` | dq-api, dq-ui |
| Observability stack | `platform-observability` | All tenant services (telemetry) |
| PostgreSQL | — | Provided by platform or tenant (TBD) |
| Redis | — | Provided by platform or tenant (TBD) |
| Airflow | — | Platform-managed lifecycle, tenant DAGs |
| Kafka | — | Platform-managed, tenant topics |

## Required labels and annotations

All resources in the `dq-dev` and `dq-test` namespaces must carry the shared platform labels and annotations defined in the [Environment and Deployment Contract](../../../../docs/infra/LOCAL_TO_PRODUCTION_HANDBOFF_CONTRACT.md):

### Required labels
```yaml
labels:
  platform.jaccloud.nl/managed-by: argocd
  platform.jaccloud.nl/environment: dev    # or test
  platform.jaccloud.nl/tenant: dq
  platform.jaccloud.nl/service: <service-name>
  platform.jaccloud.nl/version: <semver>
  platform.jaccloud.nl/image-digest: <sha256:...>
```

### Required annotations
```yaml
annotations:
  platform.jaccloud.nl/target-id: DEV-LOCAL    # or TEST-REMOTE
  platform.jaccloud.nl/workload-kind: service   # or job
  platform.jaccloud.nl/maas-register: "true"    # or "false"
  platform.jaccloud.nl/deployed-at-utc: <iso-8601>
```

## Consumer repo expectations

The `dq-made-easy` repository must provide Kubernetes manifests under `k8s/`:

```
dq-made-easy/k8s/
├── base/
│   ├── kustomization.yml
│   ├── dq-api/
│   │   ├── deployment.yml
│   │   ├── service.yml
│   │   ├── ingress.yml
│   │   └── configmap.yml
│   ├── dq-ui/
│   │   ├── deployment.yml
│   │   ├── service.yml
│   │   ├── ingress.yml
│   │   └── configmap.yml
│   └── dq-engine/
│       ├── deployment.yml
│       ├── service.yml
│       ├── ingress.yml
│       └── configmap.yml
├── overlays/
│   ├── dev/
│   │   └── kustomization.yml    # patches hostnames, replicas, resources
│   └── test/
│       └── kustomization.yml    # patches hostnames, replicas, resources
```

The ArgoCD Applications in this tenant overlay reference `{{DQ_MADE_EASY_REPO_URL}}/k8s/overlays/<env>` as their source. Once the consumer repo provides these paths, the ArgoCD sync will deploy the tenant workloads.

## Image contract

Tenant images follow the shared image promotion contract:

| Service | dev registry | test registry |
|---|---|---|
| dq-api | `docker-registry.dev.jac.dot:5000/jacbeekers/dq-api:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/dq-api:0.1.0` |
| dq-ui | `docker-registry.dev.jac.dot:5000/jacbeekers/dq-ui:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/dq-ui:0.1.0` |
| dq-engine | `docker-registry.dev.jac.dot:5000/jacbeekers/dq-engine:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/dq-engine:0.1.0` |

Images are built once and promoted by immutable tag or digest. No per-environment rebuilds.

## Secret references

Tenant services must reference secrets, never embed them. Expected secrets in the tenant namespace:

| Secret name | Type | Contents | Provider |
|---|---|---|---|
| `dq-api-db-credentials` | Opaque | `username`, `password` | Platform or consumer |
| `dq-api-redis-url` | Opaque | `redis_url` | Platform or consumer |
| `dq-api-encryption-key` | Opaque | `encryption_key` | Consumer |
| `dq-api-sso-config` | Opaque | SSO/OIDC settings | Consumer |
| `dq-engine-spark-config` | Opaque | Spark connection settings | Consumer |

## Overlay structure

```
apps/tenants/dq/
├── argocd/                       # ArgoCD Application resources (stays in argocd namespace)
│   ├── dq-api-dev.yml
│   ├── dq-api-test.yml
│   ├── dq-ui-dev.yml
│   ├── dq-ui-test.yml
│   ├── dq-engine-dev.yml
│   └── dq-engine-test.yml
├── base/
│   ├── kustomization.yml         # Shared labels, generic namespace template
│   └── namespace.yml             # Namespace 'dq' (renamed per overlay)
├── overlays/
│   ├── dev/
│   │   └── kustomization.yml     # Patches namespace → dq-dev, adds dev labels
│   └── test/
│       └── kustomization.yml     # Patches namespace → dq-test, adds test labels
└── README.md                     # This file
```

The ArgoCD Application files in `argocd/` are applied directly (not via Kustomize overlays) so they remain in the `argocd` namespace. The `overlays/` directories handle only the tenant namespace resources.
